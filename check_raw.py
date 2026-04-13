import pandas as pd

df = pd.read_csv('analysis/google_form_responses.csv')

print('=== AWARENESS COLUMN DATA ===')
awareness_col = "Are you aware of any government fuel subsidy programs?"
print(f'Column: {awareness_col}')
print(f'\nValues:')
print(df[[awareness_col]].to_string())

print(f'\nValue counts:')
print(df[awareness_col].value_counts())

print(f'\n=== USAGE FREQUENCY ===')
usage_col = "How often do you use your motorcycle?"
print(f'\nCrosstab (Awareness x Usage):')
ct = pd.crosstab(df[awareness_col].fillna('Missing'), df[usage_col].fillna('Missing'))
print(ct)
