"""
Language handler for PatchCommander.
Provides a unified interface for language-specific operations.
"""
import re

from core.ast_handler import ASTHandler
from core.formatting import get_formatter
from core.languages import get_language_for_file, FILE_EXTENSIONS
from core.manipulator.factory import get_code_manipulator
from core.models import (
    CodeElementsResult,
    CodeElement,
    CodeElementType,
    CodeRange,
    MetaElementType,
)
from core.strategies import get_strategy
from core.finder.factory import get_code_finder
from core.utils.logs import logger


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
        self.finder = get_code_finder(language_code)
        self.manipulator = get_code_manipulator(language_code)
        self.ast_handler = ASTHandler(language_code)
        self.formatter = get_formatter(language_code)
        self.strategy = get_strategy(language_code)

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
        raise ValueError(f"Unsupported file extension: {file_ext}")

    @classmethod
    def from_raw_code(cls, code: str) -> 'CodeHem':
        """
        Create a CodeHem instance from raw code string with language auto-detection.

        Args:
        code: Raw code string

        Returns:
        CodeHem instance with appropriate language settings
        """

        finders = {'python': get_code_finder('python'), 'typescript': get_code_finder('typescript')}
        matching_languages = []
        language_confidences = {}
        for (lang, finder) in finders.items():
            try:
                if finder.can_handle(code):
                    matching_languages.append(lang)
                    # Get confidence score from the finder if available
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
                best_languages = [lang for lang, score in language_confidences.items() if score == max_score]

                if len(best_languages) > 1:
                    logger.warning(f"Multiple languages have the same confidence score ({max_score}): {best_languages}. Using the first one.")

                return cls(best_languages[0])

            # If no confidence scores available, use the first matching language
            logger.warning("Couldn't determine best language based on confidence. Using first match.")
            return cls(matching_languages[0])

        logger.warning('No language handler matched the code. Defaulting to Python.')
        return cls('python')

    def content_looks_like_class_definition(self, content: str) -> bool:
        """
        Check if the provided content appears to be a class definition.
        Delegates to the language-specific strategy.

        Args:
            content: The code content to check

        Returns:
            bool: True if content looks like a class definition, False otherwise
        """
        if not content or not content.strip():
            return False
            
        # Use the strategy if available
        if self.strategy:
            lines = content.strip().splitlines()
            # Check the first non-empty line
            for line in lines:
                if line.strip():
                    return self.strategy.is_class_definition(line)

        # Fall back to the finder if strategy not available
        return self.finder.content_looks_like_class_definition(content)

    def extract_code_elements(self, code: str) -> "CodeElementsResult":
        """
        Extract code elements from source code and return them as Pydantic models.

        Args:
            code: Source code as string

        Returns:
            CodeElementsResult containing all found code elements
        """


        result = CodeElementsResult()
        code_bytes = code.encode("utf8")

        # Extract imports
        import_start, import_end = self.finder.find_imports_section(code)
        if import_start > 0 and import_end > 0:
            import_lines = code.splitlines()[import_start - 1 : import_end]
            import_content = "\n".join(import_lines)

            import_element = CodeElement(
                type=CodeElementType.IMPORT,
                name="imports",
                content=import_content,
                range=CodeRange(
                    start_line=import_start, end_line=import_end, node=None
                ),
                additional_data={"import_statements": import_lines},
            )

            result.elements.append(import_element)

        # Extract classes
        classes = self.finder.get_classes_from_code(code)
        for class_name, class_node in classes:
            class_range = self.finder.get_node_range(class_node)
            class_content = self.finder.get_node_content(class_node, code_bytes)

            # Get class decorators
            class_decorators = self.finder.get_class_decorators(code, class_name)

            class_element = CodeElement(
                type=CodeElementType.CLASS,
                name=class_name,
                content=class_content,
                range=CodeRange(
                    start_line=class_range[0], end_line=class_range[1], node=class_node
                ),
                additional_data={"decorators": class_decorators},
            )

            # Create meta-element children for class decorators
            for decorator in class_decorators:
                # Extract decorator name without @ and args
                decorator_name = decorator[1:].split("(")[0].strip()
                meta_element = CodeElement(
                    type=CodeElementType.META_ELEMENT,
                    name=decorator_name,
                    content=decorator,
                    parent_name=class_name,
                    additional_data={
                        "meta_type": MetaElementType.DECORATOR,
                        "target_type": "class",
                        "target_name": class_name,
                    },
                )
                class_element.children.append(meta_element)

            methods = self.finder.get_methods_from_class(code, class_name)
            for method_name, method_node in methods:
                method_range = self.finder.get_node_range(method_node)
                method_content = self.finder.get_node_content(method_node, code_bytes)

                decorators = self.finder.get_decorators(code, method_name, class_name)
                element_type = CodeElementType.METHOD
                if any("@property" in dec for dec in decorators):
                    element_type = CodeElementType.PROPERTY

                method_element = CodeElement(
                    type=element_type,
                    name=method_name,
                    content=method_content,
                    range=CodeRange(
                        start_line=method_range[0],
                        end_line=method_range[1],
                        node=method_node,
                    ),
                    parent_name=class_name,
                    additional_data={"decorators": decorators},
                )

                # Create meta-element children for method decorators
                for decorator in decorators:
                    # Extract decorator name without @ and args
                    decorator_name = decorator[1:].split("(")[0].strip()
                    meta_element = CodeElement(
                        type=CodeElementType.META_ELEMENT,
                        name=decorator_name,
                        content=decorator,
                        parent_name=f"{class_name}.{method_name}",
                        additional_data={
                            "meta_type": MetaElementType.DECORATOR,
                            "target_type": element_type.value,
                            "target_name": method_name,
                            "class_name": class_name,
                        },
                    )
                    method_element.children.append(meta_element)

                class_element.children.append(method_element)

            result.elements.append(class_element)

        # Extract standalone functions
        all_functions = self.finder.get_methods_from_code(code)
        for func_name, func_node in all_functions:
            # Skip methods that belong to a class
            skip = False
            for class_name, _ in classes:
                methods = self.finder.get_methods_from_class(code, class_name)
                if any(method[0] == func_name for method in methods):
                    skip = True
                    break

            if skip:
                continue

            func_range = self.finder.get_node_range(func_node)
            func_content = self.finder.get_node_content(func_node, code_bytes)

            # Get decorators for standalone functions
            decorators = self.finder.get_decorators(code, func_name)

            func_element = CodeElement(
                type=CodeElementType.FUNCTION,
                name=func_name,
                content=func_content,
                range=CodeRange(
                    start_line=func_range[0], end_line=func_range[1], node=func_node
                ),
                additional_data={"decorators": decorators},
            )

            # Create meta-element children for function decorators
            for decorator in decorators:
                # Extract decorator name without @ and args
                decorator_name = decorator[1:].split("(")[0].strip()
                meta_element = CodeElement(
                    type=CodeElementType.META_ELEMENT,
                    name=decorator_name,
                    content=decorator,
                    parent_name=func_name,
                    additional_data={
                        "meta_type": MetaElementType.DECORATOR,
                        "target_type": "function",
                        "target_name": func_name,
                    },
                )
                func_element.children.append(meta_element)

            result.elements.append(func_element)

        return result
