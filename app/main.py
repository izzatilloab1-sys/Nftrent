"""NFT Rent — FastAPI ilovasi (API + WebApp xizmati)."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    admin_routes,
    auth_routes,
    nft_routes,
    order_routes,
    payment_routes,
)
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
    description="NFT Rent — Telegram NFT sovg'alarini ijaraga olish platformasi (1-bosqich).",
)

# CORS — Telegram WebApp uchun
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # prod'da WEBAPP_URL bilan cheklash tavsiya etiladi
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Xavfsizlik sarlavhalari (XSS/clickjacking himoyasi) ---
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "ALLOW-FROM https://web.telegram.org"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# --- API routerlar ---
app.include_router(auth_routes.router)
app.include_router(nft_routes.router)
app.include_router(order_routes.router)
app.include_router(payment_routes.router)
app.include_router(admin_routes.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


# --- Global xatolik — maxfiy ma'lumot oshkor qilinmasin ---
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    if settings.debug:
        return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# --- Statik fayllar (CSS/JS) ---
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


# --- WebApp sahifalari ---
@app.get("/")
async def webapp_index():
    index = WEB_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"detail": "WebApp not built"}, status_code=404)


@app.get("/admin")
async def admin_page():
    admin = WEB_DIR / "admin.html"
    if admin.exists():
        return FileResponse(str(admin))
    return JSONResponse({"detail": "Admin page not found"}, status_code=404)
