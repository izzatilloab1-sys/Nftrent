/* ===== NFT Rent — Admin panel ===== */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  let adminId = localStorage.getItem("nftrent_admin_id") || null;

  function showLoader(v) { $("#loader").classList.toggle("hidden", !v); }
  function toast(msg, type = "") { const t = $("#toast"); t.textContent = msg; t.className = "toast " + type; setTimeout(() => t.classList.add("hidden"), 3000); }
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
  function fmtUZS(n){return new Intl.NumberFormat("ru-RU").format(Math.round(n));}

  async function api(path, { method = "GET", body = null } = {}) {
    const headers = { "Content-Type": "application/json", "X-Admin-Telegram-Id": adminId };
    const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : null });
    let data = null; try { data = await res.json(); } catch(e){}
    if (!res.ok) { const err = new Error((data&&data.detail)||("HTTP "+res.status)); err.detail = (data&&data.detail); throw err; }
    return data;
  }

  // ---------- Auth ----------
  $("#admin-enter").addEventListener("click", enter);
  $("#admin-id").addEventListener("keydown", e => { if (e.key === "Enter") enter(); });
  async function enter() {
    const id = $("#admin-id").value.trim();
    if (!id) return;
    adminId = id;
    showLoader(true);
    try {
      await api("/api/admin/stats"); // tekshiruv
      localStorage.setItem("nftrent_admin_id", id);
      $("#admin-auth").classList.add("hidden");
      $("#admin-panel").classList.remove("hidden");
      switchView("dashboard");
    } catch (err) { toast(err.detail || "Ruxsat yo'q", "error"); adminId = null; }
    finally { showLoader(false); }
  }

  $("#admin-logout").addEventListener("click", () => {
    localStorage.removeItem("nftrent_admin_id"); adminId = null;
    $("#admin-panel").classList.add("hidden"); $("#admin-auth").classList.remove("hidden");
  });

  $$(".admin-nav").forEach(b => b.addEventListener("click", () => switchView(b.dataset.view)));
  function switchView(v) {
    $$(".admin-nav").forEach(b => b.classList.toggle("active", b.dataset.view === v));
    ({ dashboard: viewDashboard, rate: viewRate, nfts: viewNfts, commissions: viewCommissions,
       payment: viewPayment, users: viewUsers, support: viewSupport })[v]();
  }

  // ---------- Dashboard ----------
  async function viewDashboard() {
    const m = $("#admin-main");
    m.innerHTML = `<div class="admin-h1">📊 Boshqaruv</div><div id="stats">Yuklanmoqda...</div>`;
    try {
      const s = await api("/api/admin/stats");
      $("#stats").innerHTML = `<div class="stats-grid">
        ${statCard(s.users_count, "Foydalanuvchilar")}
        ${statCard(s.orders_count, "Buyurtmalar")}
        ${statCard(s.active_rentals, "Faol ijaralar")}
        ${statCard(s.today_orders, "Bugungi buyurtmalar")}
        ${statCard(fmtUZS(s.current_ton_rate), "1 TON (so'm)")}
        ${statCard(s.payments_mode.toUpperCase(), "To'lovlar rejimi")}
      </div>`;
    } catch (err) { $("#stats").innerHTML = err.detail; }
  }
  function statCard(num, lbl) { return `<div class="stat-card"><div class="num">${num}</div><div class="lbl">${lbl}</div></div>`; }

  // ---------- TON kursi ----------
  async function viewRate() {
    const m = $("#admin-main");
    m.innerHTML = `<div class="admin-h1">💱 TON kursi</div><div id="rate-box">Yuklanmoqda...</div>`;
    const d = await api("/api/admin/rate");
    $("#rate-box").innerHTML = `
      <div class="admin-form">
        <div class="form-field"><label>Joriy kurs: 1 TON = ${fmtUZS(d.current)} so'm</label>
        <input type="number" id="new-rate" placeholder="Yangi kurs (so'm)" value="${d.current}"/></div>
        <button class="btn btn-primary" id="save-rate">Kursni saqlash</button>
      </div>
      <h3 style="margin:22px 0 10px;font-size:15px">Kurs o'zgarishlari tarixi</h3>
      <table class="admin-table"><thead><tr><th>Kurs (so'm)</th><th>Admin ID</th><th>Sana</th></tr></thead>
      <tbody>${d.history.map(h=>`<tr><td>${fmtUZS(h.rate)}</td><td>${h.changed_by||"-"}</td><td>${new Date(h.created_at).toLocaleString()}</td></tr>`).join("")}</tbody></table>`;
    $("#save-rate").addEventListener("click", async () => {
      const rate = parseFloat($("#new-rate").value);
      if (!(rate > 0)) { toast("Kurs musbat bo'lishi kerak", "error"); return; }
      showLoader(true);
      try { await api("/api/admin/rate", { method: "POST", body: { rate } }); toast("Saqlandi ✅", "success"); viewRate(); }
      catch (e) { toast(e.detail, "error"); } finally { showLoader(false); }
    });
  }

  // ---------- NFT boshqaruvi ----------
  async function viewNfts() {
    const m = $("#admin-main");
    m.innerHTML = `<div class="admin-h1">🎁 NFT boshqaruvi</div>
      <button class="btn btn-primary" id="add-nft" style="width:auto;margin-bottom:16px">+ NFT qo'shish</button>
      <div class="warn-box">⚠️ Bu NFT'lar DEMO. Marketapp bilan rasmiy integratsiya ulanmaguncha haqiqiy emas.</div>
      <div id="nfts-box">Yuklanmoqda...</div>`;
    $("#add-nft").addEventListener("click", () => nftForm());
    const nfts = await api("/api/admin/nfts");
    $("#nfts-box").innerHTML = `<table class="admin-table">
      <thead><tr><th>ID</th><th>Nomi</th><th>Ref</th><th>Narx/kun</th><th>Mashhur</th><th>Holat</th><th></th></tr></thead>
      <tbody>${nfts.map(n=>`<tr>
        <td>${n.id}</td><td>${esc(n.name)}</td><td>${esc(n.nft_ref)}</td>
        <td>${n.daily_price_ton} TON</td>
        <td>${n.is_popular?'★':'-'}</td>
        <td class="${n.is_hidden?'badge-off':'badge-on'}">${n.is_hidden?'Yashirin':'Faol'}</td>
        <td><button class="small-btn" data-edit="${n.id}">Tahrir</button>
            <button class="small-btn" data-toggle="${n.id}">${n.is_hidden?'Faollash':'Yashirish'}</button></td>
      </tr>`).join("")}</tbody></table>`;
    $$("[data-toggle]").forEach(b => b.addEventListener("click", async () => {
      showLoader(true); try { await api(`/api/admin/nfts/${b.dataset.toggle}/toggle`, { method: "POST" }); viewNfts(); }
      catch(e){toast(e.detail,"error");} finally{showLoader(false);}
    }));
    $$("[data-edit]").forEach(b => b.addEventListener("click", () => {
      const n = nfts.find(x => x.id == b.dataset.edit); nftForm(n);
    }));
  }

  function nftForm(n = null) {
    const m = $("#admin-main");
    m.innerHTML = `<div class="admin-h1">${n?'NFT tahrirlash':'NFT qo\\'shish'}</div>
      <div class="admin-form">
        <div class="form-field"><label>Nomi</label><input id="f-name" value="${n?esc(n.name):''}"/></div>
        <div class="form-field"><label>NFT Ref/ID</label><input id="f-ref" value="${n?esc(n.nft_ref):''}"/></div>
        <div class="form-field"><label>Rasm URL</label><input id="f-img" value="${n?esc(n.image_url):'/static/img/placeholder.svg'}"/></div>
        <div class="form-field"><label>Kunlik narx (TON)</label><input type="number" step="0.01" id="f-price" value="${n?n.daily_price_ton:'0.5'}"/></div>
        <div class="form-field"><label>Muddatlar (vergul bilan)</label><input id="f-dur" value="${n?n.allowed_durations.join(','):'1,3,7,30'}"/></div>
        <div class="form-field"><label><input type="checkbox" id="f-pop" ${n&&n.is_popular?'checked':''}/> Mashhur</label></div>
        <div class="form-field"><label><input type="checkbox" id="f-avail" ${!n||n.is_available?'checked':''}/> Mavjud</label></div>
        <button class="btn btn-primary" id="f-save">Saqlash</button>
        <button class="btn btn-ghost" id="f-cancel" style="margin-top:8px">Bekor</button>
      </div>`;
    $("#f-cancel").addEventListener("click", viewNfts);
    $("#f-save").addEventListener("click", async () => {
      const body = {
        name: $("#f-name").value.trim(), nft_ref: $("#f-ref").value.trim(),
        image_url: $("#f-img").value.trim(), daily_price_ton: parseFloat($("#f-price").value)||0,
        allowed_durations: $("#f-dur").value.split(",").map(x=>parseInt(x.trim())).filter(x=>x>0),
        is_popular: $("#f-pop").checked, is_available: $("#f-avail").checked, is_hidden: false,
      };
      showLoader(true);
      try {
        if (n) await api(`/api/admin/nfts/${n.id}`, { method: "PUT", body });
        else await api("/api/admin/nfts", { method: "POST", body });
        toast("Saqlandi ✅", "success"); viewNfts();
      } catch (e) { toast(e.detail, "error"); } finally { showLoader(false); }
    });
  }

  // ---------- Komissiyalar ----------
  async function viewCommissions() {
    const m = $("#admin-main");
    m.innerHTML = `<div class="admin-h1">💰 Komissiyalar</div>
      <div class="warn-box">⚠️ Qiymatlar taxminiy (demo). Haqiqiy Marketapp integratsiyasida tranzaksiya ma'lumotlaridan tekshiriladi.</div>
      <div id="comm-box">Yuklanmoqda...</div>`;
    const comms = await api("/api/admin/commissions");
    $("#comm-box").innerHTML = comms.map(c => `
      <div class="admin-form" style="margin-bottom:12px">
        <b>${esc(c.label_uz || c.kind)}</b> <span style="color:var(--text-dim)">(${c.kind})</span>
        <div class="form-field" style="margin-top:10px"><label>Hisoblash turi</label>
          <select data-f="calc" data-id="${c.id}">
            <option value="percent" ${c.calc_type==='percent'?'selected':''}>Foiz (%)</option>
            <option value="flat_ton" ${c.calc_type==='flat_ton'?'selected':''}>Qat'iy (TON)</option>
          </select></div>
        <div class="form-field"><label>Qiymat</label><input type="number" step="0.01" data-f="value" data-id="${c.id}" value="${c.value}"/></div>
        <div class="form-field"><label>Tartib</label><input type="number" data-f="order" data-id="${c.id}" value="${c.order_index}"/></div>
        <div class="form-field"><label><input type="checkbox" data-f="active" data-id="${c.id}" ${c.is_active?'checked':''}/> Faol</label></div>
        <button class="btn btn-primary save-comm" data-id="${c.id}" data-kind="${c.kind}" data-uz="${esc(c.label_uz)}" data-en="${esc(c.label_en)}">Saqlash</button>
      </div>`).join("");
    $$(".save-comm").forEach(b => b.addEventListener("click", async () => {
      const id = b.dataset.id;
      const body = {
        kind: b.dataset.kind,
        calc_type: $(`[data-f=calc][data-id="${id}"]`).value,
        value: parseFloat($(`[data-f=value][data-id="${id}"]`).value)||0,
        order_index: parseInt($(`[data-f=order][data-id="${id}"]`).value)||0,
        is_active: $(`[data-f=active][data-id="${id}"]`).checked,
        label_uz: b.dataset.uz, label_en: b.dataset.en,
      };
      showLoader(true);
      try { await api(`/api/admin/commissions/${id}`, { method: "PUT", body }); toast("Saqlandi ✅","success"); }
      catch(e){toast(e.detail,"error");} finally{showLoader(false);}
    }));
  }

  // ---------- TON to'lov sozlamalari ----------
  async function viewPayment() {
    const m = $("#admin-main");
    m.innerHTML = `<div class="admin-h1">🪙 TON to'lov sozlamalari</div>
      <div class="warn-box">⚠️ XAVFSIZLIK: Faqat OCHIQ qabul qiluvchi manzilni kiriting (UQ.../EQ...).
      24 so'zli seed yoki maxfiy kalitni HECH QACHON bu yerga kiritmang!</div>
      <div id="pay-box">Yuklanmoqda...</div>`;
    const d = await api("/api/admin/payment-settings");
    $("#pay-box").innerHTML = `
      <div class="admin-form">
        <div class="form-field"><label>Qabul qiluvchi TON manzili (public address)</label>
          <input id="pay-addr" placeholder="UQ... yoki EQ..." value="${esc(d.receiving_address)}"/></div>
        <div class="form-field"><label>TON Connect manifest URL</label>
          <input id="pay-manifest" placeholder="https://domen.uz/tonconnect-manifest.json" value="${esc(d.tonconnect_manifest_url)}"/></div>
        <div class="form-field"><label><input type="checkbox" id="pay-enabled" ${d.payments_enabled?'checked':''}/> To'lovni yoqish (auto to'lov)</label></div>
        <button class="btn btn-primary" id="pay-save">Saqlash</button>
      </div>`;
    $("#pay-save").addEventListener("click", async () => {
      const body = {
        receiving_address: $("#pay-addr").value.trim(),
        tonconnect_manifest_url: $("#pay-manifest").value.trim(),
        payments_enabled: $("#pay-enabled").checked,
      };
      showLoader(true);
      try { await api("/api/admin/payment-settings", { method: "POST", body }); toast("Saqlandi ✅","success"); }
      catch(e){toast(e.detail,"error");} finally{showLoader(false);}
    });
  }

  // ---------- Foydalanuvchilar ----------
  async function viewUsers() {
    const m = $("#admin-main");
    m.innerHTML = `<div class="admin-h1">👥 Foydalanuvchilar</div>
      <div class="search-bar" style="max-width:320px"><input id="u-search" placeholder="Username bo'yicha qidirish..."/></div>
      <div class="warn-box">⚠️ Parollar hech qachon ko'rsatilmaydi (xavfsizlik).</div>
      <div id="users-box">Yuklanmoqda...</div>`;
    const load = async (q) => {
      const users = await api("/api/admin/users" + (q?`?q=${encodeURIComponent(q)}`:""));
      $("#users-box").innerHTML = `<table class="admin-table">
        <thead><tr><th>ID</th><th>Username</th><th>Til</th><th>Buyurtmalar</th><th>Sana</th><th>Holat</th><th></th></tr></thead>
        <tbody>${users.map(u=>`<tr>
          <td>${u.id}</td><td>${esc(u.username)}</td><td>${u.language}</td><td>${u.orders_count}</td>
          <td>${new Date(u.created_at).toLocaleDateString()}</td>
          <td class="${u.is_blocked?'badge-off':'badge-on'}">${u.is_blocked?'Bloklangan':'Faol'}</td>
          <td><button class="small-btn ${u.is_blocked?'':'danger'}" data-block="${u.id}">${u.is_blocked?'Blokdan chiqarish':'Bloklash'}</button></td>
        </tr>`).join("")}</tbody></table>`;
      $$("[data-block]").forEach(b => b.addEventListener("click", async () => {
        showLoader(true); try { await api(`/api/admin/users/${b.dataset.block}/block`, { method: "POST" }); load($("#u-search").value); }
        catch(e){toast(e.detail,"error");} finally{showLoader(false);}
      }));
    };
    let t; $("#u-search").addEventListener("input", e => { clearTimeout(t); t = setTimeout(() => load(e.target.value), 350); });
    load("");
  }

  // ---------- Support ----------
  async function viewSupport() {
    const m = $("#admin-main");
    const d = await api("/api/admin/support");
    m.innerHTML = `<div class="admin-h1">🆘 Support sozlamasi</div>
      <div class="admin-form">
        <div class="form-field"><label>Support Telegram username</label>
          <input id="sup" placeholder="NftRentSupport" value="${esc(d.support_username)}"/></div>
        <button class="btn btn-primary" id="sup-save">Saqlash</button>
        <p style="color:var(--text-dim);font-size:12px;margin-top:10px">O'zgartirilganda butun loyihada avtomatik yangilanadi.</p>
      </div>`;
    $("#sup-save").addEventListener("click", async () => {
      showLoader(true);
      try { await api("/api/admin/support", { method: "POST", body: { support_username: $("#sup").value.trim() } }); toast("Saqlandi ✅","success"); }
      catch(e){toast(e.detail,"error");} finally{showLoader(false);}
    });
  }

  // Init — avto kirish
  if (adminId) {
    $("#admin-id").value = adminId;
    enter();
  }
})();
