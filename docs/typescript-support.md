# TypeScript Support in CodeHem

CodeHem now supports TypeScript code manipulation alongside Python. This document explains how to use TypeScript support in CodeHem.

## Supported TypeScript Elements

CodeHem can extract and manipulate the following TypeScript elements:

- **Classes**: Including methods, properties, and static properties
- **Interfaces**: TypeScript interface definitions
- **Functions**: Both regular and arrow functions
- **Imports/Exports**: TypeScript module imports and exports
- **Type Aliases**: Including generic type aliases
- **Enums**: Both string and numeric enums
- **Namespaces**: TypeScript namespaces

## Using TypeScript Support

TypeScript support is automatically enabled in CodeHem. The library will attempt to detect the language of your code and use the appropriate extractors and manipulators.

### Creating a CodeHem Instance for TypeScript

```python
from codehem import CodeHem

# Explicitly specify TypeScript
codehem = CodeHem('typescript')

# Or auto-detect from code
typescript_code = """
interface User {
  id: number;
  name: string;
}
"""
codehem = CodeHem.from_raw_code(typescript_code)
```

### Extracting TypeScript Elements

```python
# Extract all elements from TypeScript code
result = codehem.extract(typescript_code)

# Find a specific element
interface = codehem.filter(result, 'User')
class_element = codehem.filter(result, 'MyComponent')
method = codehem.filter(result, 'MyComponent.render')
```

### Manipulating TypeScript Code

```python
# Update a TypeScript interface
new_interface = """
interface User {
  id: number;
  name: string;
  email: string; // Added new field
}
"""
modified_code = codehem.upsert_element(typescript_code, 'interface', 'User', new_interface)

# Add a new method to a class
new_method = """
componentDidMount() {
  console.log('Component mounted');
}
"""
modified_code = codehem.upsert_element(typescript_code, 'method', 'componentDidMount', new_method, 'MyComponent')

# Add a type alias
new_type = """
type Result<T> = {
  data: T | null;
  error: string | null;
};
"""
modified_code = codehem.upsert_element(typescript_code, 'type_alias', 'Result', new_type)
```

## TypeScript-Specific Features

### Handling Generics

CodeHem properly handles TypeScript generic types:

```typescript
// Type with generic parameters
type Result<T> = {
  data: T;
  error: string | null;
};

// Generic class
class Container<T> {
  private value: T;
  
  constructor(value: T) {
    this.value = value;
  }
  
  getValue(): T {
    return this.value;
  }
}
```

### Working with JSX/TSX Files

CodeHem also supports TSX files (TypeScript with JSX):

```typescript
// React component in TSX
class MyComponent extends React.Component<Props, State> {
  render() {
    return (
      <div>
        <h1>{this.props.title}</h1>
        <button onClick={this.handleClick}>Click me</button>
      </div>
    );
  }
  
  private handleClick = () => {
    console.log('Button clicked');
  };
}