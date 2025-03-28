#!/usr/bin/env python
"""
Command-line tool for generating support for new languages in CodeHem.
"""
import argparse
import os
import sys
import logging
from typing import List, Optional

# Add the parent directory to the path so we can import codehem
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from codehem.core.language_factory import LanguageComponentFactory

def main():
    """Main entry point for the language generator tool."""
    parser = argparse.ArgumentParser(
        description='Generate support for a new language in CodeHem')
    
    parser.add_argument('language_code', 
                       help='The language code (e.g., ruby, go, rust)')
    
    parser.add_argument('--extensions', '-e', nargs='+', required=True,
                       help='File extensions for the language (e.g., .rb .erb)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, 
                       format='%(levelname)s: %(message)s')
    
    # Format file extensions
    extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in args.extensions]
    
    print(f"Generating language support for: {args.language_code}")
    print(f"File extensions: {', '.join(extensions)}")
    
    # Create the language components
    result = LanguageComponentFactory.initialize_language(
        language_code=args.language_code,
        file_extensions=extensions
    )
    
    if result:
        language_dir = f'd:/code/codehem/codehem/languages/lang_{args.language_code}'
        print(f"\nSuccessfully generated language support!")
        print(f"Language components created in:\n  {language_dir}")
        print("\nFiles created:")
        for root, _, files in os.walk(language_dir):
            for file in files:
                print(f"  {os.path.join(root, file)}")
        
        print("\nNext steps:")
        print("1. Implement language detection patterns in detector.py")
        print("2. Update element_type_template.py to add your language")
        print("3. Implement language-specific extractors and manipulators")
        print("4. Create tests for your language implementation")
    else:
        print("\nFailed to generate language support.")
        print("Check the logs for more information.")
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main())