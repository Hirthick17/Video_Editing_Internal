"""Deterministic file and content hashing using SHA-256."""

import hashlib
from pathlib import Path
from typing import Union


def calculate_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Calculate the SHA-256 hex digest of a file in chunks to minimize memory usage."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for checksum calculation: {file_path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_bytes_sha256(data: bytes) -> str:
    """Calculate the SHA-256 hex digest of raw in-memory bytes."""
    return hashlib.sha256(data).hexdigest()

