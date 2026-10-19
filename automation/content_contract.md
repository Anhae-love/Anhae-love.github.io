# facts.json · content.json 계약

`HCI_인스타그램_콘텐츠_프롬프트_v3.md`가 **무엇을 쓸지**를 정한다면,
이 문서는 그 결과를 **기계가 그릴 수 있는 형태**로 어떻게 적을지를 정한다.

파일은 둘이고 순서가 있다. **`facts.json`을 먼저 쓰고, 그다음 `content.json`을 쓴다.**

---

# facts.json — 사실을 얼리는 파일

## 왜 있는가

2026-09-21 첫 실행에서 GPT 교차검증이 blocker 2건을 잡았다. 둘 다 원인이 같았다.

원문은 *"전체 시간 차이가 유의하지 않았다"* 였는데 카드는 **"걸린 시간은 같았다"** 로 썼다.
그것도 한 장이 아니라 3·4·5·6장에 걸쳐서. 유의차 없음을 동일성 입증으로 뒤집은 것이고,
어려운 과제에서는 실제로 26.14초 빨랐으니 자기모순이기도 했다.

모델은 매번 원문을 다시 읽지 않는다. **자기가 방금 쓴 문장을 참조한다.**
그래서 3장에서 굳은 프레임이 나머지에 그대로 얹힌다.
조사와 카피 사이에 사실을 얼려두는 단계가 그래서 있다.

## 형식

```json
{
  "source": {
    "title": "원문 제목 그대로",
    "url": "실제로 열리는 URL",
    "access": "원문 확인 | 초록만 확인",
    "is_preprint": false,
    "venue_checked": "어디서 게재 상태를 확인했는지"
  },

  "design": {
    "type": "사전등록 실험 | 무작위 실험 | 관찰 연구 | 설문 | 단면 조사 …",
    "assignment": "무작위 배정 | 자기선택 | 해당 없음",
    "n_total": 1237,
    "samples": [
      { "label": "예상 표본", "n": 401,
        "note": "조건 배정 방식, 다른 표본과의 중복 여부" }
    ],
    "scope_limit": "연구가 다룬 범위의 경계. 과제 종류·참가자·도구·기간"
  },

  "findings": [
    { "id": "F1",
      "kind": "null_result",
      "claim": "전체 과제에서 완료 시간 차이가 유의하지 않았다",
      "value": null,
      "scope": "24개 과제 합산 전체 분석",
      "source_quote": "원문 문장 그대로" }
  ],

  "extra_allowed_numbers": [
    { "value": 1, "note": "68.5초를 카드에서 '1분 넘게'로 표현한다" }
  ],

  "not_measured": [ "연구가 확인하지 않은 것들" ]
}
```

## `kind` — 이 필드가 카드 표현을 결정한다

| 값 | 언제 |
|---|---|
| `null_result` | **유의한 차이를 발견하지 못했다.** 같다는 뜻이 아니다 |
| `difference` | 조건 간 차이가 확인됐다 |
| `expectation` | 참가자의 예상·추정치 (실제 측정값이 아니다) |
| `proportion` | 비율·퍼센트 |
| `count` | 개수 |
| `correlation` | 함께 나타난 관계. **인과가 아니다** |
| `descriptive` | 기술 통계 |

`null_result`가 하나라도 있으면 `render.py`가 카드 본문의
**"같았다 · 동일 · 똑같 · 차이가 없었다 · 다르지 않았다"를 막는다.**
`뚜렷하지 않았다 · 유의하지 않았다 · 차이를 확인하지 못했다`로 쓴다.

단, **오해를 바로잡는 문장 안에서는 허용된다.**
5장이 해야 할 일이 정확히 그것이기 때문이다.

> ✅ `"같은 시간이 걸렸다는 뜻은 아니다"` — 통과
> ❌ `"걸린 시간은 같았다"` — 차단

## `source_quote` — 지어내지 마라

원문에 **실제로 있는 문장**이어야 한다. 기억으로 쓰지 마라.
GPT 교차검증이 이걸 원문과 대조하고, 지어낸 인용은 blocker로 잡는다.
이 파이프라인에서 가장 중대한 위반이다.

## `scope` — 어디까지 해당하는가

전체 분석인가 하위 조건인가. 이게 비어 있으면 구조 검사에서 막힌다.
제한된 범위의 수치를 카드에 올리면 같은 슬라이드 footnote에 그 범위가 있어야 한다
(없으면 경고).

## `extra_allowed_numbers` — 파생값의 도피처

카드의 모든 숫자는 `facts.json` 안에 있어야 한다. 반올림·절삭은 자동 허용된다
(`26.14` → 카드의 `26초`는 통과). 하지만 단위를 바꾼 파생값은 그렇지 않다.

`68.5초`를 `1분 넘게`로 쓰면 `1`이 어디에도 없다.
그럴 때만 여기에 **근거와 함께** 적는다. 근거 없는 숫자를 끼워 넣는 용도가 아니다.

## 검사

```bash
python automation/facts.py <facts.json> <content.json>
```

`render.py`가 렌더 직전에 같은 검사를 돌린다. 따로 부를 일은 드물다.

---

# content.json 계약

렌더 엔진(`engine.py`)이 판형·배경·도트그리드·여백·타이포·footnote 위치를 전부 책임진다.
너는 **문구**와 **오브젝트 도형**만 쓴다. 좌표로 글자를 배치하려 하지 마라.

작동하는 실제 예시는 `sample_content.json`에 있다. **쓰기 전에 반드시 열어봐라.**

---

## 최상위 필드

| 필드 | 형 | 설명 |
|---|---|---|
| `date` | `"YYYY-MM-DD"` | 오늘 |
| `weekday_category` | string | `"화 — 챗봇, 의인화, 감정, 사회적 상호작용"` 형식. v3 요일표 그대로 |
| `content_title` | string | 폴더명에 쓰인다. 파일명에 못 쓰는 문자 금지 |
| `source_title` | string | **원문 제목 그대로.** 번역하지 않는다 |
| `source_url` | string | 실제로 열리는 URL. 확인 못 했으면 추측해서 적지 않는다 |
| `source_access_status` | string | `"원문 확인"` / `"초록만 확인"` / `"원문 접근 실패"` |
| `is_preprint` | bool | true면 캡션에 "아직 동료평가를 거치지 않은 프리프린트입니다" 필수 |
| `selection_sentence` | string | v3의 "이 연구는 ~을 살펴봤고, ~이 함께 나타나는 경향을 발견했다. 하지만 ~까지 확인한 것은 아니다." 완성문 |
| `candidates` | array | 검토한 후보 8건 이상. `{title, url, reject_reason}` |
| `object_name` | string | 핵심 오브젝트. `state/index.jsonl`의 과거 오브젝트와 겹치면 안 된다 |
| `object_rationale` | string | 왜 이 오브젝트가 이 연구에서 직접 도출되는가 |
| `accent_color` | `"#RRGGBB"` | 게시물당 1개 |
| `slides` | array[6] | 아래 참조 |
| `caption` | string | 500~700자. `\n\n`로 문단 구분 |
| `hashtags` | array[8~12] | `#`포함 |
| `alt_texts` | array[6] | 슬라이드별 대체 텍스트 |
| `verification_items` | array | 원문과 대조한 항목 |
| `human_check_items` | array | 게시 전 사람이 볼 것 |
| `status` | string | 항상 `"awaiting_human_review"` |

---

## 슬라이드 필드

```json
{
  "slide_number": 1,
  "narrative_role": "등장",
  "context_label": "챗봇을 켜기 전",
  "hero_copy": ["나는 나를", "이렇게 생각한다"],
  "hero_number": null,
  "support_copy": "내향적인 편. 성실한 편. 그런 감각.",
  "footnote": [],
  "object_state": "검은 점 하나. 홀로, 중립적으로 놓여 있다.",
  "layout": "top-object",
  "object_height": 250,
  "object_svg": "<circle cx=\"208\" cy=\"110\" r=\"30\" fill=\"INK\"/>",
  "object_labels": [{ "x": 208, "y": 182, "text": "나", "color": "MUTED" }]
}
```

`narrative_role`은 순서대로 고정이다:
**등장 · 작동 · 분할 · 결과 · 오해 방지 · 개방**

`hero_copy`는 **줄 배열**이다. 줄바꿈 지점이 곧 디자인이다. 한 줄 8~16자.
글자 크기는 엔진이 줄 길이에서 자동 역산한다. 억지로 키우려 줄을 쪼개지 마라.

`footnote`는 최대 2줄. 각 원소가 한 줄이다. 줄바꿈 문자를 쓰지 마라.

### `layout` 네 가지

| 값 | 배치 | 언제 |
|---|---|---|
| `top-object` | 오브젝트 위 → 카피 아래 | 1장 등장. 오브젝트가 먼저 눈에 들어와야 할 때 |
| `mid-object` | 카피 위 → 오브젝트 가운데 → 보조 아래 | 기본값. 2~5장 대부분 |
| `center-object` | 전부 중앙정렬 | 6장 개방. 수렴·확산처럼 대칭 구도일 때 |
| `number` | 큰 숫자가 화면을 지배 | `hero_number`를 쓸 때만 |

### `hero_number` — 숫자가 곧 그래픽

```json
"hero_number": { "value": "1.88", "unit": "배" }
```

쓰는 순간 `hero_copy`는 `[]`로 비운다. **숫자가 hero를 대체한다.**
단위는 엔진이 자동으로 40% 작게 조판한다.
**`footnote`가 반드시 따라붙는다.** 없으면 렌더가 막힌다.

오즈비를 "확률이 N배" / "N배 더 많은 사람"으로 쓰지 않는다.
원문에 이해하기 쉬운 실제 비율이 있으면 그걸 우선 쓴다.

한 슬라이드에 숫자는 하나. 결과 수치가 여러 개면 **가장 반직관적인 것 하나만.**

---

## `object_svg` — 오브젝트 도형

### 좌표계

원점 좌상단, **폭 896 고정**, 높이는 `object_height`(기본 380).
엔진이 알아서 카드 안의 제자리에 얹는다. 1080×1350 절대좌표를 쓰지 마라.

가로 중심은 `x = 448`. 좌우 대칭을 맞추면 카드가 안정된다.

### 색 — 토큰만 쓴다

`INK` · `ACCENT` · `MUTED` · `DOT` · `BG`

```xml
<circle cx="208" cy="100" r="30" fill="INK"/>
<circle cx="688" cy="100" r="30" fill="ACCENT"/>
```

**HEX를 직접 쓰면 렌더가 막힌다.** 엔진이 `accent_color`로 치환한다.
이 규칙이 "강조색 게시물당 1개"를 기계적으로 보장한다.

### 허용

`circle` `rect` `line` `path` `polyline` `polygon` `ellipse` `g`

- **도형 종류는 3가지 이하.** 개수가 아니라 종류다.
  같은 프리미티브를 조건 수만큼 반복하는 건 괜찮다 (점-선-점 × 2조건 = 정상).
  종류가 4가지를 넘으면 그건 픽토그램이 아니라 삽화다.
- 총 개수 24개 이하.
- 선 굵기: 주선 `7`, 점선 외곽선 `6`, 보조·연결선 `4` 이하. 그 사이 값은 쓰지 마라.
- 화살표: `marker-end="url(#ar)"` / `url(#ar-accent)` / `url(#ar-muted)`
- 점선: `stroke-dasharray="10 9"` (선) / `"9 8"` (원 외곽)

### 금지 (쓰면 렌더가 막힌다)

`image` `text` `filter` `linearGradient` `radialGradient` `pattern` `mask`
`clipPath` `use` `symbol` `animate` `style` `foreignObject`

그라디언트·그림자·광원·질감·원근·3D·사람 얼굴·캐릭터·사진 없음.
**손으로 그린 도해나 오래된 인쇄물의 도판처럼 보여야 한다.**

### `object_labels` — 다이어그램 안 라벨

오브젝트 안에 `<text>`를 직접 쓸 수 없다. 타이포는 엔진이 통제한다.
"나", "AI", "개인적인 주제" 같은 라벨은 이 배열로 넘긴다.

```json
"object_labels": [
  { "x": 208, "y": 182, "text": "나", "color": "MUTED" },
  { "x": 0, "y": 32, "text": "개인적인 주제", "color": "ACCENT", "anchor": "start" }
]
```

`color`는 색 토큰. `anchor`는 `middle`(기본) / `start` / `end`.
좌표는 오브젝트 슬롯 기준. 베이스라인 기준이므로 점 아래에 두려면 `점 y + r + 45` 정도.

---

## 오브젝트 설계 원칙

게시물마다 **하나만** 정하고, 6장에 걸쳐 위치·크기·상태·의미가 변한다.
회전·분열·확대·기울기·개방 중 하나 이상으로 변형 가능해야 한다.

| 장 | 오브젝트가 하는 일 |
|---|---|
| 1 | 처음 나타난다. 중립적 |
| 2 | 사용자에게 무언가를 한다 |
| 3 | 조건 수만큼 나뉜다 |
| 4 | 왜곡되거나 기운다 |
| 5 | 무언가를 가리거나 지운다 |
| 6 | 열리거나 비워진다 |

**시각 은유는 연구 결과보다 강한 주장을 하지 않는다.**
언어 표현만 측정 → 정신이 흡수되는 장면 금지.
의존 미측정 → 족쇄·중독 금지. 위험 미측정 → 경고·붕괴 금지.
편집적 해석을 그렸다면 `footnote`에 "편집자의 해석입니다"를 적는다.

`state/index.jsonl`에 기록된 과거 `object_name`은 재사용하지 않는다.

---

## 렌더

```bash
python automation/render.py <폴더>/content.json --check-only   # 검사만
python automation/render.py <폴더>/content.json                # 검사 + PNG 6장
```

종료 코드 `2`면 규칙 위반이다. `render_report.json`의 `errors`를 고치기 전에는
절대 다음 단계로 넘어가지 않는다. `warnings`는 고치면 좋지만 진행을 막지는 않는다.
