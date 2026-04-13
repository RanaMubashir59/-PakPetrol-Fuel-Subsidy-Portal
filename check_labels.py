import urllib.request
import json

with urllib.request.urlopen('http://127.0.0.1:8000/analytics/data/') as response:
    data = json.loads(response.read())
    chi_sq = data.get('chi_square', {})
    
    awareness = chi_sq.get('Awareness', {})
    print('=== AWARENESS CHI-SQUARE (NEW) ===')
    print(f'X-Label: {awareness.get("x_label")}')
    print(f'Y-Label: {awareness.get("y_label")}')
    print(f'Chi2: {awareness.get("chi2"):.4f}')
    print(f'P-value: {awareness.get("p_value"):.4f}')
