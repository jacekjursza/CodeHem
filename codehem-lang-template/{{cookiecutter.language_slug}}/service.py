from codehem.core.registry import language_service
from codehem.core.language_service import LanguageService

@language_service
class {{cookiecutter.language_name}}LanguageService(LanguageService):
    LANGUAGE_CODE = "{{cookiecutter.language_slug}}"
