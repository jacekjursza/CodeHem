import hashlib


def sha1_code(code: str) -> str:
    """Return the SHA1 hash of the given code string."""
    return hashlib.sha1(code.encode("utf8")).hexdigest()
