import ast
import logging
import textwrap
import re
from typing import Optional, List, Tuple, Union, Any, Dict
from codehem.core.manipulators.manipulator_base import ManipulatorBase
from codehem.core.formatting.formatter import BaseFormatter # Import BaseFormatter
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

class _NodeFinder(ast.NodeVisitor):
    """Helper visitor to find a specific node based on criteria."""
    def __init__(self, element_type: CodeElementType, name: Optional[str], parent_name: Optional[str]):
        self.element_type = element_type
        self.target_name = name
        self.parent_name = parent_name
        self.found_node: Optional[ast.AST] = None
        self.current_class_name: Optional[str] = None # Track current class context

    def _check_property_decorator(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], decorator_type: str) -> bool:
        """Checks for specific property decorators (@property, @name.setter)."""
        if not hasattr(node, 'decorator_list'): return False
        for d in node.decorator_list:
            if decorator_type == 'getter':
                if isinstance(d, ast.Name) and d.id == 'property': return True
            elif decorator_type == 'setter':
                if self.target_name and isinstance(d, ast.Attribute) and (d.attr == 'setter'):
                    if isinstance(d.value, ast.Name) and d.value.id == self.target_name: return True
        return False

    def visit_ClassDef(self, node: ast.ClassDef):
        original_class_name = self.current_class_name
        self.current_class_name = node.name
        # Check if this class itself is the target BEFORE visiting children
        if not self.found_node and self.element_type == CodeElementType.CLASS and node.name == self.target_name and self.parent_name is None:
            self.found_node = node
        else:
            if not self.found_node or (self.parent_name == self.current_class_name):
                 self.generic_visit(node)
        self.current_class_name = original_class_name

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self.found_node: return
        is_method_context = self.current_class_name is not None
        matches_parent = (self.parent_name == self.current_class_name)
        if node.name == self.target_name:
            is_getter = self._check_property_decorator(node, 'getter')
            is_setter = self._check_property_decorator(node, 'setter')
            if self.element_type == CodeElementType.PROPERTY_GETTER and is_getter and matches_parent: self.found_node = node
            elif self.element_type == CodeElementType.PROPERTY_SETTER and is_setter and matches_parent: self.found_node = node
            elif self.element_type == CodeElementType.METHOD and is_method_context and not (is_getter or is_setter) and matches_parent: self.found_node = node
            elif self.element_type == CodeElementType.FUNCTION and not is_method_context and not (is_getter or is_setter) and self.parent_name is None: self.found_node = node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
         self.visit_FunctionDef(node)

    def visit_Assign(self, node: ast.Assign):
         if self.found_node: return
         if self.element_type == CodeElementType.STATIC_PROPERTY and self.current_class_name == self.parent_name:
              for target in node.targets:
                   if isinstance(target, ast.Name) and target.id == self.target_name:
                        if self.current_class_name is not None: # Basic context check
                            self.found_node = node
                            return
         self.generic_visit(node)

# --- AST Transformer ---
class ReplaceOrInsertTransformer(ast.NodeTransformer):
    """
    AST Transformer to replace a node matching specific criteria (esp. line number)
    or insert nodes into a parent node's body.
    """
    # Add formatter argument
    def __init__(self, definition_target_line: Optional[int], target_end_line: Optional[int], new_nodes: List[ast.AST], parent_name: Optional[str], element_type: CodeElementType, target_name: Optional[str], formatter: BaseFormatter):
        super().__init__()
        self.definition_target_line = definition_target_line
        self.target_end_line = target_end_line
        self.new_nodes = new_nodes
        self.parent_name = parent_name
        self.element_type = element_type
        self.target_name = target_name
        self.is_replacing = definition_target_line is not None
        self.is_import_block_replace = self.is_replacing and self.element_type == CodeElementType.IMPORT and self.target_name == 'all'
        self.operation_done = False
        self.current_class_name: Optional[str] = None
        self.formatter = formatter # Store formatter instance

    def _check_property_decorator(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], decorator_type: str) -> bool:
        # (Implementation from previous patch)
        if not hasattr(node, 'decorator_list'): return False
        for d in node.decorator_list:
            if decorator_type == 'getter':
                if isinstance(d, ast.Name) and d.id == 'property': return True
            elif decorator_type == 'setter':
                if self.target_name and isinstance(d, ast.Attribute) and (d.attr == 'setter'):
                    if isinstance(d.value, ast.Name) and d.value.id == self.target_name: return True
        return False

    def _is_target_node(self, node: ast.AST) -> bool:
        # (Using corrected logic from v4.5)
        if not self.is_replacing or self.is_import_block_replace: return False
        if not hasattr(node, 'lineno') or node.lineno != self.definition_target_line: return False
        node_name = getattr(node, 'name', None)
        if self.parent_name and self.current_class_name != self.parent_name: return False
        elif not self.parent_name and self.current_class_name is not None: return False
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node_name != self.target_name: return False
            is_getter = self._check_property_decorator(node, 'getter'); is_setter = self._check_property_decorator(node, 'setter')
            if self.element_type == CodeElementType.PROPERTY_GETTER: return is_getter
            if self.element_type == CodeElementType.PROPERTY_SETTER: return is_setter
            if self.element_type in (CodeElementType.METHOD, CodeElementType.FUNCTION): return not (is_getter or is_setter)
            return False
        elif isinstance(node, ast.ClassDef): return self.element_type == CodeElementType.CLASS and node_name == self.target_name
        elif isinstance(node, ast.Assign):
             targets = getattr(node, 'targets', []); is_static_prop_match = any((isinstance(t, ast.Name) and t.id == self.target_name for t in targets))
             return self.element_type == CodeElementType.STATIC_PROPERTY and is_static_prop_match and self.current_class_name == self.parent_name
        elif isinstance(node, (ast.Import, ast.ImportFrom)): return False # Handled by visit_Module
        return False

    def _find_insertion_point(self, body: List[ast.AST]) -> int:
        # (Using logic from previous patch)
        insert_pos = len(body);
        if self.element_type == CodeElementType.IMPORT:
            last_import_or_docstring_idx = -1
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and hasattr(body[0], 'end_lineno'): last_import_or_docstring_idx = 0
            for i, node in enumerate(body):
                 if isinstance(node, (ast.Import, ast.ImportFrom)): last_import_or_docstring_idx = i
            insert_pos = last_import_or_docstring_idx + 1
        elif self.parent_name:
             if body: insert_pos = len(body)
             else: insert_pos = 0
        else:
            last_def_idx = -1; last_import_idx = -1
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant): last_import_idx = 0
            for i, node in enumerate(body):
                 if isinstance(node, (ast.Import, ast.ImportFrom)): last_import_idx = i
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): last_def_idx = i
            insert_pos = max(last_def_idx, last_import_idx) + 1
        return insert_pos

    # --- Visitor Methods ---
    def generic_visit(self, node):
        if self._is_target_node(node):
            logger.info(f'AST Replacing node {type(node).__name__} (target: {self.target_name}) at line {getattr(node, "lineno", "?")} with {len(self.new_nodes)} new node(s).')
            self.operation_done = True
            return self.new_nodes if self.new_nodes else None
        return super().generic_visit(node)

    def visit_list(self, nodes: List[Any]) -> List[Any]:
        new_list = []
        for node in nodes:
            result = self.visit(node)
            if result is None: continue
            elif isinstance(result, list): new_list.extend(result)
            else: new_list.append(result)
        return new_list

    def visit_Module(self, node: ast.Module) -> Any:
        if self.is_import_block_replace and not self.operation_done:
            start_replace_line = self.definition_target_line; end_replace_line = self.target_end_line
            logger.info(f'AST Performing import block replacement (Lines {start_replace_line}-{end_replace_line})')
            new_body = []
            for item in node.body:
                 item_end_line = getattr(item, 'end_lineno', getattr(item, 'lineno', -1))
                 if item_end_line < start_replace_line: new_body.append(item)
            if self.new_nodes:
                 logger.debug(f'AST Inserting {len(self.new_nodes)} new import nodes.')
                 base_lineno = new_body[-1].end_lineno + 1 if new_body and getattr(new_body[-1], 'end_lineno', None) else 1
                 current_lineno = base_lineno
                 for n_node in self.new_nodes:
                      for child_node in ast.walk(n_node):
                           if hasattr(child_node, 'lineno'): child_node.lineno = current_lineno
                           if hasattr(child_node, 'col_offset'): child_node.col_offset = 0
                      try: num_lines = len(ast.unparse(n_node).splitlines()); current_lineno += num_lines
                      except: current_lineno += 1
                 new_body.extend(self.new_nodes)
            for item in node.body:
                 item_start_line = getattr(item, 'lineno', -1)
                 if item_start_line > end_replace_line: new_body.append(item)
            node.body = self.visit_list(new_body)
            self.operation_done = True
            return node

        node.body = self.visit_list(node.body)
        if not self.is_replacing and not self.operation_done and self.parent_name is None and self.element_type in [CodeElementType.FUNCTION, CodeElementType.CLASS, CodeElementType.IMPORT]:
             insert_pos = self._find_insertion_point(node.body)
             logger.info(f"AST Inserting {len(self.new_nodes)} node(s) into Module at index {insert_pos}.")
             # Basic lineno fixup...
             base_lineno = 1
             if insert_pos > 0 and hasattr(node.body[insert_pos-1], 'end_lineno') and node.body[insert_pos-1].end_lineno: base_lineno = node.body[insert_pos-1].end_lineno + 1
             current_lineno = base_lineno
             for n_node in self.new_nodes:
                  for child_node in ast.walk(n_node):
                       if hasattr(child_node, 'lineno'): child_node.lineno = current_lineno
                       if hasattr(child_node, 'col_offset'): child_node.col_offset = 0
                  try: num_lines = len(ast.unparse(n_node).splitlines()); current_lineno += num_lines
                  except: current_lineno += 1
             node.body = node.body[:insert_pos] + self.new_nodes + node.body[insert_pos:]
             self.operation_done = True
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        if self._is_target_node(node):
             logger.info(f'AST Replacing node {type(node).__name__} (target: {self.target_name}) at line {getattr(node, "lineno", "?")} with {len(self.new_nodes)} new node(s).')
             self.operation_done = True
             return self.new_nodes if self.new_nodes else None

        original_class_name = self.current_class_name
        self.current_class_name = node.name
        node.body = self.visit_list(node.body)
        if not self.is_replacing and not self.operation_done and self.parent_name == node.name and self.element_type in [CodeElementType.METHOD, CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER, CodeElementType.STATIC_PROPERTY]:
             insert_pos = self._find_insertion_point(node.body)
             logger.info(f"AST Inserting {len(self.new_nodes)} node(s) into Class '{node.name}' at index {insert_pos}.")
             # Basic lineno fixup, using formatter for indent calculation
             base_lineno = node.lineno + 1
             if insert_pos > 0 and hasattr(node.body[insert_pos-1], 'end_lineno') and node.body[insert_pos-1].end_lineno: base_lineno = node.body[insert_pos-1].end_lineno + 1
             current_lineno = base_lineno
             # Use the formatter passed to the transformer
             class_indent = getattr(node, 'col_offset', 0)
             member_indent = class_indent + len(self.formatter.indent_string)
             for n_node in self.new_nodes:
                  for child_node in ast.walk(n_node):
                       if hasattr(child_node, 'lineno'): child_node.lineno = current_lineno
                       # Set appropriate col_offset based on class indent + 1 level
                       if hasattr(child_node, 'col_offset'): child_node.col_offset = member_indent
                  try: num_lines = len(ast.unparse(n_node).splitlines()); current_lineno += num_lines
                  except: current_lineno += 1
             node.body = node.body[:insert_pos] + self.new_nodes + node.body[insert_pos:]
             self.operation_done = True
        self.current_class_name = original_class_name
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any: return self.generic_visit(node)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any: return self.generic_visit(node)
    def visit_Assign(self, node: ast.Assign) -> Any: return self.generic_visit(node)

class PythonASTManipulator(ManipulatorBase):
    """
    Manipulator for Python code using AST transformation for structure,
    and a post-processing step to re-insert specific marker comments from the patch.
    (Version 4.6 - AST Transformation with Corrected Node Matching + Comment Hack + Fixes)
    """
    MARKERS_TO_PRESERVE = ["# REPLACEMENT_UNIQUE_MARKER", "# FUNCTION_REPLACEMENT_MARKER"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self.formatter, 'indent_string') or not isinstance(self.formatter.indent_string, str) or not self.formatter.indent_string :
            indent_size = getattr(self.formatter, 'indent_size', 4)
            self.formatter.indent_string = ' ' * indent_size

    # --- Helper: Convert line numbers to bytes ---
    def _get_byte_offset(self, code_str_bytes: bytes, target_lineno: int, target_col_offset: int) -> int:
        # (Using the refined version from v4.5)
        current_line = 1; byte_offset = 0
        while current_line < target_lineno and byte_offset < len(code_str_bytes):
            try: newline_pos = code_str_bytes.index(b'\n', byte_offset); byte_offset = newline_pos + 1
            except ValueError: byte_offset = len(code_str_bytes); break
            current_line += 1
        if current_line == target_lineno:
            line_start_offset = byte_offset; target_char_col = target_col_offset
            try: line_content = code_str_bytes[line_start_offset:].split(b'\n',1)[0].decode('utf-8', errors='ignore'); target_char_col = len(line_content[:target_col_offset])
            except Exception: pass
            char_col = 0
            while char_col < target_char_col and byte_offset < len(code_str_bytes):
                 byte = code_str_bytes[byte_offset]; inc = 1
                 if 0xC2 <= byte <= 0xDF: inc = 2
                 elif 0xE0 <= byte <= 0xEF: inc = 3
                 elif 0xF0 <= byte <= 0xF4: inc = 4
                 elif byte >= 0x80: inc=1
                 if byte_offset + inc > len(code_str_bytes): break
                 next_char_bytes = code_str_bytes[byte_offset:byte_offset+inc]
                 if next_char_bytes == b'\n': break
                 byte_offset += inc; char_col += 1
            try: newline_pos = code_str_bytes.index(b'\n', line_start_offset); byte_offset = min(byte_offset, newline_pos)
            except ValueError: byte_offset = min(byte_offset, len(code_str_bytes))
        elif byte_offset >= len(code_str_bytes): byte_offset = len(code_str_bytes)
        return byte_offset

    # --- Helper: Adjust start line for decorators (text based) ---
    def _adjust_start_line_for_decorators(self, code_lines: List[str], start_line: int) -> int:
        # (Using the implementation from v4.5)
        adjusted_start = start_line;
        for i in range(start_line - 2, -1, -1):
            if i >= len(code_lines): continue
            line = code_lines[i].strip()
            if line and not line.startswith(tuple(self.DECORATOR_MARKERS)) and not line.startswith(tuple(self.COMMENT_MARKERS)): break
            if line.startswith(tuple(self.DECORATOR_MARKERS)) or line.startswith(tuple(self.COMMENT_MARKERS)): adjusted_start = i + 1
            elif not line: adjusted_start = i + 1
        return adjusted_start

    # --- Helper to get element type enum ---
    def _get_element_type_for_upsert(self, element_type_str: str, new_code_sample: str) -> CodeElementType:
        # (Using the refined version from v4.5)
        if element_type_str and element_type_str != CodeElementType.UNKNOWN.value:
            try: return CodeElementType(element_type_str)
            except ValueError: logger.warning(f"Invalid type '{element_type_str}'. Detecting.")
        stripped_code = new_code_sample.strip()
        if not stripped_code:
             if element_type_str and element_type_str != CodeElementType.UNKNOWN.value:
                 try: return CodeElementType(element_type_str)
                 except ValueError: pass
             raise ValueError('Cannot determine type for deletion without explicit type.')
        lines = stripped_code.splitlines(); first = lines[0].strip() if lines else ""; second = lines[1].strip() if len(lines)>1 else ""
        if first.startswith('@property'): return CodeElementType.PROPERTY_GETTER
        if first.startswith('@') and '.setter' in first: return CodeElementType.PROPERTY_SETTER
        def_line = first if first.startswith(('def ','async def')) else second if second.startswith(('def ','async def')) and first.startswith('@') else None
        if def_line: return CodeElementType.FUNCTION
        if first.startswith('class '): return CodeElementType.CLASS
        if first.startswith(('import ','from ')): return CodeElementType.IMPORT
        if '=' in first.split('#')[0] and ':' in first.split('=')[0]: return CodeElementType.STATIC_PROPERTY
        if '=' in first.split('#')[0] and not first.startswith(('def ','async def','class ','import ','from ','@')): return CodeElementType.STATIC_PROPERTY
        logger.error(f"Could not determine type from '{element_type_str}' or sample: {stripped_code[:50]}")
        raise ValueError(f'Invalid/undetectable type: {element_type_str}')

    # --- Main Upsert Logic ---
    def upsert_element(self, original_code: str, element_type_str: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        logger.info(f"AST Upsert v4.6: type='{element_type_str}', name='{name}', parent='{parent_name}'")
        try:
            detection_code_sample = new_code if new_code.strip() else 'pass'
            element_type = self._get_element_type_for_upsert(element_type_str, detection_code_sample)
        except ValueError as e: logger.error(f'Cannot perform upsert: {e}'); return original_code

        # Adjust type based on context
        if element_type in (CodeElementType.FUNCTION, CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER, CodeElementType.STATIC_PROPERTY) and parent_name:
            if element_type == CodeElementType.FUNCTION:
                 stripped_new = new_code.strip(); first_line_new = stripped_new.splitlines()[0].strip() if stripped_new else ""
                 if element_type_str == 'unknown' and first_line_new.startswith('@property'): element_type = CodeElementType.PROPERTY_GETTER
                 elif element_type_str == 'unknown' and first_line_new.startswith('@') and '.setter' in first_line_new: element_type = CodeElementType.PROPERTY_SETTER
                 elif element_type != CodeElementType.STATIC_PROPERTY: element_type = CodeElementType.METHOD
            logger.debug(f"Adjusted type to {element_type.value} because parent '{parent_name}' is present.")
        elif element_type == CodeElementType.STATIC_PROPERTY and not parent_name:
             logger.error(f"Cannot upsert static property '{name}' without a parent_name."); return original_code

        is_deleting = not new_code.strip()
        target_start_line, target_end_line = None, None # Definition line numbers from ExtractionService
        is_replacing = False

        # --- Find Existing Element ---
        if name and name != 'all':
            types_to_try = [element_type] if element_type != CodeElementType.UNKNOWN else \
                           [CodeElementType.METHOD, CodeElementType.PROPERTY_GETTER, CodeElementType.PROPERTY_SETTER, CodeElementType.STATIC_PROPERTY] if parent_name else \
                           [CodeElementType.FUNCTION, CodeElementType.CLASS]
            for try_type in types_to_try:
                 start, end = self.extraction_service.find_element(original_code, try_type.value, name, parent_name)
                 if start > 0:
                      target_start_line, target_end_line = start, end
                      if element_type == CodeElementType.UNKNOWN: element_type = try_type
                      is_replacing = True
                      action = "DELETE" if is_deleting else "REPLACE"
                      logger.info(f"Planning to {action} existing element '{name}' (found as type {element_type.value}) at definition line {start}")
                      break
            if not is_replacing:
                 if is_deleting: logger.error(f"Cannot delete element '{name}': Not found."); return original_code
                 else: logger.info(f"Element '{name}' not found. Planning to INSERT.")
        elif element_type == CodeElementType.IMPORT:
             start, end = self.extraction_service.find_element(original_code, CodeElementType.IMPORT.value, 'all', None)
             if start > 0:
                 target_start_line, target_end_line = start, end
                 is_replacing = True
                 action = "DELETE" if is_deleting else "REPLACE"; logger.info(f"Planning to {action} import block at lines {start}-{end}")
             elif is_deleting: logger.warning("Cannot delete import block: Not found."); return original_code
             else: logger.info("Import block not found. Planning to INSERT import(s).")
        elif is_deleting: logger.error("Cannot delete: No name specified."); return original_code
        else: logger.info("No name/type for replacement. Planning to INSERT.")

        # --- Perform AST Transformation ---
        try: original_tree = ast.fix_missing_locations(ast.parse(original_code))
        except SyntaxError as e: logger.error(f"Syntax error in original code: {e}"); return original_code

        new_nodes: List[ast.AST] = []
        markers_in_new_code = []
        if not is_deleting:
            try:
                for marker in self.MARKERS_TO_PRESERVE:
                     if marker in new_code: markers_in_new_code.append(marker)
                new_tree = ast.parse(new_code.strip())
                new_nodes = new_tree.body
                if not new_nodes: logger.warning("New code snippet parsed empty.")
            except SyntaxError as e: logger.error(f"Syntax error in new code: {e}"); return original_code
            except Exception as e: logger.error(f"Error parsing new code: {e}"); return original_code

        modified_tree = None
        transformer = None
        try:
            transformer = ReplaceOrInsertTransformer(
                definition_target_line=target_start_line, # Pass the line of def/class
                target_end_line=target_end_line,
                new_nodes=new_nodes,
                parent_name=parent_name,
                element_type=element_type,
                target_name=name if name != 'all' else None,
                formatter=self.formatter # Pass formatter instance
            )
            modified_tree = transformer.visit(original_tree)
            if modified_tree is None: logger.info("Transformation resulted in empty AST."); return '\n'
            if not transformer.operation_done:
                 action = 'replace/delete' if is_replacing else 'insert'
                 target_desc = f"'{name}' at line {target_start_line}" if is_replacing else f"'{name or element_type.value}' into parent '{parent_name}'"
                 logger.error(f"AST Transformer failed to {action} element {target_desc}.")
                 return original_code
            modified_tree = ast.fix_missing_locations(modified_tree)
            logger.info(f"AST Transformation successful: {'Replaced/Deleted' if is_replacing else 'Inserted'}")
        except Exception as e: logger.error(f"Error during AST transformation: {e}", exc_info=True); return original_code

        # --- Unparse ---
        try:
            if not isinstance(modified_tree, ast.AST): raise TypeError(f'Transformation result is not AST: {type(modified_tree)}')
            new_source = ast.unparse(modified_tree)
            logger.info('Unparsing successful.')
        except Exception as e: logger.error(f'Error unparsing modified AST: {e}', exc_info=True); return original_code

        # --- Post-Processing: Re-insert Marker Comments (Hack) ---
        if is_replacing and not is_deleting and markers_in_new_code:
            logger.debug(f"Attempting to re-insert markers: {markers_in_new_code}")
            search_name = name
            search_name_escaped = re.escape(search_name)
            # Added capturing group for indentation: ^([ \t]*)
            def_pattern = re.compile(rf"^([ \t]*)(?:async\s+)?def\s+{search_name_escaped}\s*\(", re.MULTILINE)
            match = def_pattern.search(new_source)
            if match:
                def_line_start_pos = match.start()
                def_line_end_pos = new_source.find(':', match.end())
                if def_line_end_pos != -1:
                    newline_after_def = new_source.find('\n', def_line_end_pos)
                    if newline_after_def != -1:
                        insertion_pos = newline_after_def + 1
                        indent_match = re.match(r'^(\s*)', new_source[insertion_pos:])
                        body_indent = indent_match.group(1) if indent_match else (self.formatter.indent_string or "    ")
                        # Capture indent from group 1 now
                        def_indent = match.group(1) or ""
                        if len(body_indent) <= len(def_indent): body_indent = def_indent + (self.formatter.indent_string or "    ")
                        markers_text = "\n".join([body_indent + marker for marker in markers_in_new_code]) + "\n"
                        new_source = new_source[:insertion_pos] + markers_text + new_source[insertion_pos:]
                        logger.info(f"Re-inserted markers after 'def {search_name}(...):'.")
                    else: logger.warning(f"Could not find newline after 'def {search_name}(...):' line to insert markers.")
                else: logger.warning(f"Could not find ':' after 'def {search_name}(' to insert markers.")
            else: logger.warning(f"Could not find 'def {search_name}(' in unparsed output to insert markers.")

        # Final cleanup & Validation
        final_code = new_source.rstrip() + '\n'
        try:
            ast.parse(final_code)
            logger.info("Final syntax validation successful.")
        except SyntaxError as syntax_e:
            logger.error(f"Syntax error AFTER transformation/comment insertion! Reverting. Error: {syntax_e}")
            # Log details for debugging...
            return original_code

        return final_code

    # --- Delegate other methods ---
    def add_element(self, original_code: str, new_code: str, parent_name: Optional[str]=None) -> str:
        name = "_UNKNOWN_ADDED_ELEMENT_"; element_type_str = "unknown"
        try:
            new_code_stripped = new_code.strip(); parsed = ast.parse(new_code_stripped)
            if parsed.body: node = parsed.body[0]; name = getattr(node, 'name', name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): element_type_str = CodeElementType.FUNCTION.value
            elif isinstance(node, ast.ClassDef): element_type_str = CodeElementType.CLASS.value
            elif isinstance(node, (ast.Import, ast.ImportFrom)): element_type_str = CodeElementType.IMPORT.value; name = 'all'
            elif isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                      element_type_str = CodeElementType.STATIC_PROPERTY.value; name = node.targets[0].id
        except Exception: pass
        logger.debug(f"Calling add_element, deduced name='{name}', type='{element_type_str}'. Delegating to upsert.")
        return self.upsert_element(original_code, element_type_str, name, new_code, parent_name)

    def replace_element(self, original_code: str, name: str, new_code: str, parent_name: Optional[str]=None) -> str:
        logger.debug(f"Calling replace_element for '{name}', parent '{parent_name}'. Delegating.")
        return self.upsert_element(original_code, 'unknown', name, new_code, parent_name)

    def remove_element(self, original_code: str, name: str, parent_name: Optional[str]=None) -> str:
        logger.debug(f"Calling remove_element for '{name}', parent '{parent_name}'. Delegating.")
        return self.upsert_element(original_code, 'unknown', name, '', parent_name)

    def upsert_element_by_xpath(self, original_code: str, xpath: str, new_code: str) -> str:
        from codehem.core.engine.xpath_parser import XPathParser
        logger.debug(f"Calling upsert_element_by_xpath for '{xpath}'")
        try:
            if not xpath.startswith(XPathParser.ROOT_ELEMENT + '.') and not xpath.startswith('['): xpath_proc = XPathParser.ROOT_ELEMENT + '.' + xpath
            else: xpath_proc = xpath
            element_name, parent_name, element_type_str_from_xpath = XPathParser.get_element_info(xpath_proc)
            op_element_type_str = element_type_str_from_xpath if element_type_str_from_xpath else 'unknown'
            op_name = element_name
            if not op_name and op_element_type_str == CodeElementType.IMPORT.value: op_name = 'all'
            elif not op_name:
                 if not new_code.strip(): raise ValueError(f"Cannot delete via XPath '{xpath}' without name.")
                 else:
                      try: new_tree = ast.parse(new_code.strip()); op_name = new_tree.body[0].name; logger.info(f"Deduced name '{op_name}' from new_code for XPath '{xpath}'")
                      except: raise ValueError(f"Cannot determine name for XPath '{xpath}' and cannot deduce from new_code.")
            return self.upsert_element(original_code, op_element_type_str, op_name, new_code, parent_name)
        except Exception as e: logger.error(f"Error processing XPath upsert for '{xpath}': {e}", exc_info=True); return original_code

    # --- Helper to get element type enum ---
    def _get_element_type_for_upsert(self, element_type_str: str, new_code_sample: str) -> CodeElementType:
        # (Using the refined version from v4.5)
        if element_type_str and element_type_str != CodeElementType.UNKNOWN.value:
            try: return CodeElementType(element_type_str)
            except ValueError: logger.warning(f"Invalid type '{element_type_str}'. Detecting.")
        stripped_code = new_code_sample.strip()
        if not stripped_code:
             if element_type_str and element_type_str != CodeElementType.UNKNOWN.value:
                 try: return CodeElementType(element_type_str)
                 except ValueError: pass
             raise ValueError('Cannot determine type for deletion without explicit type.')
        lines = stripped_code.splitlines(); first = lines[0].strip() if lines else ""; second = lines[1].strip() if len(lines)>1 else ""
        if first.startswith('@property'): return CodeElementType.PROPERTY_GETTER
        if first.startswith('@') and '.setter' in first: return CodeElementType.PROPERTY_SETTER
        def_line = first if first.startswith(('def ','async def')) else second if second.startswith(('def ','async def')) and first.startswith('@') else None
        if def_line: return CodeElementType.FUNCTION
        if first.startswith('class '): return CodeElementType.CLASS
        if first.startswith(('import ','from ')): return CodeElementType.IMPORT
        if '=' in first.split('#')[0] and ':' in first.split('=')[0]: return CodeElementType.STATIC_PROPERTY
        if '=' in first.split('#')[0] and not first.startswith(('def ','async def','class ','import ','from ','@')): return CodeElementType.STATIC_PROPERTY
        logger.error(f"Could not determine type from '{element_type_str}' or sample: {stripped_code[:50]}")
        raise ValueError(f'Invalid/undetectable type: {element_type_str}')