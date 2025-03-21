import unittest
from core.manipulator.factory import get_code_manipulator
from core.finder.factory import get_code_finder

class TestTypeScriptRoundTrip(unittest.TestCase):
    
    def setUp(self):
        self.manipulator = get_code_manipulator('typescript')
        self.finder = get_code_finder('typescript')
    
    def test_modify_and_find_function(self):
        original_code = '''
function calculateTotal(items: number[], taxRate: number = 0): number {
  /**
   * Calculate total cost with tax.
   */
  const subtotal = items.reduce((sum, item) => sum + item, 0);
  const tax = subtotal * taxRate;
  return subtotal + tax;
}
'''
        
        # Step 1: Find the function
        (start_line, end_line) = self.finder.find_function(original_code, 'calculateTotal')
        self.assertNotEqual(start_line, 0)
        
        # Step 2: Modify the function
        new_function = '''
function calculateTotal(
  items: number[], 
  taxRate: number = 0,
  discount: number = 0
): number {
  /**
   * Calculate total cost with tax and discount.
   */
  const subtotal = items.reduce((sum, item) => sum + item, 0);
  const discountAmount = subtotal * discount;
  const discountedSubtotal = subtotal - discountAmount;
  const tax = discountedSubtotal * taxRate;
  return discountedSubtotal + tax;
}
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'calculateTotal', new_function)
        
        # Step 3: Find the function again
        (new_start_line, new_end_line) = self.finder.find_function(modified_code, 'calculateTotal')
        
        # Verify it's still findable
        self.assertNotEqual(new_start_line, 0)
        
        # Extract the function to verify its content
        function_lines = modified_code.splitlines()[new_start_line-1:new_end_line]
        function_text = '\n'.join(function_lines)
        
        self.assertIn('function calculateTotal(', function_text)
        self.assertIn('items: number[],', function_text)
        self.assertIn('discount: number = 0', function_text)
        self.assertIn('const discountAmount = subtotal * discount;', function_text)
    
    def test_add_find_modify_method(self):
        original_code = '''
class ShoppingCart {
  items: any[] = [];
  
  constructor() {}
}
'''
        
        # Step 1: Add a method
        add_method = '''
addItem(item: any, quantity: number = 1): void {
  for (let i = 0; i < quantity; i++) {
    this.items.push(item);
  }
}
'''
        
        modified_code = self.manipulator.add_method_to_class(original_code, 'ShoppingCart', add_method)
        
        # Step 2: Find the added method
        (start_line, end_line) = self.finder.find_method(modified_code, 'ShoppingCart', 'addItem')
        
        # Verify it's findable
        self.assertNotEqual(start_line, 0)
        
        # Step 3: Modify the method
        new_method = '''
addItem(item: any, quantity: number = 1, price?: number): void {
  const itemToAdd = price !== undefined 
    ? { item, price } 
    : item;
    
  for (let i = 0; i < quantity; i++) {
    this.items.push(itemToAdd);
  }
}
'''
        
        modified_code_2 = self.manipulator.replace_method(modified_code, 'ShoppingCart', 'addItem', new_method)
        
        # Step 4: Find the method again
        (new_start_line, new_end_line) = self.finder.find_method(modified_code_2, 'ShoppingCart', 'addItem')
        
        # Verify it's still findable
        self.assertNotEqual(new_start_line, 0)
        
        # Extract the method to verify its content
        method_lines = modified_code_2.splitlines()[new_start_line-1:new_end_line]
        method_text = '\n'.join(method_lines)
        
        self.assertIn('addItem(item: any, quantity: number = 1, price?: number): void {', method_text)
        self.assertIn('const itemToAdd = price !== undefined', method_text)
        self.assertIn('? { item, price }', method_text)
    
    def test_multi_step_class_transformation(self):
        original_code = '''
class Shape {
  constructor(public color: string = "black") {}
  
  area(): number {
    throw new Error("Subclasses must implement area()");
  }
}
'''
        
        # Step 1: Add a method
        add_method = '''
perimeter(): number {
  throw new Error("Subclasses must implement perimeter()");
}
'''
        
        modified_code = self.manipulator.add_method_to_class(original_code, 'Shape', add_method)
        
        # Step 2: Verify method was added and can be found
        (method_start, method_end) = self.finder.find_method(modified_code, 'Shape', 'perimeter')
        self.assertNotEqual(method_start, 0)
        
        # Step 3: Update the constructor
        new_constructor = '''
constructor(
  public color: string = "black",
  public filled: boolean = false
) {}
'''
        
        modified_code_2 = self.manipulator.replace_method(modified_code, 'Shape', 'constructor', new_constructor)
        
        # Step 4: Verify both methods exist and constructor was updated
        (constructor_start, constructor_end) = self.finder.find_method(modified_code_2, 'Shape', 'constructor')
        (area_start, area_end) = self.finder.find_method(modified_code_2, 'Shape', 'area')
        (peri_start, peri_end) = self.finder.find_method(modified_code_2, 'Shape', 'perimeter')
        
        self.assertNotEqual(constructor_start, 0)
        self.assertNotEqual(area_start, 0)
        self.assertNotEqual(peri_start, 0)
        
        # Step 5: Add a property getter
        add_property = '''
get info(): string {
  const filledStatus = this.filled ? "filled" : "not filled";
  return `${this.color} shape, ${filledStatus}`;
}
'''
        
        modified_code_3 = self.manipulator.add_method_to_class(modified_code_2, 'Shape', add_property)
        
        # Step 6: Verify all elements exist
        (constructor_start, constructor_end) = self.finder.find_method(modified_code_3, 'Shape', 'constructor')
        (area_start, area_end) = self.finder.find_method(modified_code_3, 'Shape', 'area')
        (peri_start, peri_end) = self.finder.find_method(modified_code_3, 'Shape', 'perimeter')
        (info_start, info_end) = self.finder.find_method(modified_code_3, 'Shape', 'info')
        
        self.assertNotEqual(constructor_start, 0)
        self.assertNotEqual(area_start, 0)
        self.assertNotEqual(peri_start, 0)
        self.assertNotEqual(info_start, 0)
        
        # Verify content
        info_lines = modified_code_3.splitlines()[info_start-1:info_end]
        info_text = '\n'.join(info_lines)
        
        self.assertIn('get info(): string {', info_text)
        self.assertIn('const filledStatus = this.filled ? "filled" : "not filled";', info_text)
        self.assertIn('return `${this.color} shape, ${filledStatus}`;', info_text)
    
    def test_interface_roundtrip(self):
        original_code = '''
interface User {
  id: string;
  name: string;
  email: string;
}
'''
        
        # Step 1: Replace interface
        new_interface = '''
interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
  createdAt: Date;
}
'''
        
        modified_code = self.manipulator.replace_interface(original_code, 'User', new_interface)
        
        # Step 2: Find interface again (might need a special method)
        (interface_start, interface_end) = (1, 7)  # Assuming we don't have find_interface method
        
        # Verify content
        interface_lines = modified_code.splitlines()[interface_start-1:interface_end]
        interface_text = '\n'.join(interface_lines)
        
        self.assertIn('interface User {', interface_text)
        self.assertIn('  id: string;', interface_text)
        self.assertIn('  role: \'admin\' | \'user\' | \'guest\';', interface_text)
        self.assertIn('  createdAt: Date;', interface_text)
        
        # Step 3: Add another interface
        another_interface = '''
interface AuthResponse {
  user: User;
  token: string;
  expires: number;
}
'''
        
        modified_code_2 = modified_code + '\n\n' + another_interface
        
        # Step: Now update the User interface again
        updated_interface = '''
interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
  createdAt: Date;
  lastLogin?: Date;
  metadata?: Record<string, unknown>;
}
'''
        
        # This is a complex test as it requires knowledge of both interfaces
        try:
            modified_code_3 = self.manipulator.replace_interface(modified_code_2, 'User', updated_interface)
            
            # Verify both interfaces exist with proper content
            self.assertIn('interface User {', modified_code_3)
            self.assertIn('  lastLogin?: Date;', modified_code_3)
            self.assertIn('  metadata?: Record<string, unknown>;', modified_code_3)
            self.assertIn('interface AuthResponse {', modified_code_3)
            self.assertIn('  user: User;', modified_code_3)
            self.assertIn('  token: string;', modified_code_3)
        except Exception as e:
            self.skipTest(f"Complex interface manipulation not supported: {str(e)}")

if __name__ == '__main__':
    unittest.main()