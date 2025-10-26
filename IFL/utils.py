import sys
from difflib import SequenceMatcher
import html

from prompt_toolkit import prompt, print_formatted_text, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import choice
import shutil
import wcwidth

def content_from_input(info):
    style = Style.from_dict({
        "frame.border": "#884444",
    })
    print_formatted_text(HTML(f'<violet>{info} (Esc + Enter to exit)</violet>'))
    while True:
        try:
            content = prompt(">>", multiline=True, style=style, show_frame=True)
            return content
        except EOFError:
            return ""

def confirm_from_input(info, byExit = True):
    style = Style.from_dict({
        "frame.border": "#884444",
    })
    # Dynamically build option list based on byExit parameter
    options = [
        (True,  "Yes"),
        (False, "No"),
    ]
    if byExit:
        options.append(("exit", "Exit directly"))

    result = choice(
        message=HTML(f"<u>{info}</u>"),
        options=options,
        style=style,
        show_frame=True)

    if result == "exit":
        sys.exit(0)

    return result

def printed_length(s):
    length = 0
    for char in s:
        width = wcwidth.wcwidth(char)
        if width > 0:  # Exclude zero-width characters
            length += width
    return length

def lined_print(info ):
    terminal_width = shutil.get_terminal_size().columns
    info_len = printed_length(info)
    dash_count = (terminal_width - info_len - 2) // 2
    line = f"{'─' * dash_count} {info} {'─' * dash_count}"
    # Adjust for odd terminal width to ensure full width line
    if printed_length(line) < terminal_width:
        line += '─'
    print("\n\n")

    print(f"\033[90m{line}\033[0m")

def framed_print(title, content, style="default"):
    """Print content in a styled frame, wrapping long lines instead of truncating"""
    lines = content.split('\n')
    frame_width = shutil.get_terminal_size().columns

    # Define ANSI color codes
    colors = {
        "default": {"frame": "\033[90m", "title": "\033[1m", "reset": "\033[0m"},
        "info": {"frame": "\033[94m", "title": "\033[1;94m", "reset": "\033[0m"},
        "warning": {"frame": "\033[93m", "title": "\033[1;93m", "reset": "\033[0m"},
        "error": {"frame": "\033[91m", "title": "\033[1;91m", "reset": "\033[0m"},
        "success": {"frame": "\033[92m", "title": "\033[1;92m", "reset": "\033[0m"}
    }

    color = colors.get(style, colors["default"])

    # Draw top border with title
    top_border_with_title = f"┌───── {title} "
    top_border_with_title += "─" * (frame_width - printed_length(top_border_with_title) - 1)
    top_border_with_title += "┐"

    # Print frame
    print(f"{color['frame']}{''.join(top_border_with_title)}{color['reset']}")

    # Print content lines with wrapping
    display_width = frame_width - 4  # 2 spaces on each side

    for line in lines:
        if line.strip() == "":
            # Empty line - just print spaces
            print(f"{color['frame']}│ {' ' * display_width} │{color['reset']}")
            continue

        # Wrap long lines
        current_pos = 0
        while current_pos < len(line):
            wrapped_line = ""
            current_width = 0
            start_pos = current_pos

            # Build wrapped line character by character
            while current_pos < len(line):
                char = line[current_pos]
                char_width = wcwidth.wcwidth(char)

                if current_width + char_width <= display_width:
                    wrapped_line += char
                    current_width += char_width
                    current_pos += 1
                else:
                    break

            # If we didn't add any characters (shouldn't happen), advance by 1
            if current_pos == start_pos:
                wrapped_line = line[current_pos]
                current_pos += 1

            # Pad with spaces to fill the line
            while current_width < display_width:
                wrapped_line += " "
                current_width += 1

            print(f"{color['frame']}│ {wrapped_line} │{color['reset']}")

    # Print bottom border
    print(f"{color['frame']}└" + "─" * (frame_width - 2) + f"┘{color['reset']}")

def readfile_with_linenumber(file_path, with_number=True):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    result = []
    for i, line in enumerate(lines, 1):
        if with_number:
            result.append(f"{i}\t{line}")
        else:
            result.append(line)

    return ''.join(result)

def normalize_line(line):
    """Normalize single line text, remove extra spaces and unify indentation"""
    # Remove leading and trailing whitespace
    normalized = line.strip()
    # Merge multiple internal spaces into single space
    normalized = ' '.join(normalized.split())
    return normalized

def preprocess_lines(lines, preserve_structure=True):
    """Preprocess line list, provide different levels of normalization"""
    if preserve_structure:
        # Preserve structure, only normalize whitespace characters
        return [line.rstrip() for line in lines]
    else:
        # Fully normalize, ignore whitespace and case differences
        return [normalize_line(line).lower() for line in lines if line.strip()]

def calculate_similarity(search_lines, content_chunk, strategy='combined'):
    """Calculate similarity using multiple strategies"""
    if len(search_lines) != len(content_chunk):
        return 0.0

    # Strategy 1: Original SequenceMatcher
    if strategy == 'original':
        return SequenceMatcher(None, search_lines, content_chunk).ratio()

    # Strategy 2: Fully normalized comparison
    elif strategy == 'normalized':
        norm_search = preprocess_lines(search_lines, preserve_structure=False)
        norm_content = preprocess_lines(content_chunk, preserve_structure=False)
        if not norm_search or not norm_content:  # Handle empty line cases
            return SequenceMatcher(None, search_lines, content_chunk).ratio()
        return SequenceMatcher(None, norm_search, norm_content).ratio()

    # Strategy 3: Structured comparison (preserve whitespace)
    elif strategy == 'structured':
        struct_search = preprocess_lines(search_lines, preserve_structure=True)
        struct_content = preprocess_lines(content_chunk, preserve_structure=True)
        return SequenceMatcher(None, struct_search, struct_content).ratio()

    # Strategy 4: Combined comparison
    elif strategy == 'combined':
        original_score = SequenceMatcher(None, search_lines, content_chunk).ratio()
        normalized_score = SequenceMatcher(
            None,
            preprocess_lines(search_lines, preserve_structure=False),
            preprocess_lines(content_chunk, preserve_structure=False)
        ).ratio()
        structured_score = SequenceMatcher(
            None,
            preprocess_lines(search_lines, preserve_structure=True),
            preprocess_lines(content_chunk, preserve_structure=True)
        ).ratio()

        # Weighted average: Original 0.4, Normalized 0.4, Structured 0.2
        return original_score * 0.4 + normalized_score * 0.4 + structured_score * 0.2

    else:
        return SequenceMatcher(None, search_lines, content_chunk).ratio()

def find_similar_lines(search_lines, content_lines, threshold=0.90, strategy='combined'):
    """
    Enhanced similar line finding function

    Args:
        search_lines: List of lines to search for
        content_lines: List of lines to search in
        threshold: Similarity threshold (0.0-1.0)
        strategy: Matching strategy ('original', 'normalized', 'structured', 'combined')

    Returns:
        tuple: (index, matched_lines, similarity_score, details)
        index: Match position, -1 means not found
        matched_lines: List of matched lines
        similarity_score: Actual similarity score
        details: Match details dictionary
    """
    # Input validation
    if not search_lines or not content_lines:
        return -1, [], 0.0, {"error": "Empty input lines"}

    if len(search_lines) > len(content_lines):
        return -1, [], 0.0, {"error": "Search lines longer than content lines"}

    best_match = {
        'index': -1,
        'lines': [],
        'score': 0.0,
        'strategy_used': strategy,
        'details': {}
    }

    # Iterate through all possible match positions
    for i in range(len(content_lines) - len(search_lines) + 1):
        chunk = content_lines[i:i + len(search_lines)]

        # Calculate similarity
        similarity = calculate_similarity(search_lines, chunk, strategy)

        # If a better match is found
        if similarity > best_match['score']:
            best_match.update({
                'index': i,
                'lines': chunk,
                'score': similarity,
                'details': {
                    'chunk_start': i,
                    'chunk_end': i + len(search_lines) - 1,
                    'line_count': len(search_lines)
                }
            })

    # Check if threshold requirement is met
    if best_match['score'] >= threshold:
        return best_match['index'], best_match['lines'], best_match['score'], best_match['details']
    else:
        # Try other strategies as fallback
        fallback_strategies = ['original', 'normalized', 'structured']
        for fallback_strategy in fallback_strategies:
            if fallback_strategy == strategy:
                continue

            fallback_match = {
                'index': -1,
                'lines': [],
                'score': 0.0,
                'strategy_used': fallback_strategy
            }

            for i in range(len(content_lines) - len(search_lines) + 1):
                chunk = content_lines[i:i + len(search_lines)]
                similarity = calculate_similarity(search_lines, chunk, fallback_strategy)

                if similarity > fallback_match['score']:
                    fallback_match.update({
                        'index': i,
                        'lines': chunk,
                        'score': similarity,
                        'details': {
                            'chunk_start': i,
                            'chunk_end': i + len(search_lines) - 1,
                            'line_count': len(search_lines),
                            'fallback_strategy': True
                        }
                    })

            if fallback_match['score'] >= threshold * 0.8:  # Fallback strategy uses slightly lower threshold
                return fallback_match['index'], fallback_match['lines'], fallback_match['score'], fallback_match['details']

        # No match found with any strategy
        return -1, [], best_match['score'], {
            "error": f"Cannot find matching context in original file. Best score: {best_match['score']:.3f}",
            "best_match_index": best_match['index'],
            "best_score": best_match['score'],
            "strategy_used": strategy,
            "threshold": threshold
        }

def find_next(lines, start_index, target):
    for i in range(start_index, len(lines)):
        if lines[i].startswith(target):
            return i
    return -1

def do_search_replace(original, blocks):
    original_lines = original.splitlines(keepends=True)
    blocks_lines = blocks.splitlines(keepends=True)

    i = 0
    while i < len(blocks_lines):
        search_start = find_next(blocks_lines, i, "<<<<<<< SEARCH")
        if search_start == -1:
            return False, "Malformed block: missing <<<<<<< SEARCH"

        # Find the starting position of the SEARCH block
        search_start = search_start + 1
        search_end = find_next(blocks_lines, search_start, "=======")
        if search_end == -1:
            return False, "Malformed block: missing ======="
        if search_end == search_start:
            return False, "Malformed block: empty SEARCH section"
        replace_end = find_next(blocks_lines, search_end + 1, ">>>>>>> REPLACE")
        if replace_end == -1:
            return False, "Malformed block: missing >>>>>>> REPLACE"

        search_lines = blocks_lines[search_start:search_end]
        replace_lines = blocks_lines[search_end + 1:replace_end]

        # Find the most similar lines in original
        match_index, matched_lines, similarity_score, details = find_similar_lines(
            search_lines, original_lines, strategy='combined'
        )
        if match_index == -1:
            error_msg = details.get("error", "Cannot find matching context in original file")
            return False, error_msg  # Return error message

        # Perform replacement, skip processed blocks
        original_lines = (
            original_lines[:match_index] +
            replace_lines +
            original_lines[match_index + len(search_lines):]
        )
        i = replace_end + 1

    return True, ''.join(original_lines)
def apply_patch(file_path, blocks):
    ## Apply search_replace to the file specified by file_path
    with open(file_path, 'r', encoding='utf-8') as file:
        original = file.read()

    success, result = do_search_replace(original, blocks)

    if success:
        # Write the modified content
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(result)
            return True, None
        except Exception as e:
            return False, f"Failed to write file {file_path}: {str(e)}"

    ## result represents the error message
    return False, result

