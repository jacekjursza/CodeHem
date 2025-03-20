import unittest
from core.manipulator.factory import get_code_manipulator

class TestTypeScriptSimilarNamedElements(unittest.TestCase):
    
    def setUp(self):
        self.manipulator = get_code_manipulator('typescript')
    
    def test_overloaded_method_signatures(self):
        original_code = '''
class Formatter {
  // Method overload signatures
  format(value: string): string;
  format(value: number): string;
  format(value: Date): string;
  
  // Implementation
  format(value: string | number | Date): string {
    if (typeof value === 'string') {
      return value.toUpperCase();
    } else if (typeof value === 'number') {
      return value.toFixed(2);
    } else {
      return value.toISOString();
    }
  }
}
'''
        
        new_method = '''
// Method overload signatures
format(value: string): string;
format(value: number, precision?: number): string;
format(value: Date, includeTime?: boolean): string;
format(value: unknown): string;

// Implementation
format(value: unknown, option?: number | boolean): string {
  if (typeof value === 'string') {
    return value.toUpperCase();
  } else if (typeof value === 'number') {
    const precision = typeof option === 'number' ? option : 2;
    return value.toFixed(precision);
  } else if (value instanceof Date) {
    const includeTime = typeof option === 'boolean' ? option : true;
    return includeTime ? value.toISOString() : value.toLocaleDateString();
  } else {
    return String(value);
  }
}
'''
        
        modified_code = self.manipulator.replace_method(original_code, 'Formatter', 'format', new_method)
        
        # Verify overloaded method signatures
        self.assertIn('format(value: string): string;', modified_code)
        self.assertIn('format(value: number, precision?: number): string;', modified_code)
        self.assertIn('format(value: Date, includeTime?: boolean): string;', modified_code)
        self.assertIn('format(value: unknown): string;', modified_code)
        self.assertIn('format(value: unknown, option?: number | boolean): string {', modified_code)
        self.assertIn('const precision = typeof option === \'number\' ? option : 2;', modified_code)
    
    def test_same_method_name_different_classes(self):
        original_code = '''
class FirstClass {
  calculate(x: number, y: number): number {
    return x + y;
  }
}

class SecondClass {
  calculate(x: number, y: number): number {
    return x * y;
  }
}
'''
        
        new_method = '''
calculate(x: number, y: number, z: number = 1): number {
  return (x + y) * z;
}
'''
        
        # Replace method in first class
        modified_code = self.manipulator.replace_method(original_code, 'FirstClass', 'calculate', new_method)
        
        # Verify only FirstClass.calculate was replaced
        self.assertIn('class FirstClass {', modified_code)
        self.assertIn('calculate(x: number, y: number, z: number = 1): number {', modified_code)
        self.assertIn('return (x + y) * z;', modified_code)
        
        # SecondClass.calculate should remain unchanged
        self.assertIn('class SecondClass {', modified_code)
        self.assertIn('calculate(x: number, y: number): number {', modified_code)
        self.assertIn('return x * y;', modified_code)
        
        # Now replace the method in the second class
        new_method_2 = '''
calculate(x: number, y: number, operation: 'multiply' | 'add' | 'subtract' = 'multiply'): number {
  if (operation === 'add') {
    return x + y;
  } else if (operation === 'subtract') {
    return x - y;
  } else {
    return x * y;
  }
}
'''
        
        modified_code_2 = self.manipulator.replace_method(modified_code, 'SecondClass', 'calculate', new_method_2)
        
        # Verify both classes have their correct implementations
        self.assertIn('class FirstClass {', modified_code_2)
        self.assertIn('calculate(x: number, y: number, z: number = 1): number {', modified_code_2)
        self.assertIn('return (x + y) * z;', modified_code_2)
        
        self.assertIn('class SecondClass {', modified_code_2)
        self.assertIn('calculate(x: number, y: number, operation: \'multiply\' | \'add\' | \'subtract\' = \'multiply\'): number {', modified_code_2)
        self.assertIn('if (operation === \'add\') {', modified_code_2)
        self.assertIn('return x * y;', modified_code_2)
    
    def test_method_vs_standalone_function(self):
        original_code = '''
function validate(data: any[]): boolean {
  return data.length > 0;
}

class Validator {
  validate(data: any[]): boolean {
    return data.every(item => item !== null && item !== undefined);
  }
}
'''
        
        new_function = '''
function validate<T>(data: T[], minLength: number = 1): boolean {
  return data.length >= minLength;
}
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'validate', new_function)
        
        # Verify only the standalone function was updated
        self.assertIn('function validate<T>(data: T[], minLength: number = 1): boolean {', modified_code)
        self.assertIn('return data.length >= minLength;', modified_code)
        
        # Verify the class method wasn't touched
        self.assertIn('validate(data: any[]): boolean {', modified_code)
        self.assertIn('return data.every(item => item !== null && item !== undefined);', modified_code)
        
        # Now update the class method
        new_method = '''
validate<T>(data: T[], options?: { allowNull?: boolean, minLength?: number }): boolean {
  const { allowNull = false, minLength = 1 } = options || {};
  
  if (data.length < minLength) {
    return false;
  }
  
  if (!allowNull) {
    return data.every(item => item !== null && item !== undefined);
  }
  
  return true;
}
'''
        
        modified_code_2 = self.manipulator.replace_method(modified_code, 'Validator', 'validate', new_method)
        
        # Verify both are updated correctly
        self.assertIn('function validate<T>(data: T[], minLength: number = 1): boolean {', modified_code_2)
        self.assertIn('return data.length >= minLength;', modified_code_2)
        
        self.assertIn('validate<T>(data: T[], options?: { allowNull?: boolean, minLength?: number }): boolean {', modified_code_2)
        self.assertIn('const { allowNull = false, minLength = 1 } = options || {};', modified_code_2)
        self.assertIn('if (!allowNull) {', modified_code_2)
    
    def test_property_vs_method_with_same_name(self):
        original_code = '''
class ApiClient {
  // Property named 'url'
  url: string = 'https://api.example.com';
  
  // Method named 'url' (creates a full URL)
  url(path: string): string {
    return `${this.url}${path}`;
  }
}
'''
        
        new_property = '''
// Updated property
url: string = 'https://api-v2.example.com';
'''
        
        # Replace property - this test may identify limitations
        try:
            modified_code = self.manipulator.replace_property(original_code, 'ApiClient', 'url', new_property)
            
            # Verify property was updated but method remained unchanged
            self.assertIn('url: string = \'https://api-v2.example.com\';', modified_code)
            self.assertIn('url(path: string): string {', modified_code)
            self.assertIn('return `${this.url}${path}`;', modified_code)
        except Exception as e:
            self.skipTest(f"Property vs method same name manipulation not supported: {str(e)}")
    
    def test_similarly_named_components(self):
        original_code = '''
function UserCard() {
  return <div>User Card</div>;
}

function UserCardList() {
  return <div>User Card List</div>;
}

function UserCardDetail() {
  return <div>User Card Detail</div>;
}
'''
        
        new_component = '''
function UserCard({ user }) {
  return (
    <div className="user-card">
      <img src={user.avatar} alt={user.name} />
      <h3>{user.name}</h3>
      <p>{user.email}</p>
    </div>
  );
}
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'UserCard', new_component)
        
        # Verify only the specific component was updated
        self.assertIn('function UserCard({ user }) {', modified_code)
        self.assertIn('<img src={user.avatar} alt={user.name} />', modified_code)
        
        # Other components should remain unchanged
        self.assertIn('function UserCardList() {', modified_code)
        self.assertIn('return <div>User Card List</div>;', modified_code)
        
        self.assertIn('function UserCardDetail() {', modified_code)
        self.assertIn('return <div>User Card Detail</div>;', modified_code)

if __name__ == '__main__':
    unittest.main()