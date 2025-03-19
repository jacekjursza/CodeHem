import textwrap
import re
import math

def normalize_indentation(code_text: str, indent: str='    ') -> str:
    # Remove the common leading whitespace from all non-blank lines
    orig_lines = code_text.splitlines()
    non_blank = [line for line in orig_lines if line.strip()]
    if non_blank:
        common = min(len(line) - len(line.lstrip()) for line in non_blank)
        rels = [(len(line) - len(line.lstrip())) - common for line in non_blank if (len(line) - len(line.lstrip())) - common > 0]
        min_rel = min(rels) if rels else 0
    else:
        common = 0
        min_rel = 0
    new_lines = []
    for i, line in enumerate(orig_lines):
        if line.strip():
            orig_indent = len(line) - len(line.lstrip())
            rel = orig_indent - common
            if rel <= 0 or min_rel == 0:
                new_indent = ""
            else:
                level = round(rel / min_rel)
                new_indent = indent * level
            new_lines.append(new_indent + line.lstrip())
        else:
            new_lines.append(line)
    result = "\n".join(new_lines)
    m = re.search(r'(\n[ \t]+)$', code_text)
    if m:
        trailing = textwrap.dedent(m.group(1))
        result = result.rstrip("\n") + trailing
    if not result.startswith("\n"):
        result = "\n" + result
    # Remove extra trailing newline if any
    result = result.rstrip("\n")
    return result

def format_python_class_content(code_text: str) -> str:
    dedented = textwrap.dedent(code_text)
    m = re.search(r'(\n[ \t]+)$', code_text)
    if m:
        trailing = textwrap.dedent(m.group(1))
        if not dedented.endswith(trailing):
            dedented = dedented.rstrip("\n") + trailing
    if not dedented.startswith("\n"):
        dedented = "\n" + dedented
    return dedented.rstrip("\n") + "\n    "

def format_python_method_content(code_text: str) -> str:
    """
    Format a Python method definition.
    If a decorator is present, leave it unindented and indent the method signature by 4 spaces.
    Otherwise, the method signature starts at column 0 and subsequent lines are indented by 4 spaces.
    """
    dedented = textwrap.dedent(code_text).rstrip("\n")
    lines = dedented.splitlines()
    if not lines:
        return ""
    new_lines = []
    if lines[0].lstrip().startswith('@'):
        new_lines.append(lines[0])
        for line in lines[1:]:
            if line.lstrip().startswith('def '):
                new_lines.append("    " + line.lstrip())
            elif line.strip() == "":
                new_lines.append(line)
            else:
                new_lines.append("    " + line)
    else:
        new_lines.append(lines[0].lstrip())
        for line in lines[1:]:
            if line.strip() == "":
                new_lines.append(line)
            else:
                new_lines.append("    " + line)
    return "\n".join(new_lines)

def process_lines(original_lines: list, start_idx: int, end_idx: int, new_lines: list) -> list:
    if not original_lines:
        return new_lines
    if start_idx < 0:
        return new_lines + original_lines
    if start_idx >= len(original_lines):
        return original_lines + new_lines
    start_idx = max(0, min(start_idx, len(original_lines) - 1))
    end_idx = max(start_idx, min(end_idx, len(original_lines) - 1))
    result = original_lines[:start_idx] + new_lines + original_lines[end_idx + 1:]
    return result