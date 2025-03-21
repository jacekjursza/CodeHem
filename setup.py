from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="CodeHem",
    version="0.1.6",
    author="Jacek Jursza",
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
    entry_points={'console_scripts': ['codehem=codehem.cli:main']}
)