import pandas as pd

# Read the CSV
df = pd.read_csv('analysis/google_form_responses.csv')

print("Current data:")
print(df[['How often do you use your motorcycle?', 'Are you aware of any government fuel subsidy programs?', 'A fuel subsidy would improve my mobility', 'I would use a digital fuel subsidy system if available']].to_string())

print("\n\nFIXING: Row 4 awareness value '5' → 'Yes'")

# Fix the malformed data
df.loc[4, 'Are you aware of any government fuel subsidy programs?'] = 'Yes'

print("\nAfter fix:")
print(df[['How often do you use your motorcycle?', 'Are you aware of any government fuel subsidy programs?', 'A fuel subsidy would improve my mobility', 'I would use a digital fuel subsidy system if available']].to_string())

# Save back
df.to_csv('analysis/google_form_responses.csv', index=False)
print("\n✅ CSV updated!")
