/* Backend API klienti */
const API = (() => {
  const base = "";
  let token = localStorage.getItem("nftrent_token") || null;

  function setToken(t) { token = t; if (t) localStorage.setItem("nftrent_token", t); else localStorage.removeItem("nftrent_token"); }
  function getToken() { return token; }

  // Telegram initData (ro'yxatda tekshiriladi)
  function initData() {
    try { return (window.Telegram && Telegram.WebApp && Telegram.WebApp.initData) || ""; }
    catch (e) { return ""; }
  }

  // Xatolik 'detail' ni har doim o'qiladigan STRING ga aylantiradi.
  // FastAPI/Pydantic validatsiya (422) da detail massiv/obyekt bo'ladi -> [object Object] oldini olamiz.
  function normalizeDetail(detail, status) {
    if (detail == null) return "HTTP " + status;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // Pydantic: [{loc:[...], msg:"...", type:"..."}]
      const parts = detail.map((d) => {
        if (d && typeof d === "object") return d.msg || JSON.stringify(d);
        return String(d);
      });
      return parts.join(", ");
    }
    if (typeof detail === "object") {
      return detail.msg || detail.message || JSON.stringify(detail);
    }
    return String(detail);
  }

  async function req(path, { method = "GET", body = null, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth && token) headers["Authorization"] = "Bearer " + token;
    let res;
    try {
      res = await fetch(base + path, {
        method, headers, body: body ? JSON.stringify(body) : null,
      });
    } catch (netErr) {
      const err = new Error("Network error");
      err.status = 0; err.detail = "Tarmoq xatosi / Network error";
      throw err;
    }
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) {
      const msg = normalizeDetail(data && data.detail, res.status);
      const err = new Error(msg); err.status = res.status; err.detail = msg;
      throw err;
    }
    return data;
  }

  return {
    setToken, getToken, initData,
    // Auth
    telegramAuth: (language) => req("/api/auth/telegram", { method: "POST", body: { init_data: initData(), language: language || "uz" }, auth: false }),
    register: (d) => req("/api/auth/register", { method: "POST", body: d, auth: false }),
    login: (d) => req("/api/auth/login", { method: "POST", body: d, auth: false }),
    logout: () => req("/api/auth/logout", { method: "POST" }),
    me: () => req("/api/auth/me"),
    changePassword: (d) => req("/api/auth/change-password", { method: "POST", body: d }),
    setLanguage: (lang) => req("/api/auth/language", { method: "POST", body: { language: lang } }),
    // NFT
    integrationStatus: () => req("/api/nfts/integration-status", { auth: false }),
    listNfts: (params) => {
      const q = new URLSearchParams(params).toString();
      return req("/api/nfts?" + q, { auth: false });
    },
    getNft: (id) => req("/api/nfts/" + id, { auth: false }),
    collections: () => req("/api/nfts/collections", { auth: false }),
    quote: (nft_id, duration_days) => req("/api/nfts/quote", { method: "POST", body: { nft_id, duration_days }, auth: false }),
    // Orders
    createOrder: (nft_id, duration_days) => req("/api/orders", { method: "POST", body: { nft_id, duration_days } }),
    myOrders: () => req("/api/orders"),
    // Payment
    paymentConfig: () => req("/api/payment/config", { auth: false }),
    initiatePayment: (orderId) => req("/api/payment/" + orderId + "/initiate", { method: "POST" }),
    verifyPayment: (orderId) => req("/api/payment/" + orderId + "/verify", { method: "POST" }),
  };
})();
