# -*- coding: utf-8 -*-
"""
content.json → slide_1~6.svg + .png

사용
  python render.py <content.json>              # 렌더 + 검사
  python render.py <content.json> --check-only # 검사만 (렌더 안 함)
  python render.py <content.json> --out DIR

종료 코드
  0  성공
  2  시각 언어 / 텍스트 규칙 위반 (errors) — 렌더하지 않음
  3  resvg 실패
  4  content.json 구조 문제
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import facts as facts_mod  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESVG = os.path.join(HERE, "bin", "resvg.exe")

REQUIRED_TOP = ["date", "weekday_category", "content_title", "source_title",
                "source_url", "object_name", "accent_color", "slides",
                "caption", "hashtags"]
ROLES = ["등장", "작동", "분할", "결과", "오해 방지", "개방"]


def fail(code, msg):
    print("[render] FAIL: " + msg)
    sys.exit(code)


def check_structure(c):
    errs = []
    for k in REQUIRED_TOP:
        if k not in c or c[k] in (None, "", []):
            errs.append("최상위 필드 누락: " + k)

    acc = str(c.get("accent_color", ""))
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", acc):
        errs.append("accent_color 가 #RRGGBB 형식이 아니다: '" + acc + "'")

    slides = c.get("slides") or []
    if len(slides) != 6:
        errs.append("슬라이드가 " + str(len(slides)) + "장 — 6장이어야 한다")

    for i, s in enumerate(slides, 1):
        if s.get("slide_number") != i:
            errs.append("슬라이드 " + str(i) + ": slide_number 불일치")
        role = (s.get("narrative_role") or "").strip()
        if i <= len(ROLES) and role and ROLES[i - 1] not in role:
            errs.append("슬라이드 " + str(i) + ": narrative_role '" + role +
                        "' — 6단 서사는 " + ROLES[i - 1] + " 자리")
        if not (s.get("hero_copy") or s.get("hero_number")):
            errs.append("슬라이드 " + str(i) + ": hero_copy 도 hero_number 도 없다")

    tags = c.get("hashtags") or []
    if not (8 <= len(tags) <= 12):
        errs.append("해시태그 " + str(len(tags)) + "개 (8~12개)")

    cap = c.get("caption") or ""
    if not (450 <= len(cap) <= 780):
        errs.append("캡션 " + str(len(cap)) + "자 (500~700자 권장, 450~780 허용)")

    if c.get("is_preprint") and "프리프린트" not in cap:
        errs.append("프리프린트인데 캡션에 고지가 없다")

    alts = c.get("alt_texts") or []
    if len(alts) != 6:
        errs.append("대체 텍스트 " + str(len(alts)) + "개 — 슬라이드마다 1개")

    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("--out", default=None)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--no-facts", action="store_true",
                    help="facts.json 게이트를 건너뛴다. 옛 자료를 다시 굽는 경우에만 쓴다.")
    a = ap.parse_args()

    if not os.path.isfile(a.content):
        fail(4, "content.json 을 찾을 수 없다: " + a.content)
    with open(a.content, "r", encoding="utf-8") as f:
        try:
            c = json.load(f)
        except Exception as e:
            fail(4, "JSON 파싱 실패: " + str(e))

    out = a.out or os.path.dirname(os.path.abspath(a.content))
    os.makedirs(out, exist_ok=True)

    errors = check_structure(c)
    warnings = []
    accent = c.get("accent_color", "#2E6F5E")

    # ── facts.json 게이트 ───────────────────────────────────────────────
    # 카드의 모든 수치가 원문에서 확인된 사실 목록 안에 있어야 하고,
    # 유의차 없음을 동일성으로 서술해서는 안 된다.
    if not a.no_facts:
        fpath = facts_mod.find_facts(a.content)
        if not fpath:
            fail(2, "facts.json 이 없다. content.json 과 같은 폴더에 있어야 한다.\n"
                    "        조사 직후, 카피를 쓰기 전에 만든다. "
                    "형식은 automation/content_contract.md 의 'facts.json' 절을 봐라.\n"
                    "        옛 자료를 다시 굽는 거라면 --no-facts 를 붙여라.")
        try:
            fa = facts_mod.load(fpath)
        except Exception as e:
            fail(2, "facts.json 파싱 실패: " + str(e))
        fe, fw = facts_mod.validate(fa, c)
        errors += fe
        warnings += fw
    else:
        warnings.append("facts.json 게이트를 건너뛰었다 (--no-facts)")

    for s in (c.get("slides") or []):
        n = s.get("slide_number", "?")
        e, w = engine.validate_object(s.get("object_svg") or "")
        errors += ["슬라이드 " + str(n) + ": " + x for x in e]
        warnings += ["슬라이드 " + str(n) + ": " + x for x in w]
        warnings += engine.validate_slide_text(s)

    report = {"errors": errors, "warnings": warnings}
    with open(os.path.join(out, "render_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    for w in warnings:
        print("[warn]  " + w)
    for e in errors:
        print("[error] " + e)

    if errors:
        fail(2, str(len(errors)) + "건의 규칙 위반 — 렌더 중단. render_report.json 확인")
    if a.check_only:
        print("[render] 검사 통과 (경고 " + str(len(warnings)) + "건)")
        return

    if not os.path.isfile(RESVG):
        fail(3, "resvg.exe 없음: " + RESVG)

    made = []
    for s in c["slides"]:
        n = s["slide_number"]
        svg_path = os.path.join(out, "slide_" + str(n) + ".svg")
        png_path = os.path.join(out, "slide_" + str(n) + ".png")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(engine.build_slide(s, accent))
        r = subprocess.run(
            [RESVG, svg_path, png_path,
             "--width", str(engine.W), "--height", str(engine.H)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not os.path.isfile(png_path):
            fail(3, "resvg 실패 (slide " + str(n) + "): " + (r.stderr or "")[:400])
        made.append(os.path.basename(png_path))

    with open(os.path.join(out, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(c.get("caption", "").strip() + "\n\n" +
                " ".join(c.get("hashtags", [])) + "\n")

    with open(os.path.join(out, "alt_texts.txt"), "w", encoding="utf-8") as f:
        for i, t in enumerate(c.get("alt_texts", []), 1):
            f.write(str(i) + ". " + str(t) + "\n")

    print("[render] OK — " + str(len(made)) + "장, 경고 " + str(len(warnings)) + "건 → " + out)


if __name__ == "__main__":
    main()
