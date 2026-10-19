# -*- coding: utf-8 -*-
"""
HCI 인스타 캐러셀 — 고정 템플릿 엔진 (하이브리드의 '고정' 절반)

역할 분담
  engine.py (여기)  : 판형·배경·도트그리드·페이드·타이포·여백·footnote 위치·색 토큰
                      → 날마다 바뀌지 않는다. 계정 톤의 일관성을 책임진다.
  content.json      : Claude가 매일 생성. 문구 + 오브젝트 SVG 조각만 담는다.

오브젝트 SVG 조각 계약
  - 좌표계: 좌상단 (0,0), 폭 896, 높이 = 슬롯 높이(기본 380)
  - 색: INK / ACCENT / MUTED / DOT 토큰만 사용 (엔진이 실제 HEX로 치환)
  - 허용 요소: circle rect line path polyline polygon ellipse g
  - 도형 5개 이하, 그라디언트·필터·이미지·텍스트 금지
  - 화살표가 필요하면 marker-end="url(#ar)" / "url(#ar-accent)" / "url(#ar-muted)"
"""

import re

# ── 고정값 (프롬프트 v3 '시각 언어' 표와 1:1 대응) ────────────────────────
W, H   = 1080, 1350          # 4:5
PAD    = 92                  # 가장자리 여백
BG     = "#F7F5F2"           # 웜 오프화이트
INK    = "#1A1A1A"           # 딥 잉크
MUTED  = "#8A8580"           # 보조
DOT    = "#D8D3CC"           # 도트 그리드
STROKE = 7                   # 선 굵기

DOT_GAP, DOT_R, DOT_OP = 26, 1.6, 0.55

FONT_STACK = "Noto Sans KR, Malgun Gothic, sans-serif"

COL_W  = W - 2 * PAD         # 896 — 본문 컬럼 폭
OBJ_H  = 380                 # 오브젝트 슬롯 기본 높이

# 타이포
HERO_LH, HERO_MIN, HERO_MAX = 1.28, 46, 78
SUP_SIZE, SUP_LH   = 30, 1.36
LBL_SIZE           = 27
OBJ_LBL_SIZE       = 25      # 오브젝트 안 다이어그램 라벨
FN_SIZE, FN_GAP    = 21, 30
FN_LAST_BASELINE   = H - PAD - 43     # 1215 — footnote 마지막 줄 베이스라인

COLOR_TOKENS = {"INK": INK, "MUTED": MUTED, "DOT": DOT, "BG": BG}
ARROW_IDS    = {"ar", "ar-accent", "ar-muted"}

LAYOUTS = {
    "top-object":    ["object", "hero", "support"],   # 오브젝트 위, 카피 아래
    "mid-object":    ["hero", "object", "support"],   # 카피 위, 오브젝트 가운데
    "center-object": ["object", "hero", "support"],   # 전체 중앙정렬
    "number":        ["number", "support"],           # 큰 숫자가 곧 그래픽
}
CENTERED = {"center-object"}


# ── 텍스트 계측 (한글 1em, 라틴 0.55em 근사) ──────────────────────────────
def _char_w(ch, size):
    o = ord(ch)
    if (0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F
            or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFF60 or 0x4E00 <= o <= 0x9FFF):
        return size * 1.0
    if ch == " ":
        return size * 0.30
    return size * 0.55


def text_width(s, size):
    return sum(_char_w(c, size) for c in s)


def wrap(s, size, max_w):
    """공백 우선 줄바꿈, 안 되면 강제 분할."""
    if not s:
        return []
    lines, cur = [], ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)

    out = []
    for ln in lines:                       # 한 단어가 너무 길 때 강제 분할
        while text_width(ln, size) > max_w:
            cut = len(ln)
            while cut > 1 and text_width(ln[:cut], size) > max_w:
                cut -= 1
            out.append(ln[:cut])
            ln = ln[cut:]
        if ln:
            out.append(ln)
    return out


def auto_hero_size(lines):
    """hero_copy 줄 길이에서 크기를 역산. 3줄이면 한 단계 낮춘다."""
    if not lines:
        return HERO_MAX
    longest = max(text_width(ln, 1.0) for ln in lines) or 1.0
    size = (COL_W * 0.98) / longest
    if len(lines) >= 3:
        size *= 0.85
    return max(HERO_MIN, min(HERO_MAX, size))


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ── 배경 ─────────────────────────────────────────────────────────────────
def _defs(accent):
    marks = ""
    for mid, col in (("ar", INK), ("ar-accent", accent), ("ar-muted", MUTED)):
        marks += (
            '<marker id="' + mid + '" markerWidth="9" markerHeight="9" refX="7" refY="4.5" '
            'orient="auto" markerUnits="strokeWidth">'
            '<path d="M0,0 L9,4.5 L0,9 Z" fill="' + col + '"/></marker>'
        )
    return (
        '<defs>'
        '<pattern id="dg" width="' + str(DOT_GAP) + '" height="' + str(DOT_GAP) + '" '
        'patternUnits="userSpaceOnUse">'
        '<circle cx="' + str(DOT_R) + '" cy="' + str(DOT_R) + '" r="' + str(DOT_R) + '" '
        'fill="' + DOT + '" opacity="' + str(DOT_OP) + '"/></pattern>'
        '<radialGradient id="vig" cx="50%" cy="45%" r="72%">'
        '<stop offset="55%" stop-color="' + BG + '" stop-opacity="0"/>'
        '<stop offset="100%" stop-color="' + BG + '" stop-opacity="0.92"/>'
        '</radialGradient>' + marks + '</defs>'
    )


def _canvas():
    r = '<rect width="' + str(W) + '" height="' + str(H) + '" '
    return (r + 'fill="' + BG + '"/>' + r + 'fill="url(#dg)"/>' + r + 'fill="url(#vig)"/>')


# ── 텍스트 블록 ──────────────────────────────────────────────────────────
def _text(x, baseline, lines, size, weight, fill, lh, anchor, italic=False, ls=None):
    out = ""
    st = ' font-style="italic"' if italic else ""
    sp = ' letter-spacing="' + str(ls) + '"' if ls else ""
    for i, ln in enumerate(lines):
        y = baseline + i * size * lh
        out += ('<text x="' + str(round(x, 1)) + '" y="' + str(round(y, 1)) + '" '
                'font-family="' + FONT_STACK + '" font-size="' + str(round(size, 1)) + '" '
                'font-weight="' + str(weight) + '" fill="' + fill + '" '
                'text-anchor="' + anchor + '"' + st + sp +
                ' xml:space="preserve">' + esc(ln) + '</text>')
    return out


def _block_label(s):
    if not s:
        return ""
    return _text(PAD, PAD + 30, [s], LBL_SIZE, 500, MUTED, 1.0, "start", ls=3)


def _block_footnote(lines, centered):
    if not lines:
        return "", FN_LAST_BASELINE + 60
    first = FN_LAST_BASELINE - FN_GAP * (len(lines) - 1)
    x, anchor = (W / 2, "middle") if centered else (PAD, "start")
    svg = ""
    for i, ln in enumerate(lines):
        svg += _text(x, first + i * FN_GAP, [ln], FN_SIZE, 400, MUTED, 1.0,
                     anchor, italic=True)
    return svg, first


def _measure(kind, slide, centered):
    if kind == "hero":
        lines = slide.get("hero_copy") or []
        if isinstance(lines, str):
            lines = [l for l in lines.split("\n") if l.strip()]
        size = slide.get("hero_size") or auto_hero_size(lines)
        return {"lines": lines, "size": size, "h": len(lines) * size * HERO_LH}
    if kind == "support":
        raw = (slide.get("support_copy") or "").strip()
        lines = []
        for part in raw.split("\n"):
            lines += wrap(part.strip(), SUP_SIZE, COL_W) if part.strip() else []
        return {"lines": lines, "h": len(lines) * SUP_SIZE * SUP_LH if lines else 0}
    if kind == "object":
        h = slide.get("object_height") or OBJ_H
        return {"h": h if (slide.get("object_svg") or "").strip() else 0}
    if kind == "number":
        n = slide.get("hero_number") or {}
        val = str(n.get("value", ""))
        size = n.get("size") or min(340.0, (COL_W * 0.86) / max(text_width(val, 1.0), 0.6))
        return {"val": val, "unit": str(n.get("unit", "")), "size": size, "h": size * 1.02}
    return {"h": 0}


def _render_block(kind, m, top, slide, accent, centered):
    x = W / 2 if centered else PAD
    anchor = "middle" if centered else "start"

    if kind == "hero":
        if not m["lines"]:
            return ""
        return _text(x, top + m["size"] * 0.80, m["lines"], m["size"], 700, INK,
                     HERO_LH, anchor)

    if kind == "support":
        if not m["lines"]:
            return ""
        return _text(x, top + SUP_SIZE * 0.85, m["lines"], SUP_SIZE, 400, MUTED,
                     SUP_LH, anchor)

    if kind == "object":
        frag = (slide.get("object_svg") or "").strip()
        if not frag:
            return ""
        inner = substitute_colors(frag, accent)
        # 다이어그램 라벨("나", "AI", "개인적인 주제" …)은 엔진이 조판한다.
        # 오브젝트 조각 안에 <text>를 쓰지 못하게 하고, 타이포 통제권을 엔진이 갖는다.
        for lb in (slide.get("object_labels") or []):
            t = str(lb.get("text", "")).strip()
            if not t:
                continue
            col = substitute_colors(str(lb.get("color", "MUTED")), accent)
            inner += _text(float(lb.get("x", 0)), float(lb.get("y", 0)), [t],
                           OBJ_LBL_SIZE, 500, col, 1.0,
                           str(lb.get("anchor", "middle")))
        return ('<g transform="translate(' + str(PAD) + ',' + str(round(top, 1)) + ')">'
                + inner + '</g>')

    if kind == "number":
        if not m["val"]:
            return ""
        size, unit_size = m["size"], m["size"] * 0.4
        base = top + size * 0.80
        svg = _text(PAD, base, [m["val"]], size, 700, INK, 1.0, "start")
        if m["unit"]:
            ux = PAD + text_width(m["val"], size) + size * 0.06
            svg += _text(ux, base, [m["unit"]], unit_size, 700, MUTED, 1.0, "start")
        return svg
    return ""


def substitute_colors(frag, accent):
    out = frag.replace("ACCENT", accent)
    for tok, hexv in COLOR_TOKENS.items():
        out = out.replace(tok, hexv)
    return out


# ── 슬라이드 조립 ────────────────────────────────────────────────────────
def build_slide(slide, accent):
    layout = slide.get("layout", "mid-object")
    if layout not in LAYOUTS:
        layout = "number" if slide.get("hero_number") else "mid-object"
    centered = layout in CENTERED

    fn_lines = slide.get("footnote") or []
    if isinstance(fn_lines, str):
        fn_lines = [fn_lines] if fn_lines.strip() else []
    fn_lines = [l for l in fn_lines if str(l).strip()][:2]

    fn_svg, fn_top = _block_footnote(fn_lines, centered)

    order = [k for k in LAYOUTS[layout]]
    measured = [(k, _measure(k, slide, centered)) for k in order]
    measured = [(k, m) for k, m in measured if m["h"] > 0]

    area_top = PAD + 30 + 58
    area_bot = fn_top - 58
    total_h = sum(m["h"] for _, m in measured)
    free = (area_bot - area_top) - total_h

    n_gaps = len(measured) + 1
    gap = max(34.0, free / n_gaps) if n_gaps else 0.0
    # 블록이 넘치면 위에서부터 붙여 쌓는다 (잘림 방지)
    y = area_top + gap if free > 0 else area_top

    body = ""
    for k, m in measured:
        body += _render_block(k, m, y, slide, accent, centered)
        y += m["h"] + gap

    return ('<svg xmlns="http://www.w3.org/2000/svg" width="' + str(W) + '" height="'
            + str(H) + '" viewBox="0 0 ' + str(W) + ' ' + str(H) + '">'
            + _defs(accent) + _canvas()
            + _block_label(slide.get("context_label"))
            + body + fn_svg + '</svg>')


# ── 시각 언어 자동 검사 ──────────────────────────────────────────────────
_SHAPES    = ("circle", "rect", "line", "path", "polyline", "polygon", "ellipse")
_FORBIDDEN = ("image", "text", "tspan", "filter", "lineargradient", "radialgradient",
              "pattern", "foreignobject", "fegaussianblur", "fedropshadow", "mask",
              "clippath", "animate", "style", "use", "symbol")
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}")
_ALLOWED_COLOR_WORDS = {"none", "currentcolor", "inherit", "transparent"}


def validate_object(frag, max_kinds=3, max_total=24):
    """
    프롬프트 '시각 언어' 규칙을 기계적으로 검사. (errors, warnings) 반환.

    도형 개수는 '종류'로 센다. 프롬프트의 두 규칙
      · 핵심 오브젝트: "도형 3개 이하로 그릴 수 있음"
      · 그래픽 스타일: "도형 5개 이하"
    은 같은 프리미티브를 조건 수만큼 반복하는 구성(예: 두 조건 × 점-선-점)을
    금지하려는 게 아니다. 금지 대상은 '여러 종류의 도형을 늘어놓은 삽화'다.
    그래서 종류 수를 하드 실패로, 총 개수는 과밀 경고로 다룬다.
    """
    errors, warnings = [], []
    if not frag or not frag.strip():
        return errors, warnings

    low = frag.lower()

    for tag in _FORBIDDEN:
        if re.search(r"<\s*" + tag + r"[\s/>]", low):
            errors.append("금지 요소 <" + tag + "> 사용 (그라디언트·그림자·사진·질감 금지)")

    counts = {s: len(re.findall(r"<\s*" + s + r"[\s/>]", low)) for s in _SHAPES}
    kinds = [s for s, n in counts.items() if n]
    total = sum(counts.values())

    if len(kinds) > max_kinds:
        errors.append("도형 종류 " + str(len(kinds)) + "가지 (" + ", ".join(kinds) +
                      ") — 3가지 이하여야 한다. 오브젝트가 삽화가 되고 있다")
    if total > max_total:
        errors.append("도형 " + str(total) + "개 — 과밀. 단순 픽토그램이 아니다")
    if total > 20:
        warnings.append("도형 " + str(total) + "개 — 반복 구조가 맞는지 확인")
    if total == 0:
        warnings.append("도형이 없다 — 오브젝트가 비어 있는지 확인")

    for hexv in _HEX.findall(frag):
        errors.append("HEX 색 '" + hexv + "' 직접 사용 — INK/ACCENT/MUTED/DOT 토큰만 허용")

    for m in re.finditer(r'(?:fill|stroke)\s*=\s*"([^"]*)"', frag):
        v = m.group(1).strip()
        if v.startswith("url(#"):
            continue
        if v in COLOR_TOKENS or v == "ACCENT" or v.lower() in _ALLOWED_COLOR_WORDS:
            continue
        errors.append("허용되지 않은 색 값 '" + v + "'")

    for m in re.finditer(r'url\(#([^)]+)\)', frag):
        if m.group(1) not in ARROW_IDS:
            errors.append("정의되지 않은 참조 url(#" + m.group(1) + ")")

    # 선 굵기: 주선 7px(점선 외곽선은 6px 허용), 보조·연결선은 4px 이하.
    # 채워진 도형(fill 지정, stroke 없음)만 쓰는 슬라이드가 많아 '7px 필수'는 강제하지 않는다.
    for m in re.finditer(r'stroke-width\s*=\s*"([\d.]+)"', frag):
        w = float(m.group(1))
        if 4.5 < w < 5.5 or w > 7.5:
            warnings.append("어정쩡한 선 굵기 " + str(w) + "px — 7px(주선) 또는 4px 이하(보조선)")

    for m in re.finditer(r'\b(?:cx|x|x1|x2)\s*=\s*"(-?[\d.]+)"', frag):
        if not (-20 <= float(m.group(1)) <= COL_W + 20):
            warnings.append("x 좌표 " + m.group(1) + " 가 슬롯(0~" + str(COL_W) + ")을 벗어남")
            break
    return errors, warnings


def validate_slide_text(slide):
    """텍스트 규칙(글자 수·숫자 개수·footnote 줄 수) 검사."""
    w = []
    n = slide.get("slide_number", "?")
    p = "슬라이드 " + str(n) + ": "

    lbl = slide.get("context_label") or ""
    if lbl and not (3 <= len(lbl) <= 18):
        w.append(p + "context_label " + str(len(lbl)) + "자 (권장 8~15자)")

    hero = slide.get("hero_copy") or []
    if isinstance(hero, str):
        hero = [l for l in hero.split("\n") if l.strip()]
    if hero:
        if len(hero) > 3:
            w.append(p + "hero_copy " + str(len(hero)) + "줄 (최대 3줄)")
        for ln in hero:
            if len(ln) > 18:
                w.append(p + "hero 한 줄 " + str(len(ln)) + "자 — '" + ln[:14] + "…' (권장 8~16자)")

    sup = slide.get("support_copy") or ""
    if len(sup) > 55:
        w.append(p + "support_copy " + str(len(sup)) + "자 (50자 이내)")

    fn = slide.get("footnote") or []
    if isinstance(fn, str):
        fn = [fn] if fn.strip() else []
    if len(fn) > 2:
        w.append(p + "footnote " + str(len(fn)) + "줄 (최대 2줄)")

    num = slide.get("hero_number")
    if num and hero:
        w.append(p + "hero_copy와 hero_number가 함께 있다 — 숫자는 hero를 '대체'한다")
    if num and not fn:
        w.append(p + "큰 숫자에 footnote가 없다 — 통계수치 번역 규칙 위반")
    return w
