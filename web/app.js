// HCI 인스타 쇼케이스 — 갤러리 + 라이트박스
(() => {
  "use strict";

  const $ = (sel, el = document) => el.querySelector(sel);
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  let items = [];
  let lb = { itemIndex: 0, slideIndex: 0 };

  // ---------- 데이터 로드 ----------
  fetch("data/gallery.json?t=" + Date.now())
    .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(init)
    .catch((e) => {
      $("#grid").innerHTML =
        '<div class="empty">갤러리 데이터를 불러오지 못했습니다.<br><small>' + esc(e.message) + "</small></div>";
    });

  function init(data) {
    const site = data.site || {};
    items = Array.isArray(data.items) ? data.items : [];

    if (site.title) { document.title = site.title; $(".brand").firstChild.textContent = site.title.split(" ")[0]; }
    if (site.subtitle) $("#heroTitle") && null; // 제목은 디자인 고정, 서브만 반영
    if (site.description) $("#heroSub").textContent = site.description;

    $("#navCount").textContent = items.length ? "(" + items.length + ")" : "";
    $("#footGen").textContent = "총 " + items.length + "개 · 더미 데이터";

    renderGrid();
    bindLightbox();
  }

  // ---------- 그리드 ----------
  function renderGrid() {
    const grid = $("#grid");
    if (!items.length) { grid.innerHTML = '<div class="empty">아직 작업이 없습니다.</div>'; return; }

    grid.innerHTML = items.map((it, i) => `
      <article class="card" data-index="${i}" tabindex="0" role="button" aria-label="${esc(it.title)} 열기">
        <div class="card-media">
          <img loading="lazy" src="${esc(it.cover)}" alt="${esc(it.title)} 커버">
          <div class="card-overlay"><span class="view">카드 보기 →</span></div>
        </div>
        <div class="card-info">
          <div class="card-cat">${esc(it.category || "")}</div>
          <h3 class="card-title">${esc(it.title)}</h3>
          <div class="card-date">${esc(it.date || "")}</div>
        </div>
      </article>`).join("");

    // 등장 애니메이션
    const cards = [...grid.querySelectorAll(".card")];
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            const el = en.target;
            el.style.transitionDelay = (el.dataset.index % 3) * 0.08 + "s";
            el.classList.add("in");
            io.unobserve(el);
          }
        });
      }, { threshold: 0.12 });
      cards.forEach((c) => io.observe(c));
    } else {
      cards.forEach((c) => c.classList.add("in"));
    }

    // 열기
    cards.forEach((c) => {
      const open = () => openLightbox(Number(c.dataset.index));
      c.addEventListener("click", open);
      c.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
    });
  }

  // ---------- 라이트박스 ----------
  function bindLightbox() {
    $("#lbClose").addEventListener("click", closeLightbox);
    $("#lbPrev").addEventListener("click", () => step(-1));
    $("#lbNext").addEventListener("click", () => step(1));
    $("#lightbox").addEventListener("click", (e) => { if (e.target === $("#lightbox") || e.target === $(".lb-stage")) closeLightbox(); });
    document.addEventListener("keydown", (e) => {
      if ($("#lightbox").hidden) return;
      if (e.key === "Escape") closeLightbox();
      else if (e.key === "ArrowRight") step(1);
      else if (e.key === "ArrowLeft") step(-1);
    });
  }

  function openLightbox(itemIndex) {
    lb = { itemIndex, slideIndex: 0 };
    paint();
    $("#lightbox").hidden = false;
    document.body.style.overflow = "hidden";
    $("#lbClose").focus();
  }

  function closeLightbox() {
    $("#lightbox").hidden = true;
    document.body.style.overflow = "";
  }

  // 슬라이드 간 이동 (끝에서 다음 작업으로 넘어감)
  function step(dir) {
    const it = items[lb.itemIndex];
    const slides = (it && it.slides && it.slides.length) ? it.slides : [it.cover];
    let s = lb.slideIndex + dir;
    if (s < 0) {
      const prev = (lb.itemIndex - 1 + items.length) % items.length;
      lb.itemIndex = prev;
      const ps = items[prev].slides || [items[prev].cover];
      lb.slideIndex = ps.length - 1;
    } else if (s >= slides.length) {
      lb.itemIndex = (lb.itemIndex + 1) % items.length;
      lb.slideIndex = 0;
    } else {
      lb.slideIndex = s;
    }
    paint();
  }

  function paint() {
    const it = items[lb.itemIndex];
    if (!it) return;
    const slides = (it.slides && it.slides.length) ? it.slides : [it.cover];
    const si = Math.min(lb.slideIndex, slides.length - 1);

    document.documentElement.style.setProperty("--accent", it.accent || "#6C5CE7");

    $("#lbImg").src = slides[si];
    $("#lbImg").alt = it.title + " 슬라이드 " + (si + 1);
    $("#lbCat").textContent = it.category || "";
    $("#lbTitle").textContent = it.title || "";
    $("#lbSource").textContent = [it.source_title, it.date].filter(Boolean).join(" · ");
    $("#lbCaption").textContent = it.caption || "";

    const dots = slides.map((_, i) =>
      `<button class="${i === si ? "active" : ""}" data-s="${i}" aria-label="슬라이드 ${i + 1}"></button>`).join("");
    const dotsEl = $("#lbDots");
    dotsEl.innerHTML = dots;
    dotsEl.querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => { lb.slideIndex = Number(b.dataset.s); paint(); }));
  }
})();
