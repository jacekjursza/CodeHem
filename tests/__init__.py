"""
Test package for CodeHem2.
"""
from codehem.languages.lang_python import initialize_python_language

# Ensure Python manipulators are registered before tests run
initialize_python_language()