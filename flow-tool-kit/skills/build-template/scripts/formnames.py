"""Name generated form parts the way the Flow Tool Kit Form Builder names them.

Every part of one form shares the form's tag, so a search of metadata, a deploy tool or the org's Form Components for
the tag finds the form and everything that belongs to it:

    form       <ORG>_<FAMILY><id>_<key>      RCG_VA7k2m_contact        tag = RCG_VA7k2m (one form)
    section    <TAG>_FS<position><index><id> RCG_VA7k2m_FS10bi6g72egm3h0
    field      <TAG>_FF<position><index><id>
    logic      <TAG>_FL<index><id>
    condition  <TAG>_FC<position><index><id>

The tag is the form's API name up to the first underscore at or after the fifth character, as the Form Builder reads
it. Three search levels: RCG_ (the organization), RCG_VA (the family, one template), RCG_VA7k2m (one form). Names are
cut to 40 characters. The Builder's id is time-based; here it is a base-25 hash of the form and the part's place, so a
rebuild keeps the same names while staying unique across forms. A field without its own name breaks the Form
Builder's per-field toolbar, which is keyed by it.
"""
import hashlib
import re

MAX_LENGTH = 40
FORM_ID_LENGTH = 4  # base 25: 390,625 forms per family


def form_tag(form_name: str) -> str:
    cut = form_name.find("_", 5)
    return form_name[:cut] if cut > 0 else form_name[:10]


def check_family(family: str) -> None:
    if form_tag(f"{family}x_y") != f"{family}x":
        raise ValueError(f"family {family!r} must be ORG_FAMILY, with at most four characters before the underscore "
                         "and no second underscore (for example RCG_VA)")


def default_family(org_name: str | None, form_name: str | None) -> str:
    """A family from the organization's and the form's initials: Riverside Community Garden, Volunteer Application -> RCG_VA."""
    def initials(text: str | None, limit: int) -> str:
        words = re.findall(r"[A-Za-z0-9]+", text or "")
        return "".join(w[0] for w in words).upper()[:limit] or "F"
    org = initials(re.sub(r"\(.*?\)", "", org_name or ""), 4)
    form = initials(form_name, 6)
    family = f"{org}_{form}"
    check_family(family)
    return family


def form_name(family: str, key: str, registry: dict) -> str:
    """A form's own name: <ORG>_<FAMILY><id>_<key>, for example RCG_VA7k2m_contact.

    registry is {key: id}, kept in plan["build"]["form_ids"], so a rebuild keeps each form's id and a new form gets an
    id no other form in the family has (a hash alone would collide: about 1.3 expected collisions at 1,000 forms).
    """
    check_family(family)
    if key not in registry:
        taken = set(registry.values())
        salt = 0
        while True:
            candidate = _base25(int(hashlib.sha1(f"{family}:{key}:{salt}".encode()).hexdigest(), 16))[:FORM_ID_LENGTH].rjust(FORM_ID_LENGTH, "0")
            if candidate not in taken:
                break
            salt += 1
        registry[key] = candidate
    slug = re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_")
    return f"{family}{registry[key]}_{slug}"[:MAX_LENGTH].rstrip("_")


def _base25(number: int) -> str:
    digits = "0123456789abcdefghijklmno"
    out = ""
    while number:
        number, rest = divmod(number, 25)
        out = digits[rest] + out
    return out or "0"


def part_name(form: str, kind: str, position: int = 0, index: int = 0) -> str:
    """kind is FS (section), FF (field), FL (logic) or FC (condition)."""
    stem = f"{form_tag(form)}_{kind}{position}{index}" if kind != "FL" else f"{form_tag(form)}_FL{index}"
    digest = int(hashlib.sha1(f"{form}:{kind}:{position}:{index}".encode()).hexdigest(), 16)
    return (stem + _base25(digest))[:MAX_LENGTH]
