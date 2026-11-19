#!/usr/bin/env python3
"""Save a confirmed brand kit to the org, in one step: images as public Asset Files in the Asset Library, the brand's
style values into the org's Form Style defaults (add-only), and brand-kit.json as a private file beside them.

Claude Code (the Salesforce CLI):
    python3 orgsave.py collect --org <org-alias> --out _brand/<slug>/org-state.json
    python3 orgsave.py plan _brand/<slug> --state _brand/<slug>/org-state.json            # what would happen; changes nothing
    python3 orgsave.py apply _brand/<slug> --org <org-alias> [--state ...]                # do it; writes org-save.json

claude.ai chat (a Salesforce connector, no CLI):
    python3 orgsave.py queries                       # the reads to run through the connector, and the state file shape
    python3 orgsave.py plan _brand/<slug> --state org-state.json --inline   # every write as a REST call, file data inline

The rules:
- An image already in the org (same MD5 as an Asset File's checksum) is reused, never loaded twice. A reused file that
  is not public is made public; one outside the Asset Library is filed there.
- A new image is uploaded as a file in the Asset Library with the asset flag on (ContentVersion IsAssetEnabled), then
  its Asset File is renamed, labelled and made public (IsVisibleByExternalUsers). Proven in a scratch org; the Flow Tool
  Kit image picker's own query lists the result.
- Style values go into the org's Form Style defaults only when this kit is the org's default brand (orgDefault), and
  only into blank fields: the same value does nothing, a different value stays and is reported (build-template then puts
  the brand on that template's Style Overrides). The logo goes into Default Logo the same way.
- If the org refuses the setting write or read, nothing is lost: global-styles-import.json is written for Form Builder's
  Global Styles, Import (the org's current values first, because Import replaces every saved org style).
- brand-kit.json is saved last, with the real asset names, as a private file in the Asset Library titled brand-kit
  (or brand-kit-<slug> for a brand that is not the org default). Saving again adds a version to the same file.

Python 3 standard library; the CLI commands call `sf`.
"""
import argparse
import base64
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brandkit  # noqa: E402

API = "v62.0"
LIBRARY_DEVELOPER_NAME = "sfdc_asset_company_assets"
ROLE_WORDS = {"logo": "logo", "logoAlternate": "logo, alternate", "favicon": "favicon", "banner": "banner", "tile": "tile"}

QUERIES = {
    "org": "SELECT Id FROM Organization",
    "library": f"SELECT Id, Name, DeveloperName, RootContentFolderId FROM ContentWorkspace WHERE DeveloperName = '{LIBRARY_DEVELOPER_NAME}' OR Name = 'Asset Library'",
    "assets": "SELECT Id, DeveloperName, MasterLabel, NamespacePrefix, IsVisibleByExternalUsers, ContentDocumentId FROM ContentAsset",
    "checksums": "SELECT ContentDocumentId, Checksum, FileExtension FROM ContentVersion WHERE IsLatest = true AND ContentDocumentId IN (SELECT ContentDocumentId FROM ContentAsset)",
    "libraryDocs": "SELECT ContentDocumentId FROM ContentWorkspaceDoc WHERE ContentWorkspaceId = '<library Id>'",
    "styleRow": "SELECT <every field of the setting> FROM FlowToolKit__Form_Style_Defaults__c WHERE SetupOwnerId = '<org Id>'",
    "brandFiles": "SELECT Id, ContentDocumentId, Title FROM ContentVersion WHERE IsLatest = true AND FileExtension = 'json' AND Title LIKE 'brand-kit%'",
    "folders": "SELECT Id, Name FROM ContentFolder WHERE ParentContentFolderId = '<root folder Id>' (only when the library has a RootContentFolderId)",
}
STATE_SHAPE = {
    "orgId": "00D000000000001AAA", "namespace": "FlowToolKit__",
    "library": {"Id": "058000000000001AAA", "RootContentFolderId": None},
    "assets": [{"Id": "03S000000000001AAA", "DeveloperName": "Riverside_Logo", "NamespacePrefix": None, "IsVisibleByExternalUsers": True,
                "ContentDocumentId": "069000000000001AAA", "Checksum": "<md5>"}],
    "libraryDocs": ["069000000000001AAA"],
    "folders": [{"Id": "07H000000000001AAA", "Name": "Riverside Community Garden"}],
    "styleFields": ["FlowToolKit__Color_Primary__c", "..."],
    "styleRow": {"Id": "a00000000000001AAA", "FlowToolKit__Color_Primary__c": None},
    "brandFiles": [{"Id": "068000000000001AAA", "ContentDocumentId": "069000000000002AAA", "Title": "brand-kit", "content": {"brandName": "..."}}],
}


class OrgError(Exception):
    pass


# ---- the Salesforce CLI ------------------------------------------------------------------------------------------------

def sf(args, org):
    result = subprocess.run(["sf", *args, "--target-org", org, "--json"], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout or "{}", strict=False)
    except json.JSONDecodeError:
        raise OrgError((result.stderr or result.stdout)[:300])
    if data.get("status", 0) != 0:
        raise OrgError(data.get("message") or json.dumps(data)[:300])
    return data.get("result")


def query(soql, org):
    return (sf(["data", "query", "--query", soql], org) or {}).get("records") or []


def rest(method, path, org, body=None, workdir=None):
    """One REST call through `sf api request rest`; the parsed response (or None for an empty one)."""
    args = ["sf", "api", "request", "rest", f"/services/data/{API}{path}", "--method", method, "--target-org", org]
    if body is not None:
        file = pathlib.Path(workdir or ".") / ".orgsave-body.json"
        file.write_text(json.dumps(body), encoding="utf-8")
        args += ["--body", f"@{file}"]
    result = subprocess.run(args, capture_output=True, text=True)
    if body is not None:
        file.unlink(missing_ok=True)
    text = (result.stdout or "").strip()
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0] or [-1])
    parsed = json.loads(text[start:]) if start >= 0 else None
    if result.returncode or (isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) and parsed[0].get("errorCode")):
        raise OrgError(f"{method} {path}: {(json.dumps(parsed) if parsed else result.stderr.strip())[:300]}")
    return parsed


def collect(org):
    """The org state a plan needs, read through the CLI."""
    org_id = query(QUERIES["org"], org)[0]["Id"]
    libraries = query(QUERIES["library"], org)
    library = next((l for l in libraries if l.get("DeveloperName") == LIBRARY_DEVELOPER_NAME), libraries[0] if libraries else None)
    assets = query(QUERIES["assets"], org)
    sums = {r["ContentDocumentId"]: r["Checksum"] for r in query(QUERIES["checksums"], org)} if assets else {}
    for a in assets:
        a["Checksum"] = sums.get(a["ContentDocumentId"])
        a.pop("attributes", None)
    docs = [r["ContentDocumentId"] for r in query(QUERIES["libraryDocs"].replace("<library Id>", library["Id"]), org)] if library else []
    folders = []
    if library and library.get("RootContentFolderId"):
        folders = [{"Id": r["Id"], "Name": r["Name"]} for r in query(QUERIES["folders"].replace("<root folder Id>", library["RootContentFolderId"]), org)]
    state = {"orgId": org_id, "library": {k: library.get(k) for k in ("Id", "Name", "RootContentFolderId")} if library else None,
             "assets": assets, "libraryDocs": docs, "folders": folders, "namespace": None, "styleFields": None, "styleRow": None, "brandFiles": []}
    for namespace in ("FlowToolKit__", ""):
        try:
            described = sf(["sobject", "describe", "--sobject", f"{namespace}Form_Style_Defaults__c"], org)
        except OrgError:
            continue
        fields = [f["name"] for f in described.get("fields", []) if f["name"].endswith("__c")]
        state["namespace"], state["styleFields"] = namespace, fields
        try:
            rows = query(f"SELECT Id, {', '.join(fields)} FROM {namespace}Form_Style_Defaults__c WHERE SetupOwnerId = '{org_id}'", org)
            state["styleRow"] = {k: v for k, v in rows[0].items() if k != "attributes"} if rows else {}
        except OrgError as error:
            state["styleReadError"] = str(error)[:200]
        break
    for row in query(QUERIES["brandFiles"], org):
        row.pop("attributes", None)
        try:
            text = subprocess.run(["sf", "api", "request", "rest", f"/services/data/{API}/sobjects/ContentVersion/{row['Id']}/VersionData",
                                   "--target-org", org], capture_output=True, text=True).stdout
            row["content"] = json.loads(text[text.find("{"):])
        except (ValueError, json.JSONDecodeError):
            row["content"] = None
        state["brandFiles"].append(row)
    return state


# ---- the plan (no org access: tested with invented states) -------------------------------------------------------------

def served_name(asset):
    return f"{asset['NamespacePrefix']}__{asset['DeveloperName']}" if asset.get("NamespacePrefix") else asset["DeveloperName"]


def file_title(kit):
    return "brand-kit" if kit.get("orgDefault", True) else f"brand-kit-{kit.get('slug') or brandkit.slugify(kit['brandName'])}"


def plan(kit, manifest, state):
    """(ops, final kit, report). ops are in the order they must run; the final kit carries the real asset names."""
    kit = json.loads(json.dumps(kit))
    ops, report = [], {"reused": [], "uploaded": [], "styles": {}, "brandFile": None, "problems": [], "notes": []}
    library = state.get("library")
    if not library:
        report["problems"].append("No Asset Library in this org (ContentWorkspace sfdc_asset_company_assets). It comes with Salesforce "
                                  "CMS and Files; open the Files tab, Libraries, and check it exists before saving.")
        return ops, kit, report
    by_sum = {}
    for asset in state.get("assets") or []:
        if asset.get("Checksum"):
            by_sum.setdefault(asset["Checksum"], asset)
    taken = {served_name(a).lower() for a in state.get("assets") or []}
    in_library = set(state.get("libraryDocs") or [])
    names = kit.setdefault("assets", {})
    foldered = []

    def label(role):
        if role.startswith("photos/"):
            return f"{kit['brandName']} photo, {role.split('/', 1)[1].split('_Photo_', 1)[-1].replace('_', ' ')}"
        return f"{kit['brandName']} {ROLE_WORDS.get(role, role)}"

    for role, entry in sorted((manifest or {}).items()):
        if not entry.get("assetName") and not role.startswith("photos/"):
            continue
        existing = by_sum.get(entry.get("md5"))
        if existing:
            name = served_name(existing)
            report["reused"].append({"role": role, "asset": name})
            if not existing.get("NamespacePrefix"):
                foldered.append({"role": role, "contentDocumentId": existing["ContentDocumentId"]})
            if not existing.get("IsVisibleByExternalUsers") and not existing.get("NamespacePrefix"):
                ops.append({"op": "make_public", "role": role, "assetId": existing["Id"], "asset": name})
            if existing["ContentDocumentId"] not in in_library and not existing.get("NamespacePrefix"):
                ops.append({"op": "file_in_library", "role": role, "contentDocumentId": existing["ContentDocumentId"], "asset": name,
                            "libraryId": library["Id"]})
        else:
            base = entry.get("assetName") or brandkit.asset_name(brandkit.short_name(kit["brandName"]), "Photo", role.split("/")[-1])
            name, n = base, 2
            while name.lower() in taken:
                name = f"{base[:76]}_{n}"
                n += 1
            taken.add(name.lower())
            ops.append({"op": "upload_asset", "role": role, "file": "assets/" + entry["file"], "asset": name, "label": label(role)[:255],
                        "libraryId": library["Id"]})
            report["uploaded"].append({"role": role, "asset": name})
            foldered.append({"role": role, "contentDocumentId": None})
        if role.startswith("photos/"):
            photos = names.setdefault("photos", [])
            old = role.split("/", 1)[1]
            names["photos"] = [name if p == old else p for p in photos] if old in photos else photos + [name]
        else:
            names[role] = name

    if foldered and library.get("RootContentFolderId"):
        existing_folder = next((f for f in state.get("folders") or [] if f.get("Name") == kit["brandName"]), None)
        ops.append({"op": "brand_folder", "name": kit["brandName"], "folderId": (existing_folder or {}).get("Id"),
                    "parentId": library["RootContentFolderId"], "files": foldered})
        report["folder"] = kit["brandName"]
    elif foldered:
        report["notes"].append("The Asset Library has no folders yet, so the images are not grouped; the image picker lists them all. "
                               "To group them by brand, create any folder in the Asset Library once (Files, Libraries) and save again.")

    style_ops, styles = style_plan(kit, state)
    ops += style_ops
    report["styles"] = styles
    title = file_title(kit)
    existing_file = next((f for f in state.get("brandFiles") or [] if f.get("Title") == title), None)
    other = (existing_file or {}).get("content") or {}
    if existing_file and other.get("brandName") and other["brandName"] != kit["brandName"] and kit.get("orgDefault", True):
        report["problems"].append(f"The org's default brand file belongs to {other['brandName']}. Ask whether {kit['brandName']} replaces it "
                                  "as the org default, or is saved as another brand (orgDefault false).")
    ops.append({"op": "brand_file", "title": title, "contentDocumentId": (existing_file or {}).get("ContentDocumentId"),
                "libraryId": library["Id"]})
    report["brandFile"] = {"title": title, "newVersion": bool(existing_file)}
    if kit.get("version", 1) > 1 and not existing_file:
        report["notes"].append("This kit has a version above 1 but no saved brand file was found; it is saved as a new file.")
    return ops, kit, report


def style_plan(kit, state):
    """(ops, report) for the add-only write of the brand's style values and logo into the org's Form Style defaults."""
    namespace = state.get("namespace")
    wanted = {}
    if kit.get("orgDefault", True):
        wanted = {brandkit.style_field(t, namespace or ""): v for t, v in brandkit.tokens(kit).items()}
        wanted.update(brandkit.logo_fields(kit, namespace or ""))
    report = {"orgDefault": kit.get("orgDefault", True), "added": [], "same": [], "keptOrgValue": [], "notInThisVersion": [], "fallback": None}
    if not wanted:
        report["note"] = "Not the org's default brand: style values stay with each template (build-template sets them)."
        return [], report
    known = set(state.get("styleFields") or [])
    if namespace is None or not known or state.get("styleRow") is None:
        report["fallback"] = state.get("styleReadError") or "the Form Style defaults could not be read"
        return [{"op": "global_styles_import", "reason": report["fallback"]}], report
    row = state["styleRow"] or {}
    to_add = {}
    for field, value in wanted.items():
        if field not in known:
            report["notInThisVersion"].append(field)
            continue
        current = str(row.get(field) or "").strip()
        if not current:
            to_add[field] = value
            report["added"].append(field)
        elif current.lower() == str(value).strip().lower():
            report["same"].append(field)
        else:
            report["keptOrgValue"].append({"field": field, "org": current, "brand": value})
    if not to_add:
        return [], report
    if row.get("Id"):
        return [{"op": "style_defaults", "method": "PATCH", "id": row["Id"], "fields": to_add, "setting": f"{namespace}Form_Style_Defaults__c"}], report
    return [{"op": "style_defaults", "method": "POST", "fields": {"SetupOwnerId": state["orgId"], **to_add},
             "setting": f"{namespace}Form_Style_Defaults__c"}], report


def rest_calls(op, folder, kit, inline=False):
    """The REST calls one op makes, for a connector to run in order. <...> marks a value from an earlier call's result."""
    data = lambda path: base64.b64encode((folder / path).read_bytes()).decode() if inline else f"<base64 of {path}>"
    if op["op"] == "upload_asset":
        name = pathlib.Path(op["file"]).name
        return [{"method": "POST", "path": "/sobjects/ContentVersion",
                 "body": {"Title": op["asset"], "PathOnClient": name, "VersionData": data(op["file"]), "FirstPublishLocationId": op["libraryId"],
                          "IsAssetEnabled": True}, "result": "the new ContentVersion Id"},
                {"method": "GET", "path": "/sobjects/ContentVersion/<ContentVersion Id>?fields=ContentDocumentId", "result": "ContentDocumentId"},
                {"method": "GET", "path": "/sobjects/ContentDocument/<ContentDocumentId>?fields=ContentAssetId", "result": "ContentAssetId"},
                {"method": "PATCH", "path": "/sobjects/ContentAsset/<ContentAssetId>",
                 "body": {"DeveloperName": op["asset"], "MasterLabel": op["label"], "IsVisibleByExternalUsers": True}}]
    if op["op"] == "make_public":
        return [{"method": "PATCH", "path": f"/sobjects/ContentAsset/{op['assetId']}", "body": {"IsVisibleByExternalUsers": True}}]
    if op["op"] == "file_in_library":
        return [{"method": "POST", "path": "/sobjects/ContentWorkspaceDoc",
                 "body": {"ContentWorkspaceId": op["libraryId"], "ContentDocumentId": op["contentDocumentId"]}}]
    if op["op"] == "style_defaults":
        path = f"/sobjects/{op['setting']}" + (f"/{op['id']}" if op["method"] == "PATCH" else "")
        return [{"method": op["method"], "path": path, "body": op["fields"]}]
    if op["op"] == "brand_file":
        text = json.dumps(kit, indent=1, ensure_ascii=False) + "\n"
        body = {"PathOnClient": "brand-kit.json", "VersionData": base64.b64encode(text.encode()).decode() if inline else "<base64 of brand-kit.json>"}
        if op.get("contentDocumentId"):
            body.update(ContentDocumentId=op["contentDocumentId"], ReasonForChange=f"Brand kit version {kit.get('version')}")
        else:
            body.update(Title=op["title"], FirstPublishLocationId=op["libraryId"])
        return [{"method": "POST", "path": "/sobjects/ContentVersion", "body": body}]
    if op["op"] == "brand_folder":
        calls = [] if op.get("folderId") else [{"method": "POST", "path": "/sobjects/ContentFolder",
                                                 "body": {"Name": op["name"], "ParentContentFolderId": op["parentId"]}, "result": "the folder Id"}]
        for f in op["files"]:
            doc = f["contentDocumentId"] or f"<ContentDocumentId of the {f['role']} upload>"
            calls += [{"method": "GET", "path": f"/query?q=SELECT+Id+FROM+ContentFolderMember+WHERE+ChildRecordId='{doc}'", "result": "the member Id"},
                      {"method": "PATCH", "path": "/sobjects/ContentFolderMember/<member Id>",
                       "body": {"ParentContentFolderId": op.get("folderId") or "<folder Id>"}}]
        return calls
    if op["op"] == "global_styles_import":
        return []
    raise ValueError(f"unknown op {op['op']}")


# ---- apply ----------------------------------------------------------------------------------------------------------------

def current_tokens(state):
    """The org's saved styles as Global Styles JSON (token names), the logo fields left out."""
    namespace, row = state.get("namespace") or "", state.get("styleRow") or {}
    out = {}
    for field, value in row.items():
        if not field.endswith("__c") or value in (None, "") or "Default_Logo" in field:
            continue
        out["--ftk-" + field.removeprefix(namespace).removesuffix("__c").replace("_", "-").lower()] = str(value)
    return out


def write_fallback(folder, kit, state, reason):
    exported = current_tokens(state) if state.get("styleRow") is not None else None
    merged, added, kept = brandkit.global_styles_import(kit, exported)
    path = folder / "global-styles-import.json"
    path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    steps = ("Form Builder, Global Styles tab, Import: paste the file, Preview import, then Save org defaults."
             if exported is not None else
             "The org's current styles could not be read, so this file holds only the brand. In Form Builder, Global Styles, Export "
             "first and save it as exported.json, then run brandkit.py global-styles brand-kit.json --export exported.json --out "
             "global-styles-import.json and paste that file into Import.")
    logo = (kit.get("assets") or {}).get("logo")
    return {"file": str(path), "reason": reason, "added": added, "keptOrgValue": kept,
            "steps": steps + (f" Set the Default Logo to {logo} in the same tab (Logo, Select Image)." if logo else "")}


def file_in_folder(op, documents, org, workdir, report):
    """Put the brand's images in a library folder named for the brand. Best effort: a failure is reported, nothing else stops."""
    try:
        folder_id = op.get("folderId") or rest("POST", "/sobjects/ContentFolder", org, {"Name": op["name"], "ParentContentFolderId": op["parentId"]}, workdir)["id"]
        for f in op["files"]:
            doc = f["contentDocumentId"] or documents.get(f["role"])
            if not doc:
                continue
            members = rest("GET", f"/query?q=SELECT+Id+FROM+ContentFolderMember+WHERE+ChildRecordId='{doc}'", org) or {}
            for member in members.get("records") or []:
                rest("PATCH", f"/sobjects/ContentFolderMember/{member['Id']}", org, {"ParentContentFolderId": folder_id}, workdir)
        return f"brand_folder {op['name']}"
    except (OrgError, KeyError, TypeError) as error:
        report["notes"].append(f"The images were saved but not put in the {op['name']} folder ({str(error)[:160]}). The image picker still lists them.")
        return "brand_folder skipped"


def apply(folder, org, state):
    kit = json.loads((folder / "brand-kit.json").read_text(encoding="utf-8"))
    manifest_path = folder / "assets" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    ops, final, report = plan(kit, manifest, state)
    if report["problems"]:
        return report, 1
    done, documents = [], {}
    for op in ops:
        try:
            if op["op"] == "brand_folder":
                done.append(file_in_folder(op, documents, org, folder, report))
                continue
            if op["op"] == "upload_asset":
                calls = rest_calls(op, folder, final, inline=True)
                created = rest("POST", calls[0]["path"], org, calls[0]["body"], folder)
                version = rest("GET", f"/sobjects/ContentVersion/{created['id']}?fields=ContentDocumentId", org)
                document = rest("GET", f"/sobjects/ContentDocument/{version['ContentDocumentId']}?fields=ContentAssetId", org)
                rest("PATCH", f"/sobjects/ContentAsset/{document['ContentAssetId']}", org, calls[3]["body"], folder)
                documents[op["role"]] = version["ContentDocumentId"]
            elif op["op"] == "global_styles_import":
                report["styles"]["fallback"] = write_fallback(folder, final, state, op["reason"])
            else:
                for call in rest_calls(op, folder, final, inline=True):
                    rest(call["method"], call["path"], org, call.get("body"), folder)
            done.append(op["op"] + (f" {op.get('asset')}" if op.get("asset") else ""))
        except OrgError as error:
            if op["op"] == "style_defaults":
                report["styles"]["added"] = []
                report["styles"]["fallback"] = write_fallback(folder, final, state, str(error))
                continue
            report["problems"].append(f"{op['op']} {op.get('asset') or ''}: {error}")
            report["done"] = done
            return report, 1
    (folder / "brand-kit.json").write_text(json.dumps(final, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    report["done"] = done
    return report, 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("collect")
    p.add_argument("--org", required=True)
    p.add_argument("--out", required=True)
    sub.add_parser("queries")
    p = sub.add_parser("plan")
    p.add_argument("folder")
    p.add_argument("--state", required=True)
    p.add_argument("--inline", action="store_true", help="put each file's base64 data in the calls (for a connector)")
    p = sub.add_parser("apply")
    p.add_argument("folder")
    p.add_argument("--org", required=True)
    p.add_argument("--state", help="an org-state.json from collect (default: read the org now)")
    a = parser.parse_args(argv)
    if a.command == "queries":
        print(json.dumps({"queries": QUERIES, "describe": "the field names of FlowToolKit__Form_Style_Defaults__c (styleFields)",
                          "brandFiles": "for each brand file, its text from /sobjects/ContentVersion/<Id>/VersionData as content",
                          "stateShape": STATE_SHAPE}, indent=1))
        return 0
    if a.command == "collect":
        try:
            state = collect(a.org)
        except OrgError as error:
            print(f"could not read the org: {error}", file=sys.stderr)
            return 1
        pathlib.Path(a.out).write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
        print(f"{a.out}: {len(state['assets'])} asset files, style defaults "
              f"{'readable' if state['styleRow'] is not None else 'not readable'}, {len(state['brandFiles'])} brand files")
        return 0
    folder = pathlib.Path(a.folder)
    if a.command == "plan":
        kit = json.loads((folder / "brand-kit.json").read_text(encoding="utf-8"))
        manifest_path = folder / "assets" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        state = json.loads(pathlib.Path(a.state).read_text(encoding="utf-8"))
        ops, final, report = plan(kit, manifest, state)
        out = {"report": report, "ops": [{**op, "calls": rest_calls(op, folder, final, a.inline)} for op in ops], "finalKit": final}
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 1 if report["problems"] else 0
    try:
        state = json.loads(pathlib.Path(a.state).read_text(encoding="utf-8")) if a.state else collect(a.org)
    except OrgError as error:
        print(f"could not read the org: {error}", file=sys.stderr)
        return 1
    report, code = apply(folder, a.org, state)
    (folder / "org-save.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
