"""Number and size formatting helpers (no Streamlit dependency, never invents values)."""

from __future__ import annotations


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def format_size(n) -> str:
    if not _is_num(n):
        return "—"
    return f"{n / 1024:,.1f} KB" if n < 1024**2 else f"{n / 1024**2:,.2f} MB"


def fmt_num(value, spec: str, suffix: str = "") -> str:
    """Format an optional numeric value. Missing -> em dash; non-numeric -> shown as received."""
    if value is None or isinstance(value, bool):
        return "—"
    try:
        return f"{float(value):{spec}}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def space_saved(res: dict):
    """Percentage saved, calculated from the byte counts (None if unavailable)."""
    orig, comp = res.get("original_bytes"), res.get("compressed_bytes")
    if not _is_num(orig) or not _is_num(comp) or orig <= 0:
        return None
    return (1 - comp / orig) * 100


def compression_ratio(res: dict):
    """original / compressed, calculated from the byte counts (None if unavailable)."""
    orig, comp = res.get("original_bytes"), res.get("compressed_bytes")
    if not _is_num(orig) or not _is_num(comp) or orig <= 0 or comp <= 0:
        return None
    return orig / comp
