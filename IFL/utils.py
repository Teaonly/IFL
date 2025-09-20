import sys
from difflib import SequenceMatcher
import html

from prompt_toolkit import prompt, print_formatted_text, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import choice

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
    # 根据 byExit 参数动态构建选项列表
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

def print_line(info, color="ansigreen"):
    print("\n")
    print_formatted_text(HTML(f'<{color}>{"-"*20}{info}{"-"*20}</{color}>'))

def print_tag(info, color="ansicyan"):
    print_formatted_text(HTML(f'<{color}>{info}</{color}>'))

def print_tag_end(color="ansicyan"):
    print_formatted_text(HTML(f'<{color}>{"-"*20}</{color}>'))

def print_warning(info):
    print_formatted_text(HTML(f'<ansired>{info}</ansired>'))


def readfile_with_linenumber(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    result = []
    for i, line in enumerate(lines, 1):
        result.append(f"{i}\t{line}")

    return ''.join(result)

def find_similar_lines(search_lines, content_lines, threshold=0.85):
    '''
    search_lines = search_lines.splitlines()
    content_lines = content_lines.splitlines()
    '''
    best_ratio = 0
    best_match = []

    if len(search_lines) > len(content_lines):
        return -1, "Context line out of range"

    for i in range(len(content_lines) - len(search_lines) + 1):
        chunk = content_lines[i : i + len(search_lines)]
        ratio = SequenceMatcher(None, search_lines, chunk).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = chunk
            best_match_i = i

    ## 如果相似度低于阈值，返回 -1 表示未找到
    if best_ratio < threshold:
        return -1, "Cannot find matching context in original file"

    ## 如果首尾行相同，直接返回完整匹配
    return best_match_i, best_match

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
        
        # 找到 SEARCH 块的起始位置
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

        # 在 original 中查找最相似的行
        match_index, matched_lines = find_similar_lines(search_lines, original_lines)
        if match_index == -1:
            return False, matched_lines  # 返回错误消息

        # 执行替换，跳过已处理的块
        original_lines = (
            original_lines[:match_index] +
            replace_lines +
            original_lines[match_index + len(search_lines):]
        )
        i = replace_end + 1

    return True, ''.join(original_lines)

def display_search_replace(blocks):
    """彩色方式显示 SEARCH/REPLACE 块"""
    lines = blocks.splitlines(keepends=True)
    output_lines = []
    in_search = False
    in_replace = False
    
    for line in lines:
        if line.startswith("<<<<<<< SEARCH"):
            output_lines.append(f"\033[91m{line.rstrip()}\033[0m")  # 红色
            in_search = True
            in_replace = False
        elif line.startswith("======="):
            output_lines.append(f"\033[93m{line.rstrip()}\033[0m")  # 黄色
            in_search = False
            in_replace = True
        elif line.startswith(">>>>>>> REPLACE"):
            output_lines.append(f"\033[92m{line.rstrip()}\033[0m")  # 绿色
            in_search = False
            in_replace = False
        elif in_search:
            output_lines.append(f"\033[91m-{line.rstrip()}\033[0m")  # 红色删除线
        elif in_replace:
            output_lines.append(f"\033[92m+{line.rstrip()}\033[0m")  # 绿色添加线
        else:
            output_lines.append(line.rstrip())
    
    return '\n'.join(output_lines)

def apply_patch(file_path, blocks):
    ## 将 search_replace 应用到 file_path 指定的文件中
    with open(file_path, 'r', encoding='utf-8') as file:
        original = file.read()

    success, result = do_search_replace(original, blocks)

    if success:
        # 写入修改后的内容
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(result)
            return True, None
        except Exception as e:
            return False, f"Failed to write file {file_path}: {str(e)}"

    ## result 表示错误消息
    return False, result
