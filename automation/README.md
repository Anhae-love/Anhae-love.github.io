# 운영 매뉴얼

매일 새벽 3~5시 사이, PC를 절전에서 깨워 콘텐츠 초안을 만들어 둔다.
**발행은 하지 않는다.** 아침에 사람이 보고 올린다.

---

## 흐름

```
작업 스케줄러 (03:00 + 최대 2h 랜덤)
   └─ run_daily.ps1          절전 차단, 로그, 타임아웃 75분
        └─ claude -p         pipeline_prompt.md 를 따라 수행
             ├─ 조사·선정    v3 프롬프트대로. 후보 8건+ → 1건
             ├─ facts.json   원문 수치·범위·인용을 먼저 고정
             ├─ content.json facts.json 만 보고 카피 작성
             ├─ render.py --check-only    기계 규칙 + facts 대조
             ├─ verify.py    ← codex.exe (GPT) 교차검증. 여기가 게이트
             │                 pass → 진행 / revise → 최대 2회 수정 / reject → 폐기
             ├─ render.py    슬라이드 6장 PNG
             └─ STATUS · NOTES.md · state/index.jsonl
```

**게이트를 건너뛰는 경로는 없다.** codex가 죽으면 카드를 만들지 않고 멈춘다.

---

## 아침에 할 일

`output/<날짜>_<주제>/` 를 연다.

| 파일 | 내용 |
|---|---|
| `slide_1~6.png` | 올릴 카드 |
| `caption.txt` | 캡션 + 해시태그 |
| `alt_texts.txt` | 대체 텍스트 |
| `NOTES.md` | **먼저 읽어라.** 무엇을 골랐고 GPT가 뭘 지적했는지 |
| `verdict.json` | GPT 판정 원본 |
| `STATUS` | 상태 한 줄 |

### STATUS 값

| 값 | 뜻 | 할 일 |
|---|---|---|
| `awaiting_human_review` | 정상 완료 | 검수하고 올린다 |
| `needs_human` | 재검증 2회에도 GPT가 통과 안 줌 | `verdict.json`을 읽고 직접 판단 |
| `rejected` | GPT가 주제 자체를 기각 | `NOTES.md`의 2순위 후보를 보고 결정 |
| `verify_failed` | codex 실행 실패 | `_codex_log.txt` 확인. 대개 로그인 만료 |
| `no_output` | 폴더가 안 생김 | `logs/`의 해당 날짜 로그 |

`state/last_run.json`에 마지막 실행 요약이 한 줄로 남는다.

---

## 명령

```powershell
# 등록 상태 / 다음 실행 시각
.\automation\setup_task.ps1 -Show

# 지금 한 번 돌려보기 (스케줄러를 통해)
.\automation\setup_task.ps1 -RunNow

# 직접 실행 — 화면에서 진행 상황을 보고 싶을 때
.\automation\run_daily.ps1

# 조사·검증까지만, 카드는 안 만듦 (게이트 동작 확인용)
.\automation\run_daily.ps1 -DryRun

# 권한 허용목록이 막을 때
.\automation\run_daily.ps1 -Bypass

# 시각 바꾸기 (예: 2시~5시)
.\automation\setup_task.ps1 -At 02:00 -WindowHours 3

# 중단
.\automation\setup_task.ps1 -Remove
```

부분만 따로 돌릴 수도 있다.

```bash
python automation/facts.py  "output/<폴더>/facts.json" "output/<폴더>/content.json"
python automation/render.py "output/<폴더>/content.json" --check-only   # 규칙 검사만
python automation/render.py "output/<폴더>/content.json"                # 카드 굽기
python automation/verify.py --dir "output/<폴더>" --attempt 1           # GPT 검증만
```

`verify.py` 종료 코드: `0` pass / `10` revise / `20` reject / `30` 실행 실패

---

## 두 층의 검사

역할이 갈려 있다. 겹치면 수정 사이클만 돈다.

**`render.py` — 기계가 세는 것**
도형 종류·개수, 선 굵기, 색 토큰, 글자 수, 줄 수, 캡션 길이, 해시태그 개수,
JSON 필드, 슬라이드 6장, 프리프린트 고지 존재 여부.
그리고 **`facts.json` 대조** — 카드의 모든 수치가 사실 목록에 있는가,
유의차 없음을 동일성으로 서술하고 있지 않은가.
위반하면 **렌더 자체가 막힌다** (exit 2). GPT에게 물어볼 일이 아니다.

**`verify.py` (GPT) — 의미를 보는 것**
원문 대조, 수치 정확성, 상관↔인과 혼동, 범위 초과, 집단 낙인,
시각 은유가 결과보다 센 주장을 하는지, 최종 검증 7항.

`verify_prompt.md`의 0절이 GPT에게 "기계가 세는 건 네 일이 아니다"라고 명시한다.
이 경계를 흐리면 GPT가 글자 수를 세느라 사실 검증을 소홀히 한다.

---

## 손댈 만한 곳

| 하고 싶은 것 | 파일 |
|---|---|
| 주제·톤·편집 규칙 | `../HCI_인스타그램_콘텐츠_프롬프트_v3.md` |
| 사실 검사 규칙 (금칙어·숫자 대조) | `facts.py` 상단 상수 |
| 레이아웃·여백·글자 크기·색 | `engine.py` 상단 고정값 |
| content.json 형식 | `content_contract.md` |
| GPT가 볼 것 / 안 볼 것 | `verify_prompt.md` |
| GPT 판정 형식 | `verify_schema.json` |
| 실행 순서·재시도 정책 | `pipeline_prompt.md` |
| 실행 파일 경로·타임아웃 | `config.json` |

**`.ps1` 파일을 편집했다면 UTF-8 BOM으로 저장해야 한다.**
PowerShell 5.1은 BOM 없는 UTF-8을 ANSI로 읽어서 한글이 깨지고 파싱이 실패한다.

```powershell
$p = "automation\run_daily.ps1"
$t = [IO.File]::ReadAllText($p, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($p, $t, (New-Object Text.UTF8Encoding($true)))
```

---

## 안 될 때

**새벽에 안 돌았다**
`setup_task.ps1 -Show`의 `마지막 실행` 결과 코드를 본다.
사용자가 로그아웃되어 있으면 실행되지 않는다 (`-LogonType Interactive`).
완전히 종료된 PC는 깨울 수 없다. 놓친 실행은 다음에 켤 때 따라 돈다.

**작업 도중 다시 잠들었다**
`run_daily.ps1`이 `SetThreadExecutionState`로 막고 있다.
로그에 `절전 차단 실패` 경고가 있으면 그것 때문이다.

**허용목록이 조용히 막았다**
`logs/run_*.out.txt`에서 거부된 도구 호출을 찾아 `.claude/settings.json`의
`allow`에 추가한다. 급하면 `-Bypass`.

**facts.json 때문에 렌더가 막힌다**
`render_report.json` 의 `errors` 를 본다. 숫자가 없다고 나오면 원문을 다시 확인해
`findings` 에 넣는다. 단위를 바꾼 파생값(68.5초 → "1분 넘게")이면
`extra_allowed_numbers` 에 근거와 함께 적는다.
"같았다" 계열이 막히면 `뚜렷하지 않았다 · 유의하지 않았다` 로 바꾼다 —
오해를 바로잡는 문장 안(`"~라는 뜻은 아니다"`)에서는 그냥 통과한다.
옛 자료를 다시 굽는 거라면 `--no-facts`.

**codex 로그인 만료**
`verify_failed`가 뜨면 대부분 이것이다. Codex를 한 번 열어 로그인하면 된다.
토큰은 자동 갱신되지만 오래 안 쓰면 끊긴다.

**Claude Code / Codex 업데이트로 경로가 바뀌었다**
`config.json`의 `claude_path` / `codex_path`를 고치거나 `""`로 비운다.
비우면 자동 탐색으로 넘어간다.

---

## 전제

- Python 3.13 (`pillow` 외 추가 패키지 불필요)
- `bin/resvg.exe` 0.47.0 — SVG → PNG
- 한글 폰트: Noto Sans KR → Malgun Gothic 순으로 폴백
- Codex CLI (ChatGPT 계정 로그인)
- Claude Code CLI
- Node.js 불필요
