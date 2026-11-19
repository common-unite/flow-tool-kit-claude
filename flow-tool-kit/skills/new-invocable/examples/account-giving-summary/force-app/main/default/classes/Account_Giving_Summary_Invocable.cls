public with sharing class Account_Giving_Summary_Invocable {

    public class Account_Giving_Summary_Exception extends Exception {}

    @TestVisible private static final String MISSING_ACCOUNT = 'Get Account Giving Summary needs an Account ID on every request. Check the value the flow passes in.';

    // Every read goes through this seam, so the tests swap in a mock and touch no org data
    @TestVisible private static DataAccess dataAccess = new DatabaseAccess();

    @InvocableMethod(Label='Get Account Giving Summary' Description='Totals the won opportunities on an account for one calendar year: the amount given, the number of gifts and the date of the latest gift. Every account in the flow run is totaled in one query, so it is safe in record-triggered and scheduled flows.')
    public static List<InvokedResult> getGivingSummary(List<InvokedRequest> requests) {
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
    }

    private static InvokedResult process(InvokedRequest request, Map<String, GivingTotal> givingMap) {
        InvokedResult result = new InvokedResult();
        GivingTotal giving = givingMap.get(givingKey(request.accountId, givingYear(request)));
        if (giving == null) return result;

        result.totalAmount = giving.totalAmount != null ? giving.totalAmount : 0;
        result.giftCount = giving.giftCount;
        result.lastGiftDate = giving.lastGiftDate;
        return result;
    }

    private static Map<String, GivingTotal> readGiving(Set<Id> accountIdSet, Set<Integer> yearSet) {
        List<Integer> years = new List<Integer>(yearSet);
        years.sort();
        Date firstDay = Date.newInstance(years[0], 1, 1);
        Date lastDay = Date.newInstance(years[years.size() - 1], 12, 31);

        Map<String, GivingTotal> givingMap = new Map<String, GivingTotal>();
        for (GivingTotal giving : dataAccess.givingTotals(accountIdSet, firstDay, lastDay)) givingMap.put(givingKey(giving.accountId, giving.year), giving);
        return givingMap;
    }

    private static Integer givingYear(InvokedRequest request) {
        return request.year != null ? request.year : Date.today().year();
    }

    private static String givingKey(Id accountId, Integer year) {
        return accountId + ':' + year;
    }

    public interface DataAccess {
        List<GivingTotal> givingTotals(Set<Id> accountIdSet, Date firstDay, Date lastDay);
    }

    // The only code that reaches the database. The mock-only tests never run it, so it holds the query and nothing else
    private with sharing class DatabaseAccess implements DataAccess {
        public List<GivingTotal> givingTotals(Set<Id> accountIdSet, Date firstDay, Date lastDay) {
            List<GivingTotal> totals = new List<GivingTotal>();
            for (AggregateResult row : [
                SELECT AccountId accountId, CALENDAR_YEAR(CloseDate) givingYear, SUM(Amount) totalAmount, COUNT(Id) giftCount, MAX(CloseDate) lastGiftDate
                FROM Opportunity
                WHERE IsWon = true AND AccountId IN :accountIdSet AND CloseDate >= :firstDay AND CloseDate <= :lastDay
                WITH USER_MODE
                GROUP BY AccountId, CALENDAR_YEAR(CloseDate)
            ]) totals.add(new GivingTotal((Id) row.get('accountId'), (Integer) row.get('givingYear'), (Decimal) row.get('totalAmount'), (Integer) row.get('giftCount'), (Date) row.get('lastGiftDate')));
            return totals;
        }
    }

    // One account's giving in one year. A plain class rather than the AggregateResult, because a test cannot build an AggregateResult
    public class GivingTotal {
        public Id accountId;
        public Integer year;
        public Decimal totalAmount;
        public Integer giftCount;
        public Date lastGiftDate;

        public GivingTotal(Id accountId, Integer year, Decimal totalAmount, Integer giftCount, Date lastGiftDate) {
            this.accountId = accountId;
            this.year = year;
            this.totalAmount = totalAmount;
            this.giftCount = giftCount;
            this.lastGiftDate = lastGiftDate;
        }
    }

    public class InvokedRequest {
        @InvocableVariable(Label='Account ID' Description='The organization or household account whose giving to total.' Required=true)
        public Id accountId;

        @InvocableVariable(Label='Year' Description='The calendar year to total, such as 2026. Leave blank for the current year.')
        public Integer year;
    }

    public class InvokedResult {
        @InvocableVariable(Label='Total Amount' Description='The sum of the amounts on the won opportunities of the account that closed in the year. 0 when there were none.')
        public Decimal totalAmount = 0;

        @InvocableVariable(Label='Gift Count' Description='How many won opportunities on the account closed in the year. 0 when there were none.')
        public Integer giftCount = 0;

        @InvocableVariable(Label='Last Gift Date' Description='The close date of the latest won opportunity in the year. Blank when there were none.')
        public Date lastGiftDate;
    }
}
