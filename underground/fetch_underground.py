# -*- coding: utf-8 -*-
"""
THE UNDERGROUND — 데이터 수집기
GitHub 에서 AI 관련 레포를 긁어와 랭킹 데이터(data/feed.json)를 만든다.

하는 일
  1) 여러 검색어로 GitHub Search API 를 때려 AI 프롬프트/도구/에이전트 레포를 모은다.
  2) 스타·최근 업데이트·설명으로 "과감함(heat)" 점수를 매긴다.
  3) 목적 태그(coding/writing/image/agent/local/free ...)를 자동으로 붙인다.
  4) 지난 스냅샷(data/_prev_stars.json)과 비교해 '오늘의 떡상' 증감을 계산한다.
  5) data/feed.json 과 다음 비교용 스냅샷을 쓴다.

인증
  토큰 없이도 돌지만 시간당 호출이 적다(미인증 10회/분 수준).
  환경변수 GITHUB_TOKEN 이 있으면 자동으로 쓴다(시간당 5000회).
    PowerShell:  $env:GITHUB_TOKEN="ghp_..."; python underground/fetch_underground.py

합법 라인
  유료 서비스 우회·크랙·토큰 탈취·약관 회피성 레포는 BLOCKLIST 로 걸러낸다.
  재미는 '의외성'에서 나오지 '불법'에서 나오지 않는다.
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FEED = DATA / "feed.json"
PREV = DATA / "_prev_stars.json"

API = "https://api.github.com/search/repositories"

# 과감하지만 합법인 것들을 끌어오는 검색어
QUERIES = [
    "awesome prompts",
    "prompt engineering",
    "system prompt leaked",      # 공개 분석된 시스템 프롬프트 (유출 아카이브는 공개 큐레이션)
    "local llm",                 # 토큰 걱정 없이 — 합법적으로 무제한
    "llm router",                # 알아서 모델 바꿔주는 류
    "ai agent framework",
    "jailbreak prompt",          # 아래 BLOCKLIST 로 위험한 건 거른다
    "ai automation",
]

# 합법 라인: 아래 패턴이 이름/설명에 있으면 제외
BLOCKLIST = re.compile(
    r"(crack|cracked|keygen|nulled|piracy|pirated|license[\s\-]?bypass|"
    r"token[\s\-]?steal|cookie[\s\-]?steal|account[\s\-]?generator|"
    r"paypal|carding|ddos|botnet|ransomware|malware|stealer|rat[\s\-]?tool|"
    r"무료.?계정|크랙|우회.?토큰)",
    re.IGNORECASE,
)

# 목적 태그 자동 분류 규칙 (키워드 → 태그)
TAG_RULES = {
    "coding": ["code", "coding", "developer", "copilot", "programming", "ide"],
    "writing": ["write", "writing", "essay", "content", "copywriting"],
    "image": ["image", "diffusion", "stable", "art", "photo", "vision"],
    "agent": ["agent", "autonomous", "autogpt", "workflow", "orchestr"],
    "prompt": ["prompt"],
    "local": ["local", "ollama", "llama.cpp", "offline", "self-host", "selfhost"],
    "free": ["free", "open-source", "opensource", "unlimited"],
    "chat": ["chat", "assistant", "chatbot", "conversation"],
}


def gh_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "the-underground-fetcher",
    })
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def classify(name: str, desc: str, topics: list[str]) -> list[str]:
    blob = " ".join([name or "", desc or "", " ".join(topics or [])]).lower()
    tags = [tag for tag, kws in TAG_RULES.items() if any(k in blob for k in kws)]
    return tags or ["misc"]


# "이게 뭐 하는 거냐"를 한국어 한 줄로. desc/topics 의 키워드를 사람 말로 바꾼다.
# 완벽한 번역이 아니라, 비개발자가 '아 이런 거구나' 하도록 돕는 요약.
KIND_RULES = [
    (["awesome", "curated", "list of", "collection"], "📚 엄선된 모음집 — 관련 도구·자료를 한곳에 정리"),
    (["ollama", "run llm", "local", "offline", "self-host", "selfhost", "llama.cpp"],
     "💻 내 컴퓨터에서 AI 모델을 직접 돌리는 도구 (토큰 비용 없음)"),
    (["agent", "autonomous", "autogpt", "orchestr", "multi-agent"],
     "🤖 스스로 작업을 수행하는 AI 에이전트"),
    (["prompt", "system prompt", "jailbreak"],
     "✍️ 프롬프트 모음·기법 — AI에게 잘 말 거는 법"),
    (["rag", "retrieval", "vector", "embedding", "knowledge base"],
     "📖 내 문서를 AI가 참고해 답하게 만드는 도구 (RAG)"),
    (["image", "diffusion", "stable diffusion", "text-to-image", "art", "photo"],
     "🎨 이미지·그림을 만들어내는 AI"),
    (["chat", "chatbot", "assistant", "conversation"],
     "💬 대화형 AI·챗봇을 만들거나 쓰는 도구"),
    (["code", "coding", "copilot", "developer", "ide", "programming"],
     "⌨️ 코딩을 돕거나 자동화하는 AI 도구"),
    (["api", "sdk", "client", "wrapper", "library", "framework"],
     "🧩 개발자가 가져다 쓰는 AI 라이브러리·프레임워크"),
    (["ui", "gui", "web ui", "interface", "frontend"],
     "🖥️ AI를 쓰기 쉽게 만든 화면·인터페이스"),
    (["tutorial", "course", "learn", "roadmap", "guide", "book"],
     "🎓 배우기 위한 튜토리얼·로드맵·강의 자료"),
    (["workflow", "automation", "automate", "no-code", "nocode"],
     "⚙️ 반복 작업을 자동화하는 도구"),
]


def summarize_kr(name: str, desc: str, topics: list[str]) -> str:
    blob = " ".join([name or "", desc or "", " ".join(topics or [])]).lower()
    for kws, line in KIND_RULES:
        if any(k in blob for k in kws):
            return line
    return "🧰 AI 관련 오픈소스 프로젝트"


def install_guide(name: str, desc: str, topics: list[str], lang: str, owner: str) -> dict:
    """
    레포 종류를 추론해 '공략집' 단계를 만든다.
    브라우저에서 진짜 자동설치는 불가능/위험하므로:
      - 받는 명령어를 '원클릭 복사'로 제공
      - GitHub 공식 ZIP 다운로드 링크 제공
    실제 설치법은 레포마다 다르니 '가장 그럴듯한' 방법을 제시하고,
    정확한 건 README 확인하라고 안내한다.
    """
    blob = " ".join([name or "", desc or "", " ".join(topics or [])]).lower()
    lang_l = (lang or "").lower()
    repo = f"{owner}/{name}"
    clone = f"git clone https://github.com/{repo}.git"
    zip_url = f"https://github.com/{repo}/archive/refs/heads/main.zip"

    # 설치 유형 추론
    if any(k in blob for k in ["awesome", "curated", "list of", "roadmap", "collection", "cheatsheet"]):
        kind = "read"
        cmd = None
        steps = [
            {"icon": "📖", "title": "읽기 자료예요", "body": "설치할 게 아니라, 링크·자료가 정리된 모음집이에요. 그냥 열어서 필요한 걸 골라 쓰면 됩니다."},
            {"icon": "🔖", "title": "북마크 추천", "body": "자주 볼 거면 즐겨찾기 해두세요. 설치/실행 과정은 없어요."},
        ]
    elif "python" in lang_l or any(k in blob for k in ["pip install", "pypi"]):
        kind = "pip"
        cmd = f"pip install {name}"
        steps = [
            {"icon": "⬇️", "title": "받기", "body": "아래 명령어를 복사해서 터미널(명령 프롬프트)에 붙여넣고 엔터. 파이썬이 깔려 있어야 해요."},
            {"icon": "📂", "title": "확인", "body": "에러가 나면 README에 적힌 정확한 패키지 이름/추가 단계를 확인하세요. (추정 명령어예요)"},
            {"icon": "🚀", "title": "실행", "body": "README의 'Usage' 또는 'Quick start' 예제를 그대로 따라 하면 첫 실행 끝."},
        ]
    elif any(k in blob for k in ["npm", "node", "javascript", "typescript"]) or lang_l in ("javascript", "typescript"):
        kind = "npm"
        cmd = f"npm install {name}"
        steps = [
            {"icon": "⬇️", "title": "받기", "body": "아래 명령어를 복사해 터미널에 붙여넣기. Node.js가 깔려 있어야 해요."},
            {"icon": "📂", "title": "확인", "body": "정확한 패키지명은 README를 확인하세요. (추정 명령어예요)"},
            {"icon": "🚀", "title": "실행", "body": "README의 예제 코드를 복사해 돌려보면 됩니다."},
        ]
    elif "docker" in blob:
        kind = "docker"
        cmd = f"docker run {owner}/{name}"
        steps = [
            {"icon": "🐳", "title": "받기", "body": "Docker가 깔려 있다면 아래 명령으로 바로 실행돼요."},
            {"icon": "📂", "title": "확인", "body": "정확한 이미지 이름/옵션은 README를 보세요."},
        ]
    else:
        kind = "clone"
        cmd = clone
        steps = [
            {"icon": "⬇️", "title": "받기 (복제)", "body": "아래 git 명령으로 통째로 받거나, ZIP 다운로드 버튼을 눌러 압축으로 받으세요."},
            {"icon": "📂", "title": "열기", "body": "받은 폴더를 열고 README 파일을 먼저 읽으세요. 설치·실행법이 거기 있어요."},
            {"icon": "🚀", "title": "실행", "body": "README의 'Getting started' 단계를 따라 하면 됩니다."},
        ]

    return {"kind": kind, "cmd": cmd, "zip": zip_url, "steps": steps}


def why_hot(stars: int, delta: int, pushed_at: str, topics: list[str]) -> list[str]:
    """왜 랭킹에 올랐는지 사람이 읽을 배지들."""
    badges = []
    if stars >= 100000:
        badges.append("🏆 전설급 스타 (10만+)")
    elif stars >= 30000:
        badges.append("⭐ 초인기 (3만+)")
    elif stars >= 5000:
        badges.append("👍 검증된 인기")
    if delta >= 500:
        badges.append(f"🚀 지금 폭주 중 (+{delta:,})")
    elif delta > 0:
        badges.append(f"📈 상승 중 (+{delta:,})")
    try:
        pushed = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - pushed).days
        if days <= 7:
            badges.append("🔥 이번 주에도 업데이트")
        elif days <= 30:
            badges.append("🟢 활발히 관리 중")
        elif days > 365:
            badges.append("🕸️ 1년+ 조용함")
    except Exception:
        pass
    if "awesome-list" in (topics or []) or "awesome" in (topics or []):
        badges.append("📚 레퍼런스로 자주 공유됨")
    return badges or ["👀 뜨고 있음"]


def heat_score(stars: int, pushed_at: str, delta: int) -> int:
    """과감함/화제성 점수. 스타 + 최근성 + 급상승 보정."""
    base = stars
    try:
        pushed = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - pushed).days
        recency = max(0, 400 - days * 4)       # 최근일수록 가점
    except Exception:
        recency = 0
    surge = max(0, delta) * 3                    # 떡상 가점
    return int(base + recency + surge)


def load_prev() -> dict:
    if PREV.exists():
        try:
            return json.loads(PREV.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def main():
    prev = load_prev()
    seen: dict[str, dict] = {}

    for q in QUERIES:
        qs = urllib.parse.urlencode({
            "q": f"{q} in:name,description,readme",
            "sort": "stars",
            "order": "desc",
            "per_page": 20,
        })
        url = f"{API}?{qs}"
        try:
            res = gh_get(url)
        except Exception as e:
            print(f"[경고] 검색 실패 '{q}': {e}", file=sys.stderr)
            time.sleep(2)
            continue

        for it in res.get("items", []):
            full = it["full_name"]
            name = it["name"]
            desc = it.get("description") or ""
            topics = it.get("topics") or []

            if BLOCKLIST.search(f"{name} {desc} {full}"):
                continue   # 합법 라인에서 제외

            stars = it.get("stargazers_count", 0)
            delta = stars - prev.get(full, stars)   # 지난 스냅샷 대비 증감

            if full in seen:
                continue
            pushed = it.get("pushed_at", "")
            seen[full] = {
                "id": full,
                "name": name,
                "owner": it["owner"]["login"],
                "url": it["html_url"],
                "desc": desc,
                "summary_kr": summarize_kr(name, desc, topics),
                "why": why_hot(stars, delta, pushed, topics),
                "guide": install_guide(name, desc, topics, it.get("language") or "", it["owner"]["login"]),
                "stars": stars,
                "delta": delta,
                "lang": it.get("language") or "—",
                "topics": topics[:6],
                "tags": classify(name, desc, topics),
                "pushed_at": pushed,
                "heat": heat_score(stars, pushed, delta),
            }
        time.sleep(1)   # API 매너

    items = sorted(seen.values(), key=lambda x: x["heat"], reverse=True)

    # 랭크·뱃지 부여
    for i, it in enumerate(items):
        it["rank"] = i + 1
        it["danger"] = min(5, 1 + it["heat"] // 8000)   # 🔥 등급(합법인데 과감함 지수)

    feed = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "top_surge": sorted(items, key=lambda x: x["delta"], reverse=True)[:5],
        "items": items,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    PREV.write_text(json.dumps({it["id"]: it["stars"] for it in items},
                               ensure_ascii=False, indent=0), encoding="utf-8")

    print(f"[wan-ryo] {len(items)} repos -> {FEED}")
    for it in items[:10]:
        fire = "*" * it["danger"]
        line = f"  #{it['rank']:<2} {fire:<6} {it['stars']:>7}star  {it['id']}"
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("ascii", "replace").decode("ascii"))


if __name__ == "__main__":
    main()
