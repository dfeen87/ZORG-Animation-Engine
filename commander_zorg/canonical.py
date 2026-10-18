"""Python-environment-bound canonical JSON and ordinary atomic publication."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import uuid


def _normalize(value):
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite canonical number")
        return 0.0 if value == 0.0 else value
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError("JSON keys must be strings")
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError(f"unsupported canonical type: {type(value).__name__}")


def canonical_bytes(value) -> bytes:
    return (json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"nonfinite JSON literal: {value}")

    result = json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
    _normalize(result)  # Also reject overflow, e.g. 1e999.
    return result


def read_json(path: Path):
    return strict_json(Path(path).read_bytes())


def read_jsonl(path: Path):
    data = Path(path).read_bytes()
    if data and not data.endswith(b"\n"):
        raise ValueError(f"truncated JSONL: {path.name}")
    return [strict_json(row) for row in data.splitlines()]


def atomic_write(path: Path, data: bytes):
    path = Path(path)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.partial")
    try:
        with temp.open("xb") as file:
            file.write(data)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_json(path: Path, value):
    atomic_write(path, canonical_bytes(value))
