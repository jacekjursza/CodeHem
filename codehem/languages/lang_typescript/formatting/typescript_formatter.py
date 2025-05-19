"""
TypeScript/JavaScript specific formatter implementation.
Provides basic formatting rules.
"""
import re
import textwrap
from typing import Callable, Optional
from codehem.core.formatting.brace_formatter import BraceFormatter
from codehem.models.enums import CodeElementType

class TypeScriptFormatter(BraceFormatter):
    """
    TypeScript/JavaScript specific implementation of the code formatter.
    Applies basic indentation and spacing rules.
    Note: For comprehensive formatting, consider integrating an external tool like Prettier.
    """

    def __init__(self, indent_size: int = 4):
        """
        Initialize the TypeScript/JavaScript formatter.
        Args:
            indent_size: Number of spaces per indentation level (default: 4)
        """
        super().__init__(indent_size)

    def _get_element_formatter(self, element_type: str) -> Optional[Callable]:
        """
        Get the formatter function for the specified element type.
        Currently provides basic indentation for common block structures.
        """
        # Map specific types if needed, otherwise use default format_code
        formatters = {
            CodeElementType.CLASS.value: self.format_block_element,
            CodeElementType.INTERFACE.value: self.format_block_element,
            CodeElementType.METHOD.value: self.format_block_element,
            CodeElementType.FUNCTION.value: self.format_block_element,
            CodeElementType.ENUM.value: self.format_block_element,
            CodeElementType.NAMESPACE.value: self.format_block_element,
            # Imports and properties often don't need complex block formatting
            CodeElementType.IMPORT.value: self.format_simple_element,
            CodeElementType.PROPERTY.value: self.format_simple_element,
            CodeElementType.STATIC_PROPERTY.value: self.format_simple_element,
            CodeElementType.TYPE_ALIAS.value: self.format_simple_element,
            CodeElementType.DECORATOR.value: self.format_simple_element,
        }
        # Fallback to default formatting
        return formatters.get(element_type, self.format_code)

    def format_code(self, code: str) -> str:
        """
        Basic formatting for a generic piece of TypeScript/JavaScript code.
        Focuses on trimming whitespace and standardizing newlines.
        """
        code = code.strip()
        # Basic cleanup: standardize line endings, remove excessive blank lines
        lines = code.splitlines()
        cleaned_lines = []
        last_line_blank = True # Assume previous was blank to avoid leading blank lines
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:
                cleaned_lines.append(line) # Keep original indentation for now
                last_line_blank = False
            elif not last_line_blank:
                cleaned_lines.append('') # Allow one blank line
                last_line_blank = True
        # Join and ensure single trailing newline
        return '\n'.join(cleaned_lines).strip() + '\n'

    def format_simple_element(self, code: str) -> str:
        """ Formats simple, likely single-line or non-block elements like imports, properties. """
        return self.dedent(code).strip()

    def format_block_element(self, code: str) -> str:
        """
        Formats elements that typically contain a block (like classes, functions).
        Applies basic indentation normalization based on the first line's indent.
        This is a simplified approach.
        """
        dedented_code = self.dedent(code).strip()
        lines = dedented_code.splitlines()
        if not lines:
            return ''

        # Try to determine base indent for the block content
        base_indent_level = 0
        found_brace = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('{') and i == 0: # Brace on first line
                 if len(lines) > 1:
                      # Estimate indent from the second line
                      base_indent_level = len(self.get_indentation(lines[1])) // self.indent_size
                 found_brace = True
                 break
            elif stripped.endswith('{'): # Brace at end of line
                 if len(lines) > i + 1:
                      # Estimate indent from the next line
                      base_indent_level = len(self.get_indentation(lines[i+1])) // self.indent_size
                 found_brace = True
                 break

        if not found_brace: # Default if no clear block start found
             base_indent_level = 1

        base_indent_str = self.indent_string * max(0, base_indent_level -1) # Indent inside braces

        # Re-indent lines based on simple logic (doesn't handle complex cases)
        result = []
        current_indent_level = 0
        definition_line = True
        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append('')
                continue

            if definition_line:
                 result.append(line) # Keep first line(s) as is
                 if '{' in stripped:
                      definition_line = False
                      current_indent_level = 1 # Assume starting indent level 1 after {
            else:
                 # Very basic indentation adjustment
                 if stripped.startswith('}'):
                      current_indent_level = max(0, current_indent_level - 1)

                 result.append(base_indent_str + (self.indent_string * current_indent_level) + stripped)

                 if stripped.endswith('{'):
                      current_indent_level += 1

        return '\n'.join(result)

    def apply_indentation(self, code: str, base_indent: str) -> str:
        """
        Apply indentation to the code, removing existing common indent first.
        Args:
            code: Code to indent
            base_indent: Base indentation string to apply
        Returns:
            Indented code
        """
        dedented_code = self.dedent(code)
        lines = dedented_code.splitlines()
        result = []
        for line in lines:
            if line.strip():
                result.append(base_indent + line)
            else:
                result.append('') # Preserve blank lines relative position
        return '\n'.join(result)

    def dedent(self, code: str) -> str:
        """ Remove common leading whitespace from all lines. """
        try:
            # Handle potential mixed tabs/spaces if necessary, though spaces are preferred
            return textwrap.dedent(code)
        except Exception:
            # Fallback for safety
            lines = code.splitlines()
            min_indent = float('inf')
            for line in lines:
                if line.strip():
                    indent = len(self.get_indentation(line))
                    min_indent = min(min_indent, indent)

            if min_indent == float('inf') or min_indent == 0:
                return code

            new_lines = []
            for line in lines:
                if line.strip():
                    new_lines.append(line[min_indent:])
                else:
                    new_lines.append('')
            return '\n'.join(new_lines)