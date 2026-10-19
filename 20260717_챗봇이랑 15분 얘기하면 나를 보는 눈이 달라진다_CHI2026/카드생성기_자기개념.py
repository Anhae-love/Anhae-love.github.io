# -*- coding: utf-8 -*-
"""HCI 인스타 캐러셀 — 자기개념 정렬 / 오브젝트: 두 개의 점"""
import cairosvg, os, math

W, H = 1080, 1350
BG     = "#F7F5F2"
INK    = "#1A1A1A"   # 나
ACCENT = "#2E6F5E"   # AI (딥 그린)
MUTED  = "#8A8580"
DOT    = "#D8D3CC"
FONT   = "Noto Sans CJK KR"
STROKE = 7
PAD    = 92

DEFS = f'''<defs>
  <pattern id="dg" width="26" height="26" patternUnits="userSpaceOnUse">
    <circle cx="1.6" cy="1.6" r="1.6" fill="{DOT}" opacity="0.55"/>
  </pattern>
  <radialGradient id="vig" cx="50%" cy="45%" r="72%">
    <stop offset="55%" stop-color="{BG}" stop-opacity="0"/>
    <stop offset="100%" stop-color="{BG}" stop-opacity="0.92"/>
  </radialGradient>
  <marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
    <path d="M0,0 L9,4.5 L0,9 Z" fill="{INK}"/>
  </marker>
</defs>'''

def base():
    return (f'<rect width="{W}" height="{H}" fill="{BG}"/>'
            f'<rect width="{W}" height="{H}" fill="url(#dg)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')

def dot(x, y, r=26, c=INK, dashed=False, fill=True):
    if dashed:
        return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{c}" '
                f'stroke-width="{STROKE-1}" stroke-dasharray="9 8"/>')
    if fill:
        return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>'
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{c}" '
            f'stroke-width="{STROKE}"/>')

def seg(x1, y1, x2, y2, c=MUTED, w=3, dashed=False):
    d = ' stroke-dasharray="10 9"' if dashed else ''
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" '
            f'stroke-width="{w}"{d}/>')

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(x, y, lines, size, weight="700", fill=INK, lh=1.28, anchor="start"):
    o = ""
    for i, ln in enumerate(lines):
        o += (f'<text x="{x}" y="{y+i*size*lh}" font-family="{FONT}" font-size="{size}" '
              f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
              f'xml:space="preserve">{esc(ln)}</text>')
    return o

def label(x, y, s):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="27" font-weight="500" '
            f'fill="{MUTED}" letter-spacing="3">{esc(s)}</text>')

def foots(x, y, lines, anchor="start"):
    o = ""
    for i, ln in enumerate(lines):
        o += (f'<text x="{x}" y="{y+i*30}" font-family="{FONT}" font-size="21" '
              f'font-weight="400" fill="{MUTED}" font-style="italic" '
              f'text-anchor="{anchor}">{esc(ln)}</text>')
    return o

def tag(x, y, s, c, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="25" font-weight="500" '
            f'fill="{c}" text-anchor="{anchor}">{esc(s)}</text>')

def wrap(b):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">{DEFS}{base()}{b}</svg>')

S = []

# 1 · 등장 — 검은 점 하나. 홀로.
S.append(wrap(
    label(PAD, PAD+30, "챗봇을 켜기 전")
    + dot(300, 400, 30)
    + tag(300, 470, "나", MUTED)
    + txt(PAD, 790, ["나는 나를", "이렇게 생각한다"], 76)
    + txt(PAD, 1090, ["내향적인 편. 성실한 편.", "그런 감각."], 30, "400", MUTED)
))

# 2 · 작동 — 초록 점 등장. 긴 선분.
S.append(wrap(
    label(PAD, PAD+30, "15분의 대화")
    + txt(PAD, 250, ["AI에게도", "성격 점수가 있다"], 66)
    + seg(300, 640, 780, 640)
    + dot(300, 640, 30) + tag(300, 712, "나", MUTED)
    + dot(780, 640, 30, ACCENT) + tag(780, 712, "AI", ACCENT)
    + txt(PAD, 900, ["연구팀은 GPT-4o에게", "성격검사를 100번 시켰다."], 32, "400", MUTED)
    + foots(PAD, 1180, ["같은 문항, 같은 설정.", "100회 평균값을 AI의 성격으로 삼았다."])
))

# 3 · 분할 — 두 조건으로 복제
S.append(wrap(
    label(PAD, PAD+30, "두 조건")
    + txt(PAD, 250, ["무슨 얘기를", "했느냐가 갈랐다"], 62)
    # 개인 조건
    + tag(PAD, 590, "개인적인 주제", MUTED, "start")
    + seg(300, 660, 780, 660)
    + dot(300, 660, 26) + dot(780, 660, 26, ACCENT)
    # 비개인 조건
    + tag(PAD, 850, "고양이 밈 같은 주제", MUTED, "start")
    + seg(300, 920, 780, 920)
    + dot(300, 920, 26) + dot(780, 920, 26, ACCENT)
    + foots(PAD, 1180, ["92명 무작위 배정. 각 조건 46명."])
))

# 4 · 결과 — 개인 조건에서 검은 점이 초록 쪽으로 이동
S.append(wrap(
    label(PAD, PAD+30, "대화가 끝난 뒤")
    + txt(PAD, 235, ["나의 자기평가가", "AI 쪽으로", "움직였다"], 60)
    # 개인 조건 — 이동
    + tag(PAD, 615, "개인적인 주제", ACCENT, "start")
    + seg(300, 690, 560, 690, MUTED, 3, True)
    + f'<line x1="330" y1="690" x2="530" y2="690" stroke="{INK}" stroke-width="4" marker-end="url(#ar)"/>'
    + seg(590, 690, 780, 690)
    + dot(300, 690, 22, MUTED, dashed=True)
    + dot(590, 690, 26) + dot(780, 690, 26, ACCENT)
    # 비개인 조건 — 그대로
    + tag(PAD, 900, "고양이 밈 같은 주제", MUTED, "start")
    + seg(300, 975, 780, 975)
    + dot(300, 975, 26) + dot(780, 975, 26, ACCENT)
    + foots(PAD, 1185, ["p < .001, d = 0.51.",
                        "비개인 조건은 유의하지 않았다 (p = .279)."])
))

# 5 · 오해 방지 — 실제 나(실선) vs 내가 아는 나(점선). 점선만 움직였다.
S.append(wrap(
    label(PAD, PAD+30, "자주 하는 오해")
    + txt(PAD, 250, ["AI가 나를", "바꾼 게 아니다"], 66)
    + seg(300, 660, 620, 660, MUTED, 3, True)
    + dot(300, 660, 30, INK, fill=False)
    + tag(300, 745, "실제 나", MUTED)
    + dot(620, 660, 26, INK, dashed=True)
    + tag(620, 745, "내가 아는 나", MUTED)
    + seg(660, 660, 830, 660)
    + dot(870, 660, 26, ACCENT)
    + tag(870, 745, "AI", ACCENT)
    + txt(PAD, 900, ["바뀐 건 내가 나를 보는 눈이다.", "실제 성격이 변했는지는 측정하지 않았다."],
          30, "400", MUTED)
    + foots(PAD, 1195, ["20문항 자기보고 척도.",
                        "행동 변화나 지속성은 이 연구의 범위 밖이다."])
))

# 6 · 개방 — 여러 검은 점이 하나의 초록 점 주위로 수렴
cx, cy = W//2, 560
conv = ""
for i in range(9):
    a = math.radians(i * 40 - 90)
    r = 175
    x, y = cx + r*math.cos(a), cy + r*math.sin(a)
    conv += seg(cx, cy, x, y, DOT, 2)
    conv += dot(x, y, 19)
S.append(wrap(
    label(PAD, PAD+30, "남은 질문")
    + conv
    + dot(cx, cy, 34, ACCENT)
    + txt(W//2, 890, ["같은 AI를 쓴 사람들은", "서로 닮아갔다"], 58, "700", INK, anchor="middle")
    + txt(W//2, 1075, ["92명의 자기평가가 서로 더 비슷해졌다.",
                       "그리고 그럴수록 대화가 더 즐거웠다."],
          29, "400", MUTED, anchor="middle")
    + foots(W//2, 1215, ["p < .001. 즐거움과의 연관은 상관이며, 인과가 아니다."], "middle")
))

os.makedirs("/mnt/user-data/outputs/cards2", exist_ok=True)
for i, s in enumerate(S, 1):
    p = f"/mnt/user-data/outputs/cards2/slide_{i}"
    open(p+".svg", "w").write(s)
    cairosvg.svg2png(bytestring=s.encode(), write_to=p+".png",
                     output_width=W, output_height=H)
print("done")
