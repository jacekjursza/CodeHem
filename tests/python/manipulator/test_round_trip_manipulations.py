import unittest
from core.manipulator.factory import get_code_manipulator
from core.finder.factory import get_code_finder

class TestRoundTripManipulations(unittest.TestCase):
    
    def setUp(self):
        self.manipulator = get_code_manipulator('python')
        self.finder = get_code_finder('python')
    
    def test_modify_and_find_function(self):
        original_code = '\ndef calculate_total(items, tax_rate=0.0):\n    """Calculate total cost with tax."""\n    subtotal = sum(items)\n    tax = subtotal * tax_rate\n    return subtotal + tax\n'
        (start_line, end_line) = self.finder.find_function(original_code, 'calculate_total')
        self.assertEqual(start_line, 2)
        self.assertEqual(end_line, 6)  # Changed from 5 to 6 to match actual end line
        new_function = '\ndef calculate_total(items, tax_rate=0.0, discount=0.0):\n    """Calculate total cost with tax and discount."""\n    subtotal = sum(items)\n    tax = subtotal * tax_rate\n    discounted = subtotal * (1 - discount)\n    return discounted + tax\n'
        modified_code = self.manipulator.replace_function(original_code, 'calculate_total', new_function)
        (new_start_line, new_end_line) = self.finder.find_function(modified_code, 'calculate_total')
        self.assertNotEqual(new_start_line, 0)
        self.assertNotEqual(new_end_line, 0)
        function_lines = modified_code.splitlines()[new_start_line - 1:new_end_line]
        function_text = '\n'.join(function_lines)
        self.assertIn('def calculate_total(items, tax_rate=0.0, discount=0.0):', function_text)
        self.assertIn('discounted = subtotal * (1 - discount)', function_text)
    
    def test_add_find_modify_method(self):
        original_code = '''
class ShoppingCart:
    def __init__(self):
        self.items = []
'''
        
        # Step 1: Add a method
        add_method = '''
def add_item(self, item, quantity=1):
    for _ in range(quantity):
        self.items.append(item)
'''
        
        modified_code = self.manipulator.add_method_to_class(original_code, 'ShoppingCart', add_method)
        
        # Step 2: Find the added method
        (start_line, end_line) = self.finder.find_method(modified_code, 'ShoppingCart', 'add_item')
        
        # Verify it's findable
        self.assertNotEqual(start_line, 0)
        self.assertNotEqual(end_line, 0)
        
        # Step 3: Modify the method
        new_method = '''
def add_item(self, item, quantity=1, price=None):
    if price is not None:
        item = {'name': item, 'price': price}
    for _ in range(quantity):
        self.items.append(item)
'''
        
        modified_code_2 = self.manipulator.replace_method(modified_code, 'ShoppingCart', 'add_item', new_method)
        
        # Step 4: Find the method again
        (new_start_line, new_end_line) = self.finder.find_method(modified_code_2, 'ShoppingCart', 'add_item')
        
        # Verify it's still findable
        self.assertNotEqual(new_start_line, 0)
        self.assertNotEqual(new_end_line, 0)
        
        # Extract the method to verify its content
        method_lines = modified_code_2.splitlines()[new_start_line-1:new_end_line]
        method_text = '\n'.join(method_lines)
        
        self.assertIn('def add_item(self, item, quantity=1, price=None):', method_text)
        self.assertIn("item = {'name': item, 'price': price}", method_text)
    
    def test_multi_step_class_transformation(self):
        original_code = '''
class Shape:
    def __init__(self, color="black"):
        self.color = color
    
    def area(self):
        raise NotImplementedError("Subclasses must implement area()")
'''
        
        # Step 1: Add a method
        add_method = '''
def perimeter(self):
    raise NotImplementedError("Subclasses must implement perimeter()")
'''
        
        modified_code = self.manipulator.add_method_to_class(original_code, 'Shape', add_method)
        
        # Step 2: Verify method was added and can be found
        (method_start, method_end) = self.finder.find_method(modified_code, 'Shape', 'perimeter')
        self.assertNotEqual(method_start, 0)
        
        # Step 3: Update the constructor
        new_init = '''
def __init__(self, color="black", filled=False):
    self.color = color
    self.filled = filled
'''
        
        modified_code_2 = self.manipulator.replace_method(modified_code, 'Shape', '__init__', new_init)
        
        # Step 4: Verify both methods exist and constructor was updated
        (init_start, init_end) = self.finder.find_method(modified_code_2, 'Shape', '__init__')
        (area_start, area_end) = self.finder.find_method(modified_code_2, 'Shape', 'area')
        (peri_start, peri_end) = self.finder.find_method(modified_code_2, 'Shape', 'perimeter')
        
        self.assertNotEqual(init_start, 0)
        self.assertNotEqual(area_start, 0)
        self.assertNotEqual(peri_start, 0)
        
        # Step 5: Add a property
        add_property = '''
@property
def info(self):
    filled_status = "filled" if self.filled else "not filled"
    return f"{self.color} shape, {filled_status}"
'''
        
        modified_code_3 = self.manipulator.add_method_to_class(modified_code_2, 'Shape', add_property)
        
        # Step 6: Verify all elements exist
        (init_start, init_end) = self.finder.find_method(modified_code_3, 'Shape', '__init__')
        (area_start, area_end) = self.finder.find_method(modified_code_3, 'Shape', 'area')
        (peri_start, peri_end) = self.finder.find_method(modified_code_3, 'Shape', 'perimeter')
        (info_start, info_end) = self.finder.find_property(modified_code_3, 'Shape', 'info')
        
        self.assertNotEqual(init_start, 0)
        self.assertNotEqual(area_start, 0)
        self.assertNotEqual(peri_start, 0)
        self.assertNotEqual(info_start, 0)
        
        # Verify content
        info_lines = modified_code_3.splitlines()[info_start-1:info_end]
        info_text = '\n'.join(info_lines)
        
        self.assertIn('@property', info_text)
        self.assertIn('def info(self):', info_text)
        self.assertIn('filled_status = "filled" if self.filled else "not filled"', info_text)
    
    def test_property_roundtrip(self):
        original_code = '''
class Temperature:
    def __init__(self, celsius=0):
        self._celsius = celsius
    
    @property
    def celsius(self):
        return self._celsius
    
    @celsius.setter
    def celsius(self, value):
        self._celsius = value
'''
        
        # Step 1: Find property
        (getter_start, getter_end) = self.finder.find_property(original_code, 'Temperature', 'celsius')
        (setter_start, setter_end) = self.finder.find_property_setter(original_code, 'Temperature', 'celsius')
        
        self.assertNotEqual(getter_start, 0)
        self.assertNotEqual(setter_start, 0)
        
        # Step 2: Replace property
        new_property = '''
@property
def celsius(self):
    """Get temperature in Celsius."""
    return round(self._celsius, 1)
'''
        
        modified_code = self.manipulator.replace_property(original_code, 'Temperature', 'celsius', new_property)
        
        # Step 3: Find property again
        (new_getter_start, new_getter_end) = self.finder.find_property(modified_code, 'Temperature', 'celsius')
        (new_setter_start, new_setter_end) = self.finder.find_property_setter(modified_code, 'Temperature', 'celsius')
        
        self.assertNotEqual(new_getter_start, 0)
        self.assertNotEqual(new_setter_start, 0)
        
        # Step 4: Add fahrenheit property
        add_property = '''
@property
def fahrenheit(self):
    """Get temperature in Fahrenheit."""
    return (self.celsius * 9/5) + 32

@fahrenheit.setter
def fahrenheit(self, value):
    """Set temperature in Fahrenheit."""
    self.celsius = (value - 32) * 5/9
'''
        
        modified_code_2 = self.manipulator.add_method_to_class(modified_code, 'Temperature', add_property)
        
        # Step 5: Find all properties
        (celsius_getter_start, _) = self.finder.find_property(modified_code_2, 'Temperature', 'celsius')
        (celsius_setter_start, _) = self.finder.find_property_setter(modified_code_2, 'Temperature', 'celsius')
        (fahrenheit_getter_start, _) = self.finder.find_property(modified_code_2, 'Temperature', 'fahrenheit')
        (fahrenheit_setter_start, _) = self.finder.find_property_setter(modified_code_2, 'Temperature', 'fahrenheit')
        
        self.assertNotEqual(celsius_getter_start, 0)
        self.assertNotEqual(celsius_setter_start, 0)
        self.assertNotEqual(fahrenheit_getter_start, 0)
        self.assertNotEqual(fahrenheit_setter_start, 0)
        
        # Extract the property to verify its content
        # Note: This verifies structural integrity after multiple operations
        lines = modified_code_2.splitlines()
        fahrenheit_getter_text = '\n'.join(lines[fahrenheit_getter_start-1:fahrenheit_setter_start-1])
        
        self.assertIn('@property', fahrenheit_getter_text)
        self.assertIn('def fahrenheit(self):', fahrenheit_getter_text)
        self.assertIn('"""Get temperature in Fahrenheit."""', fahrenheit_getter_text)
        self.assertIn('return (self.celsius * 9/5) + 32', fahrenheit_getter_text)

if __name__ == '__main__':
    unittest.main()