from codehem.models.enums import CodeElementType
from codehem.manipulator.base import BaseManipulator
from codehem.manipulator.registry import manipulator

@manipulator
class FunctionManipulator(BaseManipulator):
    @property
    def element_type(self) -> CodeElementType:
        return CodeElementType.FUNCTION