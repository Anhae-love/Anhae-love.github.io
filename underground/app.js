// THE UNDERGROUND // ai 지하실
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  let FEED = { items: [], top_surge: [] };
  let activeTag = "all";

  // ---------- 부팅 시퀀스 ----------
  const BOOT_LINES = [
    "[ok] mounting /dev/underground …",
    "[ok] decrypting ranking table …",
    "[ok] loading github feed …",
    "[warn] crack/bypass repos → BLOCKED (합법 라인)",
    "[ok] oracle online.",
    "",
    "welcome to THE_UNDERGROUND. 조용히 둘러봐.",
  ];
  function boot() {
    const el = $("#bootLog");
    let i = 0, buf = "";
    const tick = () => {
      if (i < BOOT_LINES.length) {
        buf += BOOT_LINES[i++] + "\n";
        el.textContent = buf + "_";
        setTimeout(tick, 230 + Math.random() * 180);
      } else {
        setTimeout(() => { $("#boot").classList.add("done"); }, 450);
      }
    };
    tick();
  }

  // ---------- 데이터 ----------
  fetch("data/feed.json?t=" + Date.now())
    .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then((d) => { FEED = d; onReady(); })
    .catch((e) => {
      $("#list").innerHTML = '<div class="err">// 피드 복호화 실패: ' + esc(e.message) +
        '<br>underground/fetch_underground.py 를 먼저 돌려줘</div>';
      $("#status").textContent = "feed offline";
    });

  function onReady() {
    $("#status").textContent = FEED.count + " repos armed";
    $("#genAt").textContent = "last sync: " + (FEED.generated_at || "").replace("T", " ").replace("+00:00", "Z");
    renderSurge();
    renderFilters();
    renderList();
    renderChips();
  }

  // ---------- 떡상 티커 ----------
  function renderSurge() {
    const track = $("#surge");
    const s = (FEED.top_surge || []).filter((x) => x.delta > 0);
    if (!s.length) { $("#surgeWrap").style.display = "none"; return; }
    track.innerHTML = s.map((x) =>
      `<a class="surge-item" href="${esc(x.url)}" target="_blank" rel="noopener">` +
      `<span class="up">▲ +${x.delta.toLocaleString()}</span> <span class="nm">${esc(x.name)}</span></a>`
    ).join("");
  }

  // ---------- 필터 ----------
  function renderFilters() {
    const tags = new Set(["all"]);
    FEED.items.forEach((it) => (it.tags || []).forEach((t) => tags.add(t)));
    const label = { all: "전체", coding: "코딩", writing: "글쓰기", image: "이미지",
      agent: "에이전트", prompt: "프롬프트", local: "로컬·무제한", free: "오픈/프리",
      chat: "챗", misc: "기타" };
    $("#filters").innerHTML = [...tags].map((t) =>
      `<button class="fbtn ${t === "all" ? "on" : ""}" data-tag="${t}">${label[t] || t}</button>`
    ).join("");
    $("#filters").querySelectorAll(".fbtn").forEach((b) =>
      b.addEventListener("click", () => {
        activeTag = b.dataset.tag;
        $("#filters").querySelectorAll(".fbtn").forEach((x) => x.classList.toggle("on", x === b));
        renderList();
      }));
  }

  // ---------- 랭킹 ----------
  function renderList() {
    const list = $("#list");
    const rows = FEED.items.filter((it) => activeTag === "all" || (it.tags || []).includes(activeTag));
    if (!rows.length) { list.innerHTML = '<div class="loading">// 이 태그엔 아직 없음</div>'; return; }

    list.innerHTML = rows.map((it, idx) => {
      const fire = "🔥".repeat(it.danger || 1);
      const d = it.delta > 0 ? `<span class="d-up">▲ +${it.delta.toLocaleString()}</span>` : "";
      const tag = (it.tags || [])[0] ? `<span class="tag">#${esc(it.tags[0])}</span>` : "";
      return `<div class="row" style="animation-delay:${Math.min(idx, 20) * 0.02}s">
        <div class="rnum ${idx < 3 ? "top" : ""}">${it.rank}</div>
        <div class="rmain">
          <div class="rname">${esc(it.name)}<span class="fire">${fire}</span></div>
          <div class="rowner">@${esc(it.owner)}</div>
          ${it.desc ? `<div class="rdesc">${esc(it.desc)}</div>` : ""}
          <div class="rmeta">
            <span class="star">★ ${it.stars.toLocaleString()}</span>${d}
            <span>${esc(it.lang)}</span>${tag}
          </div>
        </div>
        <div class="ropen"><a href="${esc(it.url)}" target="_blank" rel="noopener">열기 ↗</a></div>
      </div>`;
    }).join("");
  }

  // ---------- 추천 콘솔 (능글맞은 로컬 매칭, API 비용 0) ----------
  const INTENTS = [
    { kw: ["발표", "ppt", "슬라이드", "피치", "deck"], tag: "writing",
      quip: "발표자료 급하지? 이거 던져주고 커피나 마셔. 상사한텐 밤샜다고 해." },
    { kw: ["코딩", "코드", "개발", "code", "버그", "리팩", "자동화"], tag: "coding",
      quip: "손은 그만 쓰고 머리만 써. 밑에 애들이 알아서 짜준다." },
    { kw: ["이미지", "그림", "사진", "디자인", "image", "art"], tag: "image",
      quip: "포토샵 구독 끊고 싶지? 이쪽 골목으로 와." },
    { kw: ["에이전트", "agent", "자동", "워크플로", "봇"], tag: "agent",
      quip: "너 대신 일하는 애들. 밤새 돌려놓고 자." },
    { kw: ["토큰", "무제한", "공짜", "무료", "비용", "로컬", "local", "오프라인"], tag: "local",
      quip: "토큰 걱정? 네 컴에서 돌려. 요금고지서 안 날아온다. 합법이고." },
    { kw: ["프롬프트", "prompt", "지침", "시스템"], tag: "prompt",
      quip: "말 거는 법부터 배워. 좋은 질문이 좋은 답을 뽑는다." },
    { kw: ["챗", "대화", "chat", "비서", "상담"], tag: "chat",
      quip: "말동무든 비서든, 쓸만한 애들만 추렸다." },
  ];

  function recommend(q) {
    const query = (q || "").toLowerCase();
    let hit = INTENTS.find((it) => it.kw.some((k) => query.includes(k.toLowerCase())));
    const tag = hit ? hit.tag : null;
    let pool = FEED.items.filter((it) => tag ? (it.tags || []).includes(tag) : true);
    if (!pool.length) pool = FEED.items;
    const picks = pool.slice(0, 3);

    const verdict = hit
      ? hit.quip
      : "흠, 뭘 원하는지 애매하네. 그냥 지금 제일 핫한 거 세 개 던진다.";

    const out = $("#oracleOut");
    out.hidden = false;
    out.innerHTML =
      `<div class="verdict">root@underground: ${esc(verdict)}</div>` +
      picks.map((p) =>
        `<a class="pick" href="${esc(p.url)}" target="_blank" rel="noopener">` +
        `<b>#${p.rank} ${esc(p.name)}</b> ${"🔥".repeat(p.danger || 1)}<br>` +
        `<span class="why">★${p.stars.toLocaleString()} · ${esc((p.desc || "설명 없음").slice(0, 90))}</span></a>`
      ).join("");
  }

  function renderChips() {
    const samples = ["발표자료 빨리", "코딩 자동화", "토큰 걱정 없이", "이미지 생성", "에이전트"];
    $("#chips").innerHTML = samples.map((s) => `<span class="chip">${s}</span>`).join("");
    $("#chips").querySelectorAll(".chip").forEach((c) =>
      c.addEventListener("click", () => { $("#ask").value = c.textContent; recommend(c.textContent); }));
  }

  $("#askBtn").addEventListener("click", () => recommend($("#ask").value));
  $("#ask").addEventListener("keydown", (e) => { if (e.key === "Enter") recommend($("#ask").value); });

  boot();
})();
