import json

def merge_bounding_boxes(matched_word_infos, vertical_threshold=15):
    if not matched_word_infos:
        return []

    lines = []
    current_line = [matched_word_infos[0]]

    for next_word in matched_word_infos[1:]:
        prev_word = current_line[-1]
        if abs(next_word['top'] - prev_word['top']) <= vertical_threshold:
            current_line.append(next_word)
        else:
            lines.append(current_line)
            current_line = [next_word]
    lines.append(current_line)

    final_boxes = []
    for line in lines:
        tops = [w['top'] for w in line]
        bottoms = [w['bottom'] for w in line]
        lefts = [w['left'] for w in line]
        rights = [w['right'] for w in line]

        final_boxes.append({
            "top": min(tops),
            "bottom": max(bottoms),
            "left": min(lefts),
            "right": max(rights)
        })
    return final_boxes

def find_phrase_coordinates(search_query, spatial_map):
    query_tokens = [w.lower() for w in search_query.split()]
    if not query_tokens:
        return []

    results = []
    n_query = len(query_tokens)
    n_map = len(spatial_map)

    for i in range(n_map - n_query + 1):
        window_words = [spatial_map[i + j]['word'].lower() for j in range(n_query)]
        cleaned_window = [w.strip(".,;:!?()[]\"'") for w in window_words]

        if cleaned_window == query_tokens:
            matched_segment = spatial_map[i : i + n_query]
            merged_boxes = merge_bounding_boxes(matched_segment)
            results.append(merged_boxes)
    return results