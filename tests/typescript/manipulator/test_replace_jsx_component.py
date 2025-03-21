import pytest
from codehem.core import get_code_manipulator

@pytest.fixture
def typescript_manipulator():
    return get_code_manipulator('typescript')

def test_replace_functional_component(typescript_manipulator):
    original_code = '''
const Button = (props) => {
  return <button>{props.label}</button>;
};
'''
    new_component = '''
const Button = (props) => {
  return <button className="primary">{props.label}</button>;
};
'''
    expected = '''
const Button = (props) => {
  return <button className="primary">{props.label}</button>;
};
'''
    result = typescript_manipulator.replace_jsx_component(original_code, 'Button', new_component)
    assert result.strip() == expected.strip()

def test_replace_class_component(typescript_manipulator):
    original_code = '''
class Counter extends React.Component {
  render() {
    return <div>{this.props.count}</div>;
  }
}
'''
    new_component = '''
class Counter extends React.Component {
  increment = () => {
    this.setState(prev => ({ count: prev.count + 1 }));
  }
  
  render() {
    return (
      <div>
        {this.props.count}
        <button onClick={this.increment}>+</button>
      </div>
    );
  }
}
'''
    expected = '''
class Counter extends React.Component {
  increment = () => {
    this.setState(prev => ({ count: prev.count + 1 }));
  }
  
  render() {
    return (
      <div>
        {this.props.count}
        <button onClick={this.increment}>+</button>
      </div>
    );
  }
}
'''
    result = typescript_manipulator.replace_jsx_component(original_code, 'Counter', new_component)
    assert result.strip() == expected.strip()

def test_replace_jsx_component_missing(typescript_manipulator):
    original_code = '''
const ExistingComponent = () => <div>Exists</div>;
'''
    new_component = '''
const NonExistentComponent = () => <div>New</div>;
'''
    result = typescript_manipulator.replace_jsx_component(original_code, 'NonExistentComponent', new_component)
    assert result.strip() == original_code.strip()