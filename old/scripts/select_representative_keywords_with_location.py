import os

def group_similar_keywords(keywords, min_group_size=3):
    groups = []
    current_group = []
    for i, kw in enumerate(keywords):
        if not current_group or kw[0].startswith(current_group[-1][0]):
            current_group.append(kw)
        else:
            if len(current_group) >= min_group_size:
                groups.append(current_group)
            else:
                groups.extend([[k] for k in current_group])
            current_group = [kw]
    if current_group:
        if len(current_group) >= min_group_size:
            groups.append(current_group)
        else:
            groups.extend([[k] for k in current_group])
    return groups

def select_representatives(group):
    if len(group) < 3:
        return group
    return [group[0], group[len(group)//2], group[-1]]

def process_keywords(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as fin:
        header = fin.readline()
        keywords = []
        for line in fin:
            parts = line.strip().split(',')
            if len(parts) != 3:
                continue
            keywords.append(parts)
    groups = group_similar_keywords(keywords)
    result = []
    for group in groups:
        result.extend(select_representatives(group))
    with open(output_file, 'w', encoding='utf-8') as fout:
        fout.write('keyword,lat,lng\n')
        for kw, lat, lng in result:
            fout.write(f'{kw},{lat},{lng}\n')

if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(__file__), '../data/unique_sorted_keywords_with_location.csv')
    output_path = os.path.join(os.path.dirname(__file__), '../data/representative_keywords_with_location.csv')
    process_keywords(input_path, output_path)
