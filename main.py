# main.py
# Titik masuk utama aplikasi FastAPI - Toko Tanaman Hias
# Berkas ini menginisialisasi aplikasi FastAPI, mendaftarkan router,
# dan menjalankan inisialisasi database saat startup.

from fastapi import FastAPI
from contextlib import asynccontextmanager
import database as db
from routes import resource, transaction


# ============================================================
# Lifespan handler: menggantikan event on_startup/on_shutdown.
# Fungsi ini dijalankan saat aplikasi FastAPI dimulai (startup)
# dan saat aplikasi dihentikan (shutdown).
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inisialisasi database saat aplikasi dimulai."""
    await db.init_db()
    print("✅ Database berhasil diinisialisasi")
    yield
    print("🛑 Aplikasi dihentikan")


# Inisialisasi aplikasi FastAPI
app = FastAPI(
    title="🌿 Toko Tanaman Hias API",
    description=(
        "REST API untuk manajemen toko tanaman hias. "
        "Mendukung operasi CRUD tanaman, transaksi pembelian asinkron, "
        "dan mekanisme pencegahan race condition menggunakan asyncio.Lock."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# ==================== Registrasi Router ====================
# Setiap router menangani domain endpoint yang berbeda:
# - resource.router: CRUD tanaman hias (/plants)
# - transaction.router: transaksi pembelian (/transactions)
app.include_router(resource.router)
app.include_router(transaction.router)


@app.get("/", tags=["Root"])
async def root():
    """Endpoint root untuk memverifikasi API berjalan."""
    return {
        "application": "Toko Tanaman Hias API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "plants": "/plants",
            "transactions": "/transactions"
        }
    }

