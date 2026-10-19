# -*- coding: utf-8 -*-
"""
facts.json 게이트 — 사실을 서술에서 떼어낸다.

왜 있는가
  2026-09-21 첫 실행에서 GPT 교차검증이 blocker 2건을 잡았고, 둘 다 원인이 같았다.
  원문은 "전체 시간 차이가 유의하지 않았다"였는데 카드는 "걸린 시간은 같았다"로 썼다.
  그것도 한 장이 아니라 3·4·5·6장에 걸쳐서. 모델은 매번 원문을 다시 읽는 게 아니라
  자기가 방금 쓴 문장을 참조하기 때문에, 한 번 굳은 프레임이 나머지에 그대로 얹힌다.

  그래서 조사와 카피 사이에 사실을 얼려두는 단계를 끼운다.
  카드에 등장하는 모든 숫자는 facts.json 안에 있어야 하고,
  null_result 로 기록된 발견이 있으면 "같았다" 계열 표현을 쓸 수 없다.

세 가지 검사
  1. 숫자 대조    — 카드·캡션의 모든 수치가 facts.json 에 있는가         (error)
  2. null_result  — 유의차 없음을 동일성으로 서술하고 있지 않은가        (error)
  3. scope 동반   — 제한된 범위의 수치에 그 범위가 함께 붙어 있는가      (warning)
"""

import json
import os
import re

KINDS = ["null_result", "difference", "expectation", "proportion",
         "count", "correlation", "descriptive"]

# 카드 본문에서 유의차 없음을 동일성으로 바꿔 쓰는 표현들
EQUALITY_PATTERNS = [
    r"같았다", r"같다", r"같은\s*시간", r"동일", r"똑같",
    r"차이가\s*없", r"차이\s*없", r"다르지\s*않았다", r"변함\s*없",
]
# 위 표현이 '오해를 바로잡는 문장' 안에 있으면 허용한다.
# 예: "같은 시간이 걸렸다는 뜻은 아니다" — 5장이 해야 할 바로 그 일이다.
NEGATION_PATTERNS = [r"아니", r"오해", r"뜻은\s*아", r"것은\s*아", r"않다는"]

# '것 같다 · 듯하다' 는 추측이지 동일성 주장이 아니다.
# "AI한테 시키면 금방 끝날 것 같다" 를 잡으면 안 된다.
HEDGE_BEFORE = re.compile(r"(?:것|듯|거)\s*$")

SAFE_ALTERNATIVES = "뚜렷하지 않았다 · 유의하지 않았다 · 차이를 확인하지 못했다"

# 숫자 추출 전에 걷어낼 것들
_URL = re.compile(r"https?://\S+")
_IDENT = re.compile(r"[A-Za-z][A-Za-z\-]*\d[\w\-]*")        # GPT-4o, CHI2026, arXiv ID
_STAT = re.compile(r"[pdrtFβηΔ]\s*[<>=≈]\s*[-−]?\.?\d+(?:\.\d+)?", re.I)
_CI = re.compile(r"(?:CI|신뢰구간)[^,.;]*", re.I)
_NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)")


def _scrub(text):
    """숫자 대조에서 제외할 토큰을 지운다."""
    t = _URL.sub(" ", text or "")
    t = _CI.sub(" ", t)
    t = _STAT.sub(" ", t)
    t = _IDENT.sub(" ", t)
    return t


def numbers_in(text):
    return [float(m.group(1)) for m in _NUM.finditer(_scrub(text))]


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


def _walk_numbers(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_numbers(v)


def allowed_numbers(facts):
    """facts.json 어디에든 등장하는 수치 전부. 문자열 안의 숫자도 포함한다."""
    got = set(_walk_numbers(facts))
    for s in _walk_strings(facts):
        got.update(numbers_in(s))
    for n in (facts.get("extra_allowed_numbers") or []):
        try:
            got.add(float(n["value"] if isinstance(n, dict) else n))
        except (TypeError, ValueError, KeyError):
            pass
    return got


def _matches(n, allowed):
    """반올림·절삭을 허용한다. 26.14 를 카드에 '26초'로 쓰는 건 정상이다."""
    if n in allowed:
        return True
    for a in allowed:
        if a == 0:
            continue
        for k in (0, 1, 2):
            if round(a, k) == n:
                return True
        if float(int(a)) == n:
            return True
    return False


# ── 구조 검사 ────────────────────────────────────────────────────────────
def check_structure(facts):
    e = []
    src = facts.get("source") or {}
    for k in ("title", "url", "access"):
        if not src.get(k):
            e.append("facts.source." + k + " 누락")

    design = facts.get("design") or {}
    if not design.get("type"):
        e.append("facts.design.type 누락 (실험 / 관찰 / 설문 …)")
    if not design.get("scope_limit"):
        e.append("facts.design.scope_limit 누락 — 연구가 다루지 않은 범위를 적어야 한다")
    if not (design.get("samples") or []):
        e.append("facts.design.samples 가 비어 있다")

    findings = facts.get("findings") or []
    if not findings:
        e.append("facts.findings 가 비어 있다")
    seen = set()
    for i, f in enumerate(findings, 1):
        tag = "facts.findings[" + str(i) + "]"
        fid = f.get("id")
        if not fid:
            e.append(tag + ".id 누락")
        elif fid in seen:
            e.append(tag + ".id 중복: " + str(fid))
        else:
            seen.add(fid)
        if f.get("kind") not in KINDS:
            e.append(tag + ".kind 가 '" + str(f.get("kind")) + "' — 허용: " + ", ".join(KINDS))
        if not f.get("claim"):
            e.append(tag + ".claim 누락")
        if not f.get("scope"):
            e.append(tag + ".scope 누락 — 이 결과가 어디까지 해당하는가")
        if not f.get("source_quote"):
            e.append(tag + ".source_quote 누락 — 원문 문장을 그대로 넣어야 한다")
        if f.get("kind") != "null_result" and f.get("value") is None:
            e.append(tag + ".value 가 비었다 (null_result 가 아니면 수치가 있어야 한다)")

    if not (facts.get("not_measured") or []):
        e.append("facts.not_measured 가 비어 있다 — 연구가 확인하지 않은 것을 적어야 한다")
    return e


# ── 1. 숫자 대조 ─────────────────────────────────────────────────────────
def _card_texts(content):
    """검사 대상 텍스트를 (위치, 문자열) 로 펼친다."""
    out = []
    for s in (content.get("slides") or []):
        n = str(s.get("slide_number", "?"))
        hero = s.get("hero_copy") or []
        if isinstance(hero, str):
            hero = [hero]
        for ln in hero:
            out.append(("슬라이드 " + n + " hero", ln))
        num = s.get("hero_number") or {}
        if num.get("value"):
            out.append(("슬라이드 " + n + " hero_number", str(num["value"])))
        if s.get("support_copy"):
            out.append(("슬라이드 " + n + " support", s["support_copy"]))
        fn = s.get("footnote") or []
        if isinstance(fn, str):
            fn = [fn]
        for ln in fn:
            out.append(("슬라이드 " + n + " footnote", ln))
    if content.get("caption"):
        for i, p in enumerate(content["caption"].split("\n\n"), 1):
            out.append(("캡션 " + str(i) + "문단", p))
    return out


def check_numbers(facts, content):
    allowed = allowed_numbers(facts)
    errors = []
    for where, text in _card_texts(content):
        for n in numbers_in(text):
            if not _matches(n, allowed):
                shown = str(int(n)) if n == int(n) else str(n)
                errors.append(
                    where + ": 숫자 " + shown + " 가 facts.json 에 없다 — '"
                    + text.strip()[:40] + "…'  (원문 대조 후 findings 에 넣거나, "
                    "파생값이면 extra_allowed_numbers 에 근거와 함께 적어라)")
    return errors


# ── 2. null_result 금칙어 ────────────────────────────────────────────────
def _is_corrective(text, pos):
    """해당 표현이 오해를 바로잡는 문장 안에 있는가."""
    tail = text[pos:pos + 40]
    return any(re.search(p, tail) for p in NEGATION_PATTERNS)


def _is_hedge(text, start):
    """'~것 같다' 처럼 추측을 나타내는 자리인가."""
    return bool(HEDGE_BEFORE.search(text[max(0, start - 4):start]))


def check_null_result(facts, content):
    nulls = [f for f in (facts.get("findings") or []) if f.get("kind") == "null_result"]
    if not nulls:
        return []
    errors = []
    for where, text in _card_texts(content):
        for pat in EQUALITY_PATTERNS:
            for m in re.finditer(pat, text):
                if _is_corrective(text, m.end()) or _is_hedge(text, m.start()):
                    continue
                errors.append(
                    where + ": '" + m.group(0) + "' — 이 연구에는 유의차 없음(null_result)이 "
                    "있다. 차이를 확인하지 못한 것을 같다고 쓰면 귀무가설을 입증으로 "
                    "뒤집는 것이다. 이렇게 쓴다: " + SAFE_ALTERNATIVES)
                break
    return errors


# ── 3. scope 동반 (경고) ─────────────────────────────────────────────────
_WORD = re.compile(r"[가-힣]{2,}")


def check_scope(facts, content):
    limited = []
    for f in (facts.get("findings") or []):
        scope = f.get("scope") or ""
        if f.get("value") is None or "전체" in scope or not scope:
            continue
        limited.append((f, set(_WORD.findall(scope))))
    if not limited:
        return []

    warnings = []
    for s in (content.get("slides") or []):
        n = str(s.get("slide_number", "?"))
        body = " ".join(filter(None, [
            " ".join(s.get("hero_copy") or []),
            (s.get("hero_number") or {}).get("value", ""),
            s.get("support_copy") or "",
        ]))
        fn = s.get("footnote") or []
        if isinstance(fn, str):
            fn = [fn]
        context = body + " " + " ".join(fn)

        for f, words in limited:
            try:
                val = float(f["value"])
            except (TypeError, ValueError):
                continue
            if not _matches_in(val, body):
                continue
            if not any(w in context for w in words):
                warnings.append(
                    "슬라이드 " + n + ": " + str(f["value"]) + " 는 '" + f["scope"]
                    + "' 에 한정된 값인데 그 범위가 슬라이드에 없다 — footnote 에 넣어라")
    return warnings


def _matches_in(val, text):
    return any(_matches(n, {val}) for n in numbers_in(text))


# ── 진입점 ───────────────────────────────────────────────────────────────
def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(facts, content):
    errors = check_structure(facts)
    errors += check_numbers(facts, content)
    errors += check_null_result(facts, content)
    return errors, check_scope(facts, content)


def find_facts(content_path):
    p = os.path.join(os.path.dirname(os.path.abspath(content_path)), "facts.json")
    return p if os.path.isfile(p) else None


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("사용: python facts.py <facts.json> <content.json>")
        sys.exit(1)
    fa, co = load(sys.argv[1]), load(sys.argv[2])
    errs, warns = validate(fa, co)
    for w in warns:
        print("[warn]  " + w)
    for e in errs:
        print("[error] " + e)
    print("오류 " + str(len(errs)) + "건, 경고 " + str(len(warns)) + "건")
    sys.exit(2 if errs else 0)
