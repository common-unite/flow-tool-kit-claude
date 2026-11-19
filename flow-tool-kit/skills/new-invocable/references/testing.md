# Testing an invocable action

Every action ships with its test class in the same change; the skill never writes one without the other. The tests prove three things: each result is right, the action fails clearly when the flow is built wrong, and 200 requests are read (and saved) in one call each.

**The tests make no data.** They build records in memory, swap the action's data-access seam ([pattern.md](pattern.md), "The data-access seam") for a mock, and assert both the results and what the mock was asked to read or save. No DML, no SOQL against org data, no `SeeAllData`, no `Test.loadData`, and nothing that needs a record to exist in the org. So they pass the same way in every org they are deployed to, and an org's validation rules, required fields, duplicate rules and picklist values cannot break them.

The worked example's test class is [../examples/account-giving-summary/force-app/main/default/classes/Account_Giving_Summary_Invocable_Test.cls](../examples/account-giving-summary/force-app/main/default/classes/Account_Giving_Summary_Invocable_Test.cls).

## The tests to write

One test method per scenario, named for what it proves:

| Test | Proves | Example |
|---|---|---|
| The main case | Every output is right for an ordinary request, rows for other records or other keys are left out, and the seam was asked for exactly what the request needs | `totalsTheAccountForTheYear`: the mock also returns another year and another account, and only the matching row counts |
| Each default | A blank optional input behaves as its description says | `blankYearMeansThisYear`: the seam is asked for this year's dates |
| Nothing found | The outputs the descriptions promise when there is nothing to report (0, blank) | `accountWithNoGiftsReturnsZero` |
| Each branch in `process` | Unusual values the seam can return, such as a blank total | `giftsWithNoAmountTotalZero` |
| The flow built wrong | The custom exception, with the exact message, and nothing read or saved | `missingAccountIdFailsTheRun` |
| A thin record | Only for record inputs: a record with only `Id` set does not throw | see [pattern.md](pattern.md), "Records the flow hands in may be missing fields" |
| Bulk | 200 requests in one call: every result right, one call to the seam for all of them, and no query or DML reached the org | `twoHundredRequestsReadOnceAndTouchNoData` |

An action that saves records also asserts what the mock was given to save: how many records, their Ids and the fields that changed, and that nothing is saved when there is nothing to change.

## Records in memory

Build each record with `new`, give it the fields the action reads, and give it an Id when the action looks records up by Id:

```apex
Account account = new Account(Id = fakeId(Account.SObjectType, 1), Name = 'Riverside Community Garden');
```

Nothing is inserted, so nothing has a real Id. The test class makes one that is valid for the object:

```apex
// A valid-looking Id for the object. Nothing is saved, so no record has this Id in any org
static Id fakeId(Schema.SObjectType objectType, Integer index) {
    return Id.valueOf(objectType.getDescribe().getKeyPrefix() + String.valueOf(index).leftPad(12, '0'));
}
```

The key prefix makes it an Id of the right object, so `Id.getSObjectType()` and a `Map<Id, Account>` work as they would on saved records. Give each record its own index so a result returned for the wrong record is caught.

Fields Apex will not let you set on a new record (formula fields, roll-up summaries, `CreatedDate`, child relationship lists) can still be put in memory: build the record from JSON, `(Account) JSON.deserialize('{"attributes":{"type":"Account"},"Id":"...","Name":"..."}', Account.class)`. Use it only when the action reads such a field.

When the seam returns something that is not a record, such as totals from an aggregate query, it returns a small plain class instead (the example's `GivingTotal`), because a test cannot build an `AggregateResult`. The test builds those directly.

## The mock

The mock is a private class inside the test class that implements the action's `DataAccess` interface. It answers each read from what the test gives it, keeps what the action would save, and counts the calls:

```apex
private class MockDataAccess implements Account_Giving_Summary_Invocable.DataAccess {
    public List<Account_Giving_Summary_Invocable.GivingTotal> totals = new List<Account_Giving_Summary_Invocable.GivingTotal>();
    public Integer readCount = 0;
    public Set<Id> accountIdSet;

    public List<Account_Giving_Summary_Invocable.GivingTotal> givingTotals(Set<Id> accountIdSet, Date firstDay, Date lastDay) {
        readCount++;
        this.accountIdSet = accountIdSet;
        return totals;
    }
}
```

Each test puts it in place before calling the action, through the `@TestVisible` field:

```apex
MockDataAccess mock = new MockDataAccess();
Account_Giving_Summary_Invocable.dataAccess = mock;
```

A save method in the mock adds the records it is given to a list (`updatedRecords.addAll(changedRecords);`) and counts the call; the test asserts that list.

**Why a hand-written mock and not the Stub API.** `Test.createStub` builds a mock from a `StubProvider` at run time, but it cannot mock an inner class, and the seam lives inside the action class. A plain class implementing the interface is simpler and reads like any other Apex. If a project already keeps its seams as top-level classes and mocks them with `Test.createStub`, follow the project; the check accepts either.

## The bulk test

Call the action once with 200 requests, each with its own record and its own expected value (here, gift `i` is worth `i + 1`), and check:

```apex
List<Account_Giving_Summary_Invocable.InvokedResult> results = Account_Giving_Summary_Invocable.getGivingSummary(requests);

Assert.areEqual(200, results.size());
for (Integer i = 0; i < 200; i++) Assert.areEqual(i + 1, results[i].totalAmount);
Assert.areEqual(1, mock.readCount, 'One read for all 200 requests');
Assert.areEqual(200, mock.accountIdSet.size());
Assert.areEqual(0, Limits.getQueries(), 'The mock answers every read, so no query reaches the org');
Assert.areEqual(0, Limits.getDmlStatements(), 'Nothing is written to the org');
```

One call to the seam for 200 requests is the bulk proof: each seam method holds one query, so one call is one query whatever the count. The two `Limits` checks prove nothing outside the seam touched the org. An action that saves also checks one save call holding all the changed records.

## Coverage

Mock-only tests never run the lines inside the seam that do the real query or save. Everything else (gathering, `process`, the defaults, the error path) is run, so keep each seam method to the one statement, and coverage stays well above the 75 percent Salesforce requires for each class deployed to production.

| Class | Lines Apex counts (estimated) | Not run by the tests | Expected coverage |
|---|---|---|---|
| The example action | about 39 | the 4 lines of the aggregate query in `DatabaseAccess` | about 90 percent |
| A scaffold with `--object` | about 15 | the query line | about 93 percent |
| A scaffold with `--object --saves` | about 19 | the query line and the save line | about 89 percent |

These are estimates by line count; the deploy in SKILL.md step 6 reports the real number. The test class itself is not counted.

## If the person asks for a database test

Not added by default. When someone wants the seam's own lines run (to prove the query's filters, or to reach 100 percent), add one test that leaves the mock out, inserts the few records it needs and calls the action. An Apex test's DML is rolled back when the test ends and is never visible in the org, so it leaves nothing behind. It does meet the org's own rules, so that one test needs the care the mock-only tests avoid:
- look picklist values up rather than typing them, for example a won stage with `[SELECT ApiName FROM OpportunityStage WHERE IsActive = true AND IsWon = true LIMIT 1]`;
- set any field a required-field or validation rule names in the deploy error, and give records distinct names so a duplicate rule does not block them; never switch a rule off for a test;
- set the `RecordTypeId` whose process includes the picklist values used, where the object has record types.

Keep it beside the mock-only tests, named for what it proves (`queryReadsOnlyWonGiftsInTheYear`), and say in the report that it inserts test records. The check reports its DML and query as errors; that is expected for this one test, and the person agreed to it.

## Rules

- **No DML, no SOQL, no `SeeAllData`, no `Test.loadData`** in the mock-only tests. `new_invocable.py check` reports each one as an ERROR.
- **Swap the seam in every test that calls the action.** The check reports an ERROR when an action with a seam has tests that never swap it.
- **Minimal data.** Only the records and fields the scenario needs.
- **Use the `Assert` class** (`Assert.areEqual`, `Assert.isTrue`, `Assert.isNull`, `Assert.fail`). A message is optional; add one where the reason for the check is not obvious from the line, such as the one-read check in the bulk test.
- **Invented data only**: example names, `name@example.org` emails, 555-0100 to 555-0199 phone numbers.
- **A user without access**, when access is the point: the seam's user-mode query is what enforces access, and a mock does not run it. Prove it in a database test inside `System.runAs(user)`, only if the person asks for one.

## Report the numbers

After the tests pass in the org, report for the user:

| Measure | Example result |
|---|---|
| Tests | 7 of 7 passed |
| Coverage of the action class | the number the deploy reports; expected about 90 percent for the example |
| Seam calls for 200 requests | 1 read (and 1 save, for an action that saves) |
| Queries and DML that reached the org in the tests | 0 and 0 |
| CPU for 200 requests | measured with `Limits.getCpuTime()` around the call in the bulk test |
