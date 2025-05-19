"""Simple code builders for CodeHem."""

from typing import List, Optional


def build_function(
    name: str,
    args: Optional[List[str]] = None,
    body: Optional[List[str]] = None,
    decorators: Optional[List[str]] = None,
) -> str:
    """Generate a function definition as a string."""
    args_str = ", ".join(args or [])
    lines = []
    if decorators:
        lines.extend(f"@{d}" for d in decorators)
    lines.append(f"def {name}({args_str}):")
    body = body or ["pass"]
    lines.extend(f"    {line}" for line in body)
    return "\n".join(lines)


def build_class(
    name: str,
    body: Optional[List[str]] = None,
    decorators: Optional[List[str]] = None,
) -> str:
    """Generate a class definition as a string."""
    lines = []
    if decorators:
        lines.extend(f"@{d}" for d in decorators)
    lines.append(f"class {name}:")
    body = body or ["pass"]
    lines.extend(f"    {line}" for line in body)
    return "\n".join(lines)


def build_method(
    name: str,
    args: Optional[List[str]] = None,
    body: Optional[List[str]] = None,
    decorators: Optional[List[str]] = None,
) -> str:
    """Generate a method definition (like function)."""
    if args is None:
        args = ["self"]
    return build_function(name, args, body, decorators)
