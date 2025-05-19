import threading

from codehem import CodeHem


def test_workspace_find(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    sample = repo / "sample.py"
    sample.write_text("def calculate(x):\n    return x * 2\n")

    ws = CodeHem.open_workspace(str(repo))
    found = ws.find(name="calculate", kind="function")
    assert found is not None
    assert found[0] == "sample.py"
    assert found[1] == "FILE.calculate[function]"


def test_workspace_apply_patch_locked(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    sample = repo / "sample.py"
    sample.write_text("def calculate(x):\n    return x * 2\n")

    ws = CodeHem.open_workspace(str(repo))

    errors = []

    def worker(val):
        try:
            ws.apply_patch(
                "sample.py",
                "calculate[function]",
                f"def calculate(x):\n    return {val}\n",
                mode="replace",
                original_hash=None,
            )
        except Exception as e:  # pragma: no cover - ensure thread errors surface
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    content = sample.read_text()
    assert "return" in content
