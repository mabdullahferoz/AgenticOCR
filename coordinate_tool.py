def merge_bounding_boxes(matched_word_infos, vertical_threshold=15):
    """
    Takes a list of word coordinate dicts and merges them into cohesive 
    bounding boxes, handling line wraps cleanly.
    """
    if not matched_word_infos:
        return []

    # Sort words based on their appearance sequence
    lines = []
    current_line = [matched_word_infos[0]]

    for next_word in matched_word_infos[1:]:
        # If the vertical 'top' coordinate is within the threshold, it's the same line
        prev_word = current_line[-1]
        if abs(next_word['top'] - prev_word['top']) <= vertical_threshold:
            current_line.append(next_word)
        else:
            # Significant vertical jump means a new line / line wrap
            lines.append(current_line)
            current_line = [next_word]
    lines.append(current_line)

    final_boxes = []
    
    # Calculate the definitive TBLR envelope for each line segment
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
    """
    Scans the database spatial map to find occurrences of the search query
    and calculates their final combined TBLR boxes.
    """
    # Clean and split query into individual lowercase tokens
    query_tokens = [w.lower() for w in search_query.split()]
    if not query_tokens:
        return []

    results = []
    n_query = len(query_tokens)
    n_map = len(spatial_map)

    # Slide a window across the spatial map to find matching sequences
    for i in range(n_map - n_query + 1):
        window_words = [spatial_map[i + j]['word'].lower() for j in range(n_query)]
        
        # Strip common punctuation from map words to handle matches like "System."
        cleaned_window = [w.strip(".,;:!?()[]\"'") for w in window_words]

        if cleaned_window == query_tokens:
            # We found a complete match! Grab the matching objects
            matched_segment = spatial_map[i : i + n_query]
            
            # Run them through our line-merge engine
            merged_boxes = merge_bounding_boxes(matched_segment)
            results.append(merged_boxes)

    return results