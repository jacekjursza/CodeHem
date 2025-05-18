import pytest
from codehem import CodeHem
from codehem.core.error_handling import WriteConflictError


SAMPLE_CODE = """\
def foo():
    return 1
"""


def test_apply_patch_replace():
    hem = CodeHem('python')
    xpath = 'foo[function]'
    original_hash = hem.get_element_hash(SAMPLE_CODE, xpath)
    assert original_hash
    new_fragment = "def foo():\n    return 2"
    result = hem.apply_patch(SAMPLE_CODE, xpath, new_fragment, original_hash=original_hash)
    assert result['status'] == 'ok'
    assert result['lines_added'] == 1
    assert result['lines_removed'] == 1
    assert 'return 2' in result['code']


def test_apply_patch_append():
    hem = CodeHem('python')
    xpath = 'foo[function]'
    original_hash = hem.get_element_hash(SAMPLE_CODE, xpath)
    result = hem.apply_patch(SAMPLE_CODE, xpath, 'print("hi")', mode='append', original_hash=original_hash)
    assert result['lines_added'] == 1
    assert result['lines_removed'] == 0
    assert 'print("hi")' in result['code']


def test_apply_patch_conflict():
    hem = CodeHem('python')
    xpath = 'foo[function]'
    wrong_hash = '0' * 64
    with pytest.raises(WriteConflictError):
        hem.apply_patch(SAMPLE_CODE, xpath, 'print()', original_hash=wrong_hash)
