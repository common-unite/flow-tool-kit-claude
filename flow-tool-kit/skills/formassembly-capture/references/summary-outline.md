# Summary outline (one `summary.md` per built form)

Give this file to whoever writes the summaries (you, or each helper agent with its list of form ids and the archive path). The reader is a Salesforce admin rebuilding the form who asks "how did this work before?" and should never need to look up a `tfa_` id.

## Inputs, in reading order

1. `archive/<id>/logic.md`: settings, prefill lookups, calculations, repeating sections, every Salesforce step with its match rule and field sources, show/hide rules.
2. `inventory.csv` (pipe-delimited): responses, status and its basis.
3. `account-map.md`: which forms send people here and what they pass.
4. Only when logic.md is not enough: `form.html`, `connector-*.html`, `settings.json`, `processing.txt`, `notifications.txt` in the same folder.

## The file

```markdown
# <Form name> (<id>)

**Purpose:** 2-3 sentences: who fills it in, why, what it produces in Salesforce. Responses and last use.

## How someone arrives
URL parameters and the record each identifies; which forms send people here (account-map.md); where the person goes after submitting.

## Prefill (form opens)
Bullets: each record found and how; what it fills in. Plain rules, not FormAssembly steps.

## On submit / after submit
Numbered steps in run order. Every formula restated as a plain rule. Call out value conversions: picklist translations, built dates, joined text, fixed record type ids, ids passed between steps.

## Calculations worth keeping
Only the calculations that carry business meaning (fees, totals, who is primary), in plain words.

## Conditional logic worth keeping
Only the show/hide rules with business meaning.

## Payments, notifications, processing
One line each if relevant. A card payment connector: name the processor, nothing more; the rebuild uses the org's own payment setup.

## Rebuild checks
| Check | Finding | Evidence |
|---|---|---|
(one row per check below, every check completed)

## Rebuild notes
Facts only. Every claim that something is broken, inverted, dead, duplicated or reads the wrong field cites its evidence: the field ids (`tfa_1234`) or the logic.md line. Anything not proven is written "unclear: ...".
```

When `logic.md` says a connector's mapping was not captured, write it in the Purpose ("its Salesforce steps were not captured; what it writes is unknown") and mark every check that depends on the submit steps "unclear: connector not captured". Never fill the gap from the form's field names.

## Rebuild checks

These are not questions for the organization. Complete every check for every form from the captured logic, in this order. The finding is one or two plain sentences and says what the rebuild should do differently. When nothing applies, write "None found". Evidence is the field ids or the logic.md step (`1.1.2.3`, prefill lookup `#12`).

| # | Check | What to look for |
|---|---|---|
| 1 | Money set by the browser | An amount, price, quantity or total written to Salesforce or charged that comes from a form field or a form calculation the browser can change. The rebuild reads prices from Salesforce and works out totals on the server. |
| 2 | Recorded twice | The same sale, person or answer written to two objects (Opportunity and Order, two contact records), or two branches with the same mappings. Say which one reporting uses, or "unclear". |
| 3 | Records written without being chosen | Create steps whose skip rule tests a flag that prefill always sets (every repeated row, every listed contact), so a row is written whether or not the person chose it. |
| 4 | Read but never updated | Stock, seats, capacity or counters checked in prefill (`Total Available > 0`, seats left) that nothing in the form lowers. Say whether a Salesforce automation must do it. |
| 5 | One idea copied into several blocks | The same lookup, section and steps repeated per household, plot or time slot. The rebuild uses one list and one rule. |
| 6 | Values an admin should own | Record type ids, campaign or price book ids, fixed picklist values, fees, eligible membership types, dates. Move to settings or custom metadata. |
| 7 | Overwritten on every submit | Fields on existing records replaced on every submit (preferred email, primary contact, address), and whether a person acting for a household changes someone else's data. |
| 8 | How records are matched | The match rule for each update or lookup, what happens on no match and on several matches (Flow Tool Kit stops on several matches where FormAssembly may pick the most recent), and match fields that are empty or unset (duplicates). |
| 9 | Reachable by changing the link | Prefill parameters a person could change or guess (membership numbers, record ids) and what data they would see. |
| 10 | Leftovers to drop | Steps or skip rules on deleted fields, calculations nothing reads, disabled connectors, legacy payment set-up. |
| 11 | Helper fields for the old connector | Fields that exist only to give the connector an exact match key (a `Lookup_Email__c` on Contact). List them as retirement candidates once matching rules cover them; never remove one without the organization's decision, and list its other users (flows, Apex, layouts, list views, reports) first. |

## Rules

- Lists stay one level deep: the pages do not show nested lists. Write a sub-step as its own numbered line with its step number in the text (`1.1 Create the Opportunity ...`).
- When the capture does not say (who fills the form in, why a step exists), write "unclear" rather than infer it.
- Connector pages keep only the label for most field mappings, so when two fields share a label the capture cannot prove which one a mapping reads. Say so ("unclear: one of the two City fields") rather than pick one.
- logic.md labels fields that share a name with their section, `[City (Plot Address)]`. Two fields with the same label are different fields: never call a formula "the same field on both branches" without the ids.
- If logic.md does not say it, write "unclear", never guess.
- No em-dash and no section-symbol characters.
- Write only `summary.md`. Never edit generated files. If the file tool refuses to write it, write it with the shell.
