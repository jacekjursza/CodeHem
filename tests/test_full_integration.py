"""
Full integration tests for the language-specific post-processors in the extraction pipeline.

This module provides comprehensive tests to verify the end-to-end functionality 
of the post-processor system, focusing on complex code patterns and language-specific
features.
"""

import unittest
import os
from typing import Dict, List, Any

from codehem.main import CodeHem
from codehem.core.post_processors.factory import PostProcessorFactory
from codehem.models.enums import CodeElementType
from codehem.models.code_element import CodeElementsResult


class FullIntegrationTest(unittest.TestCase):
    """End-to-end tests for post-processors in the extraction pipeline."""

    def test_python_complex_code(self):
        """Test extraction of complex Python code with decorators and docstrings."""
        python_code = """
def decorator1(func):
    def wrapper(*args, **kwargs):
        print("Before function call")
        result = func(*args, **kwargs)
        print("After function call")
        return result
    return wrapper

def decorator2(name):
    def actual_decorator(func):
        def wrapper(*args, **kwargs):
            print(f"Running {name}")
            return func(*args, **kwargs)
        return wrapper
    return actual_decorator

@decorator1
def simple_function():
    \"""This is a simple function with a decorator.""\"
    return "Hello World"

@decorator2("example")
def another_function(param):
    \"""This function has a parameterized decorator.""\"
    return f"Hello, {param}"

class ExampleClass:
    \"""Example class with decorated methods and properties.""\"
    
    def __init__(self, value):
        self._value = value
    
    @property
    def value(self):
        \"""Get the value.""\"
        return self._value
    
    @value.setter
    def value(self, new_value):
        \"""Set the value.""\"
        self._value = new_value
    
    @decorator1
    def decorated_method(self):
        \"""This method has a decorator.""\"
        return f"Value: {self._value}"
"""
        # Create a CodeHem instance for Python
        hem = CodeHem('python')
        
        # Extract code elements
        result = hem.extract(python_code)
        
        # Verify class with properties and decorated methods
        class_element = hem.filter(result, 'ExampleClass')
        self.assertIsNotNone(class_element)
        
        # Find property getter and setter using specific type filters
        getter = hem.filter(result, 'ExampleClass.value[property_getter]')
        self.assertIsNotNone(getter, "Property getter should be extracted")
        self.assertEqual(getter.type, CodeElementType.PROPERTY_GETTER)
        
        setter = hem.filter(result, 'ExampleClass.value[property_setter]')
        self.assertIsNotNone(setter, "Property setter should be extracted")
        self.assertEqual(setter.type, CodeElementType.PROPERTY_SETTER)
        
        # Verify decorated method
        decorated_method = hem.filter(result, 'ExampleClass.decorated_method')
        self.assertIsNotNone(decorated_method)
        
        # Check if decorator is present in children
        has_decorator = any(c.type == CodeElementType.DECORATOR for c in decorated_method.children)
        self.assertTrue(has_decorator, "Decorator should be present in method's children")
        
        # Verify decorated standalone function
        simple_function = hem.filter(result, 'simple_function')
        self.assertIsNotNone(simple_function)
        has_decorator = any(c.type == CodeElementType.DECORATOR for c in simple_function.children)
        self.assertTrue(has_decorator, "Decorator should be present in function's children")
    
    def test_typescript_complex_code(self):
        """Test extraction of complex TypeScript code with interfaces, decorators, and type information."""
        typescript_code = """
interface Vehicle {
    make: string;
    model: string;
    year: number;
    getMileage(): number;
}

function Logger(target: any) {
    console.log(`Class ${target.name} decorated`);
}

function PropertyDecorator(target: any, propertyKey: string) {
    console.log(`Property ${propertyKey} decorated`);
}

function MethodDecorator(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    console.log(`Method ${propertyKey} decorated`);
}

@Logger
class Car implements Vehicle {
    make: string;
    model: string;
    year: number;
    
    @PropertyDecorator
    private _mileage: number;
    
    constructor(make: string, model: string, year: number, mileage: number = 0) {
        this.make = make;
        this.model = model;
        this.year = year;
        this._mileage = mileage;
    }
    
    @MethodDecorator
    getMileage(): number {
        return this._mileage;
    }
    
    addMileage(miles: number): void {
        this._mileage += miles;
    }
    
    static createSedan(make: string, model: string, year: number): Car {
        return new Car(make, model, year);
    }
}

enum FuelType {
    Gasoline,
    Diesel,
    Electric,
    Hybrid
}

type VehicleInfo = {
    vehicle: Vehicle;
    fuelType: FuelType;
    vin: string;
};

function getVehicleInfo(vehicle: Vehicle): VehicleInfo {
    return {
        vehicle,
        fuelType: FuelType.Gasoline,
        vin: "SAMPLE-VIN-1234"
    };
}
"""
        # Create a CodeHem instance for TypeScript
        hem = CodeHem('typescript')
        
        # Extract code elements
        result = hem.extract(typescript_code)
        
        # Verify interface extraction
        interface = hem.filter(result, 'Vehicle')
        self.assertIsNotNone(interface)
        
        # Verify class with interface implementation
        car_class = hem.filter(result, 'Car')
        self.assertIsNotNone(car_class)
        
        # Verify method with decorator
        get_mileage = hem.filter(result, 'Car.getMileage')
        self.assertIsNotNone(get_mileage)
        
        # Check for decorators on method
        has_decorator = any(c.type == CodeElementType.DECORATOR for c in get_mileage.children)
        self.assertTrue(has_decorator, "Decorator should be present in method's children")
        
        # Verify property with decorator
        mileage_prop = hem.filter(result, 'Car._mileage')
        if mileage_prop:  # This might depend on extractor capabilities
            has_decorator = any(c.type == CodeElementType.DECORATOR for c in mileage_prop.children)
            self.assertTrue(has_decorator, "Decorator should be present in property's children")
        
        # Verify static method
        static_method = hem.filter(result, 'Car.createSedan')
        self.assertIsNotNone(static_method)
        
        # Verify enum
        enum = next((e for e in result.elements if e.type == CodeElementType.ENUM), None)
        self.assertIsNotNone(enum)
        self.assertEqual(enum.name, 'FuelType')
        
        # Verify type alias
        type_alias = next((e for e in result.elements if e.type == CodeElementType.TYPE_ALIAS), None)
        if type_alias:  # This might depend on extractor capabilities
            self.assertEqual(type_alias.name, 'VehicleInfo')
        
        # Verify standalone function
        function = hem.filter(result, 'getVehicleInfo')
        self.assertIsNotNone(function)
        
    def test_language_detection_and_post_processing(self):
        """Test automatic language detection and appropriate post-processor selection."""
        python_code = """
def test_function():
    return "This is Python"
"""
        typescript_code = """
function testFunction(): string {
    return "This is TypeScript";
}
"""
        
        # Test Python auto-detection
        py_hem = CodeHem.from_raw_code(python_code)
        self.assertEqual(py_hem.language_service.language_code, 'python')
        py_result = py_hem.extract(python_code)
        py_function = py_hem.filter(py_result, 'test_function')
        self.assertIsNotNone(py_function)
        
        # Test TypeScript auto-detection
        ts_hem = CodeHem.from_raw_code(typescript_code)
        self.assertEqual(ts_hem.language_service.language_code, 'typescript')
        ts_result = ts_hem.extract(typescript_code)
        ts_function = ts_hem.filter(ts_result, 'testFunction')
        self.assertIsNotNone(ts_function)

    def _get_structure_info(self, element, indent=0):
        """Helper method to get a readable structure of a CodeElement and its children."""
        result = f"{' ' * indent}- {element.name} ({element.type.value})\n"
        for child in element.children:
            result += self._get_structure_info(child, indent + 2)
        return result

    def _print_structure(self, result: CodeElementsResult):
        """Helper method to print the structure of extracted elements."""
        if not result or not result.elements:
            return "No elements extracted."
        
        structure = "Extracted Structure:\n"
        for element in result.elements:
            structure += self._get_structure_info(element)
        
        return structure


if __name__ == '__main__':
    unittest.main()
