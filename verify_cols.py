import pandas as pd

df = pd.read_csv('analysis/google_form_responses.csv')

cols_to_check = [
    "How often do you use your motorcycle?",
    "Are you aware of any government fuel subsidy programs?",
    "I would use a digital fuel subsidy system if available",
    "A fuel subsidy would improve my mobility",
]

for col in cols_to_check:
    if col in df.columns:
        print(f"✓ {col}")
        print(f"  Values: {df[col].unique()}")
        print(f"  Count: {df[col].value_counts().to_dict()}")
    else:
        print(f"✗ {col} - NOT FOUND")
print(f"\nAll columns: {df.columns.tolist()}")
