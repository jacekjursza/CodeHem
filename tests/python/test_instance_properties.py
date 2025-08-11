import pytest

from codehem import CodeHem, CodeElementType


@pytest.fixture
def codehem_py():
    return CodeHem('python')


def test_extract_instance_attributes_simple(codehem_py):
    code = """
class A:
    def __init__(self):
        self.x = 1
        self.y: int = 0

    def other(self):
        pass
"""
    res = codehem_py.extract(code)

    # Find class A
    cls = codehem_py.filter(res, 'A')
    assert cls is not None and cls.type == CodeElementType.CLASS

    # Collect properties under class A
    props = [c for c in cls.children if c.type == CodeElementType.PROPERTY]
    names = {p.name for p in props}
    assert {'x', 'y'} <= names


def test_instance_property_not_conflicting_with_method_names(codehem_py):
    code = """
class B:
    @property
    def value(self):
        return 1

    def __init__(self):
        self.value = 2  # should be skipped in favor of @property
"""
    res = codehem_py.extract(code)
    cls = codehem_py.filter(res, 'B')
    assert cls is not None

    # Expect a PROPERTY_GETTER child and no plain PROPERTY named 'value'
    getters = [c for c in cls.children if c.type == CodeElementType.PROPERTY_GETTER and c.name == 'value']
    plain_props = [c for c in cls.children if c.type == CodeElementType.PROPERTY and c.name == 'value']
    assert len(getters) == 1
    assert len(plain_props) == 0

