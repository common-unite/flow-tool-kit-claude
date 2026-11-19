@IsTest
private class Account_Giving_Summary_Invocable_Test {

    @IsTest
    static void totalsTheAccountForTheYear() {
        Id accountId = fakeId(Account.SObjectType, 1);
        MockDataAccess mock = useMock(new List<Account_Giving_Summary_Invocable.GivingTotal>{
            new Account_Giving_Summary_Invocable.GivingTotal(accountId, 2025, 350, 2, Date.newInstance(2025, 9, 15)),
            new Account_Giving_Summary_Invocable.GivingTotal(accountId, 2024, 999, 1, Date.newInstance(2024, 12, 31)),
            new Account_Giving_Summary_Invocable.GivingTotal(fakeId(Account.SObjectType, 2), 2025, 75, 1, Date.newInstance(2025, 4, 1))
        });

        Account_Giving_Summary_Invocable.InvokedResult result = summarize(accountId, 2025);

        Assert.areEqual(350, result.totalAmount);
        Assert.areEqual(2, result.giftCount);
        Assert.areEqual(Date.newInstance(2025, 9, 15), result.lastGiftDate);
        Assert.areEqual(1, mock.readCount);
        Assert.areEqual(new Set<Id>{ accountId }, mock.accountIdSet);
        Assert.areEqual(Date.newInstance(2025, 1, 1), mock.firstDay);
        Assert.areEqual(Date.newInstance(2025, 12, 31), mock.lastDay);
    }

    @IsTest
    static void blankYearMeansThisYear() {
        Id accountId = fakeId(Account.SObjectType, 1);
        Integer thisYear = Date.today().year();
        MockDataAccess mock = useMock(new List<Account_Giving_Summary_Invocable.GivingTotal>{
            new Account_Giving_Summary_Invocable.GivingTotal(accountId, thisYear, 40, 1, Date.today())
        });

        Account_Giving_Summary_Invocable.InvokedResult result = summarize(accountId, null);

        Assert.areEqual(40, result.totalAmount);
        Assert.areEqual(1, result.giftCount);
        Assert.areEqual(Date.newInstance(thisYear, 1, 1), mock.firstDay);
        Assert.areEqual(Date.newInstance(thisYear, 12, 31), mock.lastDay);
    }

    @IsTest
    static void accountWithNoGiftsReturnsZero() {
        useMock(new List<Account_Giving_Summary_Invocable.GivingTotal>());

        Account_Giving_Summary_Invocable.InvokedResult result = summarize(fakeId(Account.SObjectType, 1), 2025);

        Assert.areEqual(0, result.totalAmount);
        Assert.areEqual(0, result.giftCount);
        Assert.isNull(result.lastGiftDate);
    }

    @IsTest
    static void giftsWithNoAmountTotalZero() {
        Id accountId = fakeId(Account.SObjectType, 1);
        useMock(new List<Account_Giving_Summary_Invocable.GivingTotal>{
            new Account_Giving_Summary_Invocable.GivingTotal(accountId, 2025, null, 2, Date.newInstance(2025, 2, 1))
        });

        Account_Giving_Summary_Invocable.InvokedResult result = summarize(accountId, 2025);

        Assert.areEqual(0, result.totalAmount);
        Assert.areEqual(2, result.giftCount);
    }

    @IsTest
    static void requestsForDifferentYearsShareOneRead() {
        Id accountId = fakeId(Account.SObjectType, 1);
        MockDataAccess mock = useMock(new List<Account_Giving_Summary_Invocable.GivingTotal>{
            new Account_Giving_Summary_Invocable.GivingTotal(accountId, 2024, 120, 1, Date.newInstance(2024, 6, 1)),
            new Account_Giving_Summary_Invocable.GivingTotal(accountId, 2025, 80, 1, Date.newInstance(2025, 6, 1))
        });

        List<Account_Giving_Summary_Invocable.InvokedResult> results = Account_Giving_Summary_Invocable.getGivingSummary(
            new List<Account_Giving_Summary_Invocable.InvokedRequest>{ request(accountId, 2025), request(accountId, 2024) }
        );

        Assert.areEqual(80, results[0].totalAmount);
        Assert.areEqual(120, results[1].totalAmount);
        Assert.areEqual(1, mock.readCount, 'Both years come from one read');
        Assert.areEqual(Date.newInstance(2024, 1, 1), mock.firstDay);
        Assert.areEqual(Date.newInstance(2025, 12, 31), mock.lastDay);
    }

    @IsTest
    static void missingAccountIdFailsTheRun() {
        MockDataAccess mock = useMock(new List<Account_Giving_Summary_Invocable.GivingTotal>());
        try {
            summarize(null, 2025);
            Assert.fail('A request with no Account ID must fail the run');
        } catch (Account_Giving_Summary_Invocable.Account_Giving_Summary_Exception error) {
            Assert.areEqual(Account_Giving_Summary_Invocable.MISSING_ACCOUNT, error.getMessage());
        }
        Assert.areEqual(0, mock.readCount, 'Nothing is read for a run that fails');
    }

    @IsTest
    static void twoHundredRequestsReadOnceAndTouchNoData() {
        List<Account_Giving_Summary_Invocable.GivingTotal> totals = new List<Account_Giving_Summary_Invocable.GivingTotal>();
        List<Account_Giving_Summary_Invocable.InvokedRequest> requests = new List<Account_Giving_Summary_Invocable.InvokedRequest>();
        for (Integer i = 0; i < 200; i++) {
            Id accountId = fakeId(Account.SObjectType, i + 1);
            totals.add(new Account_Giving_Summary_Invocable.GivingTotal(accountId, 2025, i + 1, 1, Date.newInstance(2025, 5, 1)));
            requests.add(request(accountId, 2025));
        }
        MockDataAccess mock = useMock(totals);

        List<Account_Giving_Summary_Invocable.InvokedResult> results = Account_Giving_Summary_Invocable.getGivingSummary(requests);

        Assert.areEqual(200, results.size());
        for (Integer i = 0; i < 200; i++) Assert.areEqual(i + 1, results[i].totalAmount);
        Assert.areEqual(1, mock.readCount, 'One read for all 200 requests');
        Assert.areEqual(200, mock.accountIdSet.size());
        Assert.areEqual(0, Limits.getQueries(), 'The mock answers every read, so no query reaches the org');
        Assert.areEqual(0, Limits.getDmlStatements(), 'Nothing is written to the org');
    }

    static Account_Giving_Summary_Invocable.InvokedResult summarize(Id accountId, Integer year) {
        List<Account_Giving_Summary_Invocable.InvokedResult> results = Account_Giving_Summary_Invocable.getGivingSummary(
            new List<Account_Giving_Summary_Invocable.InvokedRequest>{ request(accountId, year) }
        );
        Assert.areEqual(1, results.size());
        return results[0];
    }

    static Account_Giving_Summary_Invocable.InvokedRequest request(Id accountId, Integer year) {
        Account_Giving_Summary_Invocable.InvokedRequest request = new Account_Giving_Summary_Invocable.InvokedRequest();
        request.accountId = accountId;
        request.year = year;
        return request;
    }

    static MockDataAccess useMock(List<Account_Giving_Summary_Invocable.GivingTotal> totals) {
        MockDataAccess mock = new MockDataAccess();
        mock.totals = totals;
        Account_Giving_Summary_Invocable.dataAccess = mock;
        return mock;
    }

    // A valid-looking Id for the object. Nothing is saved, so no record has this Id in any org
    static Id fakeId(Schema.SObjectType objectType, Integer index) {
        return Id.valueOf(objectType.getDescribe().getKeyPrefix() + String.valueOf(index).leftPad(12, '0'));
    }

    // Stands in for the database: returns every row a test gives it, so the tests also prove the action matches rows to requests, and remembers what it was asked for
    private class MockDataAccess implements Account_Giving_Summary_Invocable.DataAccess {
        public List<Account_Giving_Summary_Invocable.GivingTotal> totals = new List<Account_Giving_Summary_Invocable.GivingTotal>();
        public Integer readCount = 0;
        public Set<Id> accountIdSet;
        public Date firstDay;
        public Date lastDay;

        public List<Account_Giving_Summary_Invocable.GivingTotal> givingTotals(Set<Id> accountIdSet, Date firstDay, Date lastDay) {
            readCount++;
            this.accountIdSet = accountIdSet;
            this.firstDay = firstDay;
            this.lastDay = lastDay;
            return totals;
        }
    }
}
