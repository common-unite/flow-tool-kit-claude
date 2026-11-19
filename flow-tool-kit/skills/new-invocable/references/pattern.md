# The invocable action pattern

Every action this skill builds has the same shape, so anyone who opens one knows where to look. The worked example is [../examples/account-giving-summary/](../examples/account-giving-summary/); every snippet here comes from it.

## The shape

```apex
public with sharing class Account_Giving_Summary_Invocable {

    public class Account_Giving_Summary_Exception extends Exception {}

    @TestVisible private static DataAccess dataAccess = new DatabaseAccess();

    @InvocableMethod(Label='Get Account Giving Summary' Description='Totals the won opportunities ...')
    public static List<InvokedResult> getGivingSummary(List<InvokedRequest> requests) {
        // 1. gather every request's keys into Sets
        // 2. read once through dataAccess into a Map
        // 3. build each result from the Map
    }

    private static InvokedResult process(InvokedRequest request, Map<String, GivingTotal> givingMap) { ... }

    public interface DataAccess { ... }                                      // every query and save the action makes
    private with sharing class DatabaseAccess implements DataAccess { ... }  // the real ones, one statement each

    public class InvokedRequest { @InvocableVariable ... }   // inputs
    public class InvokedResult { @InvocableVariable ... }    // outputs
}
```

| Part | Rule |
|---|---|
| Class | `public with sharing class <Object>_<Action>_Invocable`. Public, never `global`: `global` exists for managed packages, and Flow lists a public action in your own org the same way. |
| Exception | One inner `<Base>_Exception extends Exception` for failures the flow must see (below). |
| `@InvocableMethod` | One per class. A verb for the method name (`getGivingSummary`, `tidyContactNames`). It takes `List<InvokedRequest>` and returns `List<InvokedResult>`, one result per request, **in the same order**: Flow matches them up by position. |
| `process` | `private static InvokedResult process(InvokedRequest request, <the Maps>)`: builds one request's result from what was already queried. It never queries, saves or calls out. |
| The data-access seam | `DataAccess`, an inner interface with one method per query or save, and `DatabaseAccess`, the inner class that does them. The only place the class touches the database (below). Not needed by an action that reads and saves nothing. |
| `InvokedRequest` / `InvokedResult` | The inputs and outputs, each an `@InvocableVariable` with a label and a description ([labels-and-descriptions.md](labels-and-descriptions.md)). Only the inputs and outputs a flow needs today; add one when a flow needs it. |

## Bulk first

Flow hands an action **a list**, not one request. When a record-triggered flow runs on 200 records from a data load, or a scheduled path fires for a batch, Flow gathers every interview that reaches the action and calls it once with all of their requests. Code that queries once per request hits the 100-query limit at the 101st record, and the whole batch fails.

So the invocable method works in three steps:

```apex
Set<Id> accountIdSet = new Set<Id>();
Set<Integer> yearSet = new Set<Integer>();
for (InvokedRequest request : requests) {
    if (request.accountId == null) throw new Account_Giving_Summary_Exception(MISSING_ACCOUNT);
    accountIdSet.add(request.accountId);
    yearSet.add(givingYear(request));
}
Map<String, GivingTotal> givingMap = readGiving(accountIdSet, yearSet);

List<InvokedResult> results = new List<InvokedResult>();
for (InvokedRequest request : requests) results.add(process(request, givingMap));
return results;
```

1. **Gather**: loop the requests once, collecting every Id and key into Sets.
2. **Read once** for all of them, through the seam, into a Map keyed the way `process` will look them up. Keys made of two parts (an account and a year) become one String key.
3. **Process**: loop again; `process` reads from the Map.

Nothing with a limit or a fixed cost runs per request: no SOQL, no DML, no callout, no `Database.*` call, no platform event publish, no describe. Per-type work such as a field describe or `Type.forName` goes in a static Map keyed by the `SObjectType`, so it runs once per transaction however many requests arrive.

Saving works the same way: build a `List<SObject>` in the loop and save it once after the loop, through the seam, whose save method uses `as user`.

**CPU is a limit too.** Anything heavier than a few lines per request (JSON round trips, string building over many fields, nested loops) is measured at 200 requests in the bulk test. Keep 200 requests well under a quarter of the 10-second synchronous limit.

## The data-access seam

Every query and save goes through one small seam, so the tests can swap it for a mock, run on records built in memory and make no data in any org ([testing.md](testing.md)). The action's logic (gathering, `process`, the defaults, the errors) works only on what the seam returns.

```apex
// Every read goes through this seam, so the tests swap in a mock and touch no org data
@TestVisible private static DataAccess dataAccess = new DatabaseAccess();

public interface DataAccess {
    List<Contact> queryRecords(Set<Id> recordIdSet);
    void updateRecords(List<Contact> records);
}

private with sharing class DatabaseAccess implements DataAccess {
    public List<Contact> queryRecords(Set<Id> recordIdSet) {
        return [SELECT Id, FirstName, LastName FROM Contact WHERE Id IN :recordIdSet WITH USER_MODE];
    }

    public void updateRecords(List<Contact> records) {
        update as user records;
    }
}
```

- **One statement per method**: the query, or the save. The mock-only tests never run these lines, so anything else put here is code no test checks and coverage the class loses. Logic that decides what to read or save stays outside, where the tests run it.
- **`with sharing` on `DatabaseAccess` too.** An inner class does not take its sharing from the class around it. User mode on every query and save still applies.
- **Called once per transaction, not per request**: the seam is the "query once" and "save once" of bulk first. The bulk test proves it by counting the mock's calls.
- **Return something a test can build.** Records are fine. An aggregate query returns `AggregateResult`, which a test cannot build, so the seam copies each row into a small plain class (the example's `GivingTotal`). That copy is the one extra line a seam may hold.
- **Callouts** go through the same seam (a `send` method), so the tests need no `HttpCalloutMock`. Without a seam, use `Test.setMock` as usual.

The `check` command reports any query or save outside a class that implements the seam's interface (`D1`).

## Access: run as the person in the flow

An action runs for whoever runs the flow, and must see and change only what they can.

- **`with sharing`** on the class: queries return only the records the person can see.
- **`WITH USER_MODE`** on every query, `as user` on every save (`insert as user records;`), `AccessLevel.USER_MODE` on every `Database.*` call. User mode also enforces object and field permissions, which `with sharing` alone does not. It needs API version 57.0 or later.
- **System mode only when the user agrees.** Sometimes a flow needs one read past the person's access, such as a total over records a guest cannot see. Say so to the user first, in plain words: what it exposes, to whom. If they agree, use `WITH SYSTEM_MODE` on that one query only, return only the fields the flow shows, and put the reason in a one-line comment above it. Never use system mode to get past an error someone hit; grant the access instead.

Whoever runs the flow also needs **access to the class itself**: Apex Class Access on a permission set they hold, or on their profile. An administrator has it already, so a flow that works for you can fail for everyone else until the class is added to their permission set.

Who "the person" is depends on the caller:

| Called from | Runs as | What to know |
|---|---|---|
| A screen flow staff run | The staff member | Their profile, permission sets and sharing apply |
| A screen flow on a site for guests or signed-in members | The guest user or the member | They see little. Grant reads with guest sharing rules and permission sets: the **flow-access-fix** skill does this |
| A record-triggered or scheduled flow | The user whose change started it, or the flow's running user | Usually staff; check who loads data |
| A Flow Tool Kit conversion (mapping) flow | The conversion's running user: Salesforce's Automated Process user unless the org names one | Automated Process has no permission sets, so user-mode queries see nothing it lacks access to. Name a running user as the **new-mapping-flow** skill describes, rather than switching the action to system mode |

## Records the flow hands in may be missing fields

When an input is a record (`public Contact contact;`) or a list of records, the action receives whatever shape the calling flow built: a Get Records with only some fields, a record assembled in an Assignment. Reading a field that was never queried throws `SObjectException`, and one thin record fails every request in the call.

Guard every read of a field you did not require:

```apex
String email = request.contact.isSet(Contact.Email) ? request.contact.Email : null;
```

or take Ids as inputs and query the fields yourself, as the example does. Give the test one deliberately thin record, built in memory with only `Id` set, so the guard is proven.

## Failing

Two kinds of trouble, handled differently:

- **The flow is built wrong** (a required input is blank, an input is the wrong kind of record): throw the custom exception with a message that says what to fix, for example `Get Account Giving Summary needs an Account ID on every request. Check the value the flow passes in.` The whole call fails, and the flow's fault path shows the message. Keep messages in a constant so the test can assert them.
- **The data is unusual** (no gifts this year, no match found): return a normal result the flow can branch on. Zero, blank or an `isFound`-style output, only if the flow actually needs to branch.

Never catch an exception just to hide it. A caught exception that returns an empty result looks like "no data" to the flow.

## Callouts

An action that calls an outside service sets `callout=true` on `@InvocableMethod`. It tells Flow the action calls out, so a screen flow left to "let the flow decide" its transactions can run the action in a transaction of its own. Make one callout for the whole list when the service accepts a batch; each callout counts toward the transaction's 100. A callout cannot follow uncommitted work in the same transaction, so a flow that saves records before the action needs the action on a separate path (an asynchronous path in a record-triggered flow).

## House style for the code

- One-line control statements with no braces and no wrapping: `if (request.accountId == null) throw new ...;`, `for (InvokedRequest request : requests) results.add(process(request, givingMap));`. Braces only for blocks of several statements.
- Guard clauses at the top instead of nesting: `if (giving == null) return result;`.
- Ternaries for defaults: `request.year != null ? request.year : Date.today().year()`.
- Full words, no abbreviations. Maps end in `Map`, Sets in `Set`, Lists are plural: `givingMap`, `accountIdSet`, `results`. Short loop variables (`request`, `row`, `record`) are fine.
- `String.isNotBlank()` for Strings, `isEmpty()` for collections, `!= null` for everything else.
- Comments only for a reason the code cannot show. No comment that restates the next line.
- Build only what a flow needs today: no "in case" inputs, outputs or options.
