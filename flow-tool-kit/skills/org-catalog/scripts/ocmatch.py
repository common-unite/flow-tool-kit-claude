"""Section matching: which existing components and template sections look like a section of a new design.

The measure: the fields two sections share, divided by the larger field set, counted twice.
- "exact": a field counts when object, field and label all agree.
- "fields": labels ignored, so a relabelled field still counts.
A pair is a candidate at 80% on either count, and both numbers are reported so the person sees why.

A generic answer slot on Form Submission (Text Question 1, Yes No Question 3) holds a different question on every form,
so its label stays part of its identity even when labels are ignored.

A design field with no Salesforce field yet (a new field still to create) counts in the larger set and never matches.
Layout and styling are never scored: a design is never changed to force a match.

Nothing here decides. Each candidate says what the component has that the design lacks and the reverse, so the person
can choose reuse, extend or new.
"""
from __future__ import annotations

import re

from ocutil import NS, SUBMISSION, bare, canonical_object, norm_label

THRESHOLD = 0.8
GENERIC_SLOT = re.compile(r"^(?:Text|Long_Text|Number|Yes_No|Boolean|Date|Picklist|Currency)_Question_\d+__c$", re.I)


def field_key(field, twins=None):
    """(object, field) compared without the package prefix, unless the org has a twin pair for that name: then the
    subscriber field and the packaged one stay apart. None for a design field with no Salesforce field yet."""
    name = (field.get("field") or "").replace("*__", NS).strip()
    if not name:
        return None
    obj = canonical_object(field.get("object") or SUBMISSION)
    twin_names = {t.lower() for t in (twins or {}).get(obj, [])}
    short = bare(name)
    key_field = name.lower() if short.lower() in twin_names else short.lower()
    return bare(obj).lower(), key_field


def _keys(fields, twins, with_label):
    keys = []
    for field in fields:
        key = field_key(field, twins)
        label = norm_label(field.get("label"))
        if key is None:
            keys.append(("unplaced", id(field)))  # never equal to anything in the other list
        elif with_label or GENERIC_SLOT.match(bare(field.get("field") or "")):
            keys.append(key + (label,))
        else:
            keys.append(key)
    return keys


def answers(fields):
    """The fields that hold answers: a hidden record Id field is plumbing, not part of a section's design."""
    return [f for f in fields if (f.get("field") or "").strip().lower() != "id"]


def score(a, b, twins=None):
    """(exact, fields) for two field lists: shared fields over the larger set, with labels, then without."""
    a, b = answers(a), answers(b)
    if not a or not b:
        return 0.0, 0.0
    larger = max(len(a), len(b))
    exact = len(set(_keys(a, twins, True)) & set(_keys(b, twins, True))) / larger
    loose = len(set(_keys(a, twins, False)) & set(_keys(b, twins, False))) / larger
    return round(exact, 3), round(loose, 3)


def is_candidate(scores, threshold=THRESHOLD):
    return max(scores) >= threshold


def differences(design, existing, twins=None):
    """What the design adds (extend puts these in a new version of the component) and what the existing component has that the design does not."""
    design, existing = answers(design), answers(existing)
    design_keys = {field_key(f, twins) for f in design} - {None}
    existing_keys = {field_key(f, twins) for f in existing} - {None}
    adds = [f.get("label") or f.get("field") or "?" for f in design if field_key(f, twins) not in existing_keys]
    extra = [f.get("label") or f.get("field") for f in existing if field_key(f, twins) not in design_keys]
    relabelled = []
    by_key = {field_key(f, twins): f for f in existing}
    for f in design:
        other = by_key.get(field_key(f, twins))
        if other and norm_label(other.get("label")) != norm_label(f.get("label")):
            relabelled.append({"field": f.get("field"), "design": f.get("label"), "existing": other.get("label")})
    return {"design_adds": adds, "existing_only": extra, "relabelled": relabelled}


def pct(value):
    return f"{round(value * 100)}%"


# ---- a design against the catalog ------------------------------------------------------------------------------------

def design_sections(design):
    """Sections of a design: form-design's plan.json (pages[].sections[].fields[] with object, field, label), or
    {"sections": [{"id", "title", "object", "fields": [...]}]}. Each comes back as {id, title, page, position, fields}."""
    out = []
    if isinstance(design.get("pages"), list):
        for p, page in enumerate(design["pages"], 1):
            for s, section in enumerate(page.get("sections") or [], 1):
                title = section.get("Header_Title__c") or section.get("title") or section.get("Divider_Title__c") or f"Section {s}"
                fields = [{"object": f.get("object") or section.get("object"), "field": f.get("field"), "label": f.get("label")}
                          for f in section.get("fields") or []]
                out.append({"id": section.get("id") or f"p{p}.s{s}", "title": title, "page": p, "position": s, "fields": fields,
                            "component": section.get("component")})
        return out
    for n, section in enumerate(design.get("sections") or [], 1):
        fields = [{"object": f.get("object") or section.get("object"), "field": f.get("field"), "label": f.get("label")}
                  for f in section.get("fields") or []]
        out.append({"id": section.get("id") or f"s{n}", "title": section.get("title") or f"Section {n}",
                    "page": section.get("page"), "position": section.get("position") or n, "fields": fields,
                    "component": section.get("component")})
    return out


def component_views(component, by_name, depth=0, seen=None):
    """The field lists a component can be compared on: its own fields with the components placed inside it, and,
    when it carries a Form Template Mapping, the Form Submission fields the map writes."""
    seen = set(seen or ()) | {component["name"]}
    fields = list(component.get("fields") or [])
    if depth < 3:
        for use in component.get("uses") or []:
            inner = by_name.get(use["component"])
            if inner and inner["name"] not in seen:
                fields += component_views(inner, by_name, depth + 1, seen)[0][1]
    views = [("own", fields)]
    smap = component.get("submission_map")
    if smap:
        label_of = {f["field"]: f["label"] for f in fields}
        views.append(("mapped", [{"object": SUBMISSION, "field": sub, "label": label_of.get(src, src)} for sub, src in smap["fields"].items()]))
    return views


def where_used(component):
    out = []
    for use in component.get("used_in") or []:
        if not use.get("template_id"):  # a flow, Lightning page, site page or wrapper component
            out.append(f"{use['role']} {use.get('label') or use.get('place')}" + (" (a copy of its JSON)" if use.get("copy") else ""))
            continue
        out.append(f"{use['template']} p{use['page']} '{use['section']}'" + (f" ({use['role']})" if use.get("role") not in (None, "section") else ""))
    for use in component.get("used_by_components") or []:
        out.append(f"inside {use['component']} ({use['via']})")
    return out


def match_design(catalog, design, threshold=THRESHOLD, limit=3):
    """For each design section, the existing components (and repeated template sections) that look like it.
    Never a decision: each section gets candidates, the fit of each, and a question for the person."""
    twins = {obj: info.get("twins") or [] for obj, info in (catalog.get("fields_index") or {}).items()}
    components = catalog.get("components") or []
    by_name = {c["name"]: c for c in components}
    results = []
    sections = design_sections(design)
    for section in sections:
        candidates = []
        for component in components:
            best = None
            for view, fields in component_views(component, by_name):
                scores = score(section["fields"], fields, twins)
                if is_candidate(scores, threshold) and (best is None or (scores[1], scores[0]) > (best[1][1], best[1][0])):
                    best = (view, scores, fields)
            if best is None:
                continue
            view, scores, fields = best
            diff = differences(section["fields"], fields, twins)
            candidates.append({"component": component["name"], "kind": component["kind"], "packaged": component.get("packaged", False),
                               "label": component.get("label"), "object": component["object"], "compared_on": view,
                               "by_field": scores[1], "exact": scores[0],
                               "fit": "covers" if not diff["design_adds"] else "extend",
                               "fields": [f.get("label") for f in answers(fields)], **diff,
                               "lookup_field": (component.get("submission_map") or {}).get("lookup_field"),
                               "templates": component.get("templates", 0), "places": component.get("places") or {},
                               "inside_components": len({u["component"] for u in component.get("used_by_components") or []}),
                               "where_used": where_used(component)})
        candidates.sort(key=lambda c: (c["fit"] != "covers", -c["by_field"], -c["exact"], -c["templates"], c["packaged"], c["component"]))
        similar = []
        for group in catalog.get("repeated_sections") or []:
            scores = score(section["fields"], group["fields"], twins)
            if is_candidate(scores, threshold):
                similar.append({"group": group["id"], "title": group["title"], "templates": group["templates"],
                                "by_field": scores[1], "exact": scores[0],
                                "where": [f"{s['template']} p{s['page']} '{s['section']}'" for s in group["sections"]]})
        also_here = places_in_design(section, sections, twins, threshold)
        shape = recommend_shape(section, candidates[:limit], similar, also_here)
        results.append({"id": section["id"], "title": section["title"], "page": section["page"], "position": section["position"],
                        "fields": len(section["fields"]), "candidates": candidates[:limit], "more": max(0, len(candidates) - limit),
                        "similar_sections": similar, "also_in_design": [o["title"] for o in also_here], "decision": None, "shape": shape,
                        "question": question(section, candidates[:limit], similar, shape)})
    return {"threshold": threshold, "catalog_taken_at": catalog.get("taken_at"), "catalog_status": catalog.get("status"),
            "org": (catalog.get("org") or {}).get("name"), "sections": results}


def places_in_design(section, sections, twins, threshold):
    """The other sections of the same design that ask this block of questions: the plan points them at the same component
    key, or their fields match at the threshold (a section and a Repeater of the same Contact block, say). Reuse known at
    design time."""
    out = []
    for other in sections:
        if other is section:
            continue
        same_key = section.get("component") and other.get("component") == section["component"]
        if same_key or (section["fields"] and other["fields"] and is_candidate(score(section["fields"], other["fields"], twins), threshold)):
            out.append(other)
    return out


SHAPE_WORDS = {"metadata": "a metadata component", "record": "a record component", "json": "JSON on this section"}
SHAPE_NAMES = {"metadata": "metadata", "record": "record", "json": "JSON"}


def shape_use(kind, recommended):
    """How an alternative shape is offered, in a few words."""
    if kind == "metadata":
        return "metadata if you keep forms in source control and want it deployed (or later, through convert-to-metadata once it is final)"
    if kind == "record":
        return ("a record component if you already know another place will use these questions" if recommended == "json"
                else "record to build it straight in the org with no deploy (shared the same way)")
    return "JSON on this section if these questions must stay fixed to it"


def recommend_shape(section, candidates, similar, also_here=()):
    """The shape to recommend if the person extends or builds new, with the reason (the component shapes standard).

    A recommendation only: `answer` starts empty and the person chooses. Reuse keeps the component's own shape. An extended
    component stays in the original's shape. A new section whose reuse is known at design time (the design asks the same
    questions in another section or a Repeater, or the org already has them built in place on other templates) is one
    record component, built now and referenced by every place. Anything else is JSON on the section: the default. Metadata
    is never recommended for new work; it comes later through convert-to-metadata, or when the person asks."""
    top = candidates[0] if candidates else None
    if top and top["fit"] == "extend":
        recommended = top["kind"]
        why = (f"a new version stays in {top['component']}'s shape" + (", so one deployed update still reaches every form that uses it"
               if recommended == "metadata" else ", built in the org with no deploy"))
    elif also_here:
        recommended = "record"
        names = ", ".join(f"'{o['title']}'" for o in also_here[:3])
        why = (f"this design asks the same questions in {names} too, so one record component built now and referenced by "
               "each keeps them in step")
    elif similar:
        recommended = "record"
        why = (f"the same questions already sit on {similar[0]['templates']} templates, so one record component built now can be "
               "referenced by each")
    else:
        recommended = "json"
        why = ("only this section asks these questions; JSON is the simplest and cannot conflict with a shared component, and if "
               "other forms ask them later they can be merged into one shared component then")
    others = [k for k in ("json", "record", "metadata") if k != recommended]
    lead = {"covers": "If you build new", "extend": "If you extend or build new"}.get(top["fit"] if top else None, "Shape")
    text = (f"{lead}: I recommend {SHAPE_WORDS[recommended]} ({why}). "
            f"Or {shape_use(others[0], recommended)}, or {shape_use(others[1], recommended)}. "
            f"{SHAPE_NAMES[recommended].capitalize() if recommended != 'json' else 'JSON'}, {SHAPE_NAMES[others[0]]} or {SHAPE_NAMES[others[1]]}?")
    if top and top["fit"] == "covers":
        text = f"Reuse keeps it {SHAPE_WORDS[top['kind']]}. " + text
    return {"recommended": recommended, "why": why, "question": text, "answer": None}


def question(section, candidates, similar, shape=None):
    """The reuse, extend or new question for one section, naming the component, its fields and where it is used, and the
    shape recommended for an extend or a new build."""
    shape_text = f" {shape['question']}" if shape else ""
    if not candidates:
        if similar:
            group = similar[0]
            return (f"'{section['title']}' is new: no component matches. The same section already sits on {group['templates']} "
                    f"templates ({'; '.join(group['where'][:3])}); build it new here, or make it one shared component?{shape_text}")
        return None
    top = candidates[0]
    used = [f"{top['templates']} template(s)" if top["templates"] else "no template yet"]
    elsewhere = [f"{top['places'][k]} {words}" for k, words in (("flows", "flow(s)"), ("lightning_pages", "Lightning page(s)"),
                 ("site_pages", "site page(s)"), ("wrapper_components", "wrapper component(s)")) if (top.get("places") or {}).get(k)]
    used += elsewhere
    if top["inside_components"]:
        used.append(f"inside {top['inside_components']} other component(s)")
    via = " through its Form Template Mapping" if top["compared_on"] == "mapped" else ""
    whose = "the package's" if top["packaged"] else "your"
    name = top["component"] if top.get("label") in (None, top["component"]) else f"{top['label']} ({top['component']})"
    text = (f"'{section['title']}' matches {whose} {top['kind']} component {name} on {bare(top['object'])}{via} "
            f"({pct(top['by_field'])} by field, {pct(top['exact'])} with labels; used in {', '.join(used)}). ")
    if top["fit"] == "covers":
        extra = f" It also has {', '.join(top['existing_only'][:4])}." if top["existing_only"] else ""
        text += f"It already has every field this section needs.{extra} Reuse it, or build new?"
    else:
        what = "those fields" if len(top["design_adds"]) > 1 else "that field"
        kept = "the original and every place it is used stay as they are" if top["templates"] or top["inside_components"] or elsewhere else "the original stays as it is"
        text += (f"It lacks {', '.join(top['design_adds'][:4])}. Extend it (a new version of {top['component']} with {what}; {kept}), "
                 f"reuse it as is, or build new?")
    if len(candidates) > 1:
        text += " Other matches: " + ", ".join(f"{c['component']} ({pct(c['by_field'])})" for c in candidates[1:]) + "."
    if similar:
        text += f" The same section is also built in place on {similar[0]['templates']} templates."
    return text + shape_text


def match_markdown(result):
    lines = [f"## Reuse check against {result['org'] or 'no org'}", "",
             f"Catalog taken {result['catalog_taken_at']}. A section is a match at {pct(result['threshold'])} of shared fields over the "
             "larger set, with labels or without. Nothing is reused until you choose reuse, extend or new for each line, and the shape (metadata, record or JSON) for anything extended or new.", "",
             "| Section | Best match | By field | With labels | Fit | Used in | Shape if new or extended |", "|---|---|---|---|---|---|---|"]
    for s in result["sections"]:
        top = (s["candidates"] or [None])[0]
        if top:
            lines.append(f"| {s['id']} {s['title']} | {top['component']} ({top['kind']}, {bare(top['object'])}) | {pct(top['by_field'])} | "
                         f"{pct(top['exact'])} | {top['fit']} | {top['templates']} template(s) | {s['shape']['recommended']} (recommended) |")
        else:
            lines.append(f"| {s['id']} {s['title']} | none | | | new | | {s['shape']['recommended']} (recommended) |")
    asks = [s["question"] or f"'{s['title']}' is new: no component matches. {s['shape']['question']}" for s in result["sections"]]
    if asks:
        lines += ["", "### Questions", ""]
        lines += [f"{n}. {q}" for n, q in enumerate(asks, 1)]
    return "\n".join(lines) + "\n"
