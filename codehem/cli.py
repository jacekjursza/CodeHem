"""Command-line interface for CodeHem."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

from codehem import CodeHem
from codehem.languages import (
    get_language_service_for_code,
    get_language_service_for_file,
)


def _detect(file_path: str, raw_json: bool, console: Console) -> None:
    """Detect the language of ``file_path`` and print element statistics."""
    service = get_language_service_for_file(file_path)
    if not service:
        code = CodeHem.load_file(file_path)
        service = get_language_service_for_code(code)
        if not service:
            console.print(f"[bold red]Unsupported file:{file_path}[/bold red]")
            sys.exit(1)
    code = CodeHem.load_file(file_path)
    hem = CodeHem(service.language_code)
    elements = hem.extract(code)
    stats: Dict[str, Any] = {
        "language": service.language_code,
        "classes": len(elements.classes),
        "functions": len(elements.functions),
        "methods": len(elements.methods),
    }
    if raw_json:
        print(json.dumps(stats, indent=2))
    else:
        console.print(f"[bold]Language:[/bold] {stats['language']}")
        console.print(
            f"classes: {stats['classes']}, functions: {stats['functions']}, methods: {stats['methods']}"
        )


def _patch(
    target: str,
    xpath: str,
    patch_file: str,
    mode: str,
    dry_run: bool,
    console: Console,
) -> None:
    """Apply ``patch_file`` to ``target`` at ``xpath``."""
    if not os.path.exists(target):
        console.print(f"[bold red]File not found:[/bold red] {target}")
        sys.exit(1)
    if not os.path.exists(patch_file):
        console.print(f"[bold red]Patch file not found:[/bold red] {patch_file}")
        sys.exit(1)
    hem = CodeHem.from_file_path(target)
    original = CodeHem.load_file(target)
    with open(patch_file, "r", encoding="utf8") as fh:
        new_code = fh.read()
    original_hash = hem.get_element_hash(original, xpath)
    result = hem.apply_patch(
        original,
        xpath,
        new_code,
        mode=mode,
        original_hash=original_hash,
        dry_run=dry_run,
    )
    if dry_run:
        console.print(result)
    else:
        with open(target, "w", encoding="utf8") as fh:
            fh.write(result["code"] if isinstance(result, dict) else result)
        console.print(Panel("Patch applied", style="green"))


def main() -> None:
    """Entry point for the ``codehem`` command."""

    console = Console()
    parser = argparse.ArgumentParser(description="CodeHem command-line interface")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command")

    detect_p = sub.add_parser("detect", help="Detect language and show stats")
    detect_p.add_argument("file", help="Source file path")
    detect_p.add_argument("--raw-json", action="store_true", help="Output raw JSON")

    patch_p = sub.add_parser("patch", help="Apply patch to file")
    patch_p.add_argument("target", help="Target file to modify")
    patch_p.add_argument("--xpath", required=True, help="XPath to element")
    patch_p.add_argument("--file", required=True, help="File containing new code")
    patch_p.add_argument(
        "--mode",
        default="replace",
        choices=["replace", "append", "prepend"],
        help="Patch mode",
    )
    patch_p.add_argument("--dry-run", action="store_true", help="Preview diff only")

    extract_p = sub.add_parser("extract", help="Extract code elements to JSON")
    extract_p.add_argument("file", help="Source file path")
    extract_p.add_argument("--output", help="Output file")
    extract_p.add_argument("--raw-json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)

    if args.command == "detect":
        _detect(args.file, args.raw_json, console)
    elif args.command == "patch":
        _patch(args.target, args.xpath, args.file, args.mode, args.dry_run, console)
    elif args.command == "extract":
        if not os.path.exists(args.file):
            console.print(f"[bold red]File not found:[/bold red] {args.file}")
            sys.exit(1)

        def _extract_to_json_dict(file_path: str) -> Dict[str, Any]:
            content = CodeHem.load_file(file_path)
            hem = CodeHem.from_raw_code(content)
            elements = hem.extract(content)

            # Ensure JSON-serializable output. First dump to dicts, then sanitize recursively.
            def _to_dict(el: Any) -> Dict[str, Any]:
                if hasattr(el, "model_dump"):
                    return el.model_dump()
                if hasattr(el, "dict"):
                    return el.dict()
                return dict(getattr(el, "__dict__", {}))

            def _sanitize(obj: Any) -> Any:
                if isinstance(obj, dict):
                    clean: Dict[str, Any] = {}
                    for k, v in obj.items():
                        if k == "node":
                            continue  # drop tree-sitter node references
                        clean[k] = _sanitize(v)
                    return clean
                if isinstance(obj, list):
                    return [_sanitize(x) for x in obj]
                if isinstance(obj, (str, int, float, bool)) or obj is None:
                    return obj
                try:
                    json.dumps(obj)
                    return obj
                except Exception:
                    return str(obj)

            raw_list = [_to_dict(e) for e in elements.elements]
            return {"elements": _sanitize(raw_list)}

        # Suppress progress UI when producing machine-readable output
        if args.raw_json or args.output:
            elements_dict = _extract_to_json_dict(args.file)
            if args.output:
                with open(args.output, "w", encoding="utf8") as f:
                    json.dump(elements_dict, f, indent=2)
            else:
                print(json.dumps(elements_dict, indent=2))
        else:
            with Progress() as progress:
                task = progress.add_task("[green]Extracting...", total=3)
                progress.update(task, advance=1, description="[green]Creating instance...")
                elements_dict = _extract_to_json_dict(args.file)
                progress.update(task, advance=2, description="[green]Done")
                console.print_json(data=elements_dict)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
