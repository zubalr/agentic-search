def group_similar_keywords(keywords, min_group_size=3):
    groups = []
    current_group = []
    for i, kw in enumerate(keywords):
        if not current_group or kw.startswith(current_group[-1]):
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
    with open('../data/unique_sorted_keywords.txt', 'r', encoding='utf-8') as fin:
        keywords = [line.strip() for line in fin if line.strip()]
    groups = group_similar_keywords(keywords)
    result = []
    for group in groups:
        result.extend(select_representatives(group))
    with open('../data/representative_keywords.txt', 'w', encoding='utf-8') as fout:
        for kw in result:
            fout.write(kw + '\n')

if __name__ == "__main__":
    process_keywords('../data/unique_sorted_keywords.txt', '../data/representative_keywords.txt')
