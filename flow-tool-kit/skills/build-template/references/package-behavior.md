# Flow Tool Kit behavior the build works around

What the package does that trips up anyone building templates by script or by hand, and what the build does about it.

| Behavior | What the build does |
|---|---|
| A new template gets a default page, and every new page a default section (package triggers) | Deletes both: the default page has no `ExternalId__c`, and every section is recreated |
| A template saved with no Pre-fill Template (and Skip Prefill off) gets a new one: a Form Submission marked Is Pre-fill Template, auto-named, with no link back to the template. Deleting the template leaves it behind | Reports it (`created.prefill_template`, `prefill_template_id`) and keeps its Id in `build.prefill_template_id`. Deletes it with a new template a failed build removes, and when a rebuild finds its template gone, but only while no template or section names it. A Pre-fill Template the plan names is never touched |
| A section's `ExternalId__c` is overwritten with its own Id on every save, so sections cannot be matched across builds | Deletes and recreates every section on each build; pages are matched by `ExternalId__c` and updated in place |
| `Show_Header__c` on a section defaults to false, which hides a planned title, subtitle and icon | Turns it on whenever a header title is set |
| `Estimated_Time__c` is a number of minutes, not text | form-design writes the counted minutes |
| A form JSON needs the flags the server sets on saved forms (`isInputSection`, `isRichTextSection` with `showRichText`, and the padding classes) | Writes them on every inner section; without them a text block sits 8px left of the fields under it |
| Section Title (`title__c`) is required in Form Builder and shows "Untitled Section" when blank | Every inner section gets a few plain words: the section's title, and `<title>: intro` for its text block |
| A hidden label: `label-hidden` hides it on screen but keeps it for screen readers; `none` removes it entirely | Writes `label-hidden` for a hidden label. Only the consent card writes `none`, because its statement inside the card is the label |
| Help text is capped at 255 characters and shows under a consent card | Writes the consent statement into the card (`Label_Rich_Text__c`) |
| A field's label, help text and placeholder are Text(255); wording past that imports, then breaks the first save in Form Builder | Puts longer wording whole in `customLabelLong__c`, `helpTextLong__c` or `placeholderLong__c` (read first, the short field the fallback) and leaves the short key out |
| Section Tag is a restricted picklist on the Data Conversion Tag(s) value set, unique within a template | Checks each planned tag against the org's values before writing anything |
| A `{{$Label.X}}` token with no Form Label shows as nothing | Checks every token against the org's Form Labels and the plan's `form_labels` before writing anything |
| The Banner reads the template's Logo fields only from 5.4; 5.3's Banner has its own logo image setting | On 5.3 sets the logo on a header named after it (headers-and-brand.md) |
| A section's text block and its fields in one inner section render out of line | Gives the text block its own inner section, ahead of the fields |
| An editable address draws with its label hidden; Flow Tool Kit names it by its address section's header, as Form Builder's New Address section does. The Address row's Custom Label is what screen readers and the "is required" message read | Turns on each address section's header with the planned label as its title (left off when the section's own header already says it), and writes the same label on the Address row |
| An address's parts are all required when its Address row is (or a part's field is required in Salesforce), and all optional otherwise: the address control never reads a part's own Required | Stops a plan whose row and parts disagree on required; the round trip compares the built row with its parts |
| A field without its own name breaks the Form Builder's per-field toolbar | Names every form, section, field and rule with the Form Builder's pattern |
| Package objects and fields carry `FlowToolKit__` in a subscriber org; your own keep their names | Prefixes package names, leaves yours, and checks every object and field against the org; the renderer silently draws nothing for an unknown one |
| A header or footer form built on Form Submission vanishes the first time someone opens the Header/Footer tab | Uses Form Template forms only, and checks a named header's object |
| A record component's sections are referenced as `<name>_v0`; a metadata component by its plain name | Looks each name up in the org and writes the right one, with the record component's Id |
| The form keeps a cache of form designs | After a metadata change, Reset Form Cache in Form Builder before looking |
| A rule on one field inside a component the template only points at cannot be added from the template | Stops: put the rule on the section, or answer form-only |

## Sources and links

- A form opened from a Campaign (`?sourceId=<Campaign Id>`) reads that Campaign as its source. A guest needs Read on Campaign in the guest permission set and a guest sharing rule on Campaign. Giving guests Campaign also exposes Campaign Members under the default "Controlled by Campaign" sharing; check that with sf-guest-audit.
- On a Flow Tool Kit release before the fix, a Campaign whose **Form Prefill Flow** keeps the picklist default "-- None --" makes the form fail with "Flow '-- None --' is not found"; clear the field. Releases with the fix read "-- None --" as blank.
- A mapped URL parameter fills a Time field from the 24-hour clock (`9:30`, `14:05`); `9:30 PM` and `noon` are skipped. A 15-character record Id in a link (what a Lightning email template's lookup merge writes) is turned into its 18-character form for lookup and Id fields and for `sourceId` on the release that adds it; on an older org, put the 18-character Id in the link (CASESAFEID in a formula). Time fields fill from links on Flow Tool Kit 5.3 and later.
