from setuptools import setup, find_packages
setup(
    name='codehem', 
    version='0.1.1', 
    description='Language-agnostic library for code querying and manipulation', 
    long_description=open('README.md').read(), 
    long_description_content_type='text/markdown', 
    author='Jacek Jursza', 
    url='https://github.com/jacekjursza/CodeHem', 
    packages=find_packages(), 
    install_requires=[
        'tree-sitter', 
        'tree-sitter-python', 
        'tree-sitter-javascript', 
        'tree-sitter-typescript', 
        'rich', 
        'pydantic'
    ], 
    classifiers=[
        'Development Status :: 3 - Alpha', 
        'Intended Audience :: Developers', 
        'License :: OSI Approved :: MIT License', 
        'Programming Language :: Python :: 3', 
        'Programming Language :: Python :: 3.7', 
        'Programming Language :: Python :: 3.8', 
        'Programming Language :: Python :: 3.9', 
        'Programming Language :: Python :: 3.10'
    ], 
    python_requires='>=3.7', 
    entry_points={'console_scripts': ['codehem=codehem.cli:main']}
)