"""The template header: the package's Banner header, with each template's own words, image, logo and color.

Flow Tool Kit ships one Banner header, Header (Banner) (`Form_Header_Banner`, Overlay layout), and puts it on every new
Form Template. Its Banner section merges everything from the template, so one header serves every template:

    title     {{Name}}                                   subtitle  {{FlowToolKit__Form_Template_Subtitle__c}}
    tags      {{FlowToolKit__Header_Tags__c}} (pills)    image     {{FlowToolKit__Form_Banner_Image__c}}
    logo      {{FlowToolKit__Logo__c}}: the template's Logo Override, else the org Default Logo (Global Styles tab)
    logoAlt   {{FlowToolKit__Logo_Alt_Text__c}}          fill      the brand color (--ftk-color-primary)

The form-type rules want Compact on a one-page form and Split only when named. The package ships no Compact or Split
header, so the build creates each one once per org as a record component on Form Template, with exactly the packaged
Banner settings and only the layout changed, and reuses it after that. Nothing in a header is specific to one form:
every form-specific value lives on the Form Template.

Colors: the banner fills with the brand color, which the template's Style Overrides (or the org's Form Style defaults)
set. An org that keeps a color per template in its own Form Template text field `Brand_Color__c` gets that field merged
into the Compact and Split headers' Background Color; an empty or non-color value is ignored.

The Logo fields on Form Template (Logo, Logo Override and their alt text) arrived in Flow Tool Kit 5.4. On an earlier
org that can create record components (5.3), the logo goes on the banner itself: the Banner's own logo image setting
(`logoAsset`, with `logoAlt`), in a header named after the logo (HDR_Banner_Compact_<logo>), so every template with that
logo shares it and nothing in it belongs to one form. The packaged Overlay header cannot carry it, so an Overlay form on
such an org gets its own Overlay header the same way.
"""
from __future__ import annotations

import json
import re

import formnames

N = "FlowToolKit__"
STAR = "*__"
SHAPES = ("overlay", "split", "compact")
ALIASES = {"hero": "overlay", "band": "compact"}
PACKAGED = "Form_Header_Banner"  # the package's Header (Banner): Overlay
FAMILY = "HDR_Banner"
FOLDER = "Headers"
BRAND_COLOR_FIELD = "Brand_Color__c"  # the org's own Form Template field, never a package field
PACKAGED_PHOTO = "Background_Forest_Sunbeams"  # the package's banner photo, a public Asset File


def shape_of(banner: dict, pages: int) -> str:
    """The plan's banner.layout (form-design writes it from the form-type rules), else compact for one page, overlay otherwise."""
    named = str(banner.get("shape") or banner.get("layout") or "").lower()
    named = ALIASES.get(named, named)
    if named:
        if named not in SHAPES:
            raise ValueError(f"banner layout {named!r} is not one of {', '.join(SHAPES)}")
        return named
    return "overlay" if pages >= 2 else "compact"


NAME_LIMIT = 40  # a component name must still fit a custom metadata DeveloperName when it is converted later


def component_name(shape: str, logo_asset: str | None = None) -> str:
    """The org's header for a shape: HDR_Banner_Compact, HDR_Banner_Split. The same name for every template. With a logo on
    the banner itself (an org before the Logo fields), the logo's Asset File name is added: HDR_Banner_Compact_Riverside_Logo."""
    if shape not in SHAPES:
        raise ValueError(f"banner layout {shape!r} is not one of {', '.join(SHAPES)}")
    name = f"{FAMILY}_{shape.capitalize()}"
    if logo_asset:
        tag = re.sub(r"[^A-Za-z0-9]+", "_", logo_asset).strip("_")
        name = f"{name}_{tag}"[:NAME_LIMIT].rstrip("_")
    return name


def settings(shape: str, has_logo_fields: bool, brand_color_field: bool, logo: dict | None = None) -> dict:
    """The Banner__c settings: the packaged header's, with the layout changed. Without the Logo fields, `logo`
    ({"asset", "alt"}) goes in the Banner's own logo image setting instead."""
    out = {"layout": shape, "height": "small", "tags": "{{" + N + "Header_Tags__c}}", "title": "<p>{{Name}}</p>",
           "subtitle": "<p>{{" + N + "Form_Template_Subtitle__c}}</p>", "image": "{{" + N + "Form_Banner_Image__c}}"}
    if has_logo_fields:
        out.update(logo="{{" + N + "Logo__c}}", logoAlt="{{" + N + "Logo_Alt_Text__c}}")
    elif logo and logo.get("asset"):
        out["logoAsset"] = logo["asset"]
        if logo.get("alt"):
            out["logoAlt"] = logo["alt"]
    if brand_color_field:
        out["backgroundColor"] = "{{" + BRAND_COLOR_FIELD + "}}"
    return out


def component_json(shape: str, has_logo_fields: bool = True, brand_color_field: bool = False, logo: dict | None = None) -> tuple[str, dict]:
    """A header record component: one Banner section on Form Template, filed under Headers. `logo` only on an org without
    the Logo fields: the logo then sits on this header, named after it."""
    banner_logo = None if has_logo_fields or not (logo or {}).get("asset") else logo
    name = component_name(shape, banner_logo["asset"] if banner_logo else None)
    section = {"QualifiedApiName": formnames.part_name(name, "FS", 1, 0), "Label": f"{shape.capitalize()} banner",
               STAR + "title__c": f"{shape.capitalize()} banner", STAR + "sectionType__c": "bannerSection", "isBannerSection": True,
               STAR + "position__c": 1, STAR + "showHeader__c": False, STAR + "Banner__c": json.dumps(settings(shape, has_logo_fields, brand_color_field, banner_logo)),
               STAR + "widthLarge__c": "12", STAR + "widthMedium__c": "12", STAR + "widthSmall__c": "12", STAR + "fields__r": []}
    root = {"QualifiedApiName": name, "Label": f"Header ({shape.capitalize()} Banner)", STAR + "type__c": "form",
            STAR + "ObjectApiName__c": STAR + "Form_Template__c", STAR + "CategoryTag__c": "Template(s)",
            STAR + "Description__c": (f"Banner header in the {shape.capitalize()} layout, shared by every Form Template that uses it. It shows the "
                                      "template's name, subtitle, Header Tags, banner image and logo ("
                                      + (f"{banner_logo['asset']}, set on this header" if banner_logo else "the template's Logo Override, else the org default logo")
                                      + "), filled with the brand color. Change a form's words on its Form Template, not here.")[:255],
            STAR + "Folder__c": FOLDER, STAR + "Tags__c": "Header, Banner, Shared component",
            STAR + "conditionalLogic__r": [], STAR + "sections__r": [section]}
    return name, root


def _text(markup: str) -> str:
    import html
    import re
    return html.unescape(re.sub(r"<[^>]+>", "", markup)).strip()


def template_fields(banner: dict, template: dict, assets: dict | None) -> dict:
    """What the header shows that lives on the Form Template (unprefixed keys): subtitle, tags and the banner image.

    The title is the template Name. Explicit template keys win. The banner image is the plan's banner asset, or the
    package's photo when the plan has none (the design draws that photo too); `banner.image: false` leaves it empty, so
    the banner fills with the brand color."""
    fields = {}
    subtitle = banner.get("subtitle")
    if subtitle and "Form_Template_Subtitle__c" not in template:
        fields["Form_Template_Subtitle__c"] = _text(subtitle) if subtitle.lstrip().startswith("<") else subtitle
    tags = banner.get("tags")
    if tags and "Header_Tags__c" not in template:
        fields["Header_Tags__c"] = tags if isinstance(tags, str) else "; ".join(tags)
    if "Form_Banner_Image__c" not in template and banner.get("image") is not False:
        asset = (assets or {}).get("banner") or banner.get("imageAsset")
        fields["Form_Banner_Image__c"] = f"/file-asset/{asset}" if asset else f"/file-asset/{N}{PACKAGED_PHOTO}"
    return fields
