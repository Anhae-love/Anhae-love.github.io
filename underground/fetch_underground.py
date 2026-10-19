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
            seen[full] = {
                "id": full,
                "name": name,
                "owner": it["owner"]["login"],
                "url": it["html_url"],
                "desc": desc,
                "stars": stars,
                "delta": delta,
                "lang": it.get("language") or "—",
                "topics": topics[:6],
                "tags": classify(name, desc, topics),
                "pushed_at": it.get("pushed_at", ""),
                "heat": heat_score(stars, it.get("pushed_at", ""), delta),
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

    print(f"[완료] {len(items)}개 레포 → {FEED}")
    for it in items[:10]:
        fire = "🔥" * it["danger"]
        print(f"  #{it['rank']:<2} {fire:<6} {it['stars']:>7}★  {it['id']}")


if __name__ == "__main__":
    main()
