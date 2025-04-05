from codehem.core.manipulators.template_manipulator import TemplateManipulator
from codehem.core.registry import manipulator


@manipulator
class PythonManipulator(TemplateManipulator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    language_code = 'python'
    element_types = ['method', 'function', 'class', 'import']