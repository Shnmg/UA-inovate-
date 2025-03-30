#!/usr/bin/env python3
import sys
import json
import os
from Main import FinancialSummaryGenerator, AI_ENABLED

def batch_analyze_transactions(input_file, output_file):
    """Process a batch of transactions and analyze them using the FinancialSummaryGenerator."""
    
    # Load input data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    user_id = data.get('user_id', 1)
    transactions = data.get('transactions', [])
    
    if not transactions:
        print("No transactions to analyze")
        with open(output_file, 'w') as f:
            json.dump({}, f)
        return
    
    # Initialize the generator
    generator = FinancialSummaryGenerator()
    
    # Prepare results dictionary: index -> analysis
    results = {}
    
    # Process each transaction
    for idx, transaction in enumerate(transactions):
        # Prepare the transaction data in the expected format
        transaction_data = {
            'user_id': user_id,
            'amount': transaction['amount'],
            'category': transaction['category'],
            'timestamp': transaction['timestamp']
        }
        
        # Skip analysis if AI is disabled
        if not AI_ENABLED:
            results[idx] = {
                'flagged': False,
                'advice': "AI analysis not available",
                'impact': "",
                'tags': []
            }
            continue
        
        # Perform analysis
        try:
            # Determine if transaction is impulsive (flagged)
            flagged = is_potentially_impulsive(transaction_data)
            
            # Get AI analysis
            analysis = generator.analyze_transaction(transaction_data)
            
            # Store analysis results with transaction index
            results[idx] = {
                'flagged': flagged,
                'advice': analysis.get('advice', ''),
                'impact': analysis.get('impact', ''),
                'tags': analysis.get('tags', [])
            }
        except Exception as e:
            print(f"Error analyzing transaction {idx}: {e}")
            results[idx] = {
                'flagged': False,
                'advice': "Error during analysis",
                'impact': "",
                'tags': ["error"]
            }
    
    # Write results to output file
    with open(output_file, 'w') as f:
        json.dump(results, f)
    
    print(f"Analyzed {len(transactions)} transactions")

def is_potentially_impulsive(transaction):
    """
    Simple placeholder for impulsive transaction detection.
    In a full implementation, this would use more sophisticated logic.
    """
    amount = float(transaction['amount'])
    category = transaction['category'].lower()
    
    # Simple logic: higher amounts in discretionary categories might be impulsive
    discretionary_categories = ['entertainment', 'dining', 'shopping']
    
    if category in discretionary_categories and amount > 100:
        return True
    
    # Very high amount transactions in any category might be impulsive
    if amount > 300:
        return True
    
    return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python batch_analyze.py input_file output_file")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}")
        sys.exit(1)
    
    batch_analyze_transactions(input_file, output_file)
