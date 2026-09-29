"""Auditable local effect catalog for the bounded MVP."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class CatalogError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def load_catalog(root: Path) -> dict[str, Any]:
    path = root / "mvp" / "catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def asset_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["asset_id"]: item for item in catalog.get("assets", [])}


def asset_path(root: Path, asset_id: str) -> Path:
    item = asset_map(load_catalog(root)).get(asset_id)
    if item is None:
        raise CatalogError("asset_not_found", f"Unknown asset_id: {asset_id}")
    path = root / "mvp" / item["path"]
    if not path.is_file():
        raise CatalogError("asset_not_found", f"Missing catalog asset: {asset_id}")
    return path


def search(catalog: dict[str, Any], query: str) -> list[dict[str, Any]]:
    normalized = query.strip().lower()
    if not 1 <= len(normalized) <= 64:
        raise CatalogError("invalid_params", "query must contain 1–64 characters")
    hits = []
    for item in catalog.get("assets", []):
        terms = [str(term).lower() for term in item.get("queries", [])]
        if any(term in normalized or normalized in term for term in terms):
            hits.append(item)
    if not hits:
        raise CatalogError("asset_not_found", f"No local asset matches: {query}")
    return hits


def resolve_hashes(root: Path) -> dict[str, str]:
    """Return file hashes for the run manifest without mutating source manifests."""
    catalog = load_catalog(root)
    result: dict[str, str] = {}
    for item in catalog.get("assets", []):
        path = root / "mvp" / item["path"]
        if path.is_file():
            result[item["asset_id"]] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result
