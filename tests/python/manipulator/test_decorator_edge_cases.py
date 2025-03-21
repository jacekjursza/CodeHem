import unittest
from codehem.core.manipulator.factory import get_code_manipulator

class TestDecoratorEdgeCases(unittest.TestCase):
    
    def setUp(self):
        self.manipulator = get_code_manipulator('python')
    
    def test_parameterized_decorators(self):
        original_code = '''
@decorator_with_args("arg1", "arg2", keyword=True)
def decorated_function(x, y):
    return x + y
'''
        
        new_function = '''
@decorator_with_args("new_arg1", "new_arg2", keyword=False, extra=123)
def decorated_function(x, y, z=0):
    return x + y + z
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'decorated_function', new_function)
        
        # Verify decorator and function were updated
        self.assertIn('@decorator_with_args("new_arg1", "new_arg2", keyword=False, extra=123)', modified_code)
        self.assertIn('def decorated_function(x, y, z=0):', modified_code)
        self.assertIn('return x + y + z', modified_code)
    
    def test_multiple_stacked_decorators(self):
        original_code = '''
@decorator1
@decorator2
@decorator3
def decorated_function(x):
    return x * 2
'''
        
        new_function = '''
@decorator1
@new_decorator
@decorator3
def decorated_function(x, y=1):
    return x * y
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'decorated_function', new_function)
        
        # Verify decorators and function were updated correctly
        self.assertIn('@decorator1', modified_code)
        self.assertIn('@new_decorator', modified_code)
        self.assertIn('@decorator3', modified_code)
        self.assertNotIn('@decorator2', modified_code)
        self.assertIn('def decorated_function(x, y=1):', modified_code)
        self.assertIn('return x * y', modified_code)
    
    def test_complex_decorator_arguments(self):
        original_code = '''
@route("/api/v1/users", methods=["GET", "POST"], auth=auth_required(role="admin"))
def user_endpoint():
    return {"status": "success"}
'''
        
        new_function = '''
@route(
    "/api/v2/users", 
    methods=["GET", "POST", "PUT"], 
    auth=auth_required(role="admin", permissions=["read", "write"]),
    rate_limit=RateLimit(
        requests=100,
        period=60,
        by="ip"
    )
)
def user_endpoint(user_id=None):
    if user_id:
        return {"status": "success", "user_id": user_id}
    return {"status": "success", "users": []}
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'user_endpoint', new_function)
        
        # Verify complex decorator structure was preserved
        self.assertIn('@route(', modified_code)
        self.assertIn('"/api/v2/users",', modified_code)
        self.assertIn('methods=["GET", "POST", "PUT"],', modified_code)
        self.assertIn('auth=auth_required(role="admin", permissions=["read", "write"]),', modified_code)
        self.assertIn('rate_limit=RateLimit(', modified_code)
        self.assertIn('requests=100,', modified_code)
        self.assertIn('period=60,', modified_code)
        self.assertIn('by="ip"', modified_code)
        self.assertIn(')', modified_code)
        self.assertIn('def user_endpoint(user_id=None):', modified_code)
    
    def test_property_decorator_and_setter(self):
        original_code = '''
class Person:
    def __init__(self, name):
        self._name = name
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        if not value:
            raise ValueError("Name cannot be empty")
        self._name = value
'''
        
        new_property = '''
@property
def name(self):
    """Get the person's name."""
    return self._name.strip()
'''
        
        # Replace only the getter
        modified_code = self.manipulator.replace_property(original_code, 'Person', 'name', new_property)
        
        # Verify the getter was replaced but setter remains
        self.assertIn('@property', modified_code)
        self.assertIn('def name(self):', modified_code)
        self.assertIn('"""Get the person\'s name."""', modified_code)
        self.assertIn('return self._name.strip()', modified_code)
        self.assertIn('@name.setter', modified_code)
        self.assertIn('if not value:', modified_code)
        
        # Now replace the setter
        new_setter = '''
@name.setter
def name(self, value):
    """Set the person's name with validation."""
    value = value.strip()
    if not value:
        raise ValueError("Name cannot be empty")
    if len(value) < 2:
        raise ValueError("Name is too short")
    self._name = value
'''
        
        # Replace only the setter
        modified_code_2 = self.manipulator.replace_property_setter(modified_code, 'Person', 'name', new_setter)
        
        # Verify both getter and setter were updated
        self.assertIn('@property', modified_code_2)
        self.assertIn('"""Get the person\'s name."""', modified_code_2)
        self.assertIn('return self._name.strip()', modified_code_2)
        self.assertIn('@name.setter', modified_code_2)
        self.assertIn('"""Set the person\'s name with validation."""', modified_code_2)
        self.assertIn('if len(value) < 2:', modified_code_2)
        self.assertIn('raise ValueError("Name is too short")', modified_code_2)
    
    def test_class_decorators(self):
        original_code = '''
@dataclass
class Configuration:
    name: str
    version: str = "1.0.0"
'''
        
        new_class = '''
@dataclass(frozen=True)
class Configuration:
    name: str
    version: str = "1.0.0"
    debug: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)
'''
        
        modified_code = self.manipulator.replace_class(original_code, 'Configuration', new_class)
        
        # Verify class was replaced with updated decorator
        self.assertIn('@dataclass(frozen=True)', modified_code)
        self.assertIn('class Configuration:', modified_code)
        self.assertIn('name: str', modified_code)
        self.assertIn('debug: bool = False', modified_code)
        self.assertIn('settings: Dict[str, Any] = field(default_factory=dict)', modified_code)
    
    def test_method_decorator_with_class_method(self):
        original_code = '''
class Registry:
    _instances = {}
    
    @classmethod
    def register(cls, name):
        def decorator(class_):
            cls._instances[name] = class_()
            return class_
        return decorator
    
    @classmethod
    def get(cls, name):
        return cls._instances.get(name)
'''
        
        new_method = '''
@classmethod
def register(cls, name, *, singleton=True):
    """Register a class in the registry."""
    def decorator(class_):
        if name in cls._instances:
            raise KeyError(f"{name} already registered")
        if singleton:
            cls._instances[name] = class_()
        else:
            cls._instances[name] = class_
        return class_
    return decorator
'''
        
        modified_code = self.manipulator.replace_method(original_code, 'Registry', 'register', new_method)
        
        # Verify method decorator preserved
        self.assertIn('@classmethod', modified_code)
        self.assertIn('def register(cls, name, *, singleton=True):', modified_code)
        self.assertIn('"""Register a class in the registry."""', modified_code)
        self.assertIn('if name in cls._instances:', modified_code)
        self.assertIn('raise KeyError(f"{name} already registered")', modified_code)
        
        # Check the other method is untouched
        self.assertIn('def get(cls, name):', modified_code)
        self.assertIn('return cls._instances.get(name)', modified_code)

if __name__ == '__main__':
    unittest.main()