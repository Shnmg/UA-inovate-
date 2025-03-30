using Microsoft.EntityFrameworkCore;
using FinancialLiteracyApp.Models;

namespace FinancialLiteracyApp.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) 
            : base(options)
        {
        }

        public DbSet<FinancialProduct> FinancialProducts { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);
            // Add any model configuration here
        }
    }
}