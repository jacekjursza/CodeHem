#!/usr/bin/env python
"""
Script to build and publish the CodeHem package to PyPI.
"""
import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

def get_venv_info():
    """
    Determine if running in a virtual environment and return relevant info.
    """
    venv_path = os.environ.get('VIRTUAL_ENV')
    is_in_venv = venv_path is not None

    if is_in_venv:
        bin_dir = "Scripts" if sys.platform == "win32" else "bin"
        venv_bin_path = os.path.join(venv_path, bin_dir)
        python_path = os.path.join(venv_bin_path, 'python')
        pip_path = os.path.join(venv_bin_path, 'pip')

        # On Windows, make sure we add the .exe extension
        if sys.platform == "win32":
            python_path += '.exe'
            pip_path += '.exe'

        print(f"Using virtual environment at: {venv_path}")
        return {
            "is_active": True,
            "path": venv_path,
            "bin_path": venv_bin_path,
            "python_path": python_path,
            "pip_path": pip_path
        }
    else:
        print("Warning: Not running in a virtual environment!")
        return {
            "is_active": False,
            "path": None,
            "bin_path": None,
            "python_path": sys.executable,
            "pip_path": "pip"
        }

def clean_build_artifacts():
    """Remove previous build artifacts."""
    print("Cleaning previous build artifacts...")

    directories_to_clean = [
        "build",
        "dist",
        "CodeHem.egg-info",
        "__pycache__",
    ]

    for directory in directories_to_clean:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            print(f"  Removed {directory}/")

    # Clean __pycache__ directories recursively
    for root, dirs, files in os.walk("."):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                path = os.path.join(root, dir_name)
                shutil.rmtree(path)
                print(f"  Removed {path}/")

def run_tests(venv_info):
    """Run project tests."""
    print("Running tests...")
    try:
        result = subprocess.run(
            [venv_info["python_path"], "-m", "pytest", "-xvs", "tests"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print("Tests failed!")
        print(e.stdout)
        print(e.stderr)
        return False

def build_package(venv_info):
    """Build source distribution and wheel packages."""
    print("Building package distributions...")
    try:
        subprocess.run(
            [venv_info["python_path"], "-m", "build"],
            check=True,
            capture_output=True,
            text=True
        )
        print("Package built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print("Package build failed!")
        print(e.stdout)
        print(e.stderr)
        return False

def check_setup_py():
    """Check if setup.py exists and contains required configuration."""
    if not os.path.exists("setup.py"):
        print("ERROR: setup.py file not found!")
        print("Please create a setup.py file with your package configuration.")
        return False

    print("setup.py found!")
    return True

def check_dependencies(venv_info):
    """Check if required dependencies are installed."""
    required_packages = ["twine", "build", "wheel"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"Missing required dependencies: {', '.join(missing_packages)}")
        print("Installing missing dependencies...")

        try:
            subprocess.run(
                [venv_info["python_path"], "-m", "pip", "install"] + missing_packages,
                check=True
            )
            print("Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("Failed to install dependencies.")
            return False

    return True

def upload_to_pypi(venv_info, test=False):
    """Upload the built distributions to PyPI."""
    if not os.path.exists("dist"):
        print("No distribution files found. Please build the package first.")
        return False

    if test:
        print("Uploading to Test PyPI...")
        repo_url = "--repository-url https://test.pypi.org/legacy/"
    else:
        print("Uploading to PyPI...")
        repo_url = ""

    try:
        twine_path = os.path.join(venv_info["bin_path"], "twine") if venv_info["is_active"] else "twine"

        # On Windows, make sure we add the .exe extension if needed
        if sys.platform == "win32" and venv_info["is_active"]:
            twine_path += '.exe'

        if repo_url:
            cmd = [twine_path, "upload", "--repository-url", "https://test.pypi.org/legacy/", "dist/*"]
        else:
            cmd = [twine_path, "upload", "dist/*"]

        # Convert to string command for shell=True on Windows
        if sys.platform == "win32":
            cmd_str = " ".join(cmd)
        else:
            cmd_str = " ".join(cmd)

        print(f"Running command: {cmd_str}")

        # For security, we don't capture output here to avoid showing credentials
        result = subprocess.run(cmd_str, shell=True)

        if result.returncode == 0:
            print("Upload successful!")
            if test:
                print("Package available at: https://test.pypi.org/project/CodeHem/")
                print("You can install it with: pip install --index-url https://test.pypi.org/simple/ CodeHem")
            else:
                print("Package available at: https://pypi.org/project/CodeHem/")
                print("You can install it with: pip install CodeHem")
            return True
        else:
            print("Upload failed! Make sure you have the correct credentials.")
            return False

    except Exception as e:
        print(f"Error during upload: {str(e)}")
        return False

def create_setup_py_if_missing():
    """Create a basic setup.py file if it doesn't exist."""
    if os.path.exists("setup.py"):
        return

    print("setup.py not found, creating a basic template...")

    readme_path = "README.md"
    if not os.path.exists(readme_path):
        with open(readme_path, "w") as f:
            f.write("# CodeHem\n\nA language-agnostic library for code querying and manipulation.")

    setup_py_content = """
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="CodeHem",
    version="0.1.0",
    author="JAacek Jursza",
    author_email="jacek.jursza@gmail.com",
    description="A language-agnostic library for code querying and manipulation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jacekjursza/CodeHem",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=[
        "tree-sitter==0.24.0",
        "tree-sitter-javascript==0.23.1",
        "tree-sitter-python==0.23.6",
        "tree-sitter-typescript==0.23.2",
        "typing_extensions==4.12.2",
        "rich==13.9.4",
        "pydantic==2.10.6",
        "pydantic_core==2.27.2",
        "setuptools>=77.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "twine",
            "build",
            "wheel",
        ],
    },
)
"""

    with open("setup.py", "w") as f:
        f.write(setup_py_content.strip())

    print("TIP: Install development dependencies with: pip install -e .[dev]")

def main():
    parser = argparse.ArgumentParser(description="Build and publish CodeHem to PyPI")
    parser.add_argument("--test", action="store_true", help="Upload to Test PyPI instead of production PyPI")
    parser.add_argument("--no-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-build", action="store_true", help="Skip building the package")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading to PyPI")

    args = parser.parse_args()

    # Get virtual environment information
    venv_info = get_venv_info()

    # Create setup.py if missing
    create_setup_py_if_missing()

    # Validate setup.py and dependencies
    if not check_setup_py() or not check_dependencies(venv_info):
        return 1

    # Clean previous builds
    clean_build_artifacts()

    # Run tests if not skipped
    if not args.no_tests:
        if not run_tests(venv_info):
            if input("Tests failed. Continue anyway? (y/N): ").lower() != "y":
                return 1

    # Build package if not skipped
    if not args.skip_build:
        if not build_package(venv_info):
            return 1

    # Upload to PyPI if not skipped
    if not args.skip_upload:
        confirmation = input(f"Ready to upload to {'Test PyPI' if args.test else 'PyPI'}. Continue? (y/N): ")
        if confirmation.lower() == "y":
            if not upload_to_pypi(venv_info, test=args.test):
                return 1
        else:
            print("Upload canceled.")

    print("Done!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
