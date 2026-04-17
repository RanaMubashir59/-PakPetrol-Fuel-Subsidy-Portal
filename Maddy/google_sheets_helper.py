"""
Google Sheets API integration for fetching form responses.
Requires credentials.json in the project root.
"""
import os
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.warning("gspread not installed. Install with: pip install gspread oauth2client")


def get_credentials_path():
    """Get path to credentials.json"""
    # Try credentials.json first, then credentials.json.json
    primary = Path(__file__).parent.parent / "credentials.json"
    secondary = Path(__file__).parent.parent / "credentials.json.json"
    
    if primary.exists():
        return primary
    return secondary


def is_credentials_available():
    """Check if credentials.json exists"""
    creds_path = get_credentials_path()
    return creds_path.exists()


def fetch_google_sheets_data(sheet_name="Customer Feedback (Responses)", worksheet_index=0):
    """
    Fetch data from Google Sheets and return as DataFrame.
    
    Args:
        sheet_name: Name of the Google Sheet document
        worksheet_index: Index of the worksheet (0 for first sheet)
    
    Returns:
        pd.DataFrame or None if failed
    """
    if not GSPREAD_AVAILABLE:
        logger.error("gspread not installed. Cannot fetch from Google Sheets.")
        return None
    
    if not is_credentials_available():
        logger.warning(f"credentials.json not found at {get_credentials_path()}")
        return None
    
    try:
        # Define scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Load credentials
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            str(get_credentials_path()), 
            scope
        )
        
        # Authorize
        client = gspread.authorize(creds)
        
        # Open sheet
        sheet = client.open(sheet_name)
        worksheet = sheet.get_worksheet(worksheet_index)
        
        if not worksheet:
            logger.error(f"Worksheet at index {worksheet_index} not found")
            return None
        
        # Get data
        data = worksheet.get_all_records()
        
        if not data:
            logger.warning(f"No data found in {sheet_name}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        logger.info(f"Successfully fetched {len(df)} rows from Google Sheets")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data from Google Sheets: {e}")
        return None


def sync_sheets_to_csv(csv_path, sheet_name="Customer Feedback (Responses)", worksheet_index=0):
    """
    Sync Google Sheets data to local CSV file.
    
    Args:
        csv_path: Path where CSV should be saved
        sheet_name: Name of the Google Sheet
        worksheet_index: Worksheet index
    
    Returns:
        bool: True if successful, False otherwise
    """
    df = fetch_google_sheets_data(sheet_name, worksheet_index)
    
    if df is None:
        logger.error("Failed to fetch data from Google Sheets")
        return False
    
    try:
        # Ensure directory exists
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save to CSV
        df.to_csv(csv_path, index=False)
        logger.info(f"Successfully synced data to {csv_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving CSV: {e}")
        return False
