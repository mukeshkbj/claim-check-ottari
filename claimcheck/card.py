"""Share card: a 1200x630 PNG of a report's verdicts, used as the link preview image for /r/<id>."""
from __future__ import annotations

import io
import unicodedata
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config

W, H = 1200, 630
INK, QUIET, BG, ACCENT = (17, 24, 39), (91, 101, 117), (250, 250, 247), (37, 99, 235)
COLOURS = {"Supported": (21, 128, 61), "False": (185, 28, 28), "Misleading": (180, 83, 9),
           "Unsupported": (91, 101, 117), "Can't verify": (91, 101, 117), "Opinion": (109, 40, 217)}
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "C:/Windows/Fonts"]
CACHE = Path(config.DATA_DIR) / "cards"


@lru_cache(maxsize=16)
def _font(size: int, bold: bool = False):
    names = ["DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else ["DejaVuSans.ttf", "arial.ttf"]
    for d in FONT_DIRS:
        for n in names:
            p = Path(d) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def _clean(text: str) -> str:
    """Fold typographic characters many fonts lack (non-breaking hyphens, odd spaces) to plain ones."""
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\u2010", "-").replace("\u2011", "-").replace("\u00ad", "")


def _wrap(draw, text: str, font, width: int, lines: int) -> list[str]:
    text = _clean(text)
    out, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            cur = trial
            continue
        if cur:
            out.append(cur)
        cur = word
        if len(out) == lines:
            break
    if cur and len(out) < lines:
        out.append(cur)
    if len(out) == lines and " ".join(out) != " ".join(text.split()):
        while out[-1] and draw.textlength(out[-1] + "…", font=font) > width:
            out[-1] = out[-1][:-1]
        out[-1] = out[-1].rstrip() + "…"
    return out


def render(rows: list[dict], host: str) -> bytes:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=ACCENT)
    d.text((60, 44), "Claim", font=_font(44, True), fill=INK)
    d.text((60 + d.textlength("Claim ", font=_font(44, True)), 44), "Check", font=_font(44, True), fill=ACCENT)
    d.text((60, 104), "Fact-checked by a team of open-weight models through Otari", font=_font(24), fill=QUIET)
    y = 170
    shown = rows[:3]
    per = 2 if len(shown) == 3 else 3
    pill_font = _font(26, True)
    col = 60 + max(int(d.textlength(r.get("verdict") or "?", font=pill_font)) + 36 for r in shown) + 28 if shown else 60
    for r in shown:
        verdict = r.get("verdict") or "?"
        pw = int(d.textlength(verdict, font=pill_font)) + 36
        d.rounded_rectangle([60, y, 60 + pw, y + 46], radius=23, fill=COLOURS.get(verdict, QUIET))
        d.text((78, y + 8), verdict, font=pill_font, fill=(255, 255, 255))
        lines = _wrap(d, r.get("text", ""), _font(30), W - 60 - col, per)
        for i, line in enumerate(lines):
            d.text((col, y + 4 + i * 40), line, font=_font(30), fill=INK)
        y += max(60, 40 * len(lines) + 24)
    if len(rows) > 3:
        d.text((60, y), f"+ {len(rows) - 3} more claim(s)", font=_font(24), fill=QUIET)
    sources = len({u for r in rows for u in r.get("sources", [])})
    agree = [r["second"]["agree"] for r in rows if r.get("second")]
    foot = f"{sources} source(s) cited"
    if agree:
        foot += f"  ·  both judges agreed on {sum(agree)} of {len(agree)}"
    d.line([60, H - 92, W - 60, H - 92], fill=(226, 228, 233), width=2)
    d.text((60, H - 70), foot, font=_font(24), fill=QUIET)
    d.text((W - 60 - d.textlength(host, font=_font(24, True)), H - 70), host, font=_font(24, True), fill=ACCENT)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def card_for(report_id: str, rows: list[dict], host: str) -> bytes:
    p = CACHE / f"{report_id}.png"
    try:
        return p.read_bytes()
    except OSError:
        pass
    png = render(rows, host)
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        p.write_bytes(png)
    except OSError:
        pass
    return png
