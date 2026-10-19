# HCI 인스타 쇼케이스 (web)

`output/`에 쌓인 인스타 카드뉴스를 GDWEB 수상작 스타일 갤러리로 보여주는 정적 웹.

## 구조

```
web/
  index.html          갤러리 페이지
  styles.css          스타일 (다크, 반응형, 라이트박스)
  app.js              데이터 로드 + 그리드 + 라이트박스
  build_gallery.py    output/ → data/gallery.json 생성 스크립트
  data/gallery.json   (생성물) 갤러리 데이터
  assets/content/     (생성물) 각 콘텐츠의 slide_*.png 복사본
  assets/cover-*.svg  더미 커버 (초기 디자인용, 지금은 미사용)
```

## 콘텐츠 다시 빌드

`output/`에 새 콘텐츠가 쌓이거나 `state/index.jsonl`이 바뀌면 다시 실행:

```bash
python web/build_gallery.py                # 전체
python web/build_gallery.py --only-approved # STATUS=approved 인 것만
```

스크립트는 `state/index.jsonl`을 읽어 각 폴더의 `slide_1~6.png`를
`web/assets/content/<날짜>/`로 복사하고 `data/gallery.json`을 만든다.
`output/` 원본은 읽기만 한다.

## 로컬에서 보기

`fetch`로 JSON을 읽으므로 `file://`이 아니라 로컬 서버가 필요하다.

```bash
cd web
python -m http.server 8777
# http://localhost:8777
```

## 배포 (AWS 프리티어)

S3 정적 호스팅 + CloudFront를 염두에 두고 만들었다. 배포 시 올릴 것:
`index.html`, `styles.css`, `app.js`, `data/`, `assets/`.
