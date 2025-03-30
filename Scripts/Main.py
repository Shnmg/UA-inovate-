import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from datetime import datetime
import csv
import os
import re
import google.generativeai as genai

# IMPORTANT: Replace "YOUR_API_KEY" with your actual key
# Consider using environment variables for better security in real projects
GOOGLE_API_KEY="AIzaSyAos5KMB9rs-XaEwlnIErHjESDEt-daryQ"
genai.configure(api_key=GOOGLE_API_KEY)

# Model configuration is set up

# Initialize AI model
AI_MODEL = genai.GenerativeModel('gemini-2.0-flash-lite')
AI_ENABLED = True

class FinancialFlowchartGenerator:
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

    def generate_standard_recommendations(self):
        """Generate personalized financial recommendations based on analysis"""
        # Clear previous recommendations
        self.recommendations = []
        
        # Income and expense recommendations
        monthly_income = self.user_data['income'].get('monthly', 0)
        total_expenses = self.financial_metrics.get('total_expenses', 0)
        expense_ratio = total_expenses / monthly_income if monthly_income > 0 else float('inf')
        
        if expense_ratio > 0.7:
            self.recommendations.append({
                'category': 'Budgeting',
                'title': 'Reduce monthly expenses',
                'description': 'Your expenses are taking up more than 70% of your income. Consider using the 50/30/20 budgeting rule: 50% for needs, 30% for wants, and 20% for savings and debt repayment.'
            })
        
        # Savings recommendations
        savings_rate = self.financial_metrics.get('savings_rate', 0)
        if savings_rate < 0.1:
            self.recommendations.append({
                'category': 'Savings',
                'title': 'Increase savings rate',
                'description': 'Your current savings rate is below 10%. Try to build an emergency fund covering 3-6 months of expenses, then focus on long-term savings goals.'
            })
        
        # Debt recommendations
        debt_to_income = self.financial_metrics.get('debt_to_income', 0)
        if debt_to_income > 0.36:
            self.recommendations.append({
                'category': 'Debt Management',
                'title': 'Reduce debt burden',
                'description': 'Your debt-to-income ratio is high. Consider using the debt snowball method (paying smallest debts first) or debt avalanche method (paying highest interest debts first).'
            })
        
        # High-ticket purchase recommendations
        high_ticket_total = self.financial_metrics.get('high_ticket_total', 0)
        annual_income = monthly_income * 12
        if high_ticket_total > annual_income * 0.2:
            self.recommendations.append({
                'category': 'Spending Habits',
                'title': 'Review high-ticket purchases',
                'description': 'Your high-ticket purchases represent a significant portion of your annual income. Consider implementing a 30-day waiting period before major purchases to reduce impulse buying.'
            })
        
        # General financial literacy recommendations
        self.recommendations.append({
            'category': 'Financial Education',
            'title': 'Continue financial education',
            'description': 'Explore resources like the Consumer Financial Protection Bureau (consumerfinance.gov) for free financial education materials.'
        })
        
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

            # No need to add a last recommendation - we're using a different parsing approach now

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
    print("=" * 50)
    print("FINANCIAL ANALYZER")
    print("=" * 50)
    print("This program will help you analyze your financial situation and generate\n"
          "a summary with personalized recommendations for better money management.")
    
    # Create an instance of the flowchart generator
    generator = FinancialFlowchartGenerator()
    
    # Choose data input method
    print("\nHow would you like to input your financial data?")
    print("1. Enter data manually")
    print("2. Import from CSV file")
    print("3. Convert and import any CSV file")
    
    choice = input("Enter your choice (1, 2, or 3): ")
    
    if choice == "1":
        generator.collect_user_data()
    elif choice == "2":
        csv_path = input("Enter the path to your CSV file: ")
        if os.path.exists(csv_path):
            generator.import_from_csv(csv_path)
        else:
            print("File not found. Falling back to manual input.")
            generator.collect_user_data()
    elif choice == "3":
        csv_path = input("Enter the path to your CSV file: ")
        if os.path.exists(csv_path):
            converted_path = convert_csv(csv_path)
            if converted_path:
                generator.import_from_csv(converted_path)
            else:
                print("CSV conversion failed. Falling back to manual input.")
                generator.collect_user_data()
        else:
            print("File not found. Falling back to manual input.")
            generator.collect_user_data()
    else:
        print("Invalid choice. Falling back to manual input.")
        generator.collect_user_data()
    
    # Analyze the financial data
    generator.analyze_data()
    
    # Generate recommendations
    generator.generate_ai_recommendations()
    
    # Generate textual report
    generator.generate_report()
    
    # Generate and save summary
    summary_file = generator.generate_summary()
    
    print("\nThank you for using the Financial Analyzer!")
    print(f"Your financial summary has been saved as '{summary_file}'.")
    print("Use this summary along with the recommendations to improve your financial literacy and money management skills.")

if __name__ == "__main__":
    main()
    