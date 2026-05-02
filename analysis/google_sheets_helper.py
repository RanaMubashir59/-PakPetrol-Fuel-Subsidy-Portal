"""
google_sheets_helper.py - Secure Google Sheets integration with CSV fallback
"""
import os
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
CSV_CACHE_PATH = BASE_DIR / "analysis" / "google_form_responses.csv"

def load_google_sheet_data(sheet_id: str, range_name: str = "Sheet1!A:Z") -> pd.DataFrame:
    """
    Fetch data from Google Sheets. Falls back to local CSV if API fails.
    """
    # Try Google Sheets API first
    try:
        import google.auth
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        if not CREDENTIALS_PATH.exists():
            # Check common alternate names
            alt_paths = [
                BASE_DIR / "credential.json.json",
                BASE_DIR / "credential.json",
                BASE_DIR / "service_account.json"
            ]
            for p in alt_paths:
                if p.exists():
                    CREDENTIALS_PATH = p
                    break
            else:
                raise FileNotFoundError(f"No credentials found at {CREDENTIALS_PATH}")

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = service_account.Credentials.from_service_account_file(
            str(CREDENTIALS_PATH), scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=creds)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get("values", [])
        if not values:
            raise ValueError("Empty Google Sheet. Add data or fix range.")
            
        df = pd.DataFrame(values[1:], columns=values[0])
        logger.info(f"✅ Loaded {len(df)} rows from Google Sheets")
        
        # Cache to CSV for offline/fallback use
        df.to_csv(CSV_CACHE_PATH, index=False)
        return df

    except Exception as e:
        logger.warning(f"⚠️ Google Sheets API failed: {e}")
        return load_csv_fallback()


def load_csv_fallback() -> pd.DataFrame:
    """Load locally cached CSV as fallback"""
    if CSV_CACHE_PATH.exists():
        logger.info(f"📥 Loading cached CSV: {CSV_CACHE_PATH}")
        return pd.read_csv(CSV_CACHE_PATH)
    else:
        logger.error("❌ No CSV cache found. Upload a file via dashboard first.")
        return pd.DataFrame()