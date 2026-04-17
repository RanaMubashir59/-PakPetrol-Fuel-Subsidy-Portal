import urllib.request
import json

with urllib.request.urlopen('http://127.0.0.1:8000/analytics/data/') as response:
    data = json.loads(response.read())
    chi_sq = data.get('chi_square', {})
    print(f'Chi-square tests found: {len(chi_sq)}')
    print(f'Keys: {list(chi_sq.keys())}')
    if chi_sq:
        for name in list(chi_sq.keys())[:1]:
            test = chi_sq[name]
            print(f'\nFirst test ({name}):')
            print(f'  Title: {test.get("title")}')
            print(f'  Chi2: {test.get("chi2")}')
            print(f'  P-value: {test.get("p_value")}')
