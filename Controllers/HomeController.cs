using CsvHelper;
using FinancialLiteracyApp.Data;
using FinancialLiteracyApp.Models;
using Microsoft.AspNetCore.Mvc;
using System.Globalization;

namespace FinancialLiteracyApp.Controllers
{
    public class HomeController : Controller
    {
        private readonly AppDbContext _context;

        public HomeController(AppDbContext context) => _context = context;

        public IActionResult Index() => View();

        public IActionResult FinancialTools() => View(_context.FinancialProducts.OrderBy(p => p.TimelinePosition).ToList());

        public IActionResult Detail(int id) => View(_context.FinancialProducts.Find(id));

        [HttpPost]
        public async Task<IActionResult> ImportCsv(IFormFile file)
        {
            try
            {
                using var reader = new StreamReader(file.OpenReadStream());
                using var csv = new CsvReader(reader, CultureInfo.InvariantCulture);
                var records = csv.GetRecords<FinancialProduct>().ToList();
                
                _context.FinancialProducts.RemoveRange(_context.FinancialProducts);
                await _context.FinancialProducts.AddRangeAsync(records);
                await _context.SaveChangesAsync();
                
                TempData["Message"] = "Imported successfully! Roll Tide!";
            }
            catch (Exception ex)
            {
                TempData["Error"] = $"Error: {ex.Message}";
            }
            return RedirectToAction("Index");
        }
    }
}