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

        public IActionResult IntegratedTools()
        {
            return View();
        }

        [HttpPost]
        public async Task<IActionResult> ImportCsv(IFormFile file)
        {
            if (file == null || file.Length == 0)
            {
                TempData["Error"] = "Please select a CSV file to upload";
                return RedirectToAction("Analyze"); // Correct: Go back if no file selected
            }

            try
            {
                using var reader = new StreamReader(file.OpenReadStream());
                using var csv = new CsvReader(reader, CultureInfo.InvariantCulture);

                // *************************************************************************
                // Potential Issue: Are you sure you want FinancialProduct here?
                // Your results page uses FinancialLiteracyApp.Models.Transaction.
                // Ensure your CSV maps correctly to the model needed for the results page,
                // or perform a transformation/analysis step here.
                // Let's assume for now FinancialProduct is correct for the import step.
                // *************************************************************************
                csv.Context.RegisterClassMap<FinancialProductMap>();
                var records = csv.GetRecords<FinancialProduct>().ToList();

                // *************************************************************************
                // Potential Issue: This DELETES *all* previous data on every upload.
                // Is this the intended behavior? If not, remove this line.
                _context.FinancialProducts.RemoveRange(_context.FinancialProducts);
                // *************************************************************************

                await _context.FinancialProducts.AddRangeAsync(records);
                await _context.SaveChangesAsync(); // Save changes (including deletions and additions)

                TempData["Message"] = "Imported successfully! Roll Tide!";

                // CHANGE THIS: Redirect to results view on success
                return RedirectToAction("ShowAnalysisResults"); // <--- Replace "ShowAnalysisResults" with your actual results action name
            }
            catch (CsvHelperException ex)
            {
                // Log the full exception details for debugging if needed: _logger.LogError(ex, "CSV parsing error.");
                TempData["Error"] = $"CSV Error: {ex.Message}. Please check the file format.";
                return RedirectToAction("Analyze"); // Correct: Go back to upload on CSV error
            }
            catch (Exception ex)
            {
                // Log the full exception details for debugging: _logger.LogError(ex, "General error during import.");
                TempData["Error"] = $"An unexpected error occurred: {ex.Message}";
                return RedirectToAction("Analyze"); // Correct: Go back to upload on general error
            }

            // This final return statement should ideally not be reachable
            // because all paths (no file, success, errors) already return.
            // However, if you remove it, the compiler might complain.
            // Keeping it as RedirectToAction("Analyze") is a safe fallback.
            // return RedirectToAction("Analyze"); // Can be removed if compiler allows, or kept as fallback.
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
}