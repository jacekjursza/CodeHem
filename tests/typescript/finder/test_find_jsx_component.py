import pytest
from finder.factory import get_code_finder

@pytest.fixture
def typescript_finder():
    return get_code_finder('typescript')

def test_find_functional_component(typescript_finder):
    code = '''
import React from 'react';

const ButtonComponent = (props) => {
  return <button>{props.label}</button>;
};
'''
    (start_line, end_line) = typescript_finder.find_jsx_component(code, 'ButtonComponent')
    assert start_line == 3, f'Expected component start at line 3, got {start_line}'
    assert end_line == 5, f'Expected component end at line 5, got {end_line}'

def test_find_functional_component_with_type(typescript_finder):
    code = '''
import React from 'react';

type ButtonProps = {
  label: string;
  onClick: () => void;
};

const TypedButton: React.FC<ButtonProps> = (props) => {
  return <button onClick={props.onClick}>{props.label}</button>;
};
'''
    (start_line, end_line) = typescript_finder.find_jsx_component(code, 'TypedButton')
    assert start_line == 8, f'Expected component start at line 8, got {start_line}'
    assert end_line == 10, f'Expected component end at line 10, got {end_line}'

def test_find_class_component(typescript_finder):
    code = '''
import React from 'react';

class ClassComponent extends React.Component {
  render() {
    return <div>Class Component</div>;
  }
}
'''
    (start_line, end_line) = typescript_finder.find_jsx_component(code, 'ClassComponent')
    assert start_line == 3, f'Expected component start at line 3, got {start_line}'
    assert end_line == 7, f'Expected component end at line 7, got {end_line}'

def test_find_jsx_component_missing(typescript_finder):
    code = '''
const ExistingComponent = () => <div>Exists</div>;
'''
    (start_line, end_line) = typescript_finder.find_jsx_component(code, 'NonExistentComponent')
    assert start_line == 0 and end_line == 0, 'Expected no lines for a non-existent component'