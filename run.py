#!/usr/bin/env python3
"""
Financial Analyzer Launcher
This script allows users to choose between the command-line interface
and the graphical user interface.
"""

import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Financial Analyzer')
    parser.add_argument('--cli', action='store_true', help='Run in command-line interface mode')
    parser.add_argument('--gui', action='store_true', help='Run in graphical user interface mode')
    
    args = parser.parse_args()
    
    # Default to GUI if no arguments provided
    if not args.cli and not args.gui:
        args.gui = True
    
    # Run the selected interface
    if args.cli:
        print("Starting command-line interface...")
        from Scripts.Main import main
        main()
    else:
        print("Starting graphical user interface...")
        from Scripts.FinancialUI import main
        main()

if __name__ == "__main__":
    main()
