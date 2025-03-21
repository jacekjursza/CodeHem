"""
Language handler for PatchCommander.
Provides a unified interface for language-specific operations.
"""
import re
import os
from typing import Optional
from codehem.core.ast_handler import ASTHandler
from codehem.core.formatting import get_formatter
from codehem.core.languages import get_language_for_file, FILE_EXTENSIONS
from codehem.core.manipulator.factory import get_code_manipulator
from codehem.core.models import CodeElementsResult, CodeElement, CodeElementType
from codehem.core.services.extraction_service import ExtractionService
from codehem.core.strategies import get_strategy
from codehem.core.finder.factory import get_code_finder
from codehem.core.utils.logs import logger

class CodeHem:
    """
    Central handler for language-specific operations.
    Provides access to appropriate finder and manipulator for a given language.
    """

    def __init__(self, language_code: str):
        """
        Initialize a language handler for a specific language.

        Args:
        language_code: Code of the language (e.g., 'python', 'javascript')
        """
        self.language_code = language_code
        # JavaScript uses TypeScript finder but keeps its own language code
        finder_language = language_code
        if language_code.lower() == 'javascript':
            finder_language = 'typescript'
            self.language_code = 'typescript'
        self.finder = get_code_finder(finder_language)
        self.manipulator = get_code_manipulator(finder_language)
        self.ast_handler = ASTHandler(finder_language)
        self.formatter = get_formatter(finder_language)
        self.strategy = get_strategy(finder_language)

    @classmethod
    def from_file_path(cls, file_path: str) -> 'CodeHem':
        """
        Create a language handler based on file path.

        Args:
            file_path: Path to the file

        Returns:
            LanguageHandler for the detected language
        """
        language_code = get_language_for_file(file_path)
        return cls(language_code)

    @classmethod
    def from_file_extension(cls, file_ext: str) -> 'CodeHem':
        """
        Create a language handler based on file extension.

        Args:
            file_ext: File extension (with or without leading dot)

        Returns:
            LanguageHandler for the detected language

        Raises:
            ValueError: If the extension is not supported
        """
        file_ext = file_ext.lower()
        if not file_ext.startswith('.'):
            file_ext = '.' + file_ext
        for (ext, lang) in FILE_EXTENSIONS.items():
            if ext == file_ext:
                return cls(lang)
        raise ValueError(f'Unsupported file extension: {file_ext}')

    @staticmethod
    def load_file(file_path: str) -> str:
        """
        Load content from a file.

        Args:
            file_path: Path to the file

        Returns:
            Content of the file as string

        Raises:
            FileNotFoundError: If the file does not exist
            IOError: If the file cannot be read
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with a different encoding if UTF-8 fails
            with open(file_path, 'r') as f:
                return f.read()

    @classmethod
    def from_raw_code(cls, code_or_path: str, check_for_file: bool = True) -> 'CodeHem':
        """
        Create a CodeHem instance from raw code string or file path with language auto-detection.

        Args:
            code_or_path: Raw code string or path to a file
            check_for_file: If True, try to load file if code_or_path exists as a file

        Returns:
            CodeHem instance with appropriate language settings
        """
        code = code_or_path

        # Check if input is a file path
        if check_for_file and os.path.isfile(code_or_path):
            try:
                code = cls.load_file(code_or_path)
            except Exception as e:
                logger.warning(f"Failed to load file {code_or_path}: {str(e)}")

        # Language detection
        finders = {'python': get_code_finder('python'), 'typescript': get_code_finder('typescript')}
        matching_languages = []
        language_confidences = {}
        for (lang, finder) in finders.items():
            try:
                if finder.can_handle(code):
                    matching_languages.append(lang)
                    if hasattr(finder, 'get_confidence_score'):
                        language_confidences[lang] = finder.get_confidence_score(code)
            except Exception as e:
                logger.warning(f'Error in language detector for {lang}: {str(e)}')
        if len(matching_languages) == 1:
            return cls(matching_languages[0])
        if len(matching_languages) > 1:
            logger.warning(f'Multiple language handlers claim they can handle this code: {matching_languages}.')
            if language_confidences:
                max_score = max(language_confidences.values())
                best_languages = [lang for (lang, score) in language_confidences.items() if score == max_score]
                if len(best_languages) > 1:
                    logger.warning(f'Multiple languages have the same confidence score ({max_score}): {best_languages}. Using the first one.')
                return cls(best_languages[0])
            logger.warning("Couldn't determine best language based on confidence. Using first match.")
            return cls(matching_languages[0])
        logger.warning('No language handler matched the code. Defaulting to Python.')
        return cls('python')

    @staticmethod
    def analyze_file(file_path: str) -> None:
        """
        Analyze a file and print statistics in a rich JSON format.

        Args:
        file_path: Path to the file
        """
        try:
            # Import rich library
            from rich.console import Console
            from rich.panel import Panel

            console = Console()

            # Load the file content
            content = CodeHem.load_file(file_path)

            # Create CodeHem instance from the content, skip file path check
            hem = CodeHem.from_raw_code(content, check_for_file=False)

            # Extract code elements
            code_elements = hem.extract(content)

            # Build the analysis data structure
            analysis = {
                "file": os.path.basename(file_path),
                "path": file_path,
                "language": hem.language_code,
                "content_type": hem.get_content_type(content),
                "statistics": {}
            }

            if hasattr(code_elements, 'elements'):
                # Total elements
                analysis["statistics"]["total_elements"] = len(code_elements.elements)

                # Count by type
                type_counts = {}
                for element in code_elements.elements:
                    if element.type not in type_counts:
                        type_counts[element.type] = 0
                    type_counts[element.type] += 1

                analysis["statistics"]["elements_by_type"] = type_counts

                # Classes details
                classes = [e for e in code_elements.elements if e.is_class]
                if classes:
                    analysis["classes"] = []
                    for cls in classes:
                        methods = [c for c in cls.children if c.is_method]
                        properties = [c for c in cls.children if c.is_property]
                        meta_elements = [c for c in cls.children if c.is_meta_element]

                        class_data = {
                            "name": cls.name,
                            "methods_count": len(methods),
                            "properties_count": len(properties),
                            "meta_elements_count": len(meta_elements)
                        }

                        # Add method names if there are any
                        if methods:
                            class_data["methods"] = [{"name": m.name, "type": m.type} for m in methods]

                        # Add property names if there are any
                        if properties:
                            class_data["properties"] = [{"name": p.name, "type": p.value_type} for p in properties]

                        analysis["classes"].append(class_data)

                # Standalone functions
                funcs = [e for e in code_elements.elements if e.is_function and not getattr(e, 'parent_name', None)]
                if funcs:
                    analysis["functions"] = []
                    for func in funcs:
                        func_data = {
                            "name": func.name,
                            "parameters_count": len([p for p in func.children if p.is_parameter])
                        }

                        # Add return type if available
                        if func.return_value:
                            func_data["return_type"] = func.return_value.value_type

                        analysis["functions"].append(func_data)

                # Handle imports
                imports = [e for e in code_elements.elements if e.type == CodeElementType.IMPORT]
                if imports and imports[0].additional_data and "import_statements" in imports[0].additional_data:
                    import_statements = imports[0].additional_data["import_statements"]
                    if isinstance(import_statements, list):
                        analysis["imports"] = [s.strip() for s in import_statements if s.strip()]

            # Print a header
            console.print(Panel(f"[bold blue]Code Analysis for[/bold blue] [bold green]{os.path.basename(file_path)}[/bold green]", expand=False))

            # Print the JSON analysis
            console.print_json(data=analysis)

        except Exception as e:
            logger.error(f"[bold red]Error analyzing file:[/bold red] {str(e)}")
            import traceback
            logger.error(f"[dim red]{traceback.format_exc()}[/dim red]")

    def get_content_type(self, content: str) -> str:
        """
        Determine the type of content by delegating to the language-specific strategy.

        Args:
            content: The code content to analyze

        Returns:
            A string representation of the content type from CodeElementType
        """
        if self.strategy:
            return self.strategy.get_content_type(content)

        # Fallback to basic detection if no strategy is available
        if not content or not content.strip():
            return CodeElementType.MODULE.value

        content = content.strip()
        first_line = content.splitlines()[0] if content.splitlines() else ""

        # Generic detection logic as fallback
        if re.search(r'^\s*(class|interface)\s+\w+', first_line, re.IGNORECASE):
            if 'interface' in first_line.lower():
                return CodeElementType.INTERFACE.value
            return CodeElementType.CLASS.value

        if re.search(r'^\s*(def|function|async|public|private|protected|static)\s+\w+\s*\(', first_line, re.IGNORECASE):
            return CodeElementType.FUNCTION.value

        return CodeElementType.MODULE.value

    def extract(self, code: str) -> 'CodeElementsResult':
        """
        Extract code elements from source code and return them as Pydantic models.

        Args:
        code: Source code as string

        Returns:
        CodeElementsResult containing all found code elements
        """
        service = ExtractionService(self.finder, self.strategy)
        return service.extract_code_elements(code)

    @staticmethod
    def filter(elements: CodeElementsResult, xpath: str='') -> Optional[CodeElement]:
        """
        Filter code elements based on xpath expression.

        Args:
        elements: CodeElementsResult containing code elements
        xpath: XPath-like expression for filtering (e.g., "ClassName.method_name", "function_name")

        Returns:
        Matching CodeElement or None if not found
        """
        if not xpath or not elements or (not hasattr(elements, 'elements')):
            return None
        if xpath.lower() == 'imports':
            for element in elements.elements:
                if element.type == CodeElementType.IMPORT:
                    return element
        if '.' in xpath:
            parts = xpath.split('.', 1)
            if len(parts) == 2:
                (class_name, member_name) = parts
                for element in elements.elements:
                    if element.type == CodeElementType.CLASS and element.name == class_name:
                        for child in element.children:
                            if hasattr(child, 'name') and child.name == member_name:
                                return child
            return None
        for element in elements.elements:
            if hasattr(element, 'name') and element.name == xpath:
                if element.parent_name is None or element.parent_name == '':
                    return element
        return None