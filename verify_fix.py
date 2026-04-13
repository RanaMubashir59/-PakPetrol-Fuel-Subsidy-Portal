import urllib.request
import json

with urllib.request.urlopen('http://127.0.0.1:8000/analytics/data/') as response:
    data = json.loads(response.read())
    chi_sq = data.get('chi_square', {})
    
    print("=== CHI-SQUARE TESTS ===")
    for name, test in chi_sq.items():
        print(f"\n{name}:")
        print(f"  X-axis: {test.get('x', [])}")
        print(f"  Y-axis: {test.get('y', [])}")
        print(f"  Z (heatmap): {test.get('z', [])}")
        print(f"  Chi2: {test.get('chi2'):.3f}, p: {test.get('p_value'):.4f}")
