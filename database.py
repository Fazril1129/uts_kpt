# database.py
# Modul koneksi dan operasi basis data SQLite menggunakan aiosqlite.
# Seluruh operasi database dilakukan secara asinkron (non-blocking)
# agar tidak memblokir event loop FastAPI saat menunggu I/O disk.

import aiosqlite
import asyncio

DATABASE = "toko_tanaman.db"

# ==================== SQL Definisi Tabel ====================

# Tabel resource utama: plants (tanaman hias)
# Memiliki 6 kolom selain id, termasuk kolom kuantitas 'stok'
# yang wajib ada untuk mendukung pengujian transaksi dan konkurensi.
CREATE_PLANTS_TABLE = """
CREATE TABLE IF NOT EXISTS plants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    jenis TEXT NOT NULL,
    harga REAL NOT NULL,
    stok INTEGER NOT NULL,  -- tanpa CHECK agar overselling (stok negatif) dapat didemokan pada B3 Tahap 1
    deskripsi TEXT NOT NULL,
    asal TEXT NOT NULL
);
"""

# Tabel transaksi: menyimpan riwayat pembelian tanaman
# Status transaksi mengikuti alur: pending -> processing -> completed/failed
CREATE_TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plant_id INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    total_harga REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY (plant_id) REFERENCES plants(id)
);
"""

# ============================================================
# Inisialisasi asyncio.Lock di tingkat modul untuk melindungi
# critical section pada operasi pemotongan stok.
# Lock ini memastikan hanya satu coroutine yang dapat mengakses
# dan memodifikasi stok pada satu waktu (mutual exclusion).
# asyncio.Lock bekerja pada level event loop (single-threaded),
# sehingga efektif untuk mencegah race condition antar coroutine
# dalam satu proses worker Uvicorn.
# ============================================================
stok_lock = asyncio.Lock()


# ==================== Koneksi Database ====================

async def get_connection():
    """Membuat koneksi asinkron ke database SQLite menggunakan aiosqlite."""
    conn = await aiosqlite.connect(DATABASE)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db():
    """Inisialisasi database: membuat tabel plants dan transactions jika belum ada."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(CREATE_PLANTS_TABLE)
        await db.execute(CREATE_TRANSACTIONS_TABLE)
        await db.commit()


# ==================== CRUD Operations: Plants ====================

async def get_all_plants(skip: int = 0, limit: int = 10) -> list[dict]:
    """Mengambil daftar tanaman dengan pagination (skip & limit)."""
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM plants LIMIT ? OFFSET ?", (limit, skip)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_plant_by_id(plant_id: int) -> dict | None:
    """Mengambil detail satu tanaman berdasarkan ID."""
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM plants WHERE id = ?", (plant_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_plant(nama: str, jenis: str, harga: float,
                       stok: int, deskripsi: str, asal: str) -> int:
    """Menambahkan tanaman baru ke database. Mengembalikan ID tanaman."""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """INSERT INTO plants (nama, jenis, harga, stok, deskripsi, asal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nama, jenis, harga, stok, deskripsi, asal)
        )
        await db.commit()
        return cursor.lastrowid


async def update_plant(plant_id: int, nama: str, jenis: str, harga: float,
                       stok: int, deskripsi: str, asal: str) -> None:
    """Memperbarui data tanaman berdasarkan ID."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """UPDATE plants SET nama=?, jenis=?, harga=?, stok=?, deskripsi=?, asal=?
               WHERE id=?""",
            (nama, jenis, harga, stok, deskripsi, asal, plant_id)
        )
        await db.commit()


async def delete_plant(plant_id: int) -> bool:
    """Menghapus tanaman secara permanen (hard delete). Mengembalikan True jika berhasil."""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "DELETE FROM plants WHERE id = ?", (plant_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


# ==================== Operasi Stok ====================

async def get_stok(plant_id: int) -> int:
    """Mengambil nilai stok terkini suatu tanaman."""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT stok FROM plants WHERE id = ?", (plant_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def decrement_stok(plant_id: int, qty: int) -> None:
    """Mengurangi stok tanaman sebesar qty."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE plants SET stok = stok - ? WHERE id = ?",
            (qty, plant_id)
        )
        await db.commit()


# ============================================================
# Versi 1: Pemotongan stok TANPA lock (rentan race condition)
#
# Fungsi ini sengaja menambahkan jeda asyncio.sleep(0.01)
# setelah pembacaan stok untuk membuka jendela waktu (time window)
# terjadinya race condition. Ketika dua coroutine berjalan
# secara concurrent (bersamaan di event loop), keduanya dapat
# membaca nilai stok yang sama sebelum salah satu sempat
# memperbarui, sehingga terjadi overselling (stok menjadi negatif).
# ============================================================
async def potong_stok_tanpa_lock(plant_id: int, qty: int) -> bool:
    # Baca stok terkini dari database
    stok_terkini = await get_stok(plant_id)

    # Jeda buatan: membuka jendela race condition.
    # Pada titik ini, event loop dapat beralih ke coroutine lain
    # yang juga sedang membaca stok (context switch).
    await asyncio.sleep(0.01)

    if stok_terkini < qty:
        return False

    # Kedua coroutine membaca nilai stok yang sama (misal: 1),
    # sehingga keduanya lolos pengecekan dan mengurangi stok,
    # mengakibatkan stok akhir menjadi negatif (overselling).
    await decrement_stok(plant_id, qty)
    return True


# ============================================================
# Versi 2: Pemotongan stok DENGAN asyncio.Lock (aman)
#
# asyncio.Lock menyediakan mekanisme mutual exclusion pada
# level event loop. Ketika satu coroutine memegang lock
# (masuk ke blok 'async with stok_lock'), coroutine lain
# yang mencoba mengakuisisi lock akan di-suspend hingga
# lock dilepas. Ini memastikan operasi baca-cek-tulis stok
# berjalan secara atomik (tidak dapat diinterupsi).
# ============================================================
async def potong_stok_dengan_lock(plant_id: int, qty: int) -> bool:
    # Critical section: hanya satu coroutine yang dapat masuk
    # pada satu waktu. Coroutine lain akan menunggu (await)
    # hingga lock dilepas secara otomatis saat keluar blok 'async with'.
    async with stok_lock:
        stok_terkini = await get_stok(plant_id)

        # Meskipun ada jeda, lock mencegah coroutine lain
        # membaca stok sebelum operasi ini selesai.
        await asyncio.sleep(0.01)

        if stok_terkini < qty:
            return False

        await decrement_stok(plant_id, qty)
        return True


# ==================== Operasi Transaksi ====================

async def insert_transaction(plant_id: int, qty: int,
                             total_harga: float, status: str = "pending") -> int:
    """Menyimpan transaksi baru ke database. Mengembalikan ID transaksi."""
    from datetime import datetime
    created_at = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """INSERT INTO transactions (plant_id, qty, total_harga, status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (plant_id, qty, total_harga, status, created_at)
        )
        await db.commit()
        return cursor.lastrowid


async def get_all_transactions(status_filter: str | None = None,
                               skip: int = 0, limit: int = 10) -> list[dict]:
    """Mengambil daftar transaksi dengan opsional filter status dan pagination."""
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        if status_filter:
            cursor = await db.execute(
                "SELECT * FROM transactions WHERE status = ? LIMIT ? OFFSET ?",
                (status_filter, limit, skip)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM transactions LIMIT ? OFFSET ?",
                (limit, skip)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_transaction_by_id(trx_id: int) -> dict | None:
    """Mengambil detail satu transaksi berdasarkan ID."""
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM transactions WHERE id = ?", (trx_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_trx_status(trx_id: int, status: str) -> None:
    """Memperbarui status transaksi (pending -> processing -> completed/failed)."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE transactions SET status = ? WHERE id = ?",
            (status, trx_id)
        )
        await db.commit()

