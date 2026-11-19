# Example: Get Account Giving Summary

An invented request, built end to end with this skill. Copy it when an action reads records for each request and returns a few values per request.

## The request

> "On the account page and in the year-end thank-you flow, I want this year's giving for the account: how much, how many gifts, and when the last one came in."

## Why an action and not Flow

Flow can do it with a Get Records of every gift and a loop that adds them up. That loads every gift row (a long-time donor can have hundreds), and in a scheduled flow over many accounts it repeats for each one. One aggregate query returns only the totals, for every account in the run at once. That is the case for Apex: the database does the arithmetic, and the action stays one query however many accounts arrive.

## What was built

| File | What it is |
|---|---|
| `force-app/main/default/classes/Account_Giving_Summary_Invocable.cls` | The action: Account ID and an optional Year in; Total Amount, Gift Count and Last Gift Date out |
| `force-app/main/default/classes/Account_Giving_Summary_Invocable_Test.cls` | Seven tests, all on in-memory data through a mock of the seam: the main case, the blank year, an account with no gifts, gifts with no amount, two years in one call, a missing Account ID, and 200 requests in one call |
| `*.cls-meta.xml` | API version 62.0 |

Built with:

```bash
python3 scripts/new_invocable.py scaffold --project <project-dir> --object Account \
  --name "Account Giving Summary" --label "Get Account Giving Summary" --method getGivingSummary \
  --description "Totals the won opportunities on an account for one calendar year: the amount given, the number of gifts and the date of the latest gift. Every account in the flow run is totaled in one query, so it is safe in record-triggered and scheduled flows." \
  --input "accountId|Id|Account ID|The organization or household account whose giving to total.|required" \
  --input "year|Integer|Year|The calendar year to total, such as 2026. Leave blank for the current year." \
  --output "totalAmount|Decimal|Total Amount|The sum of the amounts on the won opportunities of the account that closed in the year. 0 when there were none." \
  --output "giftCount|Integer|Gift Count|How many won opportunities on the account closed in the year. 0 when there were none." \
  --output "lastGiftDate|Date|Last Gift Date|The close date of the latest won opportunity in the year. Blank when there were none."
```

then the seam's query was changed to the aggregate one below, `process`, the defaults and the tests were filled in, and `scripts/new_invocable.py check` reports no errors and no warnings.

## How it applies the pattern

- **Gather, query once, process.** The first loop collects every Account ID and year; one `GROUP BY` query totals the won opportunities for all of them; `process` looks each request up in the Map by `accountId:year`. Requests for different years in one call still use one query: it spans from the earliest year to the latest and groups by year.
- **The data-access seam.** The query lives in `DatabaseAccess`, behind the `DataAccess` interface, and nowhere else. It copies each `AggregateResult` row into a `GivingTotal`, because a test cannot build an `AggregateResult`. The tests swap in `MockDataAccess`, which returns `GivingTotal` rows built in memory for fake Account Ids and remembers the Ids and dates it was asked for.
- **User mode.** `with sharing` and `WITH USER_MODE`: a person sees totals only over gifts they can see.
- **Defaults in the result.** Total Amount and Gift Count start at 0, so an account with no gifts returns 0, as the descriptions promise, not blank.
- **The flow built wrong.** A request with no Account ID throws `Account_Giving_Summary_Exception` with a message saying what to fix; the flow's fault path shows it.
- **Bulk proven, no data made.** The bulk test checks each of the 200 totals against its own expected value, that the seam was asked once for all 200 accounts, and that no query or DML reached the org.

## Tests and coverage

This version, with the seam and the mock-only tests, has not yet been compiled or run in an org. Expected when it is deployed with its tests (SKILL.md step 6):

| Measure | Expected |
|---|---|
| Tests | 7 of 7 pass |
| Records created, queries run against org data | none |
| Seam calls for 200 requests | 1 |
| Coverage of the action class | about 90 percent, estimated by line count: the 4 lines of the query in `DatabaseAccess` are the only ones the mock-only tests do not run |

To run those 4 lines too, ask for a database test ([../../references/testing.md](../../references/testing.md), "If the person asks for a database test"). Its records are rolled back when the test ends.

## To use it in a flow

Add an **Action** element, search for **Get Account Giving Summary**, set **Account ID** (for example `{!$Record.Id}`) and, if needed, **Year**, then use **Total Amount**, **Gift Count** and **Last Gift Date** from the action's outputs.

## Limits to know

- A transaction may read 50,000 query rows in all. Measured on an earlier version with the same query, 200 accounts with 1,000 gifts used 200 query rows, one per account and year rather than one per gift; if a run over very many accounts nears the limit, give the scheduled flow a smaller batch size.
- It totals won opportunities only, by close date. An org that records gifts on another object needs its own action; copy this one's shape.
