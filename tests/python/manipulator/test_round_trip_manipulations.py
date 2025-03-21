import unittest

import rich

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
        print("---------------------------------------------------")
        rich.print(modified_code_3)
        print("---------------------------------------------------")
        info_text = modified_code_3.splitlines()
        self.assertIn('    @property', info_text)
        self.assertIn('    def info(self):', info_text)
        self.assertIn('        filled_status = "filled" if self.filled else "not filled"', info_text)


if __name__ == '__main__':
    unittest.main()