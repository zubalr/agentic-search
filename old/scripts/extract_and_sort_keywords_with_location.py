import json
import os

INPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/Analytics.json')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/sorted_keywords_with_location.csv')

def get_search_keywords(data):
    results = []
    for entry in data["SEARCH KEYWORDS"]:
        payload = json.loads(entry["payload"])
        keyword = payload.get("searchKeyword")
        lat = payload.get("originLat")
        lng = payload.get("originLng")
        if keyword:
            results.append((keyword, lat, lng))
    return results

def sort_keywords(keywords):
    return sorted(keywords, key=lambda x: x[0])

def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    keywords = get_search_keywords(data)
    sorted_keywords = sort_keywords(keywords)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('keyword,lat,lng\n')
        for kw, lat, lng in sorted_keywords:
            f.write(f'{kw},{lat},{lng}\n')

if __name__ == "__main__":
    main()
