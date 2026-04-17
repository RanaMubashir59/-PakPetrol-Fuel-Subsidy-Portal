import requests
import json

r = requests.get('http://127.0.0.1:8000/analytics/data/')
data = r.json()

print('CHI-SQUARE DATA (FIXED):')
chi_sq = data.get('chi_square', {})
for name in chi_sq:
    test = chi_sq[name]
    print(f'\n{name}:')
    print(f'  Title: {test.get("title")}')
    print(f'  Chi2={test.get("chi2"):.3f}, p={test.get("p_value"):.4f}')
    cont = test.get('contingency', {})
    print(f'  Rows: {list(cont.keys())[:5]}...')
