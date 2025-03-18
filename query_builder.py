"""
Query builder for constructing consistent tree-sitter queries across languages.
"""
from typing import Dict, List, Optional

class QueryBuilder:
    """
    Builder for constructing tree-sitter queries with a unified interface 
    for different languages.
    """
    
    # Standard query patterns for different languages
    QUERY_PATTERNS = {
        'python': {
            'function': '(function_definition name: (identifier) @func_name) @function',
            'class': '(class_definition name: (identifier) @class_name) @class',
            'method': '(function_definition name: (identifier) @method_name) @method',
            'property': '(decorated_definition (decorator) @decorator (function_definition name: (identifier) @prop_name)) @property',
            'import': '(import_statement) @import (import_from_statement) @import',
            'class_with_name': '(class_definition name: (identifier) @class_name (#eq? @class_name "{name}")) @class',
            'function_with_name': '(function_definition name: (identifier) @func_name (#eq? @func_name "{name}")) @function',
            'method_with_name': '(function_definition name: (identifier) @method_name (#eq? @method_name "{name}")) @method',
            'property_decorator': '@property',
            'setter_decorator': '@{name}.setter',
            'class_field': '(assignment left: (identifier) @field_name) @field',
        },
        'typescript': {
            'function': '(function_declaration name: (identifier) @func_name) @function',
            'class': '(class_declaration name: (identifier) @class_name) @class',
            'method': '(method_definition name: (property_identifier) @method_name) @method',
            'property': '(public_field_definition name: (property_identifier) @prop_name) @property',
            'import': '(import_statement) @import (import_clause) @import',
            'class_with_name': '(class_declaration name: (identifier) @class_name (#eq? @class_name "{name}")) @class',
            'function_with_name': '(function_declaration name: (identifier) @func_name (#eq? @func_name "{name}")) @function',
            'method_with_name': '(method_definition name: (property_identifier) @method_name (#eq? @method_name "{name}")) @method',
            'getter': '(method_definition name: (property_identifier) @getter (#match? @getter "^get.*")) @getter_method',
            'setter': '(method_definition name: (property_identifier) @setter (#match? @setter "^set.*")) @setter_method',
            'class_field': '(public_field_definition name: (property_identifier) @field_name) @field',
        }
    }
    
    def __init__(self, language: str):
        """
        Initialize the query builder for a specific language.
        
        Args:
            language: Language code (e.g., 'python', 'typescript')
        """
        self.language = language.lower()
        if self.language not in self.QUERY_PATTERNS:
            raise ValueError(f"Unsupported language: {language}")
        self.patterns = self.QUERY_PATTERNS[self.language]
    
    def get_pattern(self, pattern_name: str, **kwargs) -> str:
        """
        Get a query pattern for the current language with optional formatting.
        
        Args:
            pattern_name: Name of the pattern to retrieve
            **kwargs: Format arguments to inject into the pattern
            
        Returns:
            Formatted query string
        """
        if pattern_name not in self.patterns:
            raise ValueError(f"Unknown pattern: {pattern_name} for language {self.language}")
        
        pattern = self.patterns[pattern_name]
        if kwargs:
            return pattern.format(**kwargs)
        return pattern
    
    def build_class_query(self, class_name: Optional[str] = None) -> str:
        """
        Build a query to find a class, optionally with a specific name.
        
        Args:
            class_name: Optional name of the class to find
            
        Returns:
            Query string
        """
        if class_name:
            return self.get_pattern('class_with_name', name=class_name)
        return self.get_pattern('class')
    
    def build_function_query(self, function_name: Optional[str] = None) -> str:
        """
        Build a query to find a function, optionally with a specific name.
        
        Args:
            function_name: Optional name of the function to find
            
        Returns:
            Query string
        """
        if function_name:
            return self.get_pattern('function_with_name', name=function_name)
        return self.get_pattern('function')
    
    def build_method_query(self, method_name: Optional[str] = None, class_name: Optional[str] = None) -> str:
        """
        Build a query to find a method, optionally within a specific class.
        
        Args:
            method_name: Optional name of the method to find
            class_name: Optional name of the class containing the method
            
        Returns:
            Query string
        """
        if method_name:
            method_query = self.get_pattern('method_with_name', name=method_name)
            if class_name:
                # For languages like Python, we need to check if the method is inside the class
                if self.language == 'python':
                    return f"""
                    (class_definition
                      name: (identifier) @class_name (#eq? @class_name "{class_name}")
                      body: (_) @class_body
                      (#match? @class_body ".*{method_name}.*"))
                    """
            return method_query
        return self.get_pattern('method')
    
    def build_property_query(self, property_name: Optional[str] = None, class_name: Optional[str] = None) -> str:
        """
        Build a query to find a property, optionally within a specific class.
        
        Args:
            property_name: Optional name of the property to find
            class_name: Optional name of the class containing the property
            
        Returns:
            Query string
        """
        if self.language == 'python':
            if property_name:
                property_query = f"""
                (function_definition
                  name: (identifier) @prop_name (#eq? @prop_name "{property_name}"))
                """
                if class_name:
                    return f"""
                    (class_definition
                      name: (identifier) @class_name (#eq? @class_name "{class_name}")
                      body: (_) @class_body
                      (#match? @class_body ".*@property.*{property_name}.*"))
                    """
                return property_query
        elif self.language == 'typescript':
            if property_name:
                property_query = f"""
                (public_field_definition
                  name: (property_identifier) @prop_name (#eq? @prop_name "{property_name}"))
                """
                if class_name:
                    return f"""
                    (class_declaration
                      name: (identifier) @class_name (#eq? @class_name "{class_name}")
                      body: (class_body) @class_body
                      (#match? @class_body ".*{property_name}.*"))
                    """
                return property_query
        
        return self.get_pattern('property')
    
    def build_import_query(self) -> str:
        """
        Build a query to find imports.
        
        Returns:
            Query string
        """
        return self.get_pattern('import')
    
    def build_class_field_query(self, class_name: Optional[str] = None) -> str:
        """
        Build a query to find class fields.
        
        Args:
            class_name: Optional name of the class containing the fields
            
        Returns:
            Query string
        """
        field_query = self.get_pattern('class_field')
        
        if class_name:
            if self.language == 'python':
                return f"""
                (class_definition
                  name: (identifier) @class_name (#eq? @class_name "{class_name}")
                  body: (_) @class_body
                  (#match? @class_body ".*=.*"))
                """
            elif self.language == 'typescript':
                return f"""
                (class_declaration
                  name: (identifier) @class_name (#eq? @class_name "{class_name}")
                  body: (class_body) @class_body)
                """
        
        return field_query
    
    def build_custom_query(self, query_string: str, **kwargs) -> str:
        """
        Build a custom query with optional formatting.
        
        Args:
            query_string: Custom query string
            **kwargs: Format arguments to inject into the query
            
        Returns:
            Formatted query string
        """
        if kwargs:
            return query_string.format(**kwargs)
        return query_string