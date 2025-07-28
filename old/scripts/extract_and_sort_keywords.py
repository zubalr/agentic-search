import json
import os

INPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/Analytics.json')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/sorted_keywords.txt')

def get_search_keywords(data):
    keywords = []
    for entry in data["SEARCH KEYWORDS"]:
        payload = json.loads(entry["payload"])
        keyword = payload.get("searchKeyword")
        if keyword:
            keywords.append(keyword)
    return keywords

def sort_keywords(keywords):
    return sorted(keywords)

def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    keywords = get_search_keywords(data)
    sorted_keywords = sort_keywords(keywords)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for kw in sorted_keywords:
            f.write(kw + '\n')

if __name__ == "__main__":
    main()
