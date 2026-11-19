#!/usr/bin/env python3
"""Outside probe: what an unauthenticated visitor can actually reach on an Experience
Cloud site, from its public URL, as the guest (`aura.token=null`).

This is the opt-in second view of the guest audit. The inside audit reads the org's
setup with your own access; this confirms it from the outside, the way a visitor's
browser would, against a site you name and are allowed to test. Run it only against
a site you own or are engaged to test (a scratch org's own site while building).

What it does, and what it deliberately does not:
- Discovers the site's live Aura context and enumerates the objects the guest can
  query (a dictionary sweep plus any custom object named in the page markup), and
  the field names the guest can read on each.
- READ-ONLY invokes the @AuraEnabled Apex methods the page references, and lists the
  Flows it references (never runs them: flows have side effects).
- Keeps **counts and names only**: how many records the guest can read, the field
  names, and the shape of an Apex result (a list of N, the keys). It never keeps a
  field value, never dumps records, and never downloads a file: an Attachment is
  reported as a count, a parent type and a size from its metadata. No record data is
  written to disk.

Standalone use:
  python3 probe.py <site-landing-url> [--set standard|nonprofit|all] [--objects a,b,c]
      [--max-invoke N] [--workers N] [--out probe.json]

Usually it is run through guest_audit.py (`audit --probe <url>` in Claude Code, or
`probe` then `analyze --probe`), which merges this view with the inside audit.

Python 3 standard library only.
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
DICT_DIR = os.path.join(os.path.dirname(HERE), "objects")
UA = "Mozilla/5.0"
SCALAR = {"String", "Boolean", "Currency", "Date", "DateTime", "Double", "Email", "Int",
          "Percent", "Phone", "Picklist", "MultiPicklist", "TextArea", "Url", "Time",
          "Reference", "ComboBox", "Int64", "Long"}
NOACCESS = re.compile(r"no access|not accessible|not visible|access check|insufficient|"
                      r"unauthor|is not found|does not exist|permission|FieldUndefined", re.I)
EXECUTED = re.compile(r"argument|null|list has no rows|index|system\.|required|de-reference|expects", re.I)


class ProbeError(Exception):
    pass


# ---------------------------------------------------------------- transport

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def http_post_form(url, fields, timeout=45):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def certificate_failed(error):
    """True when a request failed because the site's TLS certificate did not verify.
    The probe always verifies certificates and never offers a way round it."""
    reason = getattr(error, "reason", error)
    return isinstance(reason, ssl.SSLCertVerificationError) or isinstance(error, ssl.SSLCertVerificationError)


def endpoint_for(landing):
    return landing.rstrip("/") + "/sfsites/aura"


def discover_context(landing, fetch=http_get):
    """(aura context, raw page). Raises ProbeError when the URL is not an Aura site."""
    raw = fetch(landing.rstrip("/"))
    body = urllib.parse.unquote(raw)
    fw = re.search(r'"fwuid":"([^"]+)"', body)
    app = re.search(r'"app":"(siteforce:[^"]+)"', body)
    loaded = re.search(r'"(APPLICATION@markup://[^"]+)":"([^"]+)"', body)
    if not (fw and app and loaded):
        raise ProbeError("could not read the Aura context: not an Aura-template site, "
                         "it needs a login, or it is an LWR site (LWR serves no /sfsites/aura). "
                         "The inside audit still covers it.")
    context = {"mode": "PROD", "fwuid": fw.group(1), "app": app.group(1),
               "loaded": {loaded.group(1): loaded.group(2)}, "dn": [], "globals": {}, "uad": False}
    return context, raw


def aura_action(endpoint, context, descriptor, params, post=http_post_form):
    message = {"actions": [{"id": "1;a", "descriptor": descriptor,
                            "callingDescriptor": "UNKNOWN", "params": params}]}
    fields = {"message": json.dumps(message), "aura.context": json.dumps(context),
              "aura.pageURI": "/s", "aura.token": "null"}
    data = json.loads(post(endpoint, fields))
    if data.get("exceptionEvent"):
        raise ProbeError("the site returned an Aura exception: %s" % (data.get("event") or {}).get("descriptor"))
    return (data.get("actions") or [{}])[0]


def graphql(endpoint, context, query, post=http_post_form):
    return aura_action(endpoint, context, "aura://RecordUiController/ACTION$executeGraphQL",
                       {"queryInput": {"operationName": "r", "query": query, "variables": {}}},
                       post=post)


# ---------------------------------------------------------------- object sweep

def load_dictionary(which, page_markup):
    names = set()
    files = []
    if which in ("standard", "all"):
        files.append("standard.txt")
    if which in ("nonprofit", "all"):
        files.append("nonprofit.txt")
    for name in files:
        path = os.path.join(DICT_DIR, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.split("#")[0].strip()
                    if line:
                        names.add(line)
    # Custom objects the site itself names in its markup.
    for token in re.findall(r"\b([A-Za-z0-9]+(?:__[A-Za-z0-9]+)*__c)\b", page_markup or ""):
        names.add(token)
    return sorted(names)


def object_count(endpoint, context, obj, post=http_post_form):
    """totalCount for the object if the guest can query it, else None. Reads no record."""
    query = "query r{uiapi{query{%s(first:1){totalCount}}}}" % obj
    try:
        rv = (graphql(endpoint, context, query, post=post).get("returnValue")) or {}
    except Exception:
        return None
    if rv.get("errors"):
        return None
    try:
        return rv["data"]["uiapi"]["query"][obj].get("totalCount")
    except Exception:
        return None


def object_field_names(endpoint, context, obj, cap=200, post=http_post_form):
    """The scalar field names the guest's object info lists (names only, no values)."""
    try:
        rv = (aura_action(endpoint, context, "aura://RecordUiController/ACTION$getObjectInfo",
                          {"objectApiName": obj}, post=post).get("returnValue")) or {}
    except Exception:
        return []
    fields = rv.get("fields") or {}
    names = [f for f, meta in fields.items()
             if isinstance(meta, dict) and meta.get("dataType") in SCALAR and f != "Id"]
    return sorted(names)[:cap]


def sweep_objects(endpoint, context, candidates, workers=8, post=http_post_form):
    """Which candidate objects the guest can query, with a count and the readable field
    names. No record is read. Returns a list sorted by count, high first."""
    exposed = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(object_count, endpoint, context, obj, post=post): obj for obj in candidates}
        for future in as_completed(futures):
            obj = futures[future]
            count = future.result()
            if count is not None:
                exposed.append({"object": obj, "count": count})
    for item in exposed:
        item["fields"] = object_field_names(endpoint, context, item["object"], post=post)
    exposed.sort(key=lambda e: -(e["count"] or 0))
    return exposed


# ---------------------------------------------------------------- Apex and Flow

def harvest_js(landing, fetch=http_get):
    """The page plus its same-origin script bundles, as one text corpus for reference
    scraping. Reads static markup only, no records."""
    origin = "{u.scheme}://{u.netloc}".format(u=urllib.parse.urlparse(landing))
    raw = fetch(landing.rstrip("/"))
    srcs = set(re.findall(r'<script[^>]+src="([^"]+)"', raw))
    srcs |= set(re.findall(r'["\'](/[^"\']*?/sfsites/l/[^"\']+?\.js)["\']', raw))
    corpus = [urllib.parse.unquote(raw)]
    for src in list(srcs)[:40]:
        url = src if src.startswith("http") else origin + (src if src.startswith("/") else "/" + src)
        try:
            corpus.append(fetch(url))
        except Exception:
            pass
    return "\n".join(corpus)


def parse_apex(corpus):
    refs = set()
    for descriptor, method in re.findall(r"apex://([\w.]+)/ACTION\$(\w+)", corpus):
        parts = descriptor.split(".")
        refs.add((parts[0] if len(parts) == 2 else "", parts[-1], method))
    for path in re.findall(r"@salesforce/apex/([\w.]+)", corpus):
        parts = path.split(".")
        if len(parts) == 3:
            refs.add((parts[0], parts[1], parts[2]))
        elif len(parts) == 2:
            refs.add(("", parts[0], parts[1]))
    return refs


def parse_flows(corpus):
    flows = set()
    for pattern in (r'"flowName"\s*:\s*"([\w:]+)"', r'"flowApiName"\s*:\s*"([\w]+)"',
                    r'flow-api-name="([\w]+)"', r'"apiName"\s*:\s*"([\w]+)"\s*,\s*"type"\s*:\s*"Flow"'):
        flows |= set(re.findall(pattern, corpus))
    return sorted({f.split(":")[-1] for f in flows})


def shape(value):
    """A description of an Apex result's structure, holding no value: 'list of 12, keys a, b'."""
    if isinstance(value, list):
        keys = ", ".join(list(value[0].keys())[:6]) if value and isinstance(value[0], dict) else ""
        return "list of %d%s" % (len(value), (", keys " + keys) if keys else "")
    if isinstance(value, dict):
        return "object, keys " + ", ".join(list(value.keys())[:8])
    if value in (None, "", [], {}):
        return "nothing"
    return type(value).__name__


def invoke_apex(endpoint, context, ref, post=http_post_form):
    """READ-ONLY call with empty params. Returns the verdict and the result's shape,
    never its data. EXPOSED-DATA means it returned records to an anonymous caller;
    EXPOSED-NEEDS-PARAMS means it ran but wants arguments (still callable)."""
    namespace, classname, method = ref
    try:
        action = aura_action(endpoint, context, "aura://ApexActionController/ACTION$execute",
                             {"namespace": namespace, "classname": classname, "method": method,
                              "params": {}, "cacheable": True, "isContinuation": False},
                             post=post)
    except Exception as error:
        return {"ref": list(ref), "verdict": "error", "detail": str(error)[:160]}
    if action.get("state") == "SUCCESS":
        value = action.get("returnValue")
        returned = value not in (None, [], {}, "")
        return {"ref": list(ref), "verdict": "EXPOSED-DATA" if returned else "EXPOSED-EMPTY",
                "detail": shape(value)}
    message = ""
    errors = action.get("error") or []
    if isinstance(errors, list) and errors:
        message = errors[0].get("message", "")
    if NOACCESS.search(message):
        return {"ref": list(ref), "verdict": "no-access", "detail": message[:160]}
    if EXECUTED.search(message):
        return {"ref": list(ref), "verdict": "EXPOSED-NEEDS-PARAMS", "detail": message[:160]}
    return {"ref": list(ref), "verdict": "error", "detail": (message or action.get("state") or "")[:160]}


def probe_apex(endpoint, context, landing, max_invoke=300, workers=6,
               fetch=http_get, post=http_post_form):
    corpus = harvest_js(landing, fetch=fetch)
    refs = sorted(parse_apex(corpus))[:max_invoke]
    flows = parse_flows(corpus)
    results = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(invoke_apex, endpoint, context, ref, post=post) for ref in refs]
        for future in as_completed(futures):
            results.append(future.result())
    rank = {"EXPOSED-DATA": 0, "EXPOSED-NEEDS-PARAMS": 1, "EXPOSED-EMPTY": 2, "no-access": 3, "error": 4}
    results.sort(key=lambda r: rank.get(r["verdict"], 9))
    return {"corpus_kb": len(corpus) // 1024, "refs_found": len(parse_apex(corpus)),
            "apex": results, "flows": flows}


# ---------------------------------------------------------------- one site

ATTACHMENT_OBJECTS = {"Attachment", "ContentVersion", "ContentDocument", "Document"}


def run_probe(landing, which="all", objects=None, max_invoke=300, workers=8,
              skip_apex=False, fetch=http_get, post=http_post_form):
    """Probe one site. Returns a result dict of counts, field names and Apex shapes,
    with no record value anywhere. `fetch` and `post` are injectable for tests."""
    landing = landing.rstrip("/")
    endpoint = endpoint_for(landing)
    host = urllib.parse.urlparse(landing).netloc
    result = {"site": landing, "host": host, "reachable": False}
    try:
        context, page = discover_context(landing, fetch=fetch)
    except ProbeError as error:
        result["note"] = str(error)
        return result
    except Exception as error:
        if certificate_failed(error):
            result["note"] = ("the site's TLS certificate did not verify, so the probe stopped. "
                              "Salesforce sites serve valid certificates: check the URL is the site's own address")
        else:
            result["note"] = "the site could not be reached: %s" % str(error)[:160]
        return result
    result["reachable"] = True
    candidates = [o.strip() for o in objects if o.strip()] if objects else load_dictionary(which, page)
    result["objects_tested"] = len(candidates)
    exposed = sweep_objects(endpoint, context, candidates, workers=workers, post=post)
    for item in exposed:
        obj = item["object"]
        if obj in ATTACHMENT_OBJECTS:
            item["note"] = "file object: a guest that can query it can read file metadata; this probe does not download bodies"
    result["objects"] = exposed
    if not skip_apex:
        result.update(probe_apex(endpoint, context, landing, max_invoke=max_invoke,
                                 workers=workers, fetch=fetch, post=post))
    return result


# ---------------------------------------------------------------- CLI

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("landing", help="the site's public landing URL, e.g. https://<host>/<prefix>/s")
    parser.add_argument("--set", dest="which", default="all", choices=["standard", "nonprofit", "all"])
    parser.add_argument("--objects", help="an explicit comma list of objects, instead of the dictionary")
    parser.add_argument("--max-invoke", type=int, default=300)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--skip-apex", action="store_true")
    parser.add_argument("--out", help="write the probe result here as JSON")
    args = parser.parse_args(argv)
    objects = args.objects.split(",") if args.objects else None
    result = run_probe(args.landing, which=args.which, objects=objects, max_invoke=args.max_invoke,
                       workers=args.workers, skip_apex=args.skip_apex)
    if not result["reachable"]:
        print("probe: %s" % result.get("note"), file=sys.stderr)
    else:
        exposed = result.get("objects", [])
        reachable_apex = [a for a in result.get("apex", []) if a["verdict"].startswith("EXPOSED")]
        print("probe: %d objects the guest can query, %d Apex methods reachable, %d Flows referenced"
              % (len(exposed), len(reachable_apex), len(result.get("flows", []))))
        for item in exposed[:20]:
            print("  %-40s %s records, %d fields" % (item["object"], item["count"], len(item["fields"])))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1)
            f.write("\n")
        print("probe result: %s" % args.out)
    return 0 if result["reachable"] else 1


if __name__ == "__main__":
    sys.exit(main())
