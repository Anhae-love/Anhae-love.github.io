# -*- coding: utf-8 -*-
"""
web/data/gallery.json 자동 생성 스크립트.

하는 일
  1) state/index.jsonl 을 읽어 각 콘텐츠의 메타(제목·카테고리·출처·강조색·폴더)를 가져온다.
  2) 각 output/<folder>/ 의 slide_1~6.png 를 web/assets/content/<id>/ 로 복사한다.
  3) 캡션은 content.json 의 "caption" → 없으면 caption.txt 에서 읽는다.
  4) 슬라이드 이미지가 하나도 없는 콘텐츠는 건너뛴다.
  5) 최신 날짜가 위로 오도록 정렬해 web/data/gallery.json 을 쓴다.

사용법 (프로젝트 루트 또는 web/ 어디서 실행해도 됨):
    python web/build_gallery.py
    python web/build_gallery.py --only-approved     # STATUS=approved 인 것만

데이터 원본(output/)은 읽기만 하고 수정하지 않는다.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# web/ 의 부모가 프로젝트 루트
WEB_DIR = Path(__file__).resolve().parent
ROOT = WEB_DIR.parent
OUTPUT_DIR = ROOT / "output"
INDEX_FILE = ROOT / "state" / "index.jsonl"
ASSETS_DIR = WEB_DIR / "assets" / "content"
GALLERY_JSON = WEB_DIR / "data" / "gallery.json"

SITE_META = {
    "title": "HCI 인스타 쇼케이스",
    "subtitle": "매일 새벽, 연구 한 편을 카드 여섯 장으로",
    "description": "HCI·인간-AI 상호작용 연구를 인스타그램 카드뉴스로 옮긴 아카이브입니다.",
}

DEFAULT_ACCENT = "#6C5CE7"


def read_index() -> list[dict]:
    """state/index.jsonl 을 리스트로. 없으면 빈 리스트."""
    if not INDEX_FILE.exists():
        print(f"[경고] 인덱스가 없습니다: {INDEX_FILE}", file=sys.stderr)
        return []
    rows = []
    for line in INDEX_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"[경고] 인덱스 한 줄 파싱 실패: {e}", file=sys.stderr)
    return rows


def derive_id(folder: str, date: str) -> str:
    """폴더명 앞 8자리(YYYYMMDD)를 id 로. 없으면 날짜에서 숫자만."""
    m = re.match(r"(\d{8})", folder or "")
    if m:
        return m.group(1)
    return re.sub(r"\D", "", date or "")[:8] or (folder or "item")


def find_slides(folder_path: Path) -> list[Path]:
    """slide_1.png ~ slide_6.png (존재하는 것만, 번호순)."""
    found = []
    for i in range(1, 7):
        p = folder_path / f"slide_{i}.png"
        if p.exists():
            found.append(p)
    return found


def read_caption(folder_path: Path) -> str:
    """content.json 의 caption 우선, 없으면 caption.txt."""
    cj = folder_path / "content.json"
    if cj.exists():
        try:
            data = json.loads(cj.read_text(encoding="utf-8"))
            cap = (data.get("caption") or "").strip()
            if cap:
                # 해시태그/출처 줄 이후는 갤러리 캡션에서 생략 (앞 두세 문단만)
                return cap
        except json.JSONDecodeError:
            pass
    ct = folder_path / "caption.txt"
    if ct.exists():
        return ct.read_text(encoding="utf-8").strip()
    return ""


def read_status(folder_path: Path) -> str:
    sp = folder_path / "STATUS"
    if sp.exists():
        return sp.read_text(encoding="utf-8").strip()
    return ""


def short_caption(caption: str, max_chars: int = 160) -> str:
    """갤러리 카드/라이트박스용으로 첫 문단만 추려 길이 제한."""
    if not caption:
        return ""
    first = caption.split("\n\n")[0].strip()
    if len(first) > max_chars:
        first = first[: max_chars - 1].rstrip() + "…"
    return first


def build(only_approved: bool = False) -> dict:
    index = read_index()
    items = []

    for row in index:
        folder = row.get("folder") or ""
        folder_path = OUTPUT_DIR / folder
        if not folder_path.is_dir():
            continue

        if only_approved and read_status(folder_path) != "approved":
            continue

        slides = find_slides(folder_path)
        if not slides:
            # 이미지가 없으면 갤러리에 넣지 않는다
            continue

        item_id = derive_id(folder, row.get("date", ""))
        dest_dir = ASSETS_DIR / item_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        rel_slides = []
        for src in slides:
            dst = dest_dir / src.name
            shutil.copy2(src, dst)
            rel_slides.append(f"assets/content/{item_id}/{src.name}")

        category = (row.get("weekday_category") or "").split("—")
        category = category[-1].strip() if len(category) > 1 else (row.get("weekday_category") or "")

        caption = short_caption(read_caption(folder_path))

        items.append({
            "id": item_id,
            "date": row.get("date", ""),
            "title": row.get("content_title") or row.get("title") or "(제목 없음)",
            "category": category,
            "source_title": row.get("source_title") or "",
            "source_url": row.get("source_url") or "",
            "accent": row.get("accent_color") or DEFAULT_ACCENT,
            "cover": rel_slides[0],
            "slides": rel_slides,
            "caption": caption,
        })

    # 최신순
    items.sort(key=lambda x: x.get("date", ""), reverse=True)

    return {"site": SITE_META, "items": items}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-approved", action="store_true",
                    help="STATUS 파일이 approved 인 콘텐츠만 포함")
    args = ap.parse_args()

    GALLERY_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = build(only_approved=args.only_approved)
    GALLERY_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[완료] {len(data['items'])}개 콘텐츠 → {GALLERY_JSON}")
    for it in data["items"]:
        print(f"   {it['date']}  {it['title']}  ({len(it['slides'])}장)")


if __name__ == "__main__":
    main()
