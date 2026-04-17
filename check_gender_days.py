import pandas as pd

df = pd.read_csv('analysis/google_form_responses.csv')

print("=== CHECKING DATA ===")
print("\nGender values:")
print(df['Gender'].unique())
print(df['Gender'].value_counts())

print("\nMissed Days values:")
print(df['On average how many days per month do you miss due to fuel issues?'].unique())
print(df['On average how many days per month do you miss due to fuel issues?'].value_counts())

print("\nCrosstab (Gender x Missed Days):")
ct = pd.crosstab(
    df['Gender'].fillna('Missing'), 
    df['On average how many days per month do you miss due to fuel issues?'].fillna('Missing')
)
print(ct)
