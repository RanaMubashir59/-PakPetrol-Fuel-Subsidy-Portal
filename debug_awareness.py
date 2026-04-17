import urllib.request
import json

with urllib.request.urlopen('http://127.0.0.1:8000/analytics/data/') as response:
    data = json.loads(response.read())
    chi_sq = data.get('chi_square', {})
    
    awareness = chi_sq.get('Awareness', {})
    print('=== AWARENESS CHI-SQUARE TEST ===')
    print(f'Title: {awareness.get("title")}')
    print(f'Chi2: {awareness.get("chi2")}')
    print(f'P-value: {awareness.get("p_value")}')
    print(f'DOF: {awareness.get("dof")}')
    
    print('\nCONTINGENCY TABLE:')
    cont = awareness.get('contingency', {})
    for row_key in sorted(cont.keys()):
        print(f'\n{row_key}:')
        for col_key in sorted(cont[row_key].keys()):
            print(f'  {col_key}: {cont[row_key][col_key]}')
