# Analytics Data Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Google Forms                                 │
│              (Collects user responses)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              Google Sheet "Form Responses 1"                    │
│         (Auto-populated by Google Forms)                        │
│  - Stores all survey responses                                  │
│  - Accessible via Google Sheets API                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
        ┌────────────────────────────────────────┐
        │    Google Cloud / Service Account       │
        │  - API Credentials (credentials.json)  │
        │  - Authenticates requests              │
        └────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Django Application                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Maddy/views.py::load_google_form_data()                    │
│     └─ Tries Google Sheets first                              │
│     └─ Falls back to CSV if needed                            │
│                                                                  │
│  2. Maddy/google_sheets_helper.py                              │
│     └─ fetch_google_sheets_data()     [Get live data]         │
│     └─ sync_sheets_to_csv()           [Cache locally]         │
│     └─ is_credentials_available()     [Check setup]           │
│                                                                  │
│  3. Analytics Endpoint: /analytics/data/                        │
│     └─ Returns JSON payload with charts                        │
│                                                                  │
└────┬──────────────────────────────────────────────────────┬─────┘
     │                                                      │
     ↓ (caches data)                    ↓ (reads data)      │
┌────────────────────────────┐                  │           │
│  Local CSV Cache           │                  │           │
│ analysis/                  │                  │           │
│ google_form_responses.csv  │                  │           │
│                            │                  │           │
│ ✓ Offline fallback         │                  │           │
│ ✓ Faster loading           │                  │           │
│ ✓ Data persistence         │                  │           │
└────────────────────────────┘                  │           │
                                               ↓           ↓
                                  ┌─────────────────────────────┐
                                  │   Pandas DataFrame          │
                                  │   (In-memory data)          │
                                  └────────────┬────────────────┘
                                               │
                                               ↓
                                  ┌──────────────────────────────┐
                                  │ compute_analytics_payload()  │
                                  │ (Process & analyze data)     │
                                  └────────────┬─────────────────┘
                                               │
                  ┌───────────────────────────┼───────────────────────────┐
                  ↓                           ↓                           ↓
         ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
         │ Demographics    │         │  Regression     │         │  Group Comp.    │
         │ Analysis        │         │  Analysis       │         │  Analysis       │
         │                 │         │                 │         │                 │
         │ - Q1: Urban/Rur │         │ - Q6 vs Q7      │         │ - Q8 Groups     │
         │ - Q2: Age       │         │ - R² calculation│         │ - Box plots     │
         │ - Q3: Location  │         │ - P-value       │         │ - Statistics    │
         │ - Q4: Education │         │                 │         │                 │
         │ - Q5: Income    │         │                 │         │                 │
         └────────┬────────┘         └────────┬────────┘         └────────┬────────┘
                  │                           │                           │
                  └───────────────────────────┼───────────────────────────┘
                                              │
                  ┌───────────────────────────┼───────────────────────────┐
                  ↓                           ↓                           ↓
         ┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
         │ Productivity    │         │  Awareness       │         │  Perception     │
         │ Score           │         │  Distribution    │         │  Likert Scale   │
         │                 │         │                  │         │                 │
         │ - Q9-Q13        │         │ - Q15 Responses  │         │ - Q16,17,18     │
         │- Composite Score│         │ - Pie Chart      │         │- Stacked Bars   │
         │ - Histogram     │         │                  │         │                 │
         └────────┬────────┘         └────────┬─────────┘         └────────┬────────┘
                  │                           │                           │
                  │                 ┌─────────┴─────────┐                 │
                  │                 ↓                   ↓                 │
                  │         ┌─────────────────────────────────────┐       │
                  │         │  Chi-Square Tests                   │       │
                  │         │  - Q1 vs Q14, Q3 vs Q14             │       │
                  │         │  - Contingency tables               │       │
                  │         │  - Heatmaps                         │       │
                  │         └──────────┬────────────────────────┬┘        │
                  │                    │                        │         │
                  └────────────────────┼────────────────────────┼─────────┘
                                       │                        │
                                       ↓                        ↓
                            ┌────────────────────────────────────────┐
                            │  JSON Payload                          │
                            │ ├─ demographics                        │
                            │ ├─ regression                          │
                            │ ├─ group_comparison                    │
                            │ ├─ productivity                        │
                            │ ├─ awareness                           │
                            │ ├─ perception                          │
                            │ └─ chi_square                          │
                            └────────────┬───────────────────────────┘
                                         │
                                         ↓
                            ┌────────────────────────────────────────┐
                            │  Frontend (Django Template)             │
                            │  analytics_dashboard.html              │
                            └────────────┬───────────────────────────┘
                                         │
                                 ┌───────┴────────┐
                                 ↓                ↓
                     ┌───────────────────┐  ┌──────────────────┐
                     │  analytics.js     │  │  Plotly.js Lib   │
                     │ (Chart rendering) │  │ (Chart library)  │
                     └───────────┬───────┘  └────────┬─────────┘
                                 │                   │
                                 └───────────┬───────┘
                                             ↓
                                ┌────────────────────────────────┐
                                │   Interactive Charts           │
                                │ ├─ Bar charts (demographics)   │
                                │ ├─ Scatter plots (regression)  │
                                │ ├─ Box plots (groups)          │
                                │ ├─ Pie charts (awareness)      │
                                │ ├─ Histograms (productivity)   │
                                │ ├─ Stacked bars (perception)   │
                                │ └─ Heatmaps (chi-square)       │
                                └────────────┬──────────────────┘
                                             │
                                             ↓
                                ┌────────────────────────────────┐
                                │   Browser Display              │
                                │   (User sees dashboard)        │
                                └────────────────────────────────┘
```

## Data Flow Diagram

```
USER ACTION
    ↓
Visit /analytics/
    ↓
Django analytics_dashboard view
    ↓
load_google_form_data()
    ├─ Is credentials.json available?
    │  ├─ YES → Try Google Sheets
    │  │   ├─ Success → Save to CSV + Return
    │  │   └─ Fail → Fall through to CSV
    │  └─ NO → Skip to CSV
    │
    └─ Load CSV file
       └─ Return DataFrame
           ↓
       compute_analytics_payload()
           ├─ Demographics analysis
           ├─ Regression analysis  
           ├─ Group comparison
           ├─ Productivity scoring
           ├─ Awareness analysis
           ├─ Perception analysis
           └─ Chi-square tests
               ↓
           Return JSON
               ↓
           JavaScript receives data
               ↓
           Plotly renders charts
               ↓
           User sees dashboard
```

## Component Dependencies

```
google_sheets_helper.py
├─ gspread          (Google Sheets API client)
├─ oauth2client     (Authentication)
├─ pandas           (Data manipulation)
└─ pathlib          (File paths)

views.py
├─ google_sheets_helper
├─ pandas
├─ numpy
├─ scipy.stats
├─ django.conf
├─ models.py
└─ forms.py

analytics.js
├─ Plotly.js (CDN)
└─ JavaScript Fetch API
```

## Database/File Structure

```
Project Root/
├── credentials.json              ← Service account (KEEP SECRET!)
├── manage.py
├── requirements.txt              ← Dependencies
│
├── Maddy/
│   ├── views.py                 ← Updated with Google Sheets
│   ├── google_sheets_helper.py  ← NEW: Google Sheets utility
│   ├── models.py
│   ├── forms.py
│   │
│   └── management/commands/     ← Django management
│       └── sync_google_sheets.py ← NEW: Sync command
│
├── analysis/
│   └── google_form_responses.csv ← CSV Cache
│       (Updated by sync or auto-load)
│
├── templates/
│   └── analytics_dashboard.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── analytics.js
│
└── docs/
    ├── GOOGLE_SHEETS_SETUP.md
    └── GOOGLE_SHEETS_QUICK_REF.md
```

## Sync Flow

```
Manual Sync via Command:
    python manage.py sync_google_sheets
        ↓
    Check credentials.json
        ↓
    Connect to Google Sheets
        ↓
    Fetch "Form Responses 1"
        ↓
    Convert to DataFrame
        ↓
    Save to analysis/google_form_responses.csv
        ↓
    Display success message


Automatic Sync (on page load):
    User visits /analytics/
        ↓
    Django load_google_form_data()
        ↓
    Try fetch_google_sheets_data()
        ├─ Success → Call sync_sheets_to_csv()
        │              (Update cache)
        │   └─ Return data
        └─ Fail → Load CSV directly
               └─ Return data
```

## Error Handling Hierarchy

```
load_google_form_data()
    │
    ├─ Google Sheets available?
    │  ├─ NO: Skip to CSV
    │  └─ YES: Try to fetch
    │      ├─ Network error → Fall to CSV
    │      ├─ Auth error → Fall to CSV
    │      ├─ Sheet not found → Fall to CSV
    │      └─ Success → Cache to CSV + Return
    │
    └─ Load CSV
       ├─ File exists → Return data
       └─ File missing → Return None
           (Analytics shows error message)
```

## Performance Considerations

```
Without Credentials:
└─ 50-100ms: Read CSV from disk

With Credentials (first load):
└─ 1-3s: Fetch from Google Sheets + Update CSV

With Credentials (subsequent loads):
├─ 1-3s: Try Google Sheets
└─ 50-100ms: Fallback to cached CSV (if fails)

Optimization:
- CSV cache prevents downtime if Sheets is unavailable
- Optional cron job: Sync every 6 hours
- JavaScript caching: Charts update every 10 seconds
```

## Security Considerations

```
credentials.json
├─ Contains: Service account private key
├─ Risk: If exposed, attacker can access sheet
├─ Protection:
│   ├─ Add to .gitignore
│   ├─ Set restrictive file permissions (600)
│   ├─ Use environment variables in production
│   └─ Restrict service account scopes
│
Google Sheet Sharing
├─ Share only with: Service account email
├─ Permission level: Editor (minimum needed)
├─ Uncheck: "Notify people"
└─ No public sharing
```
