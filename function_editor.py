import re
import sys


def modify_function(file_path, function_name, new_body):
    """
    Modifies the body of a function in a Python file without needing to know its previous content.

    Args:
        file_path: Path to the file
        function_name: Name of the function to modify
        new_body: New function body (with proper indentation)
    """
    with open(file_path, "r", encoding="utf-8") as file:
        file_text = file.read()

    # Pattern to find the function definition along with its body
    pattern = (
        r"(def\s+"
        + re.escape(function_name)
        + r"\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:)([^\n]*(?:\n[ \t]+[^\n]*)*)(?=\n\S|\Z)"
    )

    # Search for the function in the text
    match = re.search(pattern, file_text)
    if not match:
        print(f"Function {function_name} not found.")
        return False

    # Get the function definition (def ... :) and its original body
    func_def = match.group(1)
    original_body = match.group(2)

    # Determine indentation based on the first non-empty line of the original body
    indentation = ""
    for line in original_body.splitlines():
        if line.strip():
            indentation = re.match(r"^[ \t]*", line).group(0)
            break
    if not indentation:
        indentation = "    "  # default Python indentation

    # Adjust indentation for the new body
    indented_body = []
    for line in new_body.strip().splitlines():
        if line.strip():  # add indentation for non-empty lines
            indented_body.append(indentation + line)
        else:  # simply add empty lines
            indented_body.append("")

    new_function = func_def + "\n" + "\n".join(indented_body)

    # Replace the function in the file
    modified_text = re.sub(pattern, new_function, file_text, count=1)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(modified_text)

    return True


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print('Usage: python function_editor.py file.py function_name "new_body"')
        sys.exit(1)

    file_path = sys.argv[1]
    function_name = sys.argv[2]
    new_body = sys.argv[3]

    if modify_function(file_path, function_name, new_body):
        print(f"Function {function_name} modified successfully.")
    else:
        print(f"Failed to modify function {function_name}.")
