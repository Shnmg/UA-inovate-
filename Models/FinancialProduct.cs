namespace FinancialLiteracyApp.Models
{
    public class FinancialProduct
    {
        public int Id { get; set; }
        public required string Name { get; set; }
        public required string ShortDescription { get; set; }
        public required string DetailedDescription { get; set; }
        public required string Benefits { get; set; }
        public required string HowToGetStarted { get; set; }
        public string ImageUrl { get; set; } = "/images/default.png";
        public string LearnMoreUrl { get; set; } = "#";
        public int TimelinePosition { get; set; }
        public bool IsPriority { get; set; }
    }
}