import hashlib


def sha1_code(code: str) -> str:
    """Return the SHA1 hash of the given code string."""
    return hashlib.sha1(code.encode("utf8")).hexdigest()


def sha256_code(code: str) -> str:
    """Return the SHA256 hash of the given code string."""
    return hashlib.sha256(code.encode("utf8")).hexdigest()
