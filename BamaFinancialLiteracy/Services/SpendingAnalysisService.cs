using FinancialLiteracyApp.Models;
using System.Diagnostics;
using System.Text.Json;
using System.Text;

namespace FinancialLiteracyApp.Services
{
    public class SpendingAnalysisService
    {
        private readonly ILogger<SpendingAnalysisService> _logger;
        private readonly string _pythonScriptsPath;
        
        public SpendingAnalysisService(ILogger<SpendingAnalysisService> logger, IWebHostEnvironment env)
        {
            _logger = logger;
            
            // Path to the Python scripts directory
            _pythonScriptsPath = Path.Combine(env.ContentRootPath, "..", "Scripts");
        }
        
        public async Task<List<Transaction>> AnalyzeTransactions(List<Transaction> transactions)
        {
            try
            {
                // Prepare data for the Python script
                var transactionData = new
                {
                    user_id = 1, // Default user ID
                    transactions = transactions.Select(t => new
                    {
                        amount = t.Amount,
                        category = string.IsNullOrEmpty(t.Category) ? "other" : t.Category.ToLower(),
                        timestamp = t.Timestamp.ToString("yyyy-MM-dd HH:mm:ss"),
                    }).ToList()
                };
                
                // Convert to JSON
                string jsonInput = JsonSerializer.Serialize(transactionData);
                
                // Create a temporary JSON file
                string tempInputFile = Path.GetTempFileName();
                string tempOutputFile = Path.GetTempFileName();
                
                await File.WriteAllTextAsync(tempInputFile, jsonInput);
                
                // Run Python script (Main.py) with the temp file
                var startInfo = new ProcessStartInfo
                {
                    FileName = "python3", // or "python" depending on your system
                    Arguments = $"\"{Path.Combine(_pythonScriptsPath, "batch_analyze.py")}\" \"{tempInputFile}\" \"{tempOutputFile}\"",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                
                _logger.LogInformation($"Running Python script: {startInfo.FileName} {startInfo.Arguments}");
                
                using (var process = Process.Start(startInfo))
                {
                    if (process == null)
                    {
                        _logger.LogError("Could not start Python process");
                        return transactions;
                    }
                    
                    string output = await process.StandardOutput.ReadToEndAsync();
                    string error = await process.StandardError.ReadToEndAsync();
                    
                    await process.WaitForExitAsync();
                    
                    if (process.ExitCode != 0)
                    {
                        _logger.LogError($"Python script error (Exit code {process.ExitCode}): {error}");
                        return transactions;
                    }
                    
                    _logger.LogInformation($"Python script output: {output}");
                }
                
                // Read the analysis results
                if (File.Exists(tempOutputFile))
                {
                    string jsonOutput = await File.ReadAllTextAsync(tempOutputFile);
                    var analysisResults = JsonSerializer.Deserialize<Dictionary<int, TransactionAnalysis>>(jsonOutput);
                    
                    if (analysisResults != null)
                    {
                        // Update transactions with analysis results
                        for (int i = 0; i < transactions.Count; i++)
                        {
                            if (analysisResults.TryGetValue(i, out var analysis))
                            {
                                transactions[i].Flagged = analysis.Flagged;
                                transactions[i].AnalysisAdvice = analysis.Advice;
                                transactions[i].AnalysisImpact = analysis.Impact;
                                transactions[i].AnalysisTags = analysis.Tags ?? new List<string>();
                            }
                        }
                    }
                    
                    // Clean up temp files
                    File.Delete(tempInputFile);
                    File.Delete(tempOutputFile);
                }
                
                return transactions;
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error analyzing transactions: {ex.Message}");
                return transactions;
            }
        }
    }
    
    public class TransactionAnalysis
    {
        public bool Flagged { get; set; }
        public string? Advice { get; set; }
        public string? Impact { get; set; }
        public List<string>? Tags { get; set; }
    }
}
