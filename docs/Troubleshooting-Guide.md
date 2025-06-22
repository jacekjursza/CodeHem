# Troubleshooting Guide

This guide helps resolve common issues when using CodeHem.

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [Language Detection Problems](#language-detection-problems)
3. [Extraction Issues](#extraction-issues)
4. [Patch Application Failures](#patch-application-failures)
5. [Performance Issues](#performance-issues)
6. [Plugin Problems](#plugin-problems)
7. [Development Issues](#development-issues)

## Installation Issues

### Problem: `pip install codehem` fails

**Common causes:**
- Python version incompatibility
- Missing system dependencies
- Network/proxy issues

**Solutions:**

```bash
# Check Python version (requires 3.8+)
python --version

# Update pip
pip install --upgrade pip

# Install with verbose output
pip install -v codehem

# Use alternative index
pip install -i https://pypi.org/simple/ codehem

# Install specific version
pip install codehem==1.0.0
```

### Problem: Tree-sitter compilation errors

**Error message:** `Failed building wheel for tree-sitter`

**Solutions:**

```bash
# Install build tools (Windows)
pip install setuptools wheel

# Install build tools (macOS)
xcode-select --install

# Install build tools (Linux)
sudo apt-get install build-essential
# or
sudo yum install gcc gcc-c++ make

# Alternative: Use pre-compiled wheels
pip install --only-binary=all codehem
```

### Problem: CLI command not found

**Error:** `codehem: command not found`

**Solutions:**

```bash
# Check if installed in user directory
python -m pip show codehem

# Use python module syntax
python -m codehem detect file.py

# Install with pipx for better CLI support
pipx install codehem

# Add to PATH manually
export PATH="$HOME/.local/bin:$PATH"
```

## Language Detection Problems

### Problem: Language not detected correctly

**Symptoms:**
- Wrong language detected for file
- "Unsupported file extension" error

**Debugging:**

```bash
# Test detection manually
codehem detect suspicious_file.py --verbose

# Force language
python -c "
from codehem import CodeHem
hem = CodeHem('python')  # Force Python
result = hem.extract(code)
"
```

**Solutions:**

1. **Check file extension mapping:**
   ```python
   from codehem.core.engine.languages import FILE_EXTENSIONS
   print(FILE_EXTENSIONS)
   ```

2. **Use explicit language specification:**
   ```python
   # Instead of auto-detection
   hem = CodeHem.from_raw_code(code)
   
   # Force specific language
   hem = CodeHem("typescript")
   ```

3. **Content-based detection issues:**
   - Ensure file has recognizable language patterns
   - Check for encoding issues (use UTF-8)

### Problem: "Unknown language" error

**Error:** `ValueError: Unknown language: xyz`

**Solutions:**

```bash
# List available languages
python -c "
from codehem.core.engine.languages import LANGUAGES
print(list(LANGUAGES.keys()))
"

# Check installed plugins
pip list | grep codehem

# Install missing language plugin
pip install codehem-lang-java
```

## Extraction Issues

### Problem: No elements extracted

**Symptoms:**
- `extract()` returns empty results
- Expected classes/functions not found

**Debugging:**

```python
from codehem import CodeHem
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

hem = CodeHem("python")
result = hem.extract(code)

# Check individual element types
print(f"Classes: {len(result.classes)}")
print(f"Functions: {len(result.functions)}")
print(f"Methods: {len(result.methods)}")
```

**Common causes:**

1. **Syntax errors in code:**
   ```python
   # Test parsing
   hem = CodeHem("python")
   try:
       tree = hem._get_parser().parse(code)
       print("Parse successful")
   except Exception as e:
       print(f"Parse error: {e}")
   ```

2. **Unsupported language constructs:**
   - Very new syntax features
   - Language-specific extensions
   - Malformed code

3. **Tree-sitter query issues:**
   ```python
   # Test direct tree-sitter parsing
   import tree_sitter_python
   from tree_sitter import Language, Parser
   
   language = Language(tree_sitter_python.language())
   parser = Parser()
   parser.set_language(language)
   tree = parser.parse(code.encode())
   print(tree.root_node.sexp())  # Check AST structure
   ```

### Problem: Incorrect element relationships

**Symptoms:**
- Methods not associated with correct classes
- Wrong parent-child relationships

**Solutions:**

1. **Check post-processor logic:**
   ```python
   # Enable verbose logging for post-processing
   import logging
   logging.getLogger('codehem.core.post_processors').setLevel(logging.DEBUG)
   ```

2. **Verify extraction data:**
   ```python
   # Get raw extraction data before post-processing
   service = hem._get_language_service()
   components = service.get_components()
   extractor = components['extractor']
   
   # Extract raw data
   tree = hem._parse_code(code)
   raw_classes = extractor.extract_classes(tree, code.encode())
   raw_methods = extractor.extract_methods(tree, code.encode())
   
   print("Raw classes:", raw_classes)
   print("Raw methods:", raw_methods)
   ```

## Patch Application Failures

### Problem: "ConflictError" when applying patches

**Error:** `ConflictError: Hash mismatch - code was modified`

**Cause:** The code was changed after the hash was generated.

**Solutions:**

1. **Refresh hash before applying:**
   ```python
   # Get fresh hash
   current_text, current_hash = hem.get_text_by_xpath(
       current_code, xpath, return_hash=True
   )
   
   # Apply with fresh hash
   result = hem.apply_patch(
       xpath=xpath,
       new_code=new_code,
       mode="replace",
       original_hash=current_hash
   )
   ```

2. **Use patch without hash validation:**
   ```python
   # Skip hash validation (less safe)
   result = hem.apply_patch(
       xpath=xpath,
       new_code=new_code,
       mode="replace"
       # No original_hash parameter
   )
   ```

### Problem: "Element not found" error

**Error:** `XPathError: Element not found at xpath`

**Debugging:**

```python
# Test xpath exists
text = hem.get_text_by_xpath(code, xpath)
if text is None:
    print(f"XPath not found: {xpath}")
    
    # List available elements
    result = hem.extract(code)
    for cls in result.classes:
        print(f"Class: {cls.name}")
        for method in cls.methods:
            print(f"  Method: {cls.name}.{method.name}[method]")
```

**Common xpath issues:**

1. **Case sensitivity:**
   ```python
   # Wrong
   xpath = "myclass.mymethod[method]"
   
   # Correct  
   xpath = "MyClass.myMethod[method]"
   ```

2. **Incorrect element type:**
   ```python
   # Wrong
   xpath = "MyClass.myProperty[method]"
   
   # Correct
   xpath = "MyClass.myProperty[property]"
   ```

3. **Missing parent class:**
   ```python
   # Wrong (for method in class)
   xpath = "myMethod[method]"
   
   # Correct
   xpath = "MyClass.myMethod[method]"
   ```

### Problem: Malformed code after patch

**Symptoms:**
- Syntax errors after applying patch
- Incorrect indentation
- Missing brackets/parentheses

**Solutions:**

1. **Use dry-run to preview:**
   ```python
   result = hem.apply_patch(
       xpath=xpath,
       new_code=new_code,
       mode="replace",
       dry_run=True
   )
   print("Preview:", result["diff"])
   ```

2. **Check formatter configuration:**
   ```python
   # Get language service
   service = hem._get_language_service()
   components = service.get_components()
   formatter = components['formatter']
   
   # Check formatting settings
   print(f"Indent size: {formatter.indent_size}")
   print(f"Use tabs: {formatter.use_tabs}")
   ```

3. **Validate new code syntax:**
   ```python
   # Test new code can be parsed
   try:
       test_tree = hem._parse_code(new_code)
       print("New code syntax is valid")
   except Exception as e:
       print(f"New code has syntax error: {e}")
   ```

## Performance Issues

### Problem: Slow extraction on large files

**Symptoms:**
- Long processing times (>5 seconds)
- High memory usage
- Timeouts

**Solutions:**

1. **Use workspace for multiple files:**
   ```python
   # Instead of individual file processing
   workspace = CodeHem.open_workspace("/path/to/repo")
   
   # Indexes all files once
   matches = workspace.find(name="target", kind="method")
   ```

2. **Enable caching:**
   ```python
   # Cache is enabled by default, but verify
   import os
   print("Cache enabled:", os.environ.get('CODEHEM_CACHE', 'true'))
   
   # Clear cache if needed
   hem.clear_cache()
   ```

3. **Profile performance:**
   ```python
   import cProfile
   import time
   
   def profile_extraction():
       start = time.time()
       result = hem.extract(large_code)
       end = time.time()
       print(f"Extraction took {end - start:.2f} seconds")
       return result
   
   cProfile.run('profile_extraction()')
   ```

### Problem: Memory leaks with repeated operations

**Solutions:**

1. **Clear caches periodically:**
   ```python
   # Clear internal caches
   hem.clear_cache()
   
   # Force garbage collection
   import gc
   gc.collect()
   ```

2. **Use context managers for workspace:**
   ```python
   with CodeHem.open_workspace("/path") as workspace:
       # Operations here
       pass
   # Workspace cleaned up automatically
   ```

## Plugin Problems

### Problem: Plugin not detected

**Error:** `ModuleNotFoundError: No module named 'codehem_lang_xyz'`

**Solutions:**

```bash
# Check plugin installation
pip list | grep codehem-lang

# Reinstall plugin
pip uninstall codehem-lang-java
pip install codehem-lang-java

# Verify entry points
python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('codehem.languages'):
    print(f'{ep.name}: {ep.module_name}')
"
```

### Problem: Plugin conflicts

**Symptoms:**
- Wrong plugin used for file type
- Inconsistent behavior

**Solutions:**

1. **Check plugin priority:**
   ```python
   from codehem.core.registry import get_language_services
   services = get_language_services()
   for name, service in services.items():
       print(f"{name}: {service.get_file_extensions()}")
   ```

2. **Force specific plugin:**
   ```python
   # Don't rely on auto-detection
   hem = CodeHem("specific_language")
   ```

## Development Issues

### Problem: Tests failing

**Common test issues:**

1. **Check test environment:**
   ```bash
   # Install test dependencies
   pip install -e .[dev]
   
   # Run with verbose output
   pytest -xvs
   
   # Run specific test
   pytest tests/test_specific.py::test_function -v
   ```

2. **Check fixture loading:**
   ```python
   # Test fixture loading
   from tests.helpers.fixture_loader import load_fixture
   code = load_fixture('python/general/simple_class.txt')
   print(f"Fixture loaded: {len(code)} characters")
   ```

### Problem: Debug logging not appearing

**Solutions:**

```python
import logging

# Configure logging properly
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific loggers
logging.getLogger('codehem').setLevel(logging.DEBUG)
logging.getLogger('codehem.core').setLevel(logging.DEBUG)
```

### Problem: IDE integration issues

**For VS Code:**

1. **Check Python interpreter:**
   - Ensure correct Python environment
   - Verify CodeHem is installed in active environment

2. **Configure debugging:**
   ```json
   // .vscode/launch.json
   {
       "version": "0.2.0",
       "configurations": [
           {
               "name": "Python: CodeHem Debug",
               "type": "python",
               "request": "launch",
               "program": "${workspaceFolder}/debug_script.py",
               "console": "integratedTerminal",
               "env": {
                   "PYTHONPATH": "${workspaceFolder}",
                   "CODEHEM_DEBUG": "true"
               }
           }
       ]
   }
   ```

## Getting Help

### Enable verbose logging

```python
import logging
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Enable all CodeHem loggers
for logger_name in ['codehem', 'codehem.core', 'codehem.languages']:
    logging.getLogger(logger_name).setLevel(logging.DEBUG)
```

### Collect diagnostic information

```python
import sys
import platform
from codehem import __version__

print(f"CodeHem version: {__version__}")
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")

# Check available languages
from codehem.core.engine.languages import LANGUAGES
print(f"Available languages: {list(LANGUAGES.keys())}")

# Check installed packages
import pkg_resources
codehem_packages = [pkg for pkg in pkg_resources.working_set if 'codehem' in pkg.key]
for pkg in codehem_packages:
    print(f"Package: {pkg.key} {pkg.version}")
```

### Report issues

When reporting issues, include:

1. **Environment information** (from diagnostic script above)
2. **Minimal code example** that reproduces the issue
3. **Complete error traceback**
4. **Expected vs actual behavior**
5. **Steps to reproduce**

Submit issues at: https://github.com/codehem/codehem/issues

For urgent issues or questions:
- Check existing issues and discussions
- Provide complete context and examples
- Include logs with `DEBUG` level enabled