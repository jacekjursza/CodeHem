import os
import time
from contextlib import contextmanager
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from codehem.main import CodeHem
from codehem.core.error_handling import WriteConflictError


class Workspace:
    """Simple workspace index and patch orchestrator."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.index: Dict[Tuple[str, str], List[Tuple[str, str]]] = defaultdict(list)

    @classmethod
    def open(cls, root: str) -> "Workspace":
        ws = cls(root)
        ws._build_index()
        return ws

    def _build_index(self) -> None:
        self.index.clear()
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            try:
                hem = CodeHem.from_file_path(str(path))
            except ValueError:
                continue
            code = hem.load_file(str(path))
            result = hem.extract(code)
            self._index_file(path, hem, result)

    def _index_file(self, path: Path, hem: CodeHem, elements) -> None:
        current_file = str(path.relative_to(self.root))

        def visit(element):
            key = (element.name, element.type.value)
            xpath = hem.short_xpath(elements, element)
            self.index[key].append((current_file, xpath))
            for child in getattr(element, "children", []):
                visit(child)

        for el in elements.elements:
            visit(el)

    def find(self, name: str, kind: str) -> Optional[Tuple[str, str]]:
        matches = self.index.get((name, kind))
        if not matches:
            return None
        return matches[0]

    @contextmanager
    def _file_lock(self, path: Path):
        lock_path = path.with_suffix(path.suffix + ".lock")
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                os.remove(lock_path)
            except OSError:
                pass

    def apply_patch(
        self,
        file_path: str,
        xpath: str,
        new_code: str,
        *,
        mode: str = "replace",
        original_hash: Optional[str] = None,
        on_conflict=None,
    ) -> object:
        abs_path = self.root / file_path
        hem = CodeHem.from_file_path(str(abs_path))
        with self._file_lock(abs_path):
            # Load file content inside the lock to avoid race conditions
            text = hem.load_file(str(abs_path))
            if original_hash is None:
                original_hash = hem.get_element_hash(text, xpath)
            try:
                result = hem.apply_patch(
                    text,
                    xpath,
                    new_code,
                    mode=mode,
                    original_hash=original_hash,
                )
            except WriteConflictError as e:
                if on_conflict:
                    return on_conflict(e)
                raise
            with open(abs_path, "w", encoding="utf8") as fh:
                fh.write(result["code"])
        # Rebuild index for this file
        result_code = result["code"] if isinstance(result, dict) else result
        elements = hem.extract(result_code)
        self._index_file(abs_path, hem, elements)
        return result
