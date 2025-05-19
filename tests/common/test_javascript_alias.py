import unittest
from codehem import CodeHem
from codehem.languages import get_language_service_for_code, get_language_service
from codehem.languages.lang_typescript.service import TypeScriptLanguageService


class JavaScriptAliasTests(unittest.TestCase):
    def test_service_alias(self):
        js_service = get_language_service("javascript")
        ts_service = get_language_service("typescript")
        self.assertIsNotNone(js_service)
        self.assertIsNotNone(ts_service)
        self.assertIsInstance(js_service, TypeScriptLanguageService)

    def test_javascript_detection(self):
        code = "function greet() { console.log('hi'); }"
        service = get_language_service_for_code(code)
        self.assertIsNotNone(service)
        self.assertIn(service.language_code, ("javascript", "typescript"))
        hem = CodeHem("javascript")
        self.assertEqual(hem.language_service.language_code, "javascript")

