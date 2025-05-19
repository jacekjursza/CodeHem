#!/usr/bin/env python
"""
Refactoring script for ExtractionService.

This script updates the codebase to use the new component-based architecture
by replacing the old ExtractionService with the refactored version
and updating the PythonLanguageService to use the new ExtendedLanguageService.
"""

import os
import sys
import shutil
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_project_root():
    """Get the project root directory."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent

def backup_file(file_path, backup_dir):
    """Create a backup of a file."""
    backup_path = os.path.join(backup_dir, os.path.basename(file_path))
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup of {file_path} -> {backup_path}")
    return backup_path

def replace_file(source_path, target_path):
    """Replace target file with source file."""
    shutil.copy2(source_path, target_path)
    logger.info(f"Replaced {target_path} with {source_path}")

def main(args):
    """Main refactoring function."""
    # Get project root
    project_root = get_project_root()
    logger.info(f"Project root: {project_root}")

    # Create backup directory if it doesn't exist
    backup_dir = os.path.join(project_root, "scripts", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    logger.info(f"Backup directory: {backup_dir}")

    # Define file paths
    extraction_service_path = os.path.join(project_root, "codehem", "core", "extraction_service.py")
    extraction_service_refactored_path = os.path.join(project_root, "codehem", "core", "extraction_service_refactored.py")
    language_service_extended_path = os.path.join(project_root, "codehem", "core", "language_service_extended.py")
    python_service_path = os.path.join(project_root, "codehem", "languages", "lang_python", "service.py")
    python_service_refactored_path = os.path.join(project_root, "codehem", "languages", "lang_python", "service_refactored.py")

    # Check if all required files exist
    missing_files = []
    for file_path in [extraction_service_refactored_path, language_service_extended_path, python_service_refactored_path]:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        return 1

    # Backup existing files
    if not args.skip_backup:
        backup_file(extraction_service_path, backup_dir)
        backup_file(python_service_path, backup_dir)

    # Replace files
    replace_file(extraction_service_refactored_path, extraction_service_path)
    replace_file(python_service_refactored_path, python_service_path)

    # Verify files were replaced
    logger.info("Verifying files were replaced...")
    for file_path in [extraction_service_path, python_service_path]:
        if os.path.exists(file_path):
            logger.info(f"Verified {file_path} exists")
        else:
            logger.error(f"Failed to verify {file_path}")
            return 1

    logger.info("Refactoring completed successfully!")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refactor ExtractionService to use new component architecture")
    parser.add_argument("--skip-backup", action="store_true", help="Skip creating backups of existing files")
    args = parser.parse_args()
    
    sys.exit(main(args))
