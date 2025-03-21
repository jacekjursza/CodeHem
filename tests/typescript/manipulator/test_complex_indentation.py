import unittest

import rich

from core.manipulator.factory import get_code_manipulator

class TestTypeScriptIndentationPreservation(unittest.TestCase):
    
    def setUp(self):
        self.manipulator = get_code_manipulator('typescript')
        
    def test_nested_function_indentation(self):
        original_code = '''
function outerFunction(param1: number): number {
  /**
   * Outer function docstring.
   */
  function innerFunction(innerParam: number): string {
    // Inner function comment
    if (innerParam > 0) {
      if (innerParam > 10) {
        return "Large value";
      } else {
        return "Normal value";
      }
    } else {
      return "Negative value";
    }
  }
  
  const result = innerFunction(param1);
  return result.length;
}
'''
        
        new_function = '''
function outerFunction(param1: number, param2: string = ""): number {
  /**
   * Updated outer function docstring.
   */
  function innerFunction(innerParam: number): string {
    // Inner function comment
    if (innerParam > 0) {
      if (innerParam > 10) {
        return `Large value: ${innerParam}`;
      } else {
        for (let i = 0; i < innerParam; i++) {
          if (i % 2 === 0) {
            console.log(`Even: ${i}`);
          } else {
            console.log(`Odd: ${i}`);
          }
        }
        return "Normal value";
      }
    } else {
      return "Negative value";
    }
  }
  
  const result = innerFunction(param1);
  if (param2) {
    return result.length + param2.length;
  }
  return result.length;
}
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'outerFunction', new_function)
        
        # Verify indentation is preserved
        self.assertIn('  function innerFunction(innerParam: number): string {', modified_code)
        self.assertIn('    // Inner function comment', modified_code)
        self.assertIn('      if (innerParam > 10) {', modified_code)
        self.assertIn('        return `Large value: ${innerParam}`;', modified_code)
        self.assertIn('        for (let i = 0; i < innerParam; i++) {', modified_code)
        self.assertIn('          if (i % 2 === 0) {', modified_code)
        self.assertIn('            console.log(`Even: ${i}`);', modified_code)
    
    def test_complex_class_indentation(self):
        original_code = '''
class DataProcessor {
  private data: any[];
  
  constructor(initialData: any[] = []) {
    this.data = initialData;
  }
  
  process(): any[] {
    return this.data.map(item => {
      if (typeof item === 'string') {
        return item.toUpperCase();
      } else if (typeof item === 'number') {
        return item * 2;
      } else {
        return item;
      }
    });
  }
}
'''
        
        new_method = '''
process<T extends any[]>(options?: {
  filter?: boolean,
  transform?: (item: any) => any
}): T {
  let processed = this.data;
  
  if (options?.filter) {
    processed = processed.filter(item => item !== null && item !== undefined);
  }
  
  return processed.map(item => {
    if (options?.transform) {
      return options.transform(item);
    }
    
    if (typeof item === 'string') {
      return item.toUpperCase();
    } else if (typeof item === 'number') {
      return item * 2;
    } else if (Array.isArray(item)) {
      return [
        ...item,
        'processed'
      ];
    } else {
      return item;
    }
  }) as unknown as T;
}
'''
        
        modified_code = self.manipulator.replace_method(original_code, 'DataProcessor', 'process', new_method)
        
        # Verify complex indentation is preserved
        self.assertIn('  process<T extends any[]>(options?: {', modified_code)
        self.assertIn('    filter?: boolean,', modified_code)
        self.assertIn('    transform?: (item: any) => any', modified_code)
        self.assertIn('  }): T {', modified_code)
        self.assertIn('    let processed = this.data;', modified_code)
        self.assertIn('    if (options?.filter) {', modified_code)
        self.assertIn('      processed = processed.filter(item => item !== null && item !== undefined);', modified_code)
        self.assertIn('      return [', modified_code)
        self.assertIn('        ...item,', modified_code)
        self.assertIn('        \'processed\'', modified_code)
        self.assertIn('      ];', modified_code)
    
    def test_jsx_indentation(self):
        original_code = '''
function Component() {
  return (
    <div className="container">
      <h1>Title</h1>
      <p>Content</p>
    </div>
  );
}
'''
        
        new_component = '''
function Component({ title = "Default Title" }) {
  const [count, setCount] = React.useState(0);
  
  return (
    <div className="container">
      <h1>{title}</h1>
      <p>Content</p>
      <div className="counter">
        <button onClick={() => setCount(count - 1)}>
          -
        </button>
        <span>{count}</span>
        <button onClick={() => setCount(count + 1)}>
          +
        </button>
      </div>
    </div>
  );
}
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'Component', new_component)
        
        # Verify JSX indentation is preserved
        self.assertIn('function Component({ title = "Default Title" }) {', modified_code)
        self.assertIn('  const [count, setCount] = React.useState(0);', modified_code)
        self.assertIn('  return (', modified_code)
        self.assertIn('    <div className="container">', modified_code)
        self.assertIn('      <h1>{title}</h1>', modified_code)
        self.assertIn('      <div className="counter">', modified_code)
        self.assertIn('        <button onClick={() => setCount(count - 1)>', modified_code)
        self.assertIn('          -', modified_code)
        self.assertIn('        </button>', modified_code)
    
    def test_interface_indentation(self):
        original_code = '''
interface User {
  id: string;
  name: string;
  email: string;
}
'''
        
        new_interface = '''
interface User {
  id: string;
  name: string;
  email: string;
  preferences: {
    theme: 'light' | 'dark';
    notifications: {
      email: boolean;
      push: boolean;
      frequency: 'daily' | 'weekly' | 'monthly';
    };
    language: string;
  };
  roles: string[];
}
'''
        
        modified_code = self.manipulator.replace_interface(original_code, 'User', new_interface)
        
        # Verify interface indentation is preserved
        self.assertIn('interface User {', modified_code)
        self.assertIn('  id: string;', modified_code)
        self.assertIn('  preferences: {', modified_code)
        self.assertIn('    theme: \'light\' | \'dark\';', modified_code)
        self.assertIn('    notifications: {', modified_code)
        self.assertIn('      email: boolean;', modified_code)
        self.assertIn('      frequency: \'daily\' | \'weekly\' | \'monthly\';', modified_code)
        self.assertIn('    };', modified_code)
        self.assertIn('  };', modified_code)
        self.assertIn('  roles: string[];', modified_code)
    
    def test_complex_arrow_function_indentation(self):
        original_code = '''
const processItems = (items) => {
  return items.map(item => 
    item.value > 10 
      ? { 
          ...item, 
          processed: true 
        } 
      : item
  );
};
'''
        
        new_function = '''
const processItems = (items, options = {}) => {
  const { 
    threshold = 10,
    processAll = false
  } = options;
  
  return items.map(item => {
    // This is an important check
    if (processAll || item.value > threshold) {
      return { 
        ...item, 
        processed: true,
        timestamp: Date.now(),
        metadata: {
          processor: 'v2',
          automated: true
        }
      };
    }
    
    return item;
  });
};
'''
        
        modified_code = self.manipulator.replace_function(original_code, 'processItems', new_function)
        print('---------------------------------------')
        rich.print(modified_code)
        print('---------------------------------------')
        # Verify arrow function indentation is preserved
        self.assertIn('const processItems = (items, options = {}) => {', modified_code)
        self.assertIn('  const {', modified_code)
        self.assertIn('    threshold = 10,', modified_code)
        self.assertIn('    processAll = false', modified_code)
        self.assertIn('  } = options;', modified_code)
        self.assertIn('  return items.map(item => {', modified_code)
        self.assertIn('    // This is an important check', modified_code)
        self.assertIn('    if (processAll || item.value > threshold) {', modified_code)
        self.assertIn('      return {', modified_code)
        self.assertIn('        ...item,', modified_code)
        self.assertIn('        metadata: {', modified_code)
        self.assertIn('          processor: \'v2\',', modified_code)
        self.assertIn('        }', modified_code)
        self.assertIn('      };', modified_code)
        self.assertIn('    }', modified_code)

if __name__ == '__main__':
    unittest.main()