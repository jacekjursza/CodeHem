#!/usr/bin/env python3
"""
Scan a directory and emit NDJSON summaries or full elements per file using CodeHem SDK.

Usage:
  python examples/scan_ndjson.py PATH [--ext .py --ext .ts,.tsx] [--summary] [--output out.ndjson]
"""
import argparse
import json
import os
from typing import Dict, List

from codehem import CodeHem


def counts(elements_obj) -> Dict[str, int]:
    classes = 0
    functions = 0
    methods = 0
    for e in elements_obj.elements:
        et = getattr(e, "type", None)
        ev = et.value if et else None
        if ev == "class":
            classes += 1
            for ch in getattr(e, "children", []) or []:
                ctype = getattr(ch, "type", None)
                if ctype and getattr(ctype, "value", None) == "method":
                    methods += 1
        elif ev == "function":
            functions += 1
        elif ev == "method":
            methods += 1
    return {"classes": classes, "functions": functions, "methods": methods}


def to_dict(el) -> Dict:
    if hasattr(el, "model_dump"):
        return el.model_dump()
    if hasattr(el, "dict"):
        return el.dict()
    return dict(getattr(el, "__dict__", {}))


def sanitize(obj):
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if k == "node":
                continue
            clean[k] = sanitize(v)
        return clean
    if isinstance(obj, list):
        return [sanitize(x) for x in obj]
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


def main():
    ap = argparse.ArgumentParser(description="Emit NDJSON summaries or elements using CodeHem")
    ap.add_argument("path", help="File or directory path")
    ap.add_argument("--ext", action="append", help="Filter extensions; repeat or comma-separated (e.g., --ext .py --ext .ts,.tsx)")
    ap.add_argument("--summary", action="store_true", help="Emit summary counts instead of full elements")
    ap.add_argument("--output", help="Output file (NDJSON)")
    args = ap.parse_args()

    exts: List[str] = []
    if args.ext:
        parts: List[str] = []
        for item in args.ext:
            parts.extend([p.strip() for p in item.split(',') if p.strip()])
        for p in parts:
            p = p.lower()
            if not p.startswith('.'):
                p = '.' + p
            exts.append(p)

    items = []
    paths: List[str] = []
    if os.path.isdir(args.path):
        for root, _, files in os.walk(args.path):
            for fname in files:
                if exts and os.path.splitext(fname)[1].lower() not in exts:
                    continue
                paths.append(os.path.join(root, fname))
    else:
        paths.append(args.path)

    for p in paths:
        try:
            content = CodeHem.load_file(p)
            try:
                hem = CodeHem.from_file_path(p)
            except Exception:
                # Fallback to detection by content
                hem = CodeHem.from_raw_code(content)
            elements = hem.extract(content)
            if args.summary:
                obj = {"path": p, "summary": counts(elements)}
            else:
                raw = [to_dict(e) for e in elements.elements]
                obj = {"path": p, "elements": sanitize(raw)}
            items.append(obj)
        except Exception:
            continue

    out_line_writer = None
    if args.output:
        out_line_writer = open(args.output, "w", encoding="utf-8")
    try:
        for obj in items:
            line = json.dumps(obj, ensure_ascii=False)
            if out_line_writer:
                out_line_writer.write(line + "\n")
            else:
                print(line)
    finally:
        if out_line_writer:
            out_line_writer.close()


if __name__ == "__main__":
    main()

