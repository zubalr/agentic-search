import os

def remove_duplicates(input_file, output_file):
    seen = set()
    with open(input_file, 'r', encoding='utf-8') as fin, open(output_file, 'w', encoding='utf-8') as fout:
        header = fin.readline()
        fout.write(header)
        for line in fin:
            parts = line.strip().split(',')
            if len(parts) != 3:
                continue
            keyword, lat, lng = parts
            key = (keyword, lat, lng)
            if key not in seen:
                fout.write(f"{keyword},{lat},{lng}\n")
                seen.add(key)

if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(__file__), '../data/sorted_keywords_with_location.csv')
    output_path = os.path.join(os.path.dirname(__file__), '../data/unique_sorted_keywords_with_location.csv')
    remove_duplicates(input_path, output_path)
