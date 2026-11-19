"""The address rule: one copy for every skill that designs, builds or checks a Flow Tool Kit address.

What the package draws (its address control, flowFormFieldAddress, and the form's section templates):

- An address draws only inside an **address section**: `sectionType__c` addressSection, which a section's own JSON must
  also flag with `isAddressSection` (the form reads the flag as it is; the package computes it only for saved
  components). An Address row among other fields, or in an input section, draws as a plain field: a custom address on
  `Id` shows as a "Record ID" box, a compound field as nothing.
- The section holds one **Address row** (`addressFieldType__c` Address: the compound field, or `Id` for an address kept
  in separate fields) and all five **parts**: Street, City, State, PostalCode and Country, each bound to a field. The
  control shows the address only when every part is bound to a field the person can see; a part left out (most often
  Country) leaves one blank box, with no search and no parts. Form Builder's own New Address section always makes the
  row and the five parts.
- The **row decides what is required**. The control marks the whole address required (every part, Country included)
  when the row's `required__c` is true, the form requires every field, or a part's field is required in Salesforce
  itself; it never reads a part's own `required__c`. So a part the plan requires shows as optional under an optional
  row, and the row and its parts must agree: the row is required exactly when a part is (`required_problems`).

Plans write a part as `control: Address` with `variant` Street, City, State, PostalCode or Country, and the row with
`variant: Address`. Component JSON writes `addressFieldType__c`. Each function takes `variant_of`, which reads one field's
kind either way (`plan_variant`, `json_variant`). Python 3 standard library only.
"""
from __future__ import annotations

import re

PARTS = ("Street", "City", "State", "PostalCode", "Country")
ORDER = ("Address",) + PARTS
# The part names the design system's Address component shows
LABELS = {"Street": "Street", "City": "City", "State": "State/Province", "PostalCode": "Zip/Postal Code", "Country": "Country"}
COMPOUND = re.compile(r"^(Mailing|Other|Billing|Shipping|PersonMailing|PersonOther)?Address$")
SECTION_TYPE = "addressSection"


def plan_variant(field: dict) -> str | None:
    """A plan field's address kind (Address for the row, or a part), None for any other control."""
    return (field.get("variant") or "Address") if field.get("control") == "Address" else None


def json_variant(field: dict) -> str | None:
    """A component JSON field's address kind, whatever its key prefix (FlowToolKit__, *__ or none)."""
    for key, value in field.items():
        if key.endswith("addressFieldType__c") and value:
            return value
    return None


def json_name(field: dict) -> str:
    for key, value in field.items():
        if key.endswith("fieldName__c") and value:
            return str(value)
    return ""


def compound_parts(name: str | None) -> dict | None:
    """The part fields of a standard compound address field, the way Form Builder's New Address section binds them
    (MailingAddress: MailingStreet, MailingCity, MailingState, MailingPostalCode, MailingCountry). None for anything
    else: a custom address on Id names its own part fields."""
    bare = str(name or "").split(".")[-1]
    match = COMPOUND.match(bare)
    if not match:
        return None
    prefix = match.group(1) or ""
    return {part: prefix + part for part in PARTS}


def groups(fields: list, variant_of=plan_variant) -> list[tuple[str, list]]:
    """The fields in runs, in order: ("fields", [...]) and ("address", [...]). An address run starts at an Address row
    (or at a part with no row before it) and takes the parts after it; a second row, or a part it already has, starts
    the next address."""
    runs: list[tuple[str, list]] = []
    for field in fields or []:
        kind = variant_of(field)
        if not kind:
            if runs and runs[-1][0] == "fields":
                runs[-1][1].append(field)
            else:
                runs.append(("fields", [field]))
            continue
        current = runs[-1][1] if runs and runs[-1][0] == "address" else None
        if current is None or kind in {variant_of(f) for f in current}:
            runs.append(("address", [field]))
        else:
            current.append(field)
    return runs


def completed(fields: list) -> tuple[list, list[str]]:
    """The plan fields with the five standard parts added after each lone Address row on a standard compound address
    field (what Form Builder's New Address section binds), and one line per row filled. A custom address, or a row
    that already has a part, is left as it is for problems() to report."""
    out, lines = [], []
    for kind, run in groups(fields):
        out += run
        if kind != "address" or len(run) != 1 or plan_variant(run[0]) != "Address":
            continue
        row = run[0]
        parts = compound_parts(row.get("field"))
        if not parts:
            continue
        for part in PARTS:
            entry = {"label": LABELS[part], "object": row.get("object"), "field": parts[part], "control": "Address", "variant": part,
                     "widths": [12, 12, 12], "required": bool(row.get("required"))}
            for key in ("status", "placement"):
                if row.get(key):
                    entry[key] = row[key]
            out.append({k: v for k, v in entry.items() if v is not None})
        lines.append(f"{row.get('field')}: + {', '.join(parts.values())} (the parts the package draws an address with)")
    return out, lines


def required_of(field: dict) -> bool:
    """Whether one field is marked required: `required` in a plan, `required__c` (any key prefix) in component JSON."""
    return any((key == "required" or key.endswith("required__c")) and value is True for key, value in field.items())


def required_problems(run: list, where: str, variant_of=plan_variant) -> list[str]:
    """Where one address's row and parts disagree on required. The package takes every part's required flag from the
    row (see the module docstring), so a required part under an optional row shows as optional, and an optional part
    under a required row shows as required."""
    row = next((f for f in run if variant_of(f) == "Address"), None)
    parts = [f for f in run if variant_of(f) in PARTS]
    if row is None or not parts:
        return []
    required = [variant_of(f) for f in parts if required_of(f)]
    if required and not required_of(row):
        named = f"{', '.join(required)} part{' is' if len(required) == 1 else 's are'}"
        return [f"{where}: the address's {named} required but its Address row is optional. Flow Tool Kit takes every part's "
                "required flag from the row, so the form would show them all optional: make the row required (the form then "
                "requires every part, Country included), or make the parts optional and confirm that with the person"]
    if required_of(row) and not required:
        return [f"{where}: the Address row is required but none of its parts is. Flow Tool Kit takes every part's required "
                "flag from the row, so the form requires every part: mark the parts required as the form shows them, or make "
                "the row optional"]
    return []


def group_problems(run: list, where: str, variant_of=plan_variant, name_of=None) -> list[str]:
    """What stops the package drawing one address as planned: no row, a part missing or twice, a kind it does not know,
    a row and parts that disagree on required."""
    name_of = name_of or (lambda f: f.get("field") if isinstance(f, dict) else "")
    kinds = [variant_of(f) for f in run]
    problems = []
    unknown = [k for k in kinds if k not in ORDER]
    if unknown:
        problems.append(f"{where}: address part {', '.join(map(repr, unknown))} is not one of {', '.join(ORDER)}")
    twice = sorted({k for k in kinds if k in ORDER and kinds.count(k) > 1})
    if twice:
        problems.append(f"{where}: an address has one of each part; {', '.join(twice)} appears twice")
    row = next((f for f in run if variant_of(f) == "Address"), None)
    if row is None:
        problems.append(f"{where}: the address parts have no Address row (variant Address: the address field, or Id for an address kept in "
                        "separate fields), so the package has nothing to draw")
    missing = [p for p in PARTS if p not in kinds]
    if missing and len(missing) == len(PARTS) and row is not None and compound_parts(name_of(row)):
        parts = compound_parts(name_of(row))
        problems.append(f"{where}: the Address row on {name_of(row)} has no parts, so the package draws no address at all; add the five parts "
                        f"({', '.join(parts.values())}). form-design's draw_plan.py adds them for a standard address field")
    elif missing:
        hint = ""
        street = next((name_of(f) for f in run if variant_of(f) == "Street"), "")
        if "Country" in missing and "Street" in street:
            hint = f" (on this object perhaps {street.replace('Street', 'Country')}; check it is the country beside {street})"
        problems.append(f"{where}: the address has no {', '.join(missing)} part. The package draws an address only with all five parts "
                        f"(Street, City, State, PostalCode, Country), and draws one blank box otherwise: add a part for each{hint}")
    return problems + required_problems(run, where, variant_of)


def section_problems(fields: list, section_type: str | None, where: str, variant_of=plan_variant, name_of=None) -> list[str]:
    """What stops the package drawing the addresses in one inner section: an address outside an address section, a
    field that is not an address part inside one, two addresses in one, and each address's own problems."""
    runs = groups(fields, variant_of)
    addresses = [run for kind, run in runs if kind == "address"]
    if not addresses:
        return []
    if section_type != SECTION_TYPE:
        return [f"{where}: an address is in a {section_type or 'input'} section; the package draws an address only in its own address "
                "section (addressSection), and draws the row as a plain field otherwise"]
    problems = []
    others = [f for kind, run in runs if kind == "fields" for f in run]
    if others:
        problems.append(f"{where}: an address section holds only its address; move the other fields to their own section")
    if len(addresses) > 1:
        problems.append(f"{where}: an address section holds one address; put each in its own section")
    for run in addresses:
        problems += group_problems(run, where, variant_of, name_of)
    return problems
