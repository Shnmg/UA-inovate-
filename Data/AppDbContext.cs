 using FinancialLiteracyApp.Models;
using Microsoft.EntityFrameworkCore;

namespace FinancialLiteracyApp.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

        public DbSet<FinancialProduct> FinancialProducts { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.Entity<FinancialProduct>().HasData(
                new FinancialProduct
                {
                    Id = 1,
                    Name = "Student Credit Card",
                    ShortDescription = "Build credit responsibly",
                    DetailedDescription = "Learn responsible credit card usage...",
                    Benefits = "Establish credit history, Earn rewards",
                    HowToGetStarted = "1. Check credit score\n2. Compare offers",
                    ImageUrl = "/images/credit-card.png",
                    LearnMoreUrl = "#",
                    TimelinePosition = 1,
                    IsPriority = true
                }
            );
        }
    }
}