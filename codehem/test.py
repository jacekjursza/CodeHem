from codehem.core2fail.python.template_finder import PythonTemplateFinder
from codehem.core2fail.models import CodeElementType
import logging

# Setup logging to see the fallback paths
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

def demonstrate_finder_fallbacks():
    """Demonstrate the complete fallback path for method finding."""
    # Sample Python code with a class and method
    python_code = '''
class MyClass:
    def __init__(self, value=0):
        self.value = value
        
    def process_data(self, data):
        """Process the given data."""
        result = self.value + sum(data)
        return result
        
    def another_method(self):
        return self.value * 2
'''

    # Create a Python template finder
    finder = PythonTemplateFinder()
    
    print("=== LEVEL 1: Template Resolution ===")
    
    # 1. First attempt: Try with a valid template
    logger.debug("Attempting to get method query template...")
    query = finder.query_resolver.get_query(
        'python', 
        CodeElementType.METHOD.value, 
        'find_one', 
        method_name="process_data"
    )
    
    print(f"Template found: {query is not None}")
    if query:
        print(f"Template: {query[:50]}...")
    
    # 2. Try a non-existent template to show fallback
    logger.debug("Attempting to get non-existent template (to demonstrate fallback)...")
    non_existent = finder.query_resolver.get_query(
        'python', 
        CodeElementType.METHOD.value, 
        'non_existent_operation', 
        method_name="process_data"
    )
    
    print(f"Non-existent template found: {non_existent is not None}")
    
    # If we have a common template, it would fall back to that
    print("\n=== LEVEL 2: Finder Implementation Resolution ===")
    # This is handled by the ModuleResolver which is already initialized
    print("ModuleResolver path for 'python/method/finder':")
    path = finder.query_resolver._get_resolution_path('python', 'method')
    print("\n".join(f"- {p}" for p in path))
    
    print("\n=== LEVEL 3: Approach Fallback (Tree-sitter → Regex) ===")
    
    # First try normal method finding (should work)
    print("Finding existing method 'process_data'...")
    method_range = finder.find_method(python_code, "MyClass", "process_data")
    print(f"Method range: {method_range}")
    
    # Now try finding a non-existent method to trigger regex fallback
    print("\nFinding non-existent method 'missing_method'...")
    
    # Temporarily modify the finder's query_resolver to simulate tree-sitter failure
    original_has_query = finder.query_resolver.has_query
    finder.query_resolver.has_query = lambda *args, **kwargs: False
    
    # This should fall back to regex
    logger.debug("Tree-sitter approach will fail, expecting regex fallback...")
    missing_method_range = finder.find_method(python_code, "MyClass", "missing_method")
    print(f"Method range from regex fallback: {missing_method_range}")
    
    # Restore original behavior
    finder.query_resolver.has_query = original_has_query
    
    print("\n=== Complete Fallback Chain Demonstration ===")
    
    # Show the complete fallback chain in action
    # 1. Create a finder without internal templates
    empty_finder = PythonTemplateFinder()
    empty_finder.query_resolver._language_managers = {}  # Empty templates
    
    print("Finding method with empty templates (should trigger all fallbacks)...")
    
    # This should try tree-sitter first, then fall back to regex
    last_resort_range = empty_finder.find_method(python_code, "MyClass", "process_data")
    print(f"Final result after all fallbacks: {last_resort_range}")

if __name__ == "__main__":
    demonstrate_finder_fallbacks()