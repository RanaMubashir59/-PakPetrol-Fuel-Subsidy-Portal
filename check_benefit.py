import pandas as pd

df = pd.read_csv('analysis/google_form_responses.csv')

usage_col = "How often do you use your motorcycle?"
benefit_col = "A fuel subsidy would improve my mobility"

print("=== Crosstab Data ===")
print(f"Usage frequencies: {df[usage_col].unique()}")
print(f"Subsidy benefit values: {df[benefit_col].unique()}")

ct = pd.crosstab(df[usage_col].fillna('Missing'), df[benefit_col].fillna('Missing'))
print("\nCrosstab:")
print(ct)

print("\n.to_dict() output:")
ct_dict = ct.to_dict()
for key in ct_dict:
    print(f"  Row '{key}': {ct_dict[key]}")
