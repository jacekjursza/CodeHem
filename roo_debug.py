import sys
from codehem.core.extraction_service import ExtractionService

def debug_extraction(code: str, language_code: str = "python"):
    extractor = ExtractionService(language_code)
    print("=== RAW EXTRACTION ===")
    raw = extractor._extract_file_raw(code)
    for key, value in raw.items():
        print(f"{key}: {value}")

    print("\n=== POST-PROCESSED ELEMENTS ===")
    result = extractor.extract_all(code)
    for element in result.elements:
        print(element)
        if hasattr(element, 'children'):
            for child in element.children:
                print("  ", child)
                if hasattr(child, 'children'):
                    for grandchild in child.children:
                        print("    ", grandchild)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python roo_test.py <path_to_code_file>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        code_content = f.read()

    debug_extraction(code_content)