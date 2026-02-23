import requests
import json

def test_search():
    url = "http://localhost:8000/search-sites?q=엘리움"
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        results = response.json()
        print(f"Count: {len(results)}")
        for r in results:
            print(f"- {r.get('name')} ({r.get('id')})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
