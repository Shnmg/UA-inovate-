namespace FinancialLiteracyApp.Models
{
    public class Transaction
    {
        public int Id { get; set; }
        public int UserId { get; set; } = 1; // Default to user 1 for simplicity
        public decimal Amount { get; set; }
        public string Category { get; set; } = "other";
        public DateTime Timestamp { get; set; } = DateTime.Now;
        public bool Flagged { get; set; }
        
        // Properties to store AI analysis results
        public string? AnalysisAdvice { get; set; }
        public string? AnalysisImpact { get; set; }
        public List<string> AnalysisTags { get; set; } = new List<string>();
    }
    
    public class TransactionMap : CsvHelper.Configuration.ClassMap<Transaction>
    {
        public TransactionMap()
        {
            // Map common CSV column names to our properties
            Map(m => m.Amount).Name("Amount").Name("Transaction Amount").Name("Debit").Name("Credit");
            Map(m => m.Category).Name("Category").Name("Type").Name("Transaction Type").Optional();
            Map(m => m.Timestamp).Name("Date").Name("Transaction Date").Optional();
            
            // These will be computed by our AI
            Map(m => m.Flagged).Ignore();
            Map(m => m.AnalysisAdvice).Ignore();
            Map(m => m.AnalysisImpact).Ignore();
            Map(m => m.AnalysisTags).Ignore();
        }
    }
}
