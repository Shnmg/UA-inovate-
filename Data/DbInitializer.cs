using FinancialLiteracyApp.Models;
using Microsoft.EntityFrameworkCore;

namespace FinancialLiteracyApp.Data
{
    public static class DbInitializer
    {
        public static void Initialize(AppDbContext context)
        {
            context.Database.EnsureCreated();

            if (context.FinancialProducts.Any()) return;

            var products = new List<FinancialProduct>
            {
                new FinancialProduct 
                {
                    Name = "Student Credit Cards",
                    ShortDescription = "Build credit responsibly while in college",
                    DetailedDescription = "Learn how to use credit cards...",
                    Benefits = "Establish credit history, Earn cashback rewards...",
                    HowToGetStarted = "1. Check your credit score...",
                    ImageUrl = "/images/credit-card.png",
                    LearnMoreUrl = "https://www.nerdwallet.com/...",
                    TimelinePosition = 1,  // Now valid property
                    IsPriority = true      // Now valid property
                },
                // ... rest of your products
            };

            context.FinancialProducts.AddRange(products);
            context.SaveChanges();
        }
    }
}