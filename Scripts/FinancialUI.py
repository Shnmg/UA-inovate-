import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import pandas as pd
from Scripts.Main import FinancialFlowchartGenerator, convert_csv

class FinancialFlowchartUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Financial Flowchart Generator")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Create the main generator instance
        self.generator = FinancialFlowchartGenerator()
        
        # Create the main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.upload_tab = ttk.Frame(self.notebook)
        self.manual_tab = ttk.Frame(self.notebook)
        self.results_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.upload_tab, text="Upload CSV")
        self.notebook.add(self.manual_tab, text="Manual Entry")
        self.notebook.add(self.results_tab, text="Results")
        
        # Setup each tab
        self.setup_upload_tab()
        self.setup_manual_tab()
        self.setup_results_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_upload_tab(self):
        """Setup the CSV upload tab"""
        # Frame for upload controls
        upload_frame = ttk.LabelFrame(self.upload_tab, text="Upload Financial Data CSV", padding="10")
        upload_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # CSV file path entry
        ttk.Label(upload_frame, text="CSV File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.csv_path_var = tk.StringVar()
        self.csv_path_entry = ttk.Entry(upload_frame, textvariable=self.csv_path_var, width=50)
        self.csv_path_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        
        # Browse button
        self.browse_button = ttk.Button(upload_frame, text="Browse...", command=self.browse_csv)
        self.browse_button.grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # Convert CSV checkbox
        self.convert_csv_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(upload_frame, text="Auto-convert CSV to compatible format", 
                      variable=self.convert_csv_var).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # CSV format info
        ttk.Label(upload_frame, text="CSV Format Requirements:").grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        csv_info = (
            "The CSV file should contain the following columns:\n"
            "- monthly_income: Monthly income amount\n"
            "- housing: Monthly housing/rent expenses\n"
            "- food: Monthly food expenses\n"
            "- transportation: Monthly transportation expenses\n"
            "- books_supplies: Monthly books and supplies expenses\n"
            "- entertainment: Monthly entertainment expenses\n"
            "- personal_care: Monthly personal care expenses\n"
            "- technology: Monthly technology expenses\n"
            "- health_wellness: Monthly health and wellness expenses\n"
            "- miscellaneous: Other monthly expenses\n"
            "- tuition: Tuition expenses (will be treated as student loan debt)\n"
            "\nNote: The system will calculate averages if multiple rows are provided.\n"
            "Savings will be estimated based on income minus expenses.\n"
        )
        info_text = tk.Text(upload_frame, wrap=tk.WORD, height=15, width=60)
        info_text.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        info_text.insert(tk.END, csv_info)
        info_text.config(state=tk.DISABLED)
        
        # Sample CSV download
        sample_frame = ttk.Frame(upload_frame)
        sample_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=10)
        ttk.Label(sample_frame, text="Need a template?").pack(side=tk.LEFT, padx=5)
        ttk.Button(sample_frame, text="Download Sample CSV", command=self.download_sample_csv).pack(side=tk.LEFT, padx=5)
        
        # Process button
        process_frame = ttk.Frame(upload_frame)
        process_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        self.process_button = ttk.Button(process_frame, text="Process CSV", command=self.process_csv)
        self.process_button.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(process_frame, text="View CSV Conversion Help", 
                  command=self.show_conversion_help).pack(side=tk.LEFT, padx=10)
    
    def setup_manual_tab(self):
        """Setup the manual data entry tab"""
        # Create a canvas with scrollbar for the manual entry form
        canvas = tk.Canvas(self.manual_tab)
        scrollbar = ttk.Scrollbar(self.manual_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Income section
        income_frame = ttk.LabelFrame(scrollable_frame, text="Income Information", padding="10")
        income_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        ttk.Label(income_frame, text="Monthly Income ($):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.income_monthly_var = tk.DoubleVar(value=0.0)
        ttk.Entry(income_frame, textvariable=self.income_monthly_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Expenses section
        expenses_frame = ttk.LabelFrame(scrollable_frame, text="Monthly Expenses", padding="10")
        expenses_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        expense_categories = [
            ("Rent/Mortgage ($):", "rent"),
            ("Food ($):", "food"),
            ("Transportation ($):", "transportation"),
            ("Books/Supplies ($):", "books_supplies"),
            ("Entertainment ($):", "entertainment"),
            ("Personal Care ($):", "personal_care"),
            ("Technology ($):", "technology"),
            ("Health/Wellness ($):", "health_wellness"),
            ("Impulsive ($):", "impulsive"),
            ("Other ($):", "other")
        ]
        
        self.expense_vars = {}
        for i, (label_text, category) in enumerate(expense_categories):
            ttk.Label(expenses_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, pady=5)
            self.expense_vars[category] = tk.DoubleVar(value=0.0)
            ttk.Entry(expenses_frame, textvariable=self.expense_vars[category], width=15).grid(row=i, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Savings section
        savings_frame = ttk.LabelFrame(scrollable_frame, text="Savings Information", padding="10")
        savings_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        ttk.Label(savings_frame, text="Current Savings ($):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.savings_current_var = tk.DoubleVar(value=0.0)
        ttk.Entry(savings_frame, textvariable=self.savings_current_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(savings_frame, text="Monthly Contribution ($):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.savings_monthly_var = tk.DoubleVar(value=0.0)
        ttk.Entry(savings_frame, textvariable=self.savings_monthly_var, width=15).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Debt section
        debt_frame = ttk.LabelFrame(scrollable_frame, text="Debt Information", padding="10")
        debt_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        debt_types = [
            ("Credit Cards", "credit_cards"),
            ("Student Loans", "student_loans"),
            ("Car Loans", "car_loans"),
            ("Personal Loans", "personal_loans"),
            ("Other", "other_debt")
        ]
        
        self.debt_amount_vars = {}
        self.debt_interest_vars = {}
        
        ttk.Label(debt_frame, text="Debt Type").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(debt_frame, text="Amount ($)").grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Label(debt_frame, text="Interest Rate (%)").grid(row=0, column=2, sticky=tk.W, pady=5)
        
        for i, (label_text, debt_type) in enumerate(debt_types):
            ttk.Label(debt_frame, text=label_text).grid(row=i+1, column=0, sticky=tk.W, pady=5)
            
            self.debt_amount_vars[debt_type] = tk.DoubleVar(value=0.0)
            ttk.Entry(debt_frame, textvariable=self.debt_amount_vars[debt_type], width=15).grid(row=i+1, column=1, sticky=tk.W, pady=5, padx=5)
            
            self.debt_interest_vars[debt_type] = tk.DoubleVar(value=0.0)
            ttk.Entry(debt_frame, textvariable=self.debt_interest_vars[debt_type], width=15).grid(row=i+1, column=2, sticky=tk.W, pady=5, padx=5)
        
        # High-ticket purchases section
        purchases_frame = ttk.LabelFrame(scrollable_frame, text="High-Ticket Purchases (over $500)", padding="10")
        purchases_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        self.purchases_frame = ttk.Frame(purchases_frame)
        self.purchases_frame.pack(fill=tk.X, expand=True)
        
        self.purchases = []
        ttk.Button(purchases_frame, text="Add Purchase", command=self.add_purchase_row).pack(pady=10)
        
        # Process button
        process_frame = ttk.Frame(scrollable_frame)
        process_frame.pack(fill=tk.X, expand=False, padx=10, pady=20)
        ttk.Button(process_frame, text="Process Manual Data", command=self.process_manual_data).pack()
    
    def setup_results_tab(self):
        """Setup the results tab"""
        # Create a canvas with scrollbar for the results
        canvas = tk.Canvas(self.results_tab)
        scrollbar = ttk.Scrollbar(self.results_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Results content
        self.results_frame = scrollable_frame
        
        # Initial message
        ttk.Label(self.results_frame, text="Process data to see results", font=("Arial", 12, "italic")).pack(pady=20)
        
        # Placeholder for flowchart image
        self.flowchart_frame = ttk.LabelFrame(self.results_frame, text="Financial Flowchart", padding="10")
        self.flowchart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Placeholder for recommendations
        self.recommendations_frame = ttk.LabelFrame(self.results_frame, text="Recommendations", padding="10")
        self.recommendations_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def browse_csv(self):
        """Open file dialog to select CSV file"""
        filepath = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filepath:
            self.csv_path_var.set(filepath)
    
    def download_sample_csv(self):
        """Create and save a sample CSV template"""
        try:
            # Create sample data
            sample_data = {
                'monthly_income': [3000],
                'housing': [1000],
                'food': [400],
                'transportation': [150],
                'books_supplies': [200],
                'entertainment': [100],
                'personal_care': [100],
                'technology': [150],
                'health_wellness': [100],
                'miscellaneous': [50],
                'tuition': [10000]
            }
            
            # Convert to DataFrame
            df = pd.DataFrame(sample_data)
            
            # Ask user where to save the file
            filepath = filedialog.asksaveasfilename(
                title="Save Sample CSV Template",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")]
            )
            
            if filepath:
                df.to_csv(filepath, index=False)
                messagebox.showinfo("Success", f"Sample CSV template saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create sample CSV: {str(e)}")
    
    def add_purchase_row(self):
        """Add a new row for high-ticket purchase entry"""
        purchase_frame = ttk.Frame(self.purchases_frame)
        purchase_frame.pack(fill=tk.X, expand=True, pady=5)
        
        # Create variables for this purchase
        item_var = tk.StringVar()
        amount_var = tk.DoubleVar(value=0.0)
        date_var = tk.StringVar()
        category_var = tk.StringVar()
        
        # Store the variables
        purchase_data = {
            'frame': purchase_frame,
            'item': item_var,
            'amount': amount_var,
            'date': date_var,
            'category': category_var
        }
        self.purchases.append(purchase_data)
        
        # Create the widgets
        ttk.Label(purchase_frame, text="Item:").grid(row=0, column=0, sticky=tk.W, padx=2)
        ttk.Entry(purchase_frame, textvariable=item_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=2)
        
        ttk.Label(purchase_frame, text="Amount ($):").grid(row=0, column=2, sticky=tk.W, padx=2)
        ttk.Entry(purchase_frame, textvariable=amount_var, width=10).grid(row=0, column=3, sticky=tk.W, padx=2)
        
        ttk.Label(purchase_frame, text="Date (MM/DD/YYYY):").grid(row=0, column=4, sticky=tk.W, padx=2)
        ttk.Entry(purchase_frame, textvariable=date_var, width=12).grid(row=0, column=5, sticky=tk.W, padx=2)
        
        ttk.Label(purchase_frame, text="Category:").grid(row=0, column=6, sticky=tk.W, padx=2)
        ttk.Entry(purchase_frame, textvariable=category_var, width=10).grid(row=0, column=7, sticky=tk.W, padx=2)
        
        # Remove button
        remove_btn = ttk.Button(purchase_frame, text="X", width=2, 
                               command=lambda pf=purchase_frame, pd=purchase_data: self.remove_purchase_row(pf, pd))
        remove_btn.grid(row=0, column=8, sticky=tk.W, padx=2)
    
    def remove_purchase_row(self, frame, purchase_data):
        """Remove a high-ticket purchase entry row"""
        frame.destroy()
        if purchase_data in self.purchases:
            self.purchases.remove(purchase_data)
    
    def process_csv(self):
        """Process the uploaded CSV file"""
        csv_path = self.csv_path_var.get().strip()
        
        if not csv_path:
            messagebox.showerror("Error", "Please select a CSV file first")
            return
        
        if not os.path.exists(csv_path):
            messagebox.showerror("Error", f"File not found: {csv_path}")
            return
        
        try:
            self.status_var.set("Processing CSV file...")
            self.root.update_idletasks()
            
            # Check if conversion is needed
            if self.convert_csv_var.get():
                self.status_var.set("Converting CSV file...")
                self.root.update_idletasks()
                converted_path = convert_csv(csv_path)
                if not converted_path:
                    messagebox.showerror("Error", "Failed to convert CSV file")
                    self.status_var.set("CSV conversion failed")
                    return
                csv_path = converted_path
            
            # Import data from CSV
            self.status_var.set("Importing data from CSV...")
            self.root.update_idletasks()
            result = self.generator.import_from_csv(csv_path)
            
            if not result:
                messagebox.showerror("Error", "Failed to import data from CSV file")
                self.status_var.set("CSV import failed")
                return
            
            # Analyze data and generate recommendations
            self.status_var.set("Analyzing financial data...")
            self.root.update_idletasks()
            self.generator.analyze_data()
            self.generator.generate_ai_recommendations()
            
            # Generate financial summary
            self.status_var.set("Generating financial summary...")
            self.root.update_idletasks()
            summary_file = self.generator.generate_summary()
            
            # Display results
            self.display_results(summary_file)
            
            self.status_var.set("CSV processing complete")
            
            # Switch to results tab
            self.notebook.select(self.results_tab)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process CSV: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_var.set("Error processing CSV")
    
    def process_manual_data(self):
        """Process manually entered data"""
        try:
            self.status_var.set("Processing manual data...")
            self.root.update_idletasks()
            
            # Collect income data
            self.generator.user_data['income'] = {
                'monthly': self.income_monthly_var.get()
            }
            
            # Collect expenses data
            self.generator.user_data['expenses'] = {
                'Rent/Mortgage': self.expense_vars['rent'].get(),
                'Food': self.expense_vars['food'].get(),
                'Transportation': self.expense_vars['transportation'].get(),
                'Books/Supplies': self.expense_vars['books_supplies'].get(),
                'Entertainment': self.expense_vars['entertainment'].get(),
                'Personal Care': self.expense_vars['personal_care'].get(),
                'Technology': self.expense_vars['technology'].get(),
                'Health/Wellness': self.expense_vars['health_wellness'].get(),
                'Other': self.expense_vars['other'].get()
            }
            
            # Collect savings data
            self.generator.user_data['savings'] = {
                'current': self.savings_current_var.get(),
                'monthly_contribution': self.savings_monthly_var.get()
            }
            
            # Collect debt data
            self.generator.user_data['debt'] = {}
            debt_mapping = {
                'credit_cards': 'Credit Cards',
                'student_loans': 'Student Loans',
                'car_loans': 'Car Loans',
                'personal_loans': 'Personal Loans',
                'other_debt': 'Other'
            }
            
            for key, label in debt_mapping.items():
                amount = self.debt_amount_vars[key].get()
                if amount > 0:
                    self.generator.user_data['debt'][label] = {
                        'amount': amount,
                        'interest': self.debt_interest_vars[key].get()
                    }
            
            # Collect high-ticket purchases
            self.generator.user_data['high_ticket_purchases'] = []
            for purchase in self.purchases:
                item = purchase['item'].get().strip()
                amount = purchase['amount'].get()
                date_str = purchase['date'].get().strip()
                category = purchase['category'].get().strip()
                
                if item and amount > 0 and date_str and category:
                    try:
                        from datetime import datetime
                        date = datetime.strptime(date_str, "%m/%d/%Y").date()
                        self.generator.user_data['high_ticket_purchases'].append({
                            'item': item,
                            'amount': amount,
                            'date': date,
                            'category': category
                        })
                    except ValueError:
                        messagebox.showwarning("Warning", f"Invalid date format for {item}. This purchase will be skipped.")
            
            # Analyze data and generate recommendations
            self.generator.analyze_data()
            self.generator.generate_ai_recommendations()
            
            # Generate summary
            summary_file = self.generator.generate_summary()
            
            # Display results
            self.display_results(summary_file)
            
            self.status_var.set("Manual data processing complete")
            
            # Switch to results tab
            self.notebook.select(self.results_tab)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process manual data: {str(e)}")
            self.status_var.set("Error processing manual data")
    
    def display_results(self, flowchart_file):
        """Display the results in the results tab"""
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Title
        ttk.Label(self.results_frame, text="Financial Analysis Results", 
                 font=("Arial", 16, "bold")).pack(pady=(10, 20))
        
        # Display financial summary
        summary_frame = ttk.LabelFrame(self.results_frame, text="Financial Summary", padding="10")
        summary_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        if os.path.exists(flowchart_file):  # Now this is actually a text file
            # Create a text widget to display the summary
            summary_text = tk.Text(summary_frame, wrap=tk.WORD, height=20, width=80)
            summary_text.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
            
            # Read and display the summary content
            with open(flowchart_file, 'r') as f:
                summary_content = f.read()
                summary_text.insert(tk.END, summary_content)
            
            summary_text.config(state=tk.DISABLED)  # Make it read-only
            
            # Add a button to open the text file externally
            ttk.Button(summary_frame, text="Open Summary Externally", 
                      command=lambda: os.system(f"open {flowchart_file}")).pack(pady=5)
        else:
            ttk.Label(summary_frame, text="Financial summary not found", 
                     font=("Arial", 12, "italic")).pack(pady=20)
        
        # Display financial metrics
        metrics_frame = ttk.LabelFrame(self.results_frame, text="Financial Metrics", padding="10")
        metrics_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        metrics_text = (
            f"Monthly Income: ${self.generator.user_data['income']['monthly']:.2f}\n"
            f"Total Monthly Expenses: ${self.generator.financial_metrics['total_expenses']:.2f}\n"
            f"Discretionary Income: ${self.generator.financial_metrics['discretionary_income']:.2f}\n"
            f"Total Debt: ${self.generator.financial_metrics['total_debt']:.2f}\n"
            f"Debt-to-Income Ratio: {self.generator.financial_metrics['debt_to_income']*100:.1f}%\n"
            f"Savings Rate: {self.generator.financial_metrics['savings_rate']*100:.1f}%\n"
        )
        
        metrics_label = ttk.Label(metrics_frame, text=metrics_text, justify=tk.LEFT)
        metrics_label.pack(anchor=tk.W, padx=10, pady=10)
        
        # Display recommendations
        if self.generator.recommendations:
            rec_frame = ttk.LabelFrame(self.results_frame, text="Recommendations", padding="10")
            rec_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Create a canvas with scrollbar for recommendations
            canvas = tk.Canvas(rec_frame)
            scrollbar = ttk.Scrollbar(rec_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            # Configure the canvas
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Pack the canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            scrollbar.pack(side="right", fill="y")
            
            # Add recommendations with better styling
            for i, rec in enumerate(self.generator.recommendations):
                # Determine color based on category
                if rec.get('category') == 'AI Suggestion':
                    bg_color = '#e6f2ff'  # Light blue for AI recommendations
                    category_text = 'AI Recommendation'
                else:
                    bg_color = '#f5f5f5'  # Light gray for standard recommendations
                    category_text = rec.get('category', 'General')
                
                # Create a frame for each recommendation
                rec_item_frame = ttk.Frame(scrollable_frame)
                rec_item_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
                
                # Add a colored category indicator
                category_label = ttk.Label(rec_item_frame, 
                                          text=category_text,
                                          background=bg_color,
                                          foreground='#333333',
                                          padding=(5, 2))
                category_label.pack(anchor=tk.W, padx=10, pady=(5, 0))
                
                # Add the recommendation title
                title_label = ttk.Label(rec_item_frame, 
                                       text=f"{i+1}. {rec['title']}", 
                                       font=("Arial", 12, "bold"),
                                       wraplength=650,
                                       justify=tk.LEFT)
                title_label.pack(anchor=tk.W, padx=10, pady=(5, 0))
                
                # Add the description with better formatting
                desc_text = tk.Text(rec_item_frame, wrap=tk.WORD, height=4, width=80,
                                  relief=tk.FLAT, padx=10, pady=5)
                desc_text.insert(tk.END, rec['description'])
                desc_text.config(state=tk.DISABLED)  # Make it read-only
                desc_text.pack(fill=tk.X, expand=True, padx=20, pady=5)
                
                # Add a separator
                ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, padx=10, pady=5)
        
        # Export button
        export_frame = ttk.Frame(self.results_frame)
        export_frame.pack(fill=tk.X, expand=False, padx=10, pady=20)
        
        ttk.Button(export_frame, text="Export Report to PDF", 
                  command=self.export_report_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Export Data to CSV", 
                  command=self.export_data_csv).pack(side=tk.LEFT, padx=5)
    
    def export_report_pdf(self):
        """Export the financial report to PDF"""
        try:
            filepath = filedialog.asksaveasfilename(
                title="Save PDF Report",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")]
            )
            
            if filepath:
                # This is a placeholder - in a real implementation, you would use a PDF library
                messagebox.showinfo("Feature Not Implemented", 
                                   "PDF export functionality would be implemented here using a library like ReportLab.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
    
    def show_conversion_help(self):
        """Show information about CSV conversion"""
        help_window = tk.Toplevel(self.root)
        help_window.title("CSV Conversion Help")
        help_window.geometry("700x500")
        
        # Create a frame with scrollbar
        frame = ttk.Frame(help_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a scrollable text widget
        text = tk.Text(frame, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Help content
        help_content = """
        CSV CONVERSION FUNCTIONALITY
        
        The auto-conversion feature can process any CSV file by matching column names to the required financial categories. 
        
        HOW IT WORKS:
        
        1. You provide any CSV file with financial data
        2. The converter scans the column names looking for matches to our required categories
        3. It creates a new converted CSV file that our system can use
        
        COLUMN NAME MATCHING:
        
        The converter will look for these keywords in your column names (case insensitive):
        
        • monthly_income: 'income', 'salary', 'wage', 'earnings', 'revenue'
        • housing: 'housing', 'rent', 'mortgage', 'home', 'apartment', 'accommodation'
        • food: 'food', 'groceries', 'meals', 'dining'
        • transportation: 'transportation', 'transit', 'commute', 'travel', 'car', 'gas', 'fuel'
        • books_supplies: 'books', 'supplies', 'stationery', 'textbooks', 'materials'
        • entertainment: 'entertainment', 'leisure', 'recreation', 'fun', 'hobbies'
        • personal_care: 'personal', 'care', 'hygiene', 'beauty', 'haircut', 'cosmetics'
        • technology: 'technology', 'tech', 'electronics', 'gadgets', 'devices', 'computer', 'phone'
        • health_wellness: 'health', 'wellness', 'medical', 'fitness', 'gym', 'doctor'
        • miscellaneous: 'miscellaneous', 'misc', 'other', 'general', 'additional'
        • tuition: 'tuition', 'education', 'school', 'college', 'university', 'fees'
        
        EXAMPLE:
        
        If your CSV has a column named 'Monthly Salary', it will be mapped to 'monthly_income'.
        If your CSV has a column named 'Apartment Rent', it will be mapped to 'housing'.
        
        Any categories that aren't found will be set to zero.
        
        The converted file will be saved with '_converted' added to the original filename.
        """
        
        text.insert(tk.END, help_content)
        text.config(state=tk.DISABLED)  # Make it read-only
        
        # Close button
        ttk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)
    
    def export_data_csv(self):
        """Export the financial data to CSV"""
        try:
            filepath = filedialog.asksaveasfilename(
                title="Save Data as CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")]
            )
            
            if filepath:
                # Create a dictionary with all the financial data
                data = {
                    'monthly_income': [self.generator.user_data['income']['monthly']],
                }
                
                # Add expenses
                expense_mapping = {
                    'Rent/Mortgage': 'housing',
                    'Food': 'food',
                    'Transportation': 'transportation',
                    'Books/Supplies': 'books_supplies',
                    'Entertainment': 'entertainment',
                    'Personal Care': 'personal_care',
                    'Technology': 'technology',
                    'Health/Wellness': 'health_wellness',
                    'Impulsive': 'impulsive',
                    'Other': 'miscellaneous'
                }
                
                for category, csv_key in expense_mapping.items():
                    if category in self.generator.user_data['expenses']:
                        data[csv_key] = [self.generator.user_data['expenses'][category]]
                    else:
                        data[csv_key] = [0.0]
                
                # Add tuition (from student loans debt)
                if 'Student Loans' in self.generator.user_data['debt']:
                    data['tuition'] = [self.generator.user_data['debt']['Student Loans']['amount']]
                else:
                    data['tuition'] = [0.0]
                
                # Convert to DataFrame and save
                df = pd.DataFrame(data)
                df.to_csv(filepath, index=False)
                messagebox.showinfo("Success", f"Data exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {str(e)}")

def main():
    root = tk.Tk()
    app = FinancialFlowchartUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
