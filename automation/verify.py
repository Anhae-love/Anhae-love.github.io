# -*- coding: utf-8 -*-
"""
Codex(GPT) 교차검증 게이트.

  python verify.py --dir <작업폴더> [--attempt N] [--timeout 900]

작업폴더에 content.json 이 있어야 한다.
검증에 필요한 부속 파일(rules.md, _verify_instructions.md, attempt.txt)은 이 스크립트가 깐다.
결과는 작업폴더에 verdict.json 으로 떨어진다.

종료 코드
   0  pass     — 카드 제작으로 진행
  10  revise   — verdict.json 의 issues[].fix 를 반영하고 재호출
  20  reject   — 주제 폐기
  30  codex 실행 실패 / 응답 파싱 실패
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RULES = os.path.join(ROOT, "HCI_인스타그램_콘텐츠_프롬프트_v3.md")
INSTR = os.path.join(HERE, "verify_prompt.md")
SCHEMA = os.path.join(HERE, "verify_schema.json")

KICKOFF = (
    "이 디렉터리의 `_verify_instructions.md` 를 먼저 읽어라. 그것이 너의 전체 지시다.\n"
    "그 지시에 따라 `content.json` 을 검증하고, 지정된 JSON 스키마에 맞는 JSON만 출력하라.\n"
    "파일은 수정하지 않는다."
)

EXIT = {"pass": 0, "revise": 10, "reject": 20}


def load_config():
    p = os.path.join(HERE, "config.json")
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("[verify] config.json 파싱 실패, 기본값으로 진행: " + str(e))
    return {}


def find_codex():
    """환경변수 → config.json → 표준 설치 경로 → PATH 순으로 찾는다."""
    env = os.environ.get("HCI_CODEX_PATH")
    if env and os.path.isfile(env):
        return env
    cfg = load_config().get("codex_path")
    if cfg and os.path.isfile(cfg):
        return cfg
    for base in (os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin"),
                 os.path.expanduser(r"~\.codex\.sandbox-bin")):
        if os.path.isdir(base):
            for dirpath, _, files in os.walk(base):
                if "codex.exe" in files:
                    return os.path.join(dirpath, "codex.exe")
    return shutil.which("codex")


def extract_json(text):
    """codex 응답에서 JSON 오브젝트를 건져낸다."""
    t = (text or "").strip()
    if not t:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.S)
    if fence:
        t = fence.group(1)
    try:
        return json.loads(t)
    except Exception:
        pass
    start = t.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            ch = t[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(t[start:i + 1])
                    except Exception:
                        break
        start = t.find("{", start + 1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--model", default=None)
    a = ap.parse_args()

    wd = os.path.abspath(a.dir)
    content = os.path.join(wd, "content.json")
    if not os.path.isfile(content):
        print("[verify] content.json 없음: " + content)
        sys.exit(30)
    if not os.path.isfile(os.path.join(wd, "facts.json")):
        print("[verify] facts.json 없음 — 사실 목록 없이는 원문 대조를 시킬 수 없다.")
        sys.exit(30)

    codex = find_codex()
    if not codex:
        print("[verify] codex.exe 를 찾을 수 없다. HCI_CODEX_PATH 환경변수로 지정하라.")
        sys.exit(30)

    shutil.copyfile(RULES, os.path.join(wd, "rules.md"))
    shutil.copyfile(INSTR, os.path.join(wd, "_verify_instructions.md"))
    with open(os.path.join(wd, "attempt.txt"), "w", encoding="utf-8") as f:
        f.write(str(a.attempt))

    # 재검증이면 직전 판정을 남겨 둔다 — 지적이 실제로 반영됐는지 대조시키기 위함
    verdict_path = os.path.join(wd, "verdict.json")
    if a.attempt > 1 and os.path.isfile(verdict_path):
        shutil.copyfile(verdict_path, os.path.join(wd, "previous_verdict.json"))

    raw = os.path.join(wd, "_verdict_raw.txt")
    cmd = [codex, "exec", KICKOFF,
           "-C", wd,
           "--sandbox", "read-only",
           "--skip-git-repo-check",
           "--output-schema", SCHEMA,
           "-o", raw]
    if a.model:
        cmd[2:2] = ["-m", a.model]

    print("[verify] codex 호출 (attempt " + str(a.attempt) + ") …")
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=a.timeout)
    except subprocess.TimeoutExpired:
        print("[verify] codex 타임아웃 (" + str(a.timeout) + "s)")
        sys.exit(30)
    dur = round(time.time() - t0, 1)

    with open(os.path.join(wd, "_codex_log.txt"), "w", encoding="utf-8") as f:
        f.write("$ " + " ".join(cmd) + "\n\n=== STDOUT ===\n" + (p.stdout or "")
                + "\n\n=== STDERR ===\n" + (p.stderr or ""))

    text = ""
    if os.path.isfile(raw):
        with open(raw, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    v = extract_json(text) or extract_json(p.stdout)

    if not v or "verdict" not in v:
        print("[verify] 응답에서 JSON 판정을 얻지 못했다 (" + str(dur) + "s). "
              "_codex_log.txt 확인")
        sys.exit(30)

    v["_attempt"] = a.attempt
    v["_elapsed_sec"] = dur
    with open(verdict_path, "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=2)

    issues = v.get("issues") or []
    blockers = [i for i in issues if i.get("severity") == "blocker"]
    fails = [k for k, x in (v.get("checklist") or {}).items() if x == "fail"]

    print("[verify] verdict=" + str(v["verdict"]) + "  issues=" + str(len(issues))
          + " (blocker " + str(len(blockers)) + ")  checklist_fail=" + str(len(fails))
          + "  " + str(dur) + "s")
    for i in issues:
        print("  - [" + str(i.get("severity")) + "/" + str(i.get("category")) + "] "
              + str(i.get("location")) + " :: " + str(i.get("problem"))[:160])
    if v.get("summary"):
        print("[verify] " + str(v["summary"])[:400])

    sys.exit(EXIT.get(v["verdict"], 30))


if __name__ == "__main__":
    main()
