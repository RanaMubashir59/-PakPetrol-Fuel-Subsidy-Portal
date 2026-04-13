# Google Sheets Integration - Quick Reference

## What's New?

Your Django project now integrates with Google Sheets API to automatically fetch Google Form responses.

## New Files Added

```
Maddy/
├── google_sheets_helper.py          ← New: Google Sheets API utilities
└── management/commands/
    └── sync_google_sheets.py         ← New: Django command to sync data

requirements.txt                      ← Updated: Added gspread, oauth2client
GOOGLE_SHEETS_SETUP.md               ← New: Complete setup guide
```

## How to Use

### 1. First-Time Setup (One Time)
```bash
# Install packages
pip install -r requirements.txt

# Get credentials.json (see GOOGLE_SHEETS_SETUP.md)
# Place credentials.json in project root
```

### 2. Manual Sync (Whenever Needed)
```bash
python manage.py sync_google_sheets
```

### 3. Automatic Loads
- Every time you visit `/analytics/`, Django automatically:
  - Tries to fetch from Google Sheets
  - Falls back to cached CSV if sheets unavailable
  - Updates the cache

## Code Changes in views.py

```python
# Before (CSV only):
def load_google_form_data():
    df = pd.read_csv(ANALYTICS_CSV_PATH)
    return df

# After (Google Sheets + CSV fallback):
def load_google_form_data():
    # Try Google Sheets first
    df = fetch_google_sheets_data(sheet_name="Form Responses 1")
    if df is not None:
        # Cache to CSV
        sync_sheets_to_csv(ANALYTICS_CSV_PATH)
        return df
    
    # Fallback to CSV
    df = pd.read_csv(ANALYTICS_CSV_PATH)
    return df
```

## Data Priority

When loading analytics data, Django checks in this order:

1. **Google Sheets** (if credentials.json exists) ← Live data
2. **CSV File** (analysis/google_form_responses.csv) ← Cached data

## Key Functions

### google_sheets_helper.py

```python
# Fetch data from Google Sheets
fetch_google_sheets_data(sheet_name="Form Responses 1", worksheet_index=0)
# Returns: pd.DataFrame or None

# Sync Google Sheets to CSV (caching)
sync_sheets_to_csv(csv_path, sheet_name="Form Responses 1")
# Returns: True/False

# Check if credentials available
is_credentials_available()
# Returns: True/False

# Get credentials.json path
get_credentials_path()
# Returns: Path object
```

## Configuration

### To use a different sheet name:

**Option 1: In views.py** (line ~117)
```python
df = fetch_google_sheets_data(sheet_name="Your Sheet Name Here")
```

**Option 2: Via management command**
```bash
python manage.py sync_google_sheets --sheet-name "Your Sheet Name"
```

### Sheet Requirements

Your Google Sheet must have:
- Column headers in the first row
- Response data below headers
- Supported format: Any Google Form responses sheet

Example columns:
```
Timestamp | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | ... 
```

## Logging

Django logs all Google Sheets operations. Check console output:

```
INFO - Attempting to fetch data from Google Sheets...
INFO - Successfully fetched 30 rows from Google Sheets
INFO - Successfully synced data to analysis/google_form_responses.csv
```

## Environment Variables (Optional)

You can set custom paths via environment variables:

```bash
export GOOGLE_CREDENTIALS_PATH="/path/to/credentials.json"
export GOOGLE_SHEET_NAME="My Custom Sheet Name"
```

Then use:
```python
os.getenv('GOOGLE_CREDENTIALS_PATH')
os.getenv('GOOGLE_SHEET_NAME')
```

## Error Handling

All operations gracefully handle errors:

- ❌ credentials.json missing → Uses CSV cache
- ❌ Sheet not found → Uses CSV cache  
- ❌ Network error → Uses CSV cache
- ❌ Permission denied → Uses CSV cache

**Result**: Analytics always work, even without Google Sheets setup!

## For Production

1. **Keep credentials.json secure**:
   - Add to `.gitignore`: `credentials.json`
   - Never commit credentials to git
   - Use environment variables for production

2. **Schedule automatic syncs** (optional):
   ```bash
   # Add to cron or task scheduler
   0 */6 * * * python /path/to/manage.py sync_google_sheets
   ```
   (Syncs every 6 hours)

3. **Monitor logs**:
   - Set up Django logging
   - Alert if syncs fail

## Files to Keep Private

```
credentials.json         ← Service account credentials (SECRET!)
```

Add to `.gitignore`:
```
credentials.json
*.pyc
__pycache__/
.env
```

## Testing

```python
# Test in Django shell
python manage.py shell

from Maddy.google_sheets_helper import fetch_google_sheets_data
df = fetch_google_sheets_data()
print(df.head())
print(f"Loaded {len(df)} rows")
```

## Support

If you need help:
1. See GOOGLE_SHEETS_SETUP.md for detailed setup
2. Check console logs for error messages
3. Verify credentials.json path and permissions
4. Ensure service account email has sheet access
