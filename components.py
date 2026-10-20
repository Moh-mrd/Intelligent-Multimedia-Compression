"""Small HTML builders for the custom UI pieces (cards, pills, header, footer).

Every value that can come from the backend or the user is escaped before it is placed in HTML.
HTML is built as single-line strings on purpose: Markdown ends an HTML block at a blank line
and treats indented lines as code.
"""

from __future__ import annotations

import html

# Simple 24x24 stroke icons (inner SVG markup only).
ICONS = {
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "shrink": '<path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/>',
    "percent": '<path d="M19 5L5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "ratio": '<path d="M5 12h14M12 5v0M12 19v0"/><circle cx="12" cy="6" r="1"/><circle cx="12" cy="18" r="1"/>',
    "signal": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "frame": '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="M21 15l-5-5L5 21"/>',
    "film": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 12h18M3 7.5h4M3 16.5h4M17 7.5h4M17 16.5h4"/>',
    "files": '<path d="M15 2H9a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V7z"/><path d="M15 2v5h5M4 8v12a2 2 0 0 0 2 2h9"/>',
    "plug": '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13l3.5 7v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
}

LOGO = (
    '<svg class="logo" width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">'
    '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#22D3EE"/><stop offset="1" stop-color="#8B7CF6"/></linearGradient></defs>'
    '<rect width="40" height="40" rx="11" fill="url(#lg)"/>'
    '<path d="M12 17h5v-5M28 17h-5v-5M12 23h5v5M28 23h-5v5" fill="none" stroke="#06202B" '
    'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def icon(name: str, size: int = 18) -> str:
    return (
        f'<svg class="ico" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{ICONS[name]}</svg>'
    )


def pill(kind: str, text: str, detail: str = "") -> str:
    """kind: ok | bad | idle"""
    extra = f'<span class="status-detail">{esc(detail)}</span>' if detail else ""
    return f'<span class="pill {kind}">{esc(text)}</span>{extra}'


def brand_header(status_html: str) -> str:
    return (
        '<div class="topbar"><div class="brand">' + LOGO +
        '<div><div class="brand-name">Intelligent Multimedia Compression</div>'
        '<div class="brand-sub">Machine learning to preserve visual quality</div></div></div>'
        f'<div class="topbar-status">{status_html}</div></div>'
    )


def section_header(title: str, subtitle: str = "") -> str:
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    return f'<div class="sec-head"><h3>{esc(title)}</h3>{sub}</div>'


def card_title(title: str, subtitle: str = "") -> str:
    sub = f'<div class="card-sub">{esc(subtitle)}</div>' if subtitle else ""
    return f'<div class="card-title">{esc(title)}</div>{sub}'


def tag(text: str, out: bool = False) -> str:
    return f'<span class="tag{" out" if out else ""}">{esc(text)}</span>'


def banner(kind: str, title: str, detail: str = "") -> str:
    """kind: ok | warn"""
    extra = f'<span class="banner-detail">{esc(detail)}</span>' if detail else ""
    return f'<div class="banner {kind}"><span class="banner-title">{esc(title)}</span>{extra}</div>'


def metric_card(label: str, value: str, icon_name: str, hint: str = "", accent: bool = False) -> str:
    cls = "mcard accent" if accent else "mcard"
    return (
        f'<div class="{cls}" title="{esc(hint)}">'
        f'<div class="mcard-top"><span class="mcard-ico">{icon(icon_name)}</span>'
        f'<span class="mcard-label">{esc(label)}</span></div>'
        f'<div class="mcard-value">{esc(value)}</div></div>'
    )


def metric_grid(cards: list[str]) -> str:
    return '<div class="mgrid">' + "".join(cards) + "</div>"


def empty_state(icon_name: str, title: str, text: str) -> str:
    return (
        f'<div class="empty"><div class="empty-ico">{icon(icon_name, 26)}</div>'
        f'<div class="empty-title">{esc(title)}</div><div class="empty-text">{esc(text)}</div></div>'
    )


def steps(items: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<div class="step"><span class="step-n">{i}</span>'
        f'<div><div class="step-t">{esc(t)}</div><div class="step-d">{esc(d)}</div></div></div>'
        for i, (t, d) in enumerate(items, 1)
    )
    return f'<div class="steps">{rows}</div>'


def glossary(items: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<div class="gloss"><div class="gloss-t">{esc(t)}</div><div class="gloss-d">{esc(d)}</div></div>'
        for t, d in items
    )
    return f'<div class="gloss-grid">{rows}</div>'


def footer() -> str:
    return (
        '<div class="app-foot"><div class="foot-name">'
        "Intelligent Multimedia Compression Using Machine Learning to Preserve Visual Quality</div>"
        '<div class="foot-tag">University engineering project</div></div>'
    )
