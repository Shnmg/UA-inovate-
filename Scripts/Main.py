import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from datetime import datetime
import csv
import os
import re
import sys
import google.generativeai as genai
import logging
from spending_ai import FinancialSummaryGenerator

# IMPORTANT: Replace "YOUR_API_KEY" with your actual key
# Consider using environment variables for better security in real projects
GOOGLE_API_KEY="AIzaSyAos5KMB9rs-XaEwlnIErHjESDEt-daryQ"
genai.configure(api_key=GOOGLE_API_KEY)

# Model configuration is set up

# Initialize AI model
AI_MODEL = genai.GenerativeModel('gemini-2.0-flash-lite')
AI_ENABLED = True

class FinancialSummaryGenerator:
    def __init__(self):
        self.user_data = {
            'income': {},
            'expenses': {},
            'savings': {},
            'debt': {},
            'high_ticket_purchases': []
        }
        self.financial_metrics = {}
        self.recommendations = [] # This will store AI recommendations now

        # --- AI SETUP ---
        try:
            # Use the globally initialized model
            self.ai_model = AI_MODEL
            self.ai_enabled = AI_ENABLED
        except Exception as e:
            # Fall back to standard recommendations if AI fails
            self.ai_enabled = False
        # --- End AI Setup ---

    def collect_user_data(self):
        """Collect financial data from the user through command-line interface"""
        print("\n===== FINANCIAL DATA COLLECTION =====\n")
        
        # Income data
        print("INCOME INFORMATION:")
        self.user_data['income']['monthly'] = self._get_numeric_input("Enter your monthly income: $")
        
        # Expenses data
        print("\nEXPENSE INFORMATION:")
        categories = ['Rent/Mortgage', 'Utilities', 'Food', 'Transportation', 'Entertainment', 'Insurance', 'Other']
        self.user_data['expenses'] = {}
        for category in categories:
            self.user_data['expenses'][category] = self._get_numeric_input(f"Enter your monthly {category} expenses: $")
        
        # Savings data
        print("\nSAVINGS INFORMATION:")
        self.user_data['savings']['current'] = self._get_numeric_input("Enter your current savings amount: $")
        self.user_data['savings']['monthly_contribution'] = self._get_numeric_input("Enter your monthly savings contribution: $")
        
        # Debt data
        print("\nDEBT INFORMATION:")
        debt_types = ['Credit Cards', 'Student Loans', 'Car Loans', 'Personal Loans', 'Other']
        self.user_data['debt'] = {}
        for debt_type in debt_types:
            amount = self._get_numeric_input(f"Enter your {debt_type} debt amount (0 if none): $")
            if amount > 0:
                interest = self._get_numeric_input(f"Enter the interest rate for {debt_type} (%): ")
                self.user_data['debt'][debt_type] = {'amount': amount, 'interest': interest}
        
        # High-ticket purchases
        print("\nHIGH-TICKET PURCHASES:")
        print("Enter information about recent high-ticket purchases (over $500)")
        while True:
            add_purchase = input("Would you like to add a high-ticket purchase? (yes/no): ").lower()
            if add_purchase != 'yes':
                break
            
            item = input("Enter purchase description: ")
            amount = self._get_numeric_input("Enter purchase amount: $")
            date_str = input("Enter purchase date (MM/DD/YYYY): ")
            category = input("Enter purchase category: ")
            
            try:
                date = datetime.strptime(date_str, "%m/%d/%Y").date()
                self.user_data['high_ticket_purchases'].append({
                    'item': item,
                    'amount': amount,
                    'date': date,
                    'category': category
                })
            except ValueError:
                print("Invalid date format. Please try again.")

    def import_from_csv(self, filepath):
        """Import financial data from a CSV file"""
        try:
            # Read the CSV file using pandas
            df = pd.read_csv(filepath)
            
            # Extract income data
            if 'monthly_income' in df.columns:
                # Calculate average monthly income across all records
                avg_monthly_income = df['monthly_income'].mean()
                self.user_data['income']['monthly'] = avg_monthly_income
            
            # Extract expense data
            expense_categories = {
                'housing': 'Rent/Mortgage',
                'food': 'Food',
                'transportation': 'Transportation',
                'books_supplies': 'Books/Supplies',
                'entertainment': 'Entertainment',
                'personal_care': 'Personal Care',
                'technology': 'Technology',
                'health_wellness': 'Health/Wellness',
                'miscellaneous': 'Other'
            }
            
            self.user_data['expenses'] = {}
            for csv_cat, program_cat in expense_categories.items():
                if csv_cat in df.columns:
                    # Calculate average expense across all records
                    avg_expense = df[csv_cat].mean()
                    self.user_data['expenses'][program_cat] = avg_expense
            
            # Extract savings data (we'll have to estimate this)
            if 'monthly_income' in df.columns and all(cat in df.columns for cat in expense_categories.keys()):
                # Calculate average total expenses
                total_expenses = sum(df[cat].mean() for cat in expense_categories.keys() if cat in df.columns)
                # Estimate monthly savings as income - expenses
                estimated_savings = max(0, avg_monthly_income - total_expenses)
                self.user_data['savings']['monthly_contribution'] = estimated_savings
                # Set a default current savings (this would need user input in a real scenario)
                self.user_data['savings']['current'] = estimated_savings * 3  # Rough estimate of 3 months savings
            
            # Extract debt data (tuition can be considered as debt)
            self.user_data['debt'] = {}
            if 'tuition' in df.columns:
                avg_tuition = df['tuition'].mean()
                if avg_tuition > 0:
                    self.user_data['debt']['Student Loans'] = {
                        'amount': avg_tuition,
                        'interest': 5.0  # Assuming 5% interest as default
                    }
            
            # We don't have high-ticket purchase data in the CSV, so leave it empty
            self.user_data['high_ticket_purchases'] = []
            
            print(f"Successfully imported data from {filepath}")
            print("Note: Some values are averages calculated from the dataset.")
            print("You can modify these values when reviewing the analysis.")
            return True
            
        except Exception as e:
            print(f"Error importing CSV: {e}")
            # Print more details for debugging
            import traceback
            traceback.print_exc()
            return False

    def analyze_data(self):
        """Analyze the user's financial data and calculate key metrics"""
        # Calculate total monthly expenses
        total_expenses = sum(self.user_data['expenses'].values())
        
        # Calculate total debt
        total_debt = sum(item['amount'] for item in self.user_data['debt'].values())
        
        # Calculate total high-ticket purchases
        high_ticket_total = sum(purchase['amount'] for purchase in self.user_data['high_ticket_purchases'])
        
        # Calculate debt-to-income ratio
        monthly_income = self.user_data['income']['monthly']
        debt_to_income = (total_debt / 12) / monthly_income if monthly_income > 0 else float('inf')
        
        # Calculate savings rate
        savings_rate = self.user_data['savings']['monthly_contribution'] / monthly_income if monthly_income > 0 else 0
        
        # Calculate discretionary income
        discretionary_income = monthly_income - total_expenses
        
        # Store calculated metrics
        self.financial_metrics = {
            'total_expenses': total_expenses,
            'total_debt': total_debt,
            'high_ticket_total': high_ticket_total,
            'debt_to_income': debt_to_income,
            'savings_rate': savings_rate,
            'discretionary_income': discretionary_income
        }
        
        # Analyze high-ticket purchases
        if self.user_data['high_ticket_purchases']:
            by_category = {}
            for purchase in self.user_data['high_ticket_purchases']:
                category = purchase['category']
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(purchase)
            
            self.financial_metrics['high_ticket_by_category'] = by_category
        # Standard recommendations generated
    
    def generate_ai_recommendations(self):
        """Generate personalized recommendations using an AI model."""
        if not self.ai_enabled:
            # Fallback to standard recommendations
            self.generate_standard_recommendations()
            return
        self.recommendations = [] # Clear previous recommendations

        # --- 1. Construct the Prompt ---
        # Gather key data points for the AI
        income = self.user_data['income'].get('monthly', 0)
        expenses = self.financial_metrics.get('total_expenses', 0)
        savings_rate = self.financial_metrics.get('savings_rate', 0) * 100
        debt_ratio = self.financial_metrics.get('debt_to_income', 0) * 100
        total_debt = self.financial_metrics.get('total_debt', 0)
        debt_details = self.user_data.get('debt', {})
        high_ticket_purchases = self.user_data.get('high_ticket_purchases', [])

        # Format high-ticket purchases for the prompt
        ht_summary = "None"
        if high_ticket_purchases:
            ht_summary_list = [
                f"- {p['item']} (${p['amount']:.2f}, Category: {p.get('category', 'N/A')})"
                for p in high_ticket_purchases
            ]
            ht_summary = "\n".join(ht_summary_list)

        # The core prompt engineering happens here!
        prompt = f"""
        Act as a friendly financial advisor specializing in helping young adults in their twenties.
        Analyze the following financial snapshot and recent high-ticket spending activity (purchases over $500).
        Provide 3-5 actionable, personalized recommendations focused on improving money management skills and building financial literacy for long-term success.
        Tailor the advice considering the user is likely in their twenties. Be specific about how the high-ticket spending impacts their situation and goals.
        Format the output as a list of recommendations, each with a clear 'Title:' and 'Description:'.

        Financial Snapshot:
        - Monthly Income: ${income:.2f}
        - Total Monthly Expenses: ${expenses:.2f}
        - Savings Rate: {savings_rate:.1f}%
        - Debt-to-Income Ratio: {debt_ratio:.1f}%
        - Total Debt: ${total_debt:.2f}
        - Debt Details: {debt_details}
        - Recent High-Ticket Purchases:
        {ht_summary}

        Recommendations:
        """

        # --- 2. Call the AI Model ---
        try:
            # Send request to AI model and get response
            response = self.ai_model.generate_content(prompt)
            ai_text = response.text

            # --- 3. Parse the AI Response ---
            # Process AI response into structured recommendations
            
            # Try to extract recommendations in a more robust way
            parsed_recs = []
            
            # Split by numbered items or bullet points
            sections = re.split(r'\n\s*(?:\d+\.\s*|•\s*|\*\s*)', ai_text)
            
            # Remove any empty sections
            sections = [s.strip() for s in sections if s.strip()]
            
            # Process each section that looks like a recommendation
            for section in sections:
                if len(section) < 10:  # Skip very short sections
                    continue
                    
                # Try to extract title and description
                title_match = re.search(r'(?:Title:\s*|\*\*)(.*?)(?:\.|\n|$)', section)
                desc_match = re.search(r'(?:Description:\s*|\n\s*)(.*)', section, re.DOTALL)
                
                if title_match:
                    title = title_match.group(1).strip()
                    description = desc_match.group(1).strip() if desc_match else section
                    
                    # If we couldn't extract a separate description, use the whole section
                    # but remove the title part
                    if not desc_match and title:
                        description = re.sub(r'(?:Title:\s*|\*\*)(.*?)(?:\.|\n|$)', '', section, 1).strip()
                    
                    # Create a recommendation
                    if title and description:
                        parsed_recs.append({
                            'title': title,
                            'description': description,
                            'category': 'AI Suggestion'
                        })
            
            # If parsing fails, try a simpler approach - just split by lines and use first line as title
            if not parsed_recs:
                print("First parsing approach failed, trying simpler method...")
                lines = [line.strip() for line in ai_text.splitlines() if line.strip()]
                
                i = 0
                while i < len(lines):
                    if len(lines[i]) > 5 and not lines[i].startswith("Financial") and not lines[i].startswith("Recommendation"):
                        title = lines[i]
                        description = ""
                        
                        # Collect the next lines as description until we hit another potential title
                        i += 1
                        while i < len(lines) and not (len(lines[i]) < 60 and lines[i].endswith(":")):
                            description += lines[i] + " "
                            i += 1
                        
                        if title and description:
                            parsed_recs.append({
                                'title': title,
                                'description': description.strip(),
                                'category': 'AI Suggestion'
                            })
                    else:
                        i += 1

            # Basic validation: Ensure we got something reasonable
            if parsed_recs and all('title' in r and 'description' in r for r in parsed_recs):
                 # Assign category (optional, could ask AI for this too)
                 for rec in parsed_recs:
                     rec['category'] = "AI Suggestion" # Add a category
                 self.recommendations = parsed_recs
                 # AI recommendations successfully generated
                 pass
            else:
                # AI response parsing failed, use standard recommendations
                self.generate_standard_recommendations()

        except Exception as e:
            # Error occurred, use standard recommendations
            self.generate_standard_recommendations()
            
    def analyze_transaction(self, transaction_data):
        """Analyze a specific transaction and provide AI feedback.
        
        Args:
            transaction_data: Dictionary containing transaction details such as:
                - amount: float, the transaction amount
                - category: str, the transaction category
                - timestamp: datetime, when the transaction occurred
                - financial_context: dict, additional financial context (optional)
                
        Returns:
            dict: Analysis results containing:
                - advice: str, personalized advice about the transaction
                - tags: list, relevant behavior tags (e.g., 'impulsive', 'planned')
                - impact: str, assessment of financial impact
        """        
        if not self.ai_enabled:
            # Fallback to basic analysis if AI is not available
            return self._basic_transaction_analysis(transaction_data)
            
        # Unpack transaction data with defaults
        amount = transaction_data.get('amount', 0)
        category = transaction_data.get('category', 'unknown')
        timestamp = transaction_data.get('timestamp', datetime.now())
        financial_context = transaction_data.get('financial_context', {})
        
        # Format time for context
        time_of_day = timestamp.strftime('%H:%M')
        day_of_week = timestamp.strftime('%A')
        date_str = timestamp.strftime('%Y-%m-%d')
        
        # Extract useful context if available
        monthly_income = financial_context.get('monthly_income', 0)
        budget_limit = financial_context.get('budget_limit', {}).get(category, 0)
        current_spending = financial_context.get('current_spending', {}).get(category, 0)
        
        # Prepare budget context
        budget_context = ""
        if budget_limit > 0:
            remaining = budget_limit - current_spending
            budget_context = f"\nBudget for {category}: ${budget_limit:.2f}\nAlready spent this month: ${current_spending:.2f}\nRemaining budget: ${remaining:.2f}"
        
        # Prepare income context
        income_context = ""
        if monthly_income > 0:
            percentage = (amount / monthly_income) * 100
            income_context = f"\nThis transaction represents {percentage:.1f}% of your monthly income."
        
        # Construct AI prompt
        prompt = f"""
        Act as a personal financial assistant analyzing a single transaction. Provide immediate, concise feedback on this spending:
        
        Transaction details:
        - Amount: ${amount:.2f}
        - Category: {category}
        - Date: {date_str}
        - Time: {time_of_day} ({day_of_week})
        {budget_context}
        {income_context}
        
        Analyze this specific transaction and provide:
        1. SPENDING ADVICE: One or two sentences of personalized feedback on this specific purchase. Consider timing, amount, category, and financial context.
        2. BEHAVIOR TAGS: Classify this spending with 1-3 brief tags (e.g. 'essential', 'impulsive', 'planned', 'recreational')
        3. FINANCIAL IMPACT: A single sentence assessment of how this affects the person's overall financial health.
        
        Format your response like this:
        ADVICE: [your specific advice]
        TAGS: [tag1, tag2, tag3]
        IMPACT: [impact assessment]
        """
        
        try:
            # Send request to AI model and get response
            response = self.ai_model.generate_content(prompt)
            ai_text = response.text.strip()
            
            # Parse the AI response
            advice = ""
            tags = []
            impact = ""
            
            # Extract the advice section
            advice_match = re.search(r'ADVICE:\s*(.*?)(?:\n|$)', ai_text, re.DOTALL)
            if advice_match:
                advice = advice_match.group(1).strip()
            
            # Extract the tags
            tags_match = re.search(r'TAGS:\s*(.*?)(?:\n|$)', ai_text)
            if tags_match:
                # Split tags by commas and clean them up
                tags_text = tags_match.group(1).strip()
                tags = [tag.strip().lower() for tag in re.split(r'[,\s]+', tags_text) if tag.strip()]
            
            # Extract the impact assessment
            impact_match = re.search(r'IMPACT:\s*(.*?)(?:\n|$)', ai_text, re.DOTALL)
            if impact_match:
                impact = impact_match.group(1).strip()
            
            # Ensure we have at least the minimum required data
            if not advice:
                advice = "Consider whether this purchase aligns with your financial goals."
            if not tags:
                tags = ["unclassified"]
            if not impact:
                impact = "This transaction's impact is unclear without more context."
                
            return {
                'advice': advice,
                'tags': tags,
                'impact': impact,
                'ai_generated': True
            }
            
        except Exception as e:
            print(f"Error generating AI transaction analysis: {e}")
            # Fallback to basic analysis
            return self._basic_transaction_analysis(transaction_data)
    
    def _basic_transaction_analysis(self, transaction_data):
        """Provide basic transaction analysis without AI."""
        amount = transaction_data.get('amount', 0)
        category = transaction_data.get('category', 'unknown')
        
        # Very simple rules-based analysis
        advice = "Consider tracking your spending in this category over time."
        tags = ["tracked"]
        impact = "This transaction has been recorded in your financial history."
        
        # Categorize based on amount thresholds
        if amount > 100:
            tags.append("significant")
            advice = "This is a significant purchase. Make sure it aligns with your priorities."
            impact = "Larger purchases can impact your monthly budget significantly."
        elif amount < 10:
            tags.append("small")
        
        # Categorize based on category type
        essential_categories = ['groceries', 'utilities', 'rent', 'mortgage', 'healthcare', 'transportation']
        if category.lower() in essential_categories:
            tags.append("essential")
            advice = "Essential spending is necessary, but still look for ways to optimize."
            impact = "Essential spending is part of your necessary monthly expenses."
        else:
            tags.append("discretionary")
            if amount > 50:
                advice = "For discretionary spending, always consider if the value matches the cost."
                impact = "Non-essential purchases should be balanced with your saving goals."
        
        return {
            'advice': advice,
            'tags': tags,
            'impact': impact,
            'ai_generated': False
        }
        
    def generate_summary(self, output_file="financial_summary.txt"):
        
        # Create a text-based summary instead of a visual flowchart
        with open(output_file, 'w') as f:
            # Write header
            f.write("===== FINANCIAL SUMMARY =====\n\n")
            
            # Write income information
            monthly_income = self.user_data['income'].get('monthly', 0)
            f.write(f"Monthly Income: ${monthly_income:.2f}\n\n")
            
            # Write expense information
            f.write("EXPENSES:\n")
            total_expenses = self.financial_metrics.get('total_expenses', 0)
            for category, amount in self.user_data['expenses'].items():
                percentage = (amount / monthly_income) * 100 if monthly_income > 0 else 0
                f.write(f"  {category}: ${amount:.2f} ({percentage:.1f}% of income)\n")
            f.write(f"  Total Expenses: ${total_expenses:.2f}\n\n")
            
            # Write savings information
            savings_contrib = self.user_data['savings'].get('monthly_contribution', 0)
            savings_rate = self.financial_metrics.get('savings_rate', 0) * 100
            f.write(f"Monthly Savings: ${savings_contrib:.2f} ({savings_rate:.1f}% of income)\n\n")
            
            # Write debt information if any
            if self.user_data.get('debt'):
                f.write("DEBT:\n")
                for debt_type, details in self.user_data['debt'].items():
                    interest = details.get('interest', 0)
                    f.write(f"  {debt_type}: ${details['amount']:.2f} at {interest:.1f}% interest\n")
                f.write(f"  Total Debt: ${self.financial_metrics.get('total_debt', 0):.2f}\n\n")
            
            # Write high-ticket purchases if any
            if self.user_data.get('high_ticket_purchases'):
                f.write("HIGH-TICKET PURCHASES:\n")
                for purchase in self.user_data['high_ticket_purchases']:
                    f.write(f"  {purchase['item']}: ${purchase['amount']:.2f} ({purchase.get('category', 'N/A')})\n")
                f.write("\n")
            
            # Write recommendations
            if self.recommendations:
                f.write("RECOMMENDATIONS:\n\n")
                for i, rec in enumerate(self.recommendations):
                        # Format the recommendation title with category
                    f.write(f"  {i+1}. {rec['title']} ({rec.get('category', 'General')})\n")
                    
                    # Format the description with proper indentation and wrapping
                    description = rec['description']
                    # Wrap the description text to ~80 characters with proper indentation
                    wrapped_lines = []
                    current_line = "     "
                    
                    # Split description into words and reconstruct with wrapping
                    for word in description.split():
                        if len(current_line + word) > 85:  # Allow some buffer
                            wrapped_lines.append(current_line)
                            current_line = "     " + word + " "
                        else:
                            current_line += word + " "
                    
                    # Add the last line if not empty
                    if current_line.strip():
                        wrapped_lines.append(current_line)
                    
                    # Write the wrapped description
                    for line in wrapped_lines:
                        f.write(f"{line}\n")
                    
                    f.write("\n")
                f.write("\n")
            else:
                f.write("RECOMMENDATIONS:\n\n  No specific recommendations available for your financial situation.\n\n")
        
        # File saved
        return output_file

    def generate_report(self):
        """Generate a textual report of the financial analysis and recommendations"""
        print("\n===== FINANCIAL ANALYSIS REPORT =====\n")
        
        # Print income and expense summary
        monthly_income = self.user_data['income']['monthly']
        total_expenses = self.financial_metrics['total_expenses']
        print(f"Monthly Income: ${monthly_income:.2f}")
        print(f"Total Monthly Expenses: ${total_expenses:.2f}")
        print(f"Discretionary Income: ${self.financial_metrics['discretionary_income']:.2f}")
        
        # Print expense breakdown
        print("\nEXPENSE BREAKDOWN:")
        for category, amount in self.user_data['expenses'].items():
            percentage = (amount / total_expenses) * 100 if total_expenses > 0 else 0
            print(f"  {category}: ${amount:.2f} ({percentage:.1f}%)")
        
        # Print savings information
        print("\nSAVINGS INFORMATION:")
        current_savings = self.user_data['savings']['current']
        monthly_contribution = self.user_data['savings']['monthly_contribution']
        savings_rate = self.financial_metrics['savings_rate'] * 100
        print(f"  Current Savings: ${current_savings:.2f}")
        print(f"  Monthly Contribution: ${monthly_contribution:.2f}")
        print(f"  Savings Rate: {savings_rate:.1f}% of income")
        
        # Print debt information
        print("\nDEBT INFORMATION:")
        total_debt = self.financial_metrics['total_debt']
        debt_to_income = self.financial_metrics['debt_to_income'] * 100
        print(f"  Total Debt: ${total_debt:.2f}")
        print(f"  Debt-to-Income Ratio: {debt_to_income:.1f}%")
        
        # Print high-ticket purchases
        if self.user_data['high_ticket_purchases']:
            print("\nHIGH-TICKET PURCHASES:")
            for purchase in self.user_data['high_ticket_purchases']:
                print(f"  {purchase['item']}: ${purchase['amount']:.2f} on {purchase['date'].strftime('%m/%d/%Y')} (Category: {purchase['category']})")
        
        # Print recommendations
        if self.recommendations:
            print("\nFINANCIAL RECOMMENDATIONS:")
            for i, rec in enumerate(self.recommendations):
                print(f"\n{i+1}. {rec['title']} ({rec['category']})")
                print(f"   {rec['description']}")

    def _get_numeric_input(self, prompt):
        """Helper method to get valid numeric input from user"""
        while True:
            try:
                value = float(input(prompt))
                if value < 0:
                    print("Please enter a non-negative value.")
                    continue
                return value
            except ValueError:
                print("Please enter a valid number.")

def convert_csv(input_file, output_file=None):
    """Convert any CSV file to the format expected by the financial analyzer
    
    Args:
        input_file: Path to the input CSV file
        output_file: Path to save the converted CSV file (if None, will use input_file with '_converted' suffix)
    
    Returns:
        Path to the converted CSV file
    """
    if output_file is None:
        # Generate output filename based on input filename
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_converted{ext}"
    
    try:
        # Read the input CSV file
        df = pd.read_csv(input_file)
        columns = df.columns.tolist()
        
        # Create a new DataFrame with expected columns
        new_data = {
            'monthly_income': [],
            'housing': [],
            'food': [],
            'transportation': [],
            'books_supplies': [],
            'entertainment': [],
            'personal_care': [],
            'technology': [],
            'health_wellness': [],
            'miscellaneous': [],
            'tuition': []
        }
        
        # Helper function to find matching columns using regex patterns
        def find_matching_columns(pattern, columns):
            return [col for col in columns if re.search(pattern, col.lower())]
        
        # Map input columns to expected columns
        column_mapping = {
            'monthly_income': ['income', 'salary', 'wage', 'earnings', 'revenue'],
            'housing': ['housing', 'rent', 'mortgage', 'home', 'apartment', 'accommodation'],
            'food': ['food', 'groceries', 'meals', 'dining'],
            'transportation': ['transportation', 'transit', 'commute', 'travel', 'car', 'gas', 'fuel'],
            'books_supplies': ['books', 'supplies', 'stationery', 'textbooks', 'materials'],
            'entertainment': ['entertainment', 'leisure', 'recreation', 'fun', 'hobbies'],
            'personal_care': ['personal', 'care', 'hygiene', 'beauty', 'haircut', 'cosmetics'],
            'technology': ['technology', 'tech', 'electronics', 'gadgets', 'devices', 'computer', 'phone'],
            'health_wellness': ['health', 'wellness', 'medical', 'fitness', 'gym', 'doctor'],
            'miscellaneous': ['miscellaneous', 'misc', 'other', 'general', 'additional'],
            'tuition': ['tuition', 'education', 'school', 'college', 'university', 'fees']
        }
        
        # Find columns in the input CSV that match expected categories
        matched_columns = {}
        for target_col, patterns in column_mapping.items():
            for pattern in patterns:
                matches = find_matching_columns(pattern, columns)
                if matches:
                    matched_columns[target_col] = matches[0]  # Use the first match
                    break
        
        # For each row in the input CSV, create a row in the new DataFrame
        for _, row in df.iterrows():
            new_row = {}
            
            # Fill in values for matched columns
            for target_col, source_col in matched_columns.items():
                if pd.notna(row.get(source_col, None)):
                    try:
                        # Try to convert to float, use 0 if fails
                        new_row[target_col] = float(row[source_col])
                    except (ValueError, TypeError):
                        new_row[target_col] = 0.0
                else:
                    new_row[target_col] = 0.0
            
            # Fill in any missing columns with 0
            for col in new_data.keys():
                if col not in new_row:
                    new_row[col] = 0.0
                new_data[col].append(new_row[col])
        
        # Create and save the new DataFrame
        new_df = pd.DataFrame(new_data)
        new_df.to_csv(output_file, index=False)
        
        print(f"\nSuccessfully converted CSV file to compatible format.")
        print(f"Converted file saved as: {output_file}")
        print(f"\nThe following mappings were used:")
        for target_col, source_col in matched_columns.items():
            print(f"  {source_col} -> {target_col}")
        print(f"\nCategory matches not found were set to 0.")
        
        return output_file
    
    except Exception as e:
        print(f"Error converting CSV file: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    # --- Argument Handling --- 
    csv_file_path_arg = None
    if len(sys.argv) > 1:
        csv_file_path_arg = sys.argv[1]
        # Basic check if the argument looks like a path (optional)
        if not os.path.exists(csv_file_path_arg) or not csv_file_path_arg.lower().endswith('.csv'):
            # Log error to stderr if running non-interactively and path is bad
            print(f"Error: Invalid or non-existent CSV path provided: {csv_file_path_arg}", file=sys.stderr)
            sys.exit(1) # Exit if bad path provided via argument

    # --- Conditional Output Control --- 
    # Only print prompts/titles if NOT run with a CSV argument (i.e., interactive mode)
    is_interactive = csv_file_path_arg is None

    if is_interactive:
        print("=" * 50)
        print("FINANCIAL ANALYZER")
        print("=" * 50)
        print("This program will help you analyze your financial situation and generate\n"
              "a summary with personalized recommendations for better money management.")
    
    # Create an instance of the analysis class
    generator = FinancialSummaryGenerator()
    
    # --- Data Input --- 
    user_data = None
    if csv_file_path_arg:
        # Load directly from CSV provided via argument
        try:
            user_data = generator.import_from_csv(csv_file_path_arg)
        except FileNotFoundError:
            print(f"Error: CSV file not found at: {csv_file_path_arg}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error processing CSV file {csv_file_path_arg}: {e}", file=sys.stderr)
            sys.exit(1)
    else: # Interactive mode
        if is_interactive:
             print("\nHow would you like to input your financial data?")
             print("1. Enter data manually")
             print("2. Import from standard CSV file")
             print("3. Convert and import any CSV file")
        
        while True:
            if is_interactive:
                choice = input("Enter your choice (1, 2, or 3): ")
            else: # Should not happen if logic is correct, but as fallback
                choice = '1' 

            if choice == '1':
                generator.collect_user_data()
                user_data = generator.user_data
                break
            elif choice == '2':
                if is_interactive:
                    csv_file_path = input("Enter the path to your standard CSV file: ")
                else:
                     # Should not be reached if csv_file_path_arg was set
                     print("Error: Interactive choice selected in non-interactive mode.", file=sys.stderr)
                     sys.exit(1)
                try:
                    user_data = generator.import_from_csv(csv_file_path)
                    break
                except FileNotFoundError:
                     if is_interactive: print("File not found. Please check the path and try again.")
                     else: sys.exit(1)
                except Exception as e:
                     if is_interactive: print(f"Error processing CSV: {e}")
                     else: 
                         print(f"Error processing CSV {csv_file_path}: {e}", file=sys.stderr)
                         sys.exit(1)
            # Removed choice 3 for simplicity when called from C#
            # elif choice == '3': 
            #     # ... (keep convert_and_import logic if needed for interactive use) ...
            #     pass 
            else:
                 if is_interactive: print("Invalid choice. Please enter 1, 2, or 3.")

    # --- Analysis and Output --- 
    if user_data:
        generator.user_data = user_data
        generator.analyze_data()
        generator.generate_ai_recommendations()

        if is_interactive:
            # Print full report in interactive mode
            print("\n===== FINANCIAL ANALYSIS REPORT =====")
            # ... (print the detailed breakdown: income, expenses, savings, debt etc.) ...
            # Example (needs fleshing out based on your FinancialSummaryGenerator details):
            print(f"\nMonthly Income: ${generator.user_data.get('income', {}).get('monthly_income', 0):,.2f}")
            # ... print other sections ...
            print("\nFINANCIAL RECOMMENDATIONS:")
            for i, rec in enumerate(generator.recommendations):
                print(f"\n{i+1}. {rec['title']} ({rec['category']})")
                print(f"   {rec['description']}")
            # Save to file (optional for interactive)
            try:
                with open("financial_summary.txt", "w") as f:
                    # Write the full report here if desired
                    f.write("===== FINANCIAL ANALYSIS REPORT =====\n")
                    # ... write details ...
                    f.write("\nFINANCIAL RECOMMENDATIONS:\n")
                    for i, rec in enumerate(generator.recommendations):
                        f.write(f"\n{i+1}. {rec['title']} ({rec['category']})\n")
                        f.write(f"   {rec['description']}\n")
                print("\nThank you for using the Financial Analyzer!")
                print("Your financial summary has been saved as 'financial_summary.txt'.")
            except IOError as e:
                print(f"\nWarning: Could not save summary to file: {e}")
        else:
            # Only print recommendations to stdout when run non-interactively
            for i, rec in enumerate(generator.recommendations):
                print(f"\n{i+1}. {rec['title']} ({rec['category']})")
                print(f"   {rec['description']}")

if __name__ == "__main__":
    main()