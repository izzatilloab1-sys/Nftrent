/* Frontend tarjimalari: uz / en */
const I18N = {
  uz: {
    brand_sub: "NFT sovg'alarini ijaraga oling",
    login_title: "Kirish", register_title: "Ro'yxatdan o'tish",
    btn_login: "Kirish", btn_register: "Ro'yxatdan o'tish",
    no_account: "Akkauntingiz yo'qmi?", register_link: "Ro'yxatdan o'tish",
    have_account: "Akkauntingiz bormi?", login_link: "Kirish",
    nav_home: "Bosh", nav_collections: "Kolleksiyalar", nav_orders: "Buyurtmalar", nav_profile: "Profil",
    home_title: "NFT Katalog", search_ph: "NFT nomi yoki ID bo'yicha qidirish...",
    sec_all: "Barchasi", sec_popular: "Mashhur", sec_new: "Yangi", sec_myrentals: "Mening ijaralarim",
    sort_default: "Saralash", sort_price_asc: "Narx: arzon", sort_price_desc: "Narx: qimmat", sort_newest: "Eng yangi",
    per_day: "/kun", available: "Mavjud", unavailable: "Mavjud emas", details: "Batafsil",
    empty_nfts: "NFT topilmadi", empty_orders: "Buyurtmalaringiz yo'q", empty_my_nfts: "Hali ijaraga olingan NFT yo'q",
    collections_title: "Kolleksiyalar", orders_title: "Buyurtmalarim", profile_title: "Profil",
    rent_duration: "Ijara muddati", days: "kun", day: "kun",
    base_price: "Asosiy narx", marketplace: "Marketplace komissiyasi", network: "TON tarmoq xarajati",
    service: "Xizmat haqi", refundable_deposit: "Qaytariladigan depozit", total: "Jami to'lov",
    btn_rent: "Ijaraga olish", btn_pay: "TON orqali to'lash", btn_close: "Yopish",
    my_profile: "Mening profilim", username: "Username", created_at: "Yaratilgan sana",
    balance: "Balans", my_nfts: "Mening NFT'larim", my_orders: "Ijara buyurtmalarim",
    change_lang: "Tilni o'zgartirish", change_pass: "Parolni almashtirish", logout: "Chiqish", support: "Support",
    old_pass: "Eski parol", new_pass: "Yangi parol", confirm_pass: "Parolni tasdiqlang",
    btn_save: "Saqlash", order_created: "Buyurtma yaratildi!",
    payment_disabled: "To'lov tizimi hali yoqilmagan. Admin yoqqach ishlaydi.",
    rental_start: "Boshlandi", rental_end: "Tugaydi", time_left: "Qolgan vaqt", expired: "Tugagan",
    connect_wallet: "Hamyonni ulash", pay_confirm: "To'lovni hamyoningizda tasdiqlang",
    checking_payment: "To'lov tekshirilmoqda...", payment_confirmed: "To'lov tasdiqlandi! Ijara faollashdi.",
    st_draft: "Qoralama", st_pending_payment: "To'lov kutilmoqda", st_paid: "To'langan",
    st_rental_active: "Faol ijara", st_rental_completed: "Yakunlangan", st_cancelled: "Bekor qilingan", st_failed: "Xato",
    loading: "Yuklanmoqda...", error_generic: "Xatolik yuz berdi",
  },
  en: {
    brand_sub: "Rent Telegram NFT gifts",
    login_title: "Login", register_title: "Register",
    btn_login: "Login", btn_register: "Register",
    no_account: "No account?", register_link: "Register",
    have_account: "Have an account?", login_link: "Login",
    nav_home: "Home", nav_collections: "Collections", nav_orders: "Orders", nav_profile: "Profile",
    home_title: "NFT Catalog", search_ph: "Search by NFT name or ID...",
    sec_all: "All", sec_popular: "Popular", sec_new: "New", sec_myrentals: "My rentals",
    sort_default: "Sort", sort_price_asc: "Price: low", sort_price_desc: "Price: high", sort_newest: "Newest",
    per_day: "/day", available: "Available", unavailable: "Unavailable", details: "Details",
    empty_nfts: "No NFTs found", empty_orders: "No orders yet", empty_my_nfts: "No rented NFTs yet",
    collections_title: "Collections", orders_title: "My Orders", profile_title: "Profile",
    rent_duration: "Rental duration", days: "days", day: "day",
    base_price: "Base price", marketplace: "Marketplace fee", network: "TON network fee",
    service: "Service fee", refundable_deposit: "Refundable deposit", total: "Total",
    btn_rent: "Rent now", btn_pay: "Pay with TON", btn_close: "Close",
    my_profile: "My profile", username: "Username", created_at: "Created at",
    balance: "Balance", my_nfts: "My NFTs", my_orders: "My rental orders",
    change_lang: "Change language", change_pass: "Change password", logout: "Logout", support: "Support",
    old_pass: "Old password", new_pass: "New password", confirm_pass: "Confirm password",
    btn_save: "Save", order_created: "Order created!",
    payment_disabled: "Payments are not enabled yet. Works once admin turns it on.",
    rental_start: "Started", rental_end: "Ends", time_left: "Time left", expired: "Expired",
    connect_wallet: "Connect wallet", pay_confirm: "Confirm the payment in your wallet",
    checking_payment: "Checking payment...", payment_confirmed: "Payment confirmed! Rental is active.",
    st_draft: "Draft", st_pending_payment: "Pending payment", st_paid: "Paid",
    st_rental_active: "Active rental", st_rental_completed: "Completed", st_cancelled: "Cancelled", st_failed: "Failed",
    loading: "Loading...", error_generic: "Something went wrong",
  },
};

let LANG = localStorage.getItem("nftrent_lang") || "uz";

function setLang(l) {
  LANG = (l === "en") ? "en" : "uz";
  localStorage.setItem("nftrent_lang", LANG);
  applyI18n();
}
function T(key) { return (I18N[LANG] && I18N[LANG][key]) || (I18N.uz[key]) || key; }

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = T(el.getAttribute("data-i18n"));
  });
  document.querySelectorAll(".lang-btn").forEach(b => {
    b.classList.toggle("active", b.getAttribute("data-lang") === LANG);
  });
}
