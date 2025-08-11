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
    parser.add_argument("--quiet", action="store_true", help="Reduce logs to errors only")
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
    extract_p.add_argument("file", help="Source file or directory path")
    extract_p.add_argument("--output", help="Output file (for aggregated results if --recursive)")
    extract_p.add_argument("--raw-json", action="store_true", help="Output raw JSON (no progress UI)")
    extract_p.add_argument("--summary", action="store_true", help="Only output counts (classes/functions/methods)")
    extract_p.add_argument("--recursive", action="store_true", help="Scan directory recursively (requires path to be a directory)")
    extract_p.add_argument(
        "--ext",
        action="append",
        help="Limit to files with given extension(s); repeat or use comma-separated (e.g., --ext .py --ext .ts,.tsx)",
    )
    extract_p.add_argument(
        "--ndjson",
        action="store_true",
        help="Emit one JSON object per line for each file (recursive mode)",
    )
    extract_p.add_argument(
        "--out-dir",
        help="Write per-file JSON outputs under this directory (recursive mode)",
    )

    args = parser.parse_args()
    # Determine logging level
    if getattr(args, "debug", False):
        log_level = logging.DEBUG
    elif getattr(args, "quiet", False):
        log_level = logging.ERROR
    elif getattr(args, "verbose", False):
        log_level = logging.INFO
    else:
        log_level = logging.WARNING
    logging.basicConfig(level=log_level)

    if args.command == "detect":
        _detect(args.file, args.raw_json, console)
    elif args.command == "patch":
        _patch(args.target, args.xpath, args.file, args.mode, args.dry_run, console)
    elif args.command == "extract":
        if not os.path.exists(args.file):
            console.print(f"[bold red]Path not found:[/bold red] {args.file}")
            sys.exit(1)

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

        def _counts(elements_obj) -> Dict[str, int]:
            # Compute basic counts (walks nested children for methods)
            try:
                classes = 0
                functions = 0
                methods = 0

                for e in elements_obj.elements:
                    et = getattr(e, "type", None)
                    ev = et.value if et else None
                    if ev == "class":
                        classes += 1
                        # count methods among children
                        try:
                            for ch in getattr(e, "children", []) or []:
                                ctype = getattr(ch, "type", None)
                                if ctype and getattr(ctype, "value", None) == "method":
                                    methods += 1
                        except Exception:
                            pass
                    elif ev == "function":
                        functions += 1
                    elif ev == "method":
                        methods += 1
                return {"classes": classes, "functions": functions, "methods": methods}
            except Exception:
                return {"classes": 0, "functions": 0, "methods": 0}

        def _extract_file(path: str) -> Dict[str, Any]:
            content = CodeHem.load_file(path)
            try:
                hem = CodeHem.from_raw_code(content)
            except Exception:
                return {"path": path, "error": "unsupported_or_detection_failed"}
            elements = hem.extract(content)
            if args.summary:
                return {"path": path, "summary": _counts(elements)}
            else:
                raw_list = [_to_dict(e) for e in elements.elements]
                return {"path": path, "elements": _sanitize(raw_list)}

        output_data: Dict[str, Any]
        if args.recursive and os.path.isdir(args.file):
            # Prepare extension filters
            exts: set[str] = set()
            if args.ext:
                parts: list[str] = []
                for item in args.ext:
                    parts.extend([p.strip() for p in item.split(',') if p.strip()])
                for p in parts:
                    p = p.lower()
                    if not p.startswith('.'):  # normalize
                        p = '.' + p
                    exts.add(p)

            root_dir = os.path.abspath(args.file)
            collected = []
            for root, _, files in os.walk(args.file):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    # Filter by extension if provided
                    if exts and os.path.splitext(fname)[1].lower() not in exts:
                        continue
                    try:
                        result = _extract_file(fpath)
                        # Skip files where detection failed
                        if "error" in result:
                            continue
                        collected.append(result)
                    except Exception:
                        continue
            # Handle output modes for recursive
            if args.out_dir:
                out_root = os.path.abspath(args.out_dir)
                os.makedirs(out_root, exist_ok=True)
                for item in collected:
                    rel = os.path.relpath(item["path"], root_dir)
                    rel_json = rel + (".summary.json" if args.summary else ".json")
                    out_path = os.path.join(out_root, rel_json)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, "w", encoding="utf8") as f:
                        json.dump(item, f, indent=2)
                # When writing to out-dir, also print or save aggregate index if requested
                if args.output:
                    with open(args.output, "w", encoding="utf8") as f:
                        json.dump({"files": collected}, f, indent=2)
                output_data = {"files": collected}
            elif args.ndjson:
                # NDJSON to stdout or file
                if args.output:
                    with open(args.output, "w", encoding="utf8") as f:
                        for item in collected:
                            f.write(json.dumps(item) + "\n")
                    output_data = {"written": len(collected), "format": "ndjson", "path": args.output}
                else:
                    for item in collected:
                        print(json.dumps(item))
                    output_data = {"written": len(collected), "format": "ndjson"}
            elif args.summary:
                total = {"classes": 0, "functions": 0, "methods": 0}
                for item in collected:
                    s = item.get("summary", {})
                    for k in total:
                        total[k] += int(s.get(k, 0))
                output_data = {"files": collected, "total": total}
            else:
                output_data = {"files": collected}
        else:
            # Single file mode
            if args.summary:
                # No progress for summary
                output_data = _extract_file(args.file)
            elif args.raw_json or args.output:
                output_data = _extract_file(args.file)
            else:
                # Progress UI for interactive single-file extraction
                with Progress() as progress:
                    task = progress.add_task("[green]Extracting...", total=3)
                    progress.update(task, advance=1, description="[green]Creating instance...")
                    output_data = _extract_file(args.file)
                    progress.update(task, advance=2, description="[green]Done")

        # Emit results
        # Emit final results if not already streamed via ndjson or out-dir
        if not (args.recursive and (args.ndjson or args.out_dir)):
            if args.output:
                with open(args.output, "w", encoding="utf8") as f:
                    json.dump(output_data, f, indent=2)
            else:
                if args.raw_json or args.summary or args.recursive:
                    print(json.dumps(output_data, indent=2))
                else:
                    console.print_json(data=output_data)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
