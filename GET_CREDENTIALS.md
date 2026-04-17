# Get credentials.json - Step by Step

## Fastest Way (5 minutes)

### Step 1: Go to Google Cloud Console
- Open: https://console.cloud.google.com
- Sign in with your Google account

### Step 2: Create a Project
1. Click the **blue dropdown** at the top (says "Select a project")
2. Click **NEW PROJECT**
3. Enter name: `PakPetrol Analytics`
4. Click **CREATE**
5. Wait 30 seconds while it creates

### Step 3: Enable APIs
1. Search for: `Google Sheets API`
2. Click the result
3. Click **ENABLE**
4. Go back and search for: `Google Drive API`
5. Click the result
6. Click **ENABLE**

### Step 4: Create Service Account
1. On the left sidebar, click **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **Service Account**
3. Fill in:
   - **Service account name:** `PakPetrol`
   - Leave other fields as default
4. Click **CREATE AND CONTINUE**
5. Skip the optional steps
6. Click **DONE**

### Step 5: Download credentials.json
1. You'll see the service account listed (named "PakPetrol")
2. Click on it
3. Go to **KEYS** tab
4. Click **ADD KEY** → **Create new key**
5. Choose **JSON** format
6. Click **CREATE**
7. A JSON file will download automatically

### Step 6: Place credentials.json
1. Move the downloaded file to your project root:
```
C:\Users\RanaM\Desktop\Project\FinalProject\-PakPetrol-Fuel-Subsidy-Portal\
├── credentials.json  ← PUT THE FILE HERE
├── manage.py
├── requirements.txt
└── ...
```

### Step 7: Share Your Google Sheet
1. Open your Google Form responses sheet
2. Click **Share** (top right)
3. Open the downloaded `credentials.json` file in Notepad
4. Find the line: `"client_email": "something@something.iam.gserviceaccount.com"`
5. Copy that email address
6. Paste it in the Share dialog
7. Click **Editor** (give it edit access)
8. Uncheck "Notify people"
9. Click **SHARE**

### Done! ✅
Now run:
```bash
python manage.py sync_google_sheets
```

Or just visit `/analytics/` - it will auto-fetch from Google Sheets!

---

## Troubleshooting

### "Where's my credentials.json file after download?"
- **Windows**: Usually in `Downloads` folder
- **Mac/Linux**: Check Downloads or home folder
- Look for `XXX-XXX-XXX-XXX.json` file

### "I can't find client_email in credentials.json"
1. Open credentials.json with Notepad
2. Look for: `"client_email"`
3. Copy the entire email address (inside the quotes)
4. Example: `my-service@my-project.iam.gserviceaccount.com`

### "Google Sheet shows permission denied error"
1. Make sure you pasted the full `client_email` address (with @)
2. Make sure sheet is shared with "Editor" permission, not "Viewer"
3. Try refreshing the page

### "Still getting credentials.json not found error"
1. Check filename is exactly: `credentials.json` (lowercase, no numbers)
2. Make sure it's in the project root (same folder as `manage.py`)
3. Restart Django: `python manage.py runserver`

---

## For Now (Temporary)

If you want to skip Google Sheets setup for now, the dashboard still works with the sample CSV data:
- Your analytics page will show sample data from `analysis/google_form_responses.csv`
- You can come back to this setup later anytime

The system is designed to work either way! 🎉
