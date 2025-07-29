import json

internal_file = 'raw/api_results_solr_280_300.jsonl'
google_file = 'raw/google_places_results_280_300.jsonl'

def load_queries(path, aggregate_google=False):
    queries = set()
    results_map = {}
    with open(path, 'r') as f:
        for line in f:
            try:
                obj = json.loads(line)
                query = obj.get('query')
                if isinstance(query, dict):
                    keyword = query.get('keyword')
                    if keyword:
                        queries.add(keyword)
                        if aggregate_google:
                            # Aggregate all Google POIs
                            all_pois = []
                            # text_search.places
                            ts = obj.get('text_search', {})
                            ts_places = ts.get('places', []) if isinstance(ts, dict) else []
                            all_pois.extend(ts_places)
                            # nearby_search.places
                            ns = obj.get('nearby_search', {})
                            ns_places = ns.get('places', []) if isinstance(ns, dict) else []
                            all_pois.extend(ns_places)
                            # place_details
                            pd = obj.get('place_details', None)
                            if pd:
                                if isinstance(pd, list):
                                    all_pois.extend(pd)
                                elif isinstance(pd, dict):
                                    all_pois.append(pd)
                            results_map[keyword] = all_pois
                        else:
                            results_map[keyword] = obj.get('result')
                elif isinstance(query, str):
                    queries.add(query)
                    results_map[query] = obj.get('result')
            except Exception as e:
                print(f"Error parsing line: {e}")
    return queries, results_map

internal_queries, internal_results_map = load_queries(internal_file)
google_queries, google_results_map = load_queries(google_file, aggregate_google=True)

def find_empty_results(queries, results_map, label):
    empty = []
    non_empty = []
    for q in queries:
        res = results_map.get(q)
        if not res or (isinstance(res, list) and len(res) == 0):
            empty.append(q)
        else:
            non_empty.append(q)
    print(f"Queries with empty or missing results in {label}: {empty}")
    print(f"Queries with non-empty results in {label}: {non_empty}")

print('Queries in internal but not in google:', internal_queries - google_queries)
print('Queries in google but not in internal:', google_queries - internal_queries)
print('Queries present in both:', internal_queries & google_queries)

find_empty_results(internal_queries, internal_results_map, 'internal')
find_empty_results(google_queries, google_results_map, 'google')
