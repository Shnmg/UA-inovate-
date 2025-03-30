using Microsoft.AspNetCore.Mvc;
using FinancialLiteracyApp.Models;
using FinancialLiteracyApp.Data; // Add this for AppDbContext
using CsvHelper;
using System.Globalization;

namespace FinancialLiteracyApp.Controllers
{
    public class HomeController : Controller
    {
        private readonly AppDbContext _context;

        public HomeController(AppDbContext context)
        {
            _context = context;
        }

        public IActionResult Index()
        {
            return View();
        }

        public IActionResult Finance101()
        {
            return View();
        }

        public IActionResult Analyze()
        {
            return View();
        }

        [HttpPost]
        public async Task<IActionResult> ImportCsv(IFormFile file)
        {
            if (file == null || file.Length == 0)
            {
                TempData["Error"] = "Please select a CSV file to upload";
                return RedirectToAction("Analyze");
            }

            try
            {
                using var reader = new StreamReader(file.OpenReadStream());
                using var csv = new CsvReader(reader, CultureInfo.InvariantCulture);
                
                csv.Context.RegisterClassMap<FinancialProductMap>();
                var records = csv.GetRecords<FinancialProduct>().ToList();
                
                _context.FinancialProducts.RemoveRange(_context.FinancialProducts);
                await _context.FinancialProducts.AddRangeAsync(records);
                await _context.SaveChangesAsync();
                
                TempData["Message"] = "Imported successfully! Roll Tide!";
            }
            catch (CsvHelperException ex)
            {
                TempData["Error"] = $"CSV Error: {ex.Message}";
            }
            catch (Exception ex)
            {
                TempData["Error"] = $"Error: {ex.Message}";
            }
            
            return RedirectToAction("Analyze");
        }
    }

    public class FinancialProductMap : CsvHelper.Configuration.ClassMap<FinancialProduct>
    {
        public FinancialProductMap()
        {
            Map(m => m.Name).Name("Name");
            Map(m => m.ShortDescription).Name("ShortDescription");
            Map(m => m.DetailedDescription).Name("DetailedDescription");
            Map(m => m.Benefits).Name("Benefits");
            Map(m => m.HowToGetStarted).Name("HowToGetStarted");
            Map(m => m.ImageUrl).Name("ImageUrl").Optional();
            Map(m => m.LearnMoreUrl).Name("LearnMoreUrl").Optional();
            Map(m => m.TimelinePosition).Name("TimelinePosition");
            Map(m => m.IsPriority).Name("IsPriority");
        }
    }
}