# Google Sheets Integration Setup Guide

This guide explains how to connect your Django analytics dashboard to Google Forms responses via Google Sheets.

## Prerequisites
- A Google account
- A Google Form that saves responses to a Google Sheet
- Python packages: `gspread` and `oauth2client` (included in `requirements.txt`)

## Step 1: Install Required Packages

```bash
pip install -r requirements.txt
```

Or individually:
```bash
pip install gspread oauth2client
```

## Step 2: Create Google Cloud Project & Service Account

1. **Go to Google Cloud Console**: https://console.cloud.google.com

2. **Create a new project**:
   - Click the project dropdown at the top
   - Click "NEW PROJECT"
   - Enter a project name (e.g., "PakPetrol Analytics")
   - Click CREATE

3. **Enable Google Sheets API**:
   - In the search bar, type "Google Sheets API"
   - Click "Google Sheets API"
   - Click ENABLE

4. **Enable Google Drive API**:
   - In the search bar, type "Google Drive API"
   - Click "Google Drive API"
   - Click ENABLE

5. **Create a Service Account**:
   - Go to "APIs & Services" → "Credentials"
   - Click "CREATE CREDENTIALS" → "Service Account"
   - Fill in the details:
     - Service account name: "PakPetrol Analytics"
     - Service account ID: auto-fill is fine
   - Click CREATE AND CONTINUE
   - Skip the optional steps and click DONE

6. **Generate credentials.json**:
   - Click on the created Service Account
   - Go to "KEYS" tab
   - Click "ADD KEY" → "Create new key"
   - Choose "JSON" format
   - Click CREATE
   - The credentials.json file will download automatically

7. **Move credentials.json**:
   - Move the downloaded `credentials.json` to your project root directory:
   ```
   -PakPetrol-Fuel-Subsidy-Portal/
   ├── credentials.json  ← Put it here
   ├── manage.py
   ├── Maddy/
   └── ...
   ```

## Step 3: Share Your Google Sheet with Service Account

1. **Find the Service Account Email**:
   - Open the downloaded `credentials.json` in a text editor
   - Find the value of `"client_email"` (looks like `xxx@xxx.iam.gserviceaccount.com`)

2. **Share the Sheet**:
   - Open your Google Form responses sheet
   - Click "Share" (top right)
   - Paste the service account email
   - Give it "Editor" access
   - Uncheck "Notify people"
   - Click SHARE

## Step 4: Configure Django

1. **Update Sheet Name (if needed)**:
   - In `Maddy/views.py`, the default sheet name is `"Form Responses 1"`
   - If your sheet has a different name, either:
     - Rename your sheet to "Form Responses 1", OR
     - Update the view: change `sheet_name="Form Responses 1"` to your sheet name

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 5: Sync Data

### Option A: Automatic (Every page load)
- The analytics page automatically syncs from Google Sheets on each request
- Falls back to CSV if sheets isn't available

### Option B: Manual Sync
```bash
python manage.py sync_google_sheets
```

### Option C: Custom Sheet Name
```bash
python manage.py sync_google_sheets --sheet-name "My Custom Sheet Name"
```

## Step 6: Test the Integration

1. **Start Django**:
   ```bash
   python manage.py runserver
   ```

2. **Go to Analytics**:
   - Visit: http://127.0.0.1:8000/analytics/
   - You should see data loading from your Google Sheet

3. **Check Logs**:
   - If something goes wrong, check the console output
   - It will show if it's using Google Sheets or falling back to CSV

## Troubleshooting

### "credentials.json not found"
- Make sure `credentials.json` is in the project root (same folder as `manage.py`)
- Check the file is named exactly `credentials.json` (case-sensitive)

### "PERMISSION_DENIED"
- Make sure you shared the Google Sheet with the service account email
- Make sure you used "Editor" access level

### "Sheet not found"
- Verify the sheet name matches exactly (including spaces and capitalization)
- Default is "Form Responses 1"

### Analytics shows no data
- Check if CSV file exists: `analysis/google_form_responses.csv`
- Run: `python manage.py sync_google_sheets` to manually sync
- Check Django logs for error messages

### Gspread module not found
- Install it: `pip install gspread oauth2client`
- Or: `pip install -r requirements.txt`

## How It Works

1. **Page Load**: When you visit the analytics page, Django tries to fetch data from Google Sheets
2. **Sync**: If successful, it automatically caches the data to a local CSV
3. **Fallback**: If Google Sheets fails or credentials aren't set up, it uses the CSV cache
4. **Display**: The dashboard shows interactive charts from the data

## Data Flow

```
Google Forms
    ↓
Google Sheet ("Form Responses 1")
    ↓
Google Sheets API (via gspread)
    ↓
Django load_google_form_data()
    ↓
CSV Cache (analysis/google_form_responses.csv)
    ↓
Analytics Dashboard + Charts
```

## Additional Resources

- [gspread Documentation](https://docs.gspread.org/)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [Service Account Setup](https://cloud.google.com/docs/authentication/getting-started)

## Questions?

If you encounter issues:
1. Check the Django console output for error messages
2. Verify credentials.json permissions
3. Make sure the service account email has access to your Google Sheet
4. Check that all required packages are installed
