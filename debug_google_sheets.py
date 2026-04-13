#!/usr/bin/env python
"""
Debug script to diagnose Google Sheets sync issues
"""
import os
import sys
import logging
from pathlib import Path
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinalProject.settings')
django.setup()

from Maddy.google_sheets_helper import fetch_google_sheets_data, is_credentials_available
import pandas as pd

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

print("\n" + "="*60)
print("🔍 GOOGLE SHEETS SYNC DIAGNOSTIC")
print("="*60)

# Check credentials
print("\n1️⃣ Checking credentials...")
if is_credentials_available():
    print("   ✅ Credentials file found")
else:
    print("   ❌ Credentials file NOT found")
    sys.exit(1)

# Try to fetch with hardcoded sheet name
print("\n2️⃣ Attempting to fetch from 'Customer Feedback (Responses)'...")
df = fetch_google_sheets_data(sheet_name="Customer Feedback (Responses)")

if df is not None:
    print(f"   ✅ Successfully fetched data")
    print(f"   📊 Rows: {len(df)}")
    print(f"   📋 Columns: {len(df.columns)}")
    print(f"\n   Column names: {list(df.columns)}")
    print(f"\n   Preview (first 3 rows):")
    print(df.head(3).to_string())
else:
    print("   ❌ Failed to fetch from 'Customer Feedback (Responses)'")
    print("\n3️⃣ Attempting to list all available sheets...")
    
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        import gspread
        
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds_path = Path(__file__).parent / "credentials.json.json"
        if not creds_path.exists():
            creds_path = Path(__file__).parent / "credentials.json"
        
        creds = ServiceAccountCredentials.from_json_keyfile_name(str(creds_path), scope)
        client = gspread.authorize(creds)
        
        # List all spreadsheets accessible
        print("   📁 Searching for accessible Google Sheets...")
        spreadsheets = client.list_spreadsheet_files()
        
        print(f"\n   Found {len(spreadsheets)} spreadsheet(s):")
        for sheet in spreadsheets[:10]:  # Show first 10
            print(f"      • {sheet['name']}")
            
            # Try to open and list worksheets
            try:
                opened = client.open(sheet['name'])
                worksheets = opened.worksheets()
                print(f"        Worksheets: {[ws.title for ws in worksheets]}")
            except Exception as e:
                print(f"        Error accessing: {e}")
        
    except Exception as e:
        print(f"   ❌ Error listing sheets: {e}")

# Check CSV cache
print("\n4️⃣ Checking CSV cache...")
csv_path = Path(__file__).parent / "analysis" / "google_form_responses.csv"
if csv_path.exists():
    df_csv = pd.read_csv(csv_path)
    print(f"   ✅ CSV cache exists")
    print(f"   📊 Cached rows: {len(df_csv)}")
else:
    print(f"   ⚠️  CSV cache not found at {csv_path}")

print("\n" + "="*60)
print("✅ Diagnostic complete!")
print("="*60)
