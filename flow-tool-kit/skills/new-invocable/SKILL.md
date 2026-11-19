---
name: new-invocable
description: Build an Invocable Action, the Apex class a flow calls as an Action element, for a step Flow cannot do well, such as totals from an aggregate query, text parsing, sorting or matching across many records, or a call to an outside service. Writes the class in the standard shape (InvokedRequest and InvokedResult inner classes, one process method, bulk-safe, with sharing and user-mode queries), labels and descriptions an admin can read in Flow Builder, every query and save behind a small data-access seam, and always its test class, which runs on in-memory records and a mock of the seam so it creates no data and passes in any org, including a 200-request bulk test; then deploys it and runs the tests. Use when someone asks for "an invocable", "an Apex action for my flow" or "make an action that formats this address", or when build-flow-section or new-mapping-flow finds a step that needs Apex.
---

# New Invocable Action

An Invocable Action is an Apex class a flow calls like any other Action element. Admins keep the logic they can see in Flow; the action does the one step Flow cannot do well, and hands values back.

Flow comes first. Write an action only when Flow cannot do the step, or can only do it badly:
- **totals and counts across many records** (an aggregate query returns the sums; Flow would load every row and loop);
- **text work**: parsing, patterns, formatting an address or a name;
- **matching, sorting or grouping** large collections;
- **calls to outside services** that need Apex;
- **anything that must stay one query for a whole batch**, where a Flow loop would repeat per record.

If a Get Records, a formula, a Transform or an existing action does the job, say so and stop.

**Called by** build-flow-section and new-mapping-flow when a step needs Apex, and directly. **Hands back** to the skill or person that asked, with the action's label and its inputs and outputs, ready for the Action element.

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat | Steps 1 to 5: decide, name, write the class and its test class (always both), and run `scripts/new_invocable.py scaffold` and `check` in the code sandbox. With a Salesforce connector, also step 1's look at the org's existing actions. **Chat cannot deploy Apex or run Apex tests.** Say so in one line and hand over the four files for Claude Code (or for the person's own deployment tool). |
| Claude Code, local or on the web, with the Salesforce CLI | Everything, including deploying, running the tests in the org and reporting the numbers. |

Read on demand, beside this file:
- [references/pattern.md](references/pattern.md): the shape, bulk first, access and user mode, who the action runs as, records with missing fields, failing, callouts, code style.
- [references/labels-and-descriptions.md](references/labels-and-descriptions.md): what the admin sees in Flow Builder and how to write it; class, method and variable names.
- [references/testing.md](references/testing.md): the tests to write, the bulk test, test data that survives any org, the numbers to report.
- [examples/account-giving-summary/](examples/account-giving-summary/): a finished action (Get Account Giving Summary) with its seam and its mock-only tests.
- Plugin standards: `_shared/standards/documentation.md` (section 1, the writing shape for every description), `_shared/standards/naming.md`, `_shared/standards/project-config.md`.

## 1. Look for one that exists

Before writing anything, check what the org already has, and **ask, naming what you found**; never reuse or duplicate silently.

1. **Actions in the org.** List every Apex action the org's flows can call, Flow Tool Kit's included:

   ```bash
   sf api request rest "/services/data/v62.0/actions/custom/apex" -o <org-alias>
   ```

   Each entry has a `label` and a `name`. Read the labels for one that does the job. To see one action's inputs and outputs as Flow Builder shows them, add its name: `.../actions/custom/apex/<name>`.
2. **Classes in the project.** Search the project's classes for `@InvocableMethod`, and note the `Category` the others use (step 3).
3. **Flow's own actions and elements.** Many asks are a standard action (Send Email, Post to Chatter, Create Records) or a Transform, a collection filter or a sort.

Found one: "Get Account Giving Summary already returns this year's total for an account. Use it, or build a new one?" Extending an existing action means adding an input or output to it; never rename what flows already use.

In chat with a Salesforce connector, list the actions through the connector. Without one, ask the person, and go on.

## 2. Settle what it does

Write the action's contract from the request, then **show it for confirmation** rather than asking open questions:

- **Label**: the verb phrase the admin will search for (`Get Account Giving Summary`).
- **Inputs**: each with its type, whether it is required, and what a blank means. Prefer Ids and plain values; take a record only when the flow already has it and the action needs several of its fields.
- **Outputs**: each with its type and its value when there is nothing to report (0, blank).
- **Who runs it**: staff in a screen flow, a guest or member on a site, a record-triggered or scheduled flow, or a Flow Tool Kit conversion. It decides the access work ([references/pattern.md](references/pattern.md), "Access").
- **What it reads and saves**: the objects and fields. Read only what the outputs need.

Only what a flow needs today: no inputs, outputs or options "in case".

## 3. Name it

- Class `<Object>_<Action>_Invocable`, at most 35 characters so the test class fits Apex's 40 (`Account_Giving_Summary_Invocable`).
- Method: a camelCase verb (`getGivingSummary`).
- Category: optional. If the project's other actions share one, use it; otherwise leave it out unless the person wants their actions grouped.
- Labels and descriptions in the summary-first shape: [references/labels-and-descriptions.md](references/labels-and-descriptions.md). No class names, history, issue numbers or em-dashes in them.

## 4. Scaffold and write it

From the project folder (the one with `sfdx-project.json`), where `<this skill>` is the folder this file is in. The script is Python 3 standard library only.

```bash
python3 <this skill>/scripts/new_invocable.py scaffold --name "Account Giving Summary" \
  --label "Get Account Giving Summary" --method getGivingSummary \
  --description "Totals the won opportunities on an account for one calendar year: ..." \
  --input "accountId|Id|Account ID|The organization or household account whose giving to total.|required" \
  --input "year|Integer|Year|The calendar year to total, such as 2026. Leave blank for the current year." \
  --output "totalAmount|Decimal|Total Amount|The sum of the won gifts in the year. 0 when there were none." \
  --object Account [--saves] [--category "<the project's category>"]
```

Each `--input` and `--output` is `name|Type|Label|Description`, from the contract confirmed in step 2; an input may end in `|required`. `--object` is the object whose records the action reads, keyed by the first input of type `Id`; it adds the data-access seam and its mock. `--saves` adds a save to both. Leave both out for an action that reads and saves nothing, such as formatting text. Give at least one of each: Apex refuses to save an action whose request or result class has no `@InvocableVariable`. Types are what Flow can pass: `Id`, `String`, `Integer`, `Decimal`, `Boolean`, `Date`, `Datetime`, an object such as `Account`, or a `List<...>` of one.

It writes the class, its test class and both `-meta.xml` files into the default package's `main/default/classes` folder, at the project's `sourceApiVersion`, always all four together: an action never ships without its tests. The TODOs mark what to fill in; step 6 compiles them and runs the tests. It refuses to overwrite any of the four files: when the class exists, retrieve the org's copy and edit that.

In chat with no project, pass `--project` a working folder and `--api-version` (the org's API version, 57.0 or later).

Then write the action in the shape of [references/pattern.md](references/pattern.md), with the example open beside you:
- `InvokedRequest` and `InvokedResult` with an `@InvocableVariable` label and description on every input and output, `Required=true` on the inputs the action cannot run without;
- **bulk first**: gather every request's keys into Sets, query once into a Map, and build each result in `process` from the Map; nothing per request that has a limit;
- **a data-access seam**: every query and save in `DatabaseAccess`, behind the `DataAccess` interface, one statement per method; the logic works only on the records the seam returns ([references/pattern.md](references/pattern.md), "The data-access seam");
- `with sharing`, `WITH USER_MODE` on every query, `as user` on every save. System mode only after the person agreed to exactly what it exposes, on one query, with the reason in a comment;
- the custom exception, with a message that says what to fix, for a flow built wrong; a normal result for unusual data;
- `isSet()` before reading any field of a record the flow hands in.

## 5. Write the tests and check the code

The test class is never optional, and it touches no data: it builds records in memory (with valid-looking fake Ids for the object), swaps the seam for a mock, and asserts both the results and what the mock was asked to read or save. No DML, no SOQL against org data, no `SeeAllData`, and nothing that needs a record to exist in the org, so the tests are safe to run in any org and pass the same way in all of them.

Fill it in from [references/testing.md](references/testing.md): the main case, each default, nothing found, the flow built wrong, a thin record when a record is an input, and the 200-request bulk test, which checks each of the 200 results, that the seam was called once for all of them, and that no query or DML reached the org.

**Coverage, said plainly.** Mock-only tests never run the lines inside the seam that do the real query or save. Keep each seam method to that one statement and the rest of the class is fully covered, well above the 75 percent Salesforce requires per class for a production deploy. Expected for the example: about 90 percent (the 4 lines of its aggregate query are the only ones not run); for a fresh scaffold with `--object`, about 93 percent, and about 89 percent with `--saves`. These are estimates by line count: tell the person the expected figure, then the real one from step 6.

**A database test only on request.** If the person wants the seam's own lines run, offer one test that inserts its few records and runs the real query: an Apex test's DML is rolled back when the test ends and is never visible in the org. It has to survive the org's validation rules and required fields, so it is not added by default ([references/testing.md](references/testing.md), "If the person asks for a database test").

```bash
python3 <this skill>/scripts/new_invocable.py check force-app/main/default/classes/Account_Giving_Summary_Invocable.cls
```

Fix every ERROR. Read every WARN; a TODO left behind is a WARN. It checks: public and `with sharing`; one `@InvocableMethod` with a label and a description; a label and description on every variable, with no em-dash or issue number; the two inner classes, each with at least one variable; user mode on every query and save; every query and save inside the data-access seam; no query, save, callout or describe inside a loop or inside `process`; the API version; and a test class beside it, with no DML, no SOQL, no `SeeAllData`, no `Test.loadData`, a mock that swaps the seam, and a 200-request bulk test. It is a pattern check, not a compiler, and cannot follow a call into another class: read the code too.

## 6. Deploy and run the tests (Claude Code)

1. **Retrieve before you deploy** when the class already exists in the org, and merge: never overwrite a change someone made there.
2. **Deploy the four files and run the test class in the same step**:

   ```bash
   sf project deploy start --source-dir force-app/main/default/classes/Account_Giving_Summary_Invocable.cls \
     --source-dir force-app/main/default/classes/Account_Giving_Summary_Invocable_Test.cls \
     --test-level RunSpecifiedTests --tests Account_Giving_Summary_Invocable_Test -o <org-alias>
   ```

   `--source-dir` on a `.cls` file takes its `-meta.xml` with it. A failing test or a class under 75 percent coverage stops the deploy, and nothing is saved. The tests themselves create no records in the org.
3. **A mock-only test cannot fail on the org's own rules**: it saves nothing. If a test fails, the action's logic or the test's expectation is wrong; fix that. Only a database test the person asked for meets validation rules, required fields and duplicate rules: fix its data, as [references/testing.md](references/testing.md) says, and never switch the rule off.
4. **Report the numbers**: tests passed, coverage of the action class (against the expected figure from step 5), seam calls for 200 requests, queries and DML that reached the org in the tests (0 and 0), and CPU at 200 (`Limits.getCpuTime()` around the call). Show them in a table.

In chat: hand over the four files and the deploy command above. The person runs it in Claude Code, or deploys with their own tool and runs the test class in Setup, Apex Test Execution.

## 7. Hand it to the flow

Give the caller (the person, build-flow-section or new-mapping-flow) what the Action element needs: the action's label to search for, each input with what to pass, and each output with what it holds.

Then the access work:
- **everyone who runs the flow needs access to the class**: Apex Class Access on a permission set they hold (or their profile). Add the class to the permission set the flow's users already get; without it the flow fails for them, though it works for an administrator;
- guests and signed-in site members: the **flow-access-fix** skill grants that class access on their own permission set, and the reads the action makes;
- a Flow Tool Kit conversion flow: the action runs as the conversion's running user, Automated Process unless one is named, so user-mode queries see nothing that user lacks. Name a running user as **new-mapping-flow** describes.

## Done when

- The action does a step Flow could not do well, and no existing action did it (step 1 was asked, naming what was found).
- The class is public, `with sharing`, user mode throughout, bulk first, in the InvokedRequest, InvokedResult and process shape, with a label and a description on the action and on every input and output.
- Every query and save is in the data-access seam, one statement per method.
- The class and its test class exist together, and `new_invocable.py check` reports no errors.
- The test class covers each scenario in [references/testing.md](references/testing.md), including 200 requests read in one seam call, on in-memory records and a mock: no DML, no SOQL, no `SeeAllData`, no record in the org needed.
- The person was told the expected coverage and that the seam's own lines are the ones the tests do not run.
- The flow's users have Apex Class Access to the class through a permission set.
- In Claude Code: deployed with its tests passing, and the numbers reported. Never claim the tests pass, or give a coverage figure as measured, before they ran in an org. In chat: the four files and the deploy command handed over, with the one line saying deploying needs Claude Code.

## Common mistakes

| Mistake | Instead |
|---|---|
| An action for something a Get Records, formula or Transform does | Flow first, and state why Flow is not enough |
| A query or save inside the loop over requests, or inside `process` | Gather keys, query once into a Map, save once after the loop |
| Results in a different order from the requests, or fewer of them | One result per request, in request order |
| `global` | `public`; `global` is for managed packages |
| `without sharing`, or no `WITH USER_MODE` | `with sharing` and user mode; system mode only when the person agreed, on one query |
| Reading a field of a record the flow passed in without `isSet()` | Guard it, or take an Id and query the fields |
| Catching an exception and returning an empty result | Throw the custom exception for a flow built wrong; return a real result for unusual data |
| A description that names the class, a field API name or the history | Summary first, written for the admin |
| Writing the class without its test class, or the test later | Both, every time; the scaffold writes them together |
| A test that inserts records, queries org data or uses `SeeAllData` | Records in memory with fake Ids, and a mock of the seam |
| A query or save outside the seam, or logic inside it | One statement per seam method; everything else outside, where the tests run it |
| Calling the mock-only coverage 100 percent | Say plainly that the seam's lines are not run, and give the expected figure |
| A bulk test that only checks the result count | Check each of the 200 results, one seam call, and no query or DML in the org |
| Testing the flow only as an administrator | Give the flow's users Apex Class Access to the class, then run it as one of them |
| Renaming the class, method or a variable after flows use it | Choose names before the first flow; change labels and descriptions freely |
