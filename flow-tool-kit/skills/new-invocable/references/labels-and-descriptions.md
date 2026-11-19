# Names, labels and descriptions

An admin meets your action in Flow Builder, months later, with no access to the code. Everything they see comes from the annotations, so the annotation text is written for them, in the shape `_shared/standards/documentation.md` section 1 sets for every description: summary first, detail only where it is needed, the bigger picture when it helps.

## What the admin sees, and where it comes from

| In Flow Builder | Comes from | Write it like |
|---|---|---|
| The action's name in the Action list and on the canvas | `@InvocableMethod(Label=...)` | A verb phrase in Title Case naming the outcome: `Get Account Giving Summary`, `Tidy Contact Names`, `Send Volunteer Shift Reminder`. Never the class name. |
| The group the action is listed under | `@InvocableMethod(Category=...)` | Optional. When the org's other actions share a category, use the same one so they list together. Leave it out when there is none; the action still lists under Apex. |
| The text under the action's name | `@InvocableMethod(Description=...)` | One or two sentences: what it does and what comes back. Then, only if it matters, how it behaves at volume or what it does not do. |
| Each input and output field | `@InvocableVariable(Label=...)` | Like a field label, in Title Case: `Account ID`, `Year`, `Total Amount`. |
| The help beside each field | `@InvocableVariable(Description=...)` | For an input: what to pass, and what a blank means. For an output: what it holds, and its value when there is nothing to report. |
| The required marker | `@InvocableVariable(Required=true)` | Only on inputs the action cannot run without. Flow Builder then refuses to save the flow without a value. |

## The never list

Never in a label or description:
- class, method, variable or constant names (write "the account", not `accountId`);
- history ("used to", "now also", "replaces");
- issue numbers, ticket numbers, commit hashes or dates;
- em-dashes (use a colon, a comma or a new sentence).

`scripts/new_invocable.py check` fails a missing label or description, an em-dash and an issue number.

## Before and after

| | Text |
|---|---|
| Before | `Description='Runs AggregateResult query on Opportunity grouped by AccountId and CALENDAR_YEAR, returns InvokedResult with SUM(Amount).'` |
| After | `Description='Totals the won opportunities on an account for one calendar year: the amount given, the number of gifts and the date of the latest gift. Every account in the flow run is totaled in one query, so it is safe in record-triggered and scheduled flows.'` |
| Before | `@InvocableVariable(Label='year' Description='Integer year, null = current')` |
| After | `@InvocableVariable(Label='Year' Description='The calendar year to total, such as 2026. Leave blank for the current year.')` |

## Quotes inside the text

Annotation text is an Apex string in single quotes. An apostrophe must be written `\'` (`'The donor\'s preferred name.'`); the scaffold does this for you. Wording without the apostrophe ("the preferred name of the donor") is easier to keep right when someone edits it later.

## Names in the code

| Thing | Name | Example |
|---|---|---|
| Class | `<Object>_<Action>_Invocable`, the object and action words matching the label | `Account_Giving_Summary_Invocable` |
| Test class | the class name plus `_Test` | `Account_Giving_Summary_Invocable_Test` |
| Length | Apex allows 40 characters, so the class can be at most 35 to leave room for `_Test` | |
| Method | a camelCase verb phrase | `getGivingSummary` |
| Exception | the class name without `_Invocable`, plus `_Exception` | `Account_Giving_Summary_Exception` |
| Inner classes | always `InvokedRequest` and `InvokedResult` | |
| Variables | camelCase, full words, no type prefixes | `accountId`, `totalAmount`, `lastGiftDate` |

Changing a label or description later is safe: flows store the class and variable names, not the text. **Renaming the class, the method or a variable is not**: every flow that uses the action has to change with it. Pick the names once, before the first flow uses it.
