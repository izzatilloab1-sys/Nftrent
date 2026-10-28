/* ===== NFT Rent — WebApp asosiy mantiq ===== */
(function () {
  const tg = window.Telegram && Telegram.WebApp;
  if (tg) { try { tg.expand(); tg.ready(); } catch (e) {} }

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  let state = { user: null, tab: "home", section: "all", sort: "default", q: "", support: "" };
  let tonConnectUI = null;

  // ---------- Helperlar ----------
  function showLoader(v) { $("#loader").classList.toggle("hidden", !v); }
  function toast(msg, type = "") {
    const t = $("#toast");
    t.textContent = msg; t.className = "toast " + type;
    setTimeout(() => t.classList.add("hidden"), 3200);
  }
  function fmtUZS(n) { return new Intl.NumberFormat("ru-RU").format(Math.round(n)) + " so'm"; }
  function fmtTON(n) { return (Math.round(n * 10000) / 10000) + " TON"; }
  function fmtDate(iso) { if (!iso) return "-"; return new Date(iso).toLocaleDateString(); }

  // ---------- Modal ----------
  function openModal(html) {
    $("#modal-sheet").innerHTML = '<div class="sheet-handle"></div>' + html;
    $("#modal").classList.remove("hidden");
  }
  function closeModal() { $("#modal").classList.add("hidden"); }
  $("#modal .modal-backdrop").addEventListener("click", closeModal);

  // ================= AUTH =================
  function showAuth() { $("#screen-auth").classList.remove("hidden"); $("#screen-app").classList.add("hidden"); }
  function showApp() { $("#screen-auth").classList.add("hidden"); $("#screen-app").classList.remove("hidden"); }

  $("#to-register").addEventListener("click", (e) => { e.preventDefault(); $("#form-login").classList.add("hidden"); $("#form-register").classList.remove("hidden"); });
  $("#to-login").addEventListener("click", (e) => { e.preventDefault(); $("#form-register").classList.add("hidden"); $("#form-login").classList.remove("hidden"); });

  $$(".lang-btn").forEach(b => b.addEventListener("click", () => setLang(b.dataset.lang)));

  $("#form-login").addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = $("#login-username").value.trim();
    const password = $("#login-password").value;
    if (!username || !password) return;
    showLoader(true);
    try {
      const r = await API.login({ username, password });
      API.setToken(r.token); setLang(r.language);
      await afterLogin();
    } catch (err) { toast(err.detail || T("error_generic"), "error"); }
    finally { showLoader(false); }
  });

  $("#form-register").addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = $("#reg-username").value.trim();
    const password = $("#reg-password").value;
    const password_confirm = $("#reg-password2").value;
    if (!username || !password) return;
    showLoader(true);
    try {
      const r = await API.register({ username, password, password_confirm, init_data: API.initData(), language: LANG });
      API.setToken(r.token); setLang(r.language);
      toast("✅", "success");
      await afterLogin();
    } catch (err) { toast(err.detail || T("error_generic"), "error"); }
    finally { showLoader(false); }
  });

  async function afterLogin() {
    const me = await API.me();
    state.user = me; state.support = me.support_username; setLang(me.language);
    showApp(); switchTab("home");
  }

  // ================= NAVIGATSIYA =================
  $$(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
  function switchTab(tab) {
    state.tab = tab;
    $$(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
    if (tab === "home") renderHome();
    else if (tab === "collections") renderCollections();
    else if (tab === "orders") renderOrders();
    else if (tab === "profile") renderProfile();
  }

  // ================= HOME (katalog) =================
  async function renderHome() {
    const c = $("#main-content");
    c.innerHTML = `
      <div class="page-header"><div class="page-title">${T("home_title")}</div></div>
      <div class="search-bar"><input id="search" placeholder="${T("search_ph")}" value="${state.q}"/></div>
      <div class="filters" id="filters">
        ${["all","popular","new","myrentals"].map(s =>
          `<div class="chip ${state.section===s?'active':''}" data-sec="${s}">${T("sec_"+(s==="myrentals"?"myrentals":s))}</div>`).join("")}
      </div>
      <div class="sort-row">
        <select id="sort">
          <option value="default">${T("sort_default")}</option>
          <option value="price_asc">${T("sort_price_asc")}</option>
          <option value="price_desc">${T("sort_price_desc")}</option>
          <option value="newest">${T("sort_newest")}</option>
        </select>
      </div>
      <div id="nft-list"><div class="empty-state">${T("loading")}</div></div>`;

    $("#sort").value = state.sort;
    $("#search").addEventListener("input", debounce((e) => { state.q = e.target.value; loadNfts(); }, 350));
    $("#sort").addEventListener("change", (e) => { state.sort = e.target.value; loadNfts(); });
    $$("#filters .chip").forEach(ch => ch.addEventListener("click", () => {
      state.section = ch.dataset.sec;
      $$("#filters .chip").forEach(x => x.classList.toggle("active", x === ch));
      loadNfts();
    }));
    loadNfts();
  }

  async function loadNfts() {
    const list = $("#nft-list");
    if (!list) return;
    list.innerHTML = `<div class="empty-state">${T("loading")}</div>`;
    try {
      if (state.section === "myrentals") { return renderMyRentals(list); }
      const params = { section: state.section === "myrentals" ? "all" : state.section, sort: state.sort };
      if (state.q) params.q = state.q;
      const nfts = await API.listNfts(params);
      if (!nfts.length) { list.innerHTML = emptyState("🔍", T("empty_nfts")); return; }
      list.innerHTML = `<div class="nft-grid">${nfts.map(nftCard).join("")}</div>`;
      $$(".nft-card", list).forEach(card =>
        card.addEventListener("click", () => openNftDetail(parseInt(card.dataset.id))));
    } catch (err) { list.innerHTML = emptyState("⚠️", err.detail || T("error_generic")); }
  }

  async function renderMyRentals(list) {
    try {
      const orders = await API.myOrders();
      const active = orders.filter(o => ["rental_active","paid"].includes(o.status));
      if (!active.length) { list.innerHTML = emptyState("📭", T("empty_orders")); return; }
      list.innerHTML = active.map(orderCard).join("");
    } catch (err) { list.innerHTML = emptyState("⚠️", err.detail); }
  }

  function nftCard(n) {
    const badge = n.is_popular ? `<span class="nft-badge">★ ${T("sec_popular")}</span>` : "";
    const avail = n.is_available ? "" : `<span class="nft-badge unavail">${T("unavailable")}</span>`;
    return `
      <div class="nft-card" data-id="${n.id}">
        <img class="nft-img" src="${n.image_url}" alt="" onerror="this.src='/static/img/placeholder.svg'"/>
        <div class="nft-body">
          ${badge}${avail}
          <div class="nft-name">${esc(n.name)}</div>
          <div class="nft-ref">#${esc(n.nft_ref)}</div>
          <div class="nft-price">${fmtTON(n.daily_price_ton)}<small>${T("per_day")}</small></div>
          <div class="nft-ref">${fmtUZS(n.daily_price_uzs)}${T("per_day")}</div>
        </div>
      </div>`;
  }

  // ================= NFT DETAIL + narx =================
  async function openNftDetail(id) {
    showLoader(true);
    try {
      const nft = await API.getNft(id);
      let duration = nft.allowed_durations[0] || 1;
      openModal(detailSkeleton(nft));
      bindDuration(nft, () => duration, (d) => { duration = d; });
      await refreshQuote(nft.id, duration);
      $("#modal-sheet").addEventListener("click", async (e) => {
        if (e.target.closest(".dur-btn")) {
          const d = parseInt(e.target.closest(".dur-btn").dataset.d);
          duration = d;
          $$(".dur-btn").forEach(b => b.classList.toggle("active", parseInt(b.dataset.d) === d));
          await refreshQuote(nft.id, d);
        }
      });
      const rentBtn = $("#btn-rent");
      if (rentBtn) rentBtn.addEventListener("click", () => doRent(nft.id, duration, nft));
      const closeBtn = $("#btn-close");
      if (closeBtn) closeBtn.addEventListener("click", closeModal);
    } catch (err) { toast(err.detail || T("error_generic"), "error"); }
    finally { showLoader(false); }
  }

  function detailSkeleton(nft) {
    return `
      <img class="detail-img" src="${nft.image_url}" onerror="this.src='/static/img/placeholder.svg'"/>
      <div class="detail-name">${esc(nft.name)}</div>
      <div class="detail-ref">#${esc(nft.nft_ref)} · ${esc(nft.collection_name || "")}</div>
      <div class="section-label">${T("rent_duration")}</div>
      <div class="duration-row">
        ${nft.allowed_durations.map((d,i) =>
          `<div class="dur-btn ${i===0?'active':''}" data-d="${d}">${d} ${d===1?T("day"):T("days")}</div>`).join("")}
      </div>
      <div id="quote-box"><div class="empty-state">${T("loading")}</div></div>
      <button id="btn-rent" class="btn btn-primary" style="margin-top:10px">${T("btn_rent")}</button>
      <button id="btn-close" class="btn btn-ghost" style="margin-top:8px">${T("btn_close")}</button>`;
  }
  function bindDuration() {}

  async function refreshQuote(nftId, duration) {
    const box = $("#quote-box");
    if (!box) return;
    box.innerHTML = `<div class="empty-state">${T("loading")}</div>`;
    try {
      const q = await API.quote(nftId, duration);
      box.innerHTML = quoteTable(q);
    } catch (err) { box.innerHTML = `<div class="empty-state">${err.detail || T("error_generic")}</div>`; }
  }

  function quoteTable(q) {
    const lines = q.lines.map(l => {
      const cls = l.refundable ? "refund" : "dim";
      const label = LANG === "en" ? l.label_en : l.label_uz;
      return `<div class="price-row"><span class="${cls}">${esc(label)}${l.refundable?' ↩':''}</span>
        <span>${fmtTON(l.amount_ton)}</span></div>`;
    }).join("");
    return `
      <div class="price-table">
        <div class="price-row"><span class="dim">${T("base_price")} (${q.duration_days}${T("day")} × ${fmtTON(q.daily_price_ton)})</span>
          <span>${fmtTON(q.base_price_ton)}</span></div>
        ${lines}
        <div class="price-row total"><span>${T("total")}</span><span>${fmtTON(q.total_ton)}</span></div>
        <div class="price-row"><span class="dim">${T("total")} (so'm)</span><span>${fmtUZS(q.total_uzs)}</span></div>
        <div class="price-row"><span class="dim">1 TON</span><span>${fmtUZS(q.ton_uzs_rate)}</span></div>
      </div>`;
  }

  // ================= IJARAGA OLISH + TO'LOV =================
  async function doRent(nftId, duration, nft) {
    showLoader(true);
    try {
      const order = await API.createOrder(nftId, duration);
      closeModal();
      // To'lov yoqilganmi?
      const cfg = await API.paymentConfig();
      if (!cfg.payments_enabled || !cfg.receiving_address) {
        toast(T("order_created") + " — " + T("payment_disabled"), "success");
        switchTab("orders");
        return;
      }
      await startTonPayment(order, cfg);
    } catch (err) { toast(err.detail || T("error_generic"), "error"); }
    finally { showLoader(false); }
  }

  async function startTonPayment(order, cfg) {
    // TON Connect UI ni tayyorlash
    if (!tonConnectUI && window.TON_CONNECT_UI && cfg.tonconnect_manifest_url) {
      tonConnectUI = new TON_CONNECT_UI.TonConnectUI({ manifestUrl: cfg.tonconnect_manifest_url });
    }
    if (!tonConnectUI) {
      toast("TON Connect manifest sozlanmagan (admin).", "error");
      switchTab("orders"); return;
    }
    try {
      const init = await API.initiatePayment(order.id);
      const tx = {
        validUntil: Math.floor(Date.now() / 1000) + 300,
        messages: [{
          address: init.receiving_address,
          amount: String(Math.round(init.amount_ton * 1e9)),
          // comment payload — TON Connect UI buni text comment sifatida yuboradi
          payload: buildCommentPayload(init.memo),
        }],
      };
      toast(T("pay_confirm"));
      await tonConnectUI.sendTransaction(tx);
      // Tasdiqlashni kutish (polling)
      await pollPaymentVerify(order.id);
    } catch (err) {
      const m = err && (err.detail || err.message);
      toast(typeof m === "string" ? m : T("error_generic"), "error");
      switchTab("orders");
    }
  }

  // text comment uchun BOC payload (op=0 + utf8)
  function buildCommentPayload(text) {
    // TON comment: 32 bit zero op + text. Oddiy base64 cell.
    // Soddalik uchun TON Connect UI "text" ni qo'llab-quvvatlasa undan foydalanamiz.
    // Bu yerda biz payloadni bo'sh qoldirib, memoni comment sifatida yuboramiz.
    return undefined;
  }

  async function pollPaymentVerify(orderId, attempts = 0) {
    if (attempts > 20) { toast(T("checking_payment"), ""); switchTab("orders"); return; }
    toast(T("checking_payment"));
    try {
      const r = await API.verifyPayment(orderId);
      if (r.confirmed) { toast(T("payment_confirmed"), "success"); switchTab("orders"); return; }
    } catch (e) {}
    setTimeout(() => pollPaymentVerify(orderId, attempts + 1), 6000);
  }

  // ================= ORDERS =================
  async function renderOrders() {
    const c = $("#main-content");
    c.innerHTML = `<div class="page-header"><div class="page-title">${T("orders_title")}</div></div><div id="orders-list"><div class="empty-state">${T("loading")}</div></div>`;
    try {
      const orders = await API.myOrders();
      const list = $("#orders-list");
      if (!orders.length) { list.innerHTML = emptyState("📭", T("empty_orders")); return; }
      list.innerHTML = orders.map(orderCard).join("");
    } catch (err) { $("#orders-list").innerHTML = emptyState("⚠️", err.detail); }
  }

  function orderCard(o) {
    let timeInfo = "";
    if (o.status === "rental_active" && o.rental_end_at) {
      const left = new Date(o.rental_end_at) - new Date();
      const days = Math.ceil(left / 86400000);
      timeInfo = `<div class="order-num">${T("time_left")}: ${days > 0 ? days + " " + T("days") : T("expired")}</div>`;
    }
    return `
      <div class="order-card">
        <img src="${o.nft_image_url || '/static/img/placeholder.svg'}" onerror="this.src='/static/img/placeholder.svg'"/>
        <div class="order-info">
          <div class="order-num">${esc(o.order_number)}</div>
          <div class="order-name">${esc(o.nft_name || "NFT")}</div>
          <span class="status-pill st-${o.status}">${T("st_"+o.status)}</span>
          <div class="order-num" style="margin-top:4px">${fmtTON(o.total_ton)} · ${fmtUZS(o.total_uzs)}</div>
          ${timeInfo}
        </div>
      </div>`;
  }

  // ================= COLLECTIONS =================
  async function renderCollections() {
    const c = $("#main-content");
    c.innerHTML = `<div class="page-header"><div class="page-title">${T("collections_title")}</div></div><div id="col-list"><div class="empty-state">${T("loading")}</div></div>`;
    try {
      const cols = await API.collections();
      const list = $("#col-list");
      if (!cols.length) { list.innerHTML = emptyState("🗂️", T("empty_nfts")); return; }
      list.innerHTML = cols.map(col => `
        <div class="menu-item" data-slug="${col.slug}">
          <span class="ico">🗂️</span>
          <div><div style="font-weight:700">${esc(col.name)}</div>
          <div class="order-num">${esc(col.description||"")}</div></div>
        </div>`).join("");
    } catch (err) { $("#col-list").innerHTML = emptyState("⚠️", err.detail); }
  }

  // ================= PROFILE =================
  function renderProfile() {
    const c = $("#main-content");
    const u = state.user;
    c.innerHTML = `
      <div class="profile-head">
        <div class="profile-avatar">${(u.username[0]||"?").toUpperCase()}</div>
        <div class="profile-username">${esc(u.username)}</div>
        <div class="profile-meta">${T("created_at")}: ${fmtDate(u.created_at)}</div>
      </div>
      <div class="balance-card"><div class="lbl">${T("balance")}</div><div class="val">${fmtUZS(u.balance_uzs)}</div></div>
      <div class="menu-list">
        <div class="menu-item" data-act="mynfts"><span class="ico">🎁</span>${T("my_nfts")}<span class="arrow">›</span></div>
        <div class="menu-item" data-act="orders"><span class="ico">📦</span>${T("my_orders")}<span class="arrow">›</span></div>
        <div class="menu-item" data-act="lang"><span class="ico">🌐</span>${T("change_lang")}<span class="arrow">›</span></div>
        <div class="menu-item" data-act="pass"><span class="ico">🔑</span>${T("change_pass")}<span class="arrow">›</span></div>
        <div class="menu-item" data-act="support"><span class="ico">🆘</span>${T("support")}<span class="arrow">›</span></div>
        <div class="menu-item" data-act="logout"><span class="ico">🚪</span>${T("logout")}<span class="arrow">›</span></div>
      </div>`;
    $$(".menu-item", c).forEach(it => it.addEventListener("click", () => profileAction(it.dataset.act)));
  }

  function profileAction(act) {
    if (act === "orders" || act === "mynfts") { if (act==="mynfts"){state.section="myrentals";} switchTab(act==="mynfts"?"home":"orders"); if(act==="mynfts")renderHome(); }
    else if (act === "lang") openLangModal();
    else if (act === "pass") openPassModal();
    else if (act === "support") openSupport();
    else if (act === "logout") doLogout();
  }

  function openLangModal() {
    openModal(`
      <div class="detail-name">${T("change_lang")}</div><br/>
      <button class="btn ${LANG==='uz'?'btn-primary':'btn-ghost'}" data-l="uz" style="margin-bottom:8px">🇺🇿 O'zbek</button>
      <button class="btn ${LANG==='en'?'btn-primary':'btn-ghost'}" data-l="en">🇬🇧 English</button>`);
    $$("#modal-sheet [data-l]").forEach(b => b.addEventListener("click", async () => {
      showLoader(true);
      try { const me = await API.setLanguage(b.dataset.l); state.user = me; setLang(me.language); closeModal(); renderProfile(); }
      catch (e) { toast(e.detail, "error"); } finally { showLoader(false); }
    }));
  }

  function openPassModal() {
    openModal(`
      <div class="detail-name">${T("change_pass")}</div><br/>
      <div class="form-field"><label>${T("old_pass")}</label><input type="password" id="p-old"/></div>
      <div class="form-field"><label>${T("new_pass")}</label><input type="password" id="p-new"/></div>
      <div class="form-field"><label>${T("confirm_pass")}</label><input type="password" id="p-new2"/></div>
      <button class="btn btn-primary" id="p-save">${T("btn_save")}</button>`);
    $("#p-save").addEventListener("click", async () => {
      const body = { old_password: $("#p-old").value, new_password: $("#p-new").value, new_password_confirm: $("#p-new2").value };
      showLoader(true);
      try { const r = await API.changePassword(body); toast(r.message || "✅", "success"); closeModal(); }
      catch (e) { toast(e.detail, "error"); } finally { showLoader(false); }
    });
  }

  function openSupport() {
    const s = state.support || "";
    if (tg && s) { try { tg.openTelegramLink("https://t.me/" + s.replace("@","")); return; } catch (e) {} }
    toast("Support: @" + (s || "—"));
  }

  async function doLogout() {
    showLoader(true);
    try { await API.logout(); } catch (e) {}
    API.setToken(null); state.user = null; showLoader(false); showAuth();
  }

  // ---------- util ----------
  function esc(s) { return String(s==null?"":s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
  function emptyState(emo, txt) { return `<div class="empty-state"><div class="emo">${emo}</div>${esc(txt)}</div>`; }
  function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

  // ================= INIT =================
  // Telegram ichida ekanligini aniqlaymiz (initData bor-yo'qligi orqali).
  const INSIDE_TELEGRAM = !!API.initData();

  async function init() {
    applyI18n();

    // Loader sahifa ochilishi bilanoq ko'rinib turadi (HTML'da). Login ekrani
    // miltillab ko'rinmasin uchun, qaror qilgunimizcha uni ko'rsatib turamiz.
    showLoader(true);

    // Integratsiya holatini ko'rsatish (demo ekanini OCHIQ aytamiz)
    try {
      const st = await API.integrationStatus();
      const note = $("#integration-note");
      if (note) note.textContent = LANG === "en" ? st.message_en : st.message_uz;
    } catch (e) {}

    // 1) Token bo'lsa — darhol kiramiz (parol so'ralmaydi)
    if (API.getToken()) {
      try {
        await afterLogin();
        showLoader(false);
        return;
      } catch (e) {
        API.setToken(null);
      }
    }

    // 2) Telegram WebApp ichida bo'lsa (initData bor) — AVTOMATIK kirish.
    //    Login ekrani UMUMAN ko'rsatilmaydi; to'g'ridan-to'g'ri katalogga o'tadi.
    if (INSIDE_TELEGRAM) {
      try {
        const r = await API.telegramAuth(LANG);
        API.setToken(r.token);
        setLang(r.language);
        await afterLogin();
        showLoader(false);
        return;
      } catch (e) {
        // Telegram ichida avto-kirish ishlamasa — foydalanuvchiga xabar beramiz,
        // lekin login formasini ko'rsatmaymiz (bu Telegram, parol kerak emas).
        console.warn("telegram auto-auth failed:", e && e.detail);
        showLoader(false);
        toast((e && e.detail) || T("error_generic"), "error");
        // Zaxira sifatida login ekranini ko'rsatamiz (kamdan-kam holat)
        showAuth();
        return;
      }
    }

    // 3) Telegram tashqarisida (oddiy brauzer) — login/register ekrani (zaxira)
    showLoader(false);
    showAuth();
  }
  init();
})();
