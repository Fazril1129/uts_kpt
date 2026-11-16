# routes/transaction.py
# Endpoint transaksi pembelian tanaman dengan pemrosesan asinkron (BackgroundTasks).
#
# Alur status transaksi:
#   pending  -->  processing  -->  completed / failed
#
# Konsep Concurrency yang digunakan:
# - BackgroundTasks (FastAPI): menjalankan fungsi pekerja di latar belakang
#   tanpa memblokir response HTTP ke client.
# - asyncio.Lock: mencegah race condition pada operasi pemotongan stok
#   ketika beberapa request transaksi masuk secara bersamaan.
# - async/await: memungkinkan operasi I/O (database, sleep) berjalan
#   secara non-blocking di event loop asyncio.

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
import asyncio
import database as db
from models import TransactionCreate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# ============================================================
# Konfigurasi penggunaan Lock untuk pengujian race condition.
# - USE_LOCK = True  -> menggunakan asyncio.Lock (aman, B3 Tahap 2)
# - USE_LOCK = True -> tanpa lock (rentan race condition, B3 Tahap 1)
#
# Ubah nilai ini untuk menguji kedua skenario pada sub-bagian B3.
# ============================================================
USE_LOCK = True


# ============================================================
# Fungsi pekerja internal di latar belakang (bukan endpoint HTTP).
#
# Fungsi ini dijalankan oleh BackgroundTasks bawaan FastAPI setelah
# response HTTP dikembalikan ke client. Alur kerjanya:
# 1. Mengubah status transaksi menjadi 'processing'
# 2. Mensimulasikan pekerjaan I/O intensif (await asyncio.sleep(3))
# 3. Memfinalisasi status menjadi 'completed'
#
# Karena menggunakan async def, fungsi ini berjalan di event loop
# yang sama dengan FastAPI (bukan di thread terpisah), sehingga
# asyncio.Lock tetap efektif untuk sinkronisasi.
# ============================================================
async def proses_transaksi_background(trx_id: int, plant_id: int, qty: int):
    """Fungsi pekerja latar belakang untuk memproses transaksi."""
    try:
        # 1. Perbarui status menjadi 'processing' di basis data
        await db.update_trx_status(trx_id, "processing")

        # 2. Simulasi pekerjaan I/O intensif (misalnya: validasi pembayaran,
        #    notifikasi, pencetakan invoice, dsb.)
        await asyncio.sleep(3)

        # 3. Finalisasi: perbarui status menjadi 'completed'
        await db.update_trx_status(trx_id, "completed")

    except Exception:
        # Jika terjadi error, tandai transaksi sebagai 'failed'
        await db.update_trx_status(trx_id, "failed")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_transaction(data: TransactionCreate, bg: BackgroundTasks):
    """
    Membuat transaksi pembelian tanaman baru.

    Alur:
    1. Validasi: pastikan tanaman ada di database
    2. Pemotongan stok (dengan atau tanpa lock sesuai konfigurasi USE_LOCK)
    3. Simpan transaksi dengan status 'pending'
    4. Jalankan pemrosesan di latar belakang via BackgroundTasks
    5. Kembalikan response instan tanpa menunggu proses selesai

    Response langsung dikembalikan dengan status 'pending'.
    Client dapat memantau perubahan status via GET /transactions/{id}.
    """
    # Validasi: pastikan tanaman terdaftar di basis data
    plant = await db.get_plant_by_id(data.plant_id)
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tanaman dengan ID {data.plant_id} tidak ditemukan"
        )

    # Pemotongan stok: pilih versi berdasarkan konfigurasi USE_LOCK
    # Bagian ini adalah critical section yang rentan race condition
    if USE_LOCK:
        # Versi aman: asyncio.Lock menjamin mutual exclusion
        stok_cukup = await db.potong_stok_dengan_lock(data.plant_id, data.qty)
    else:
        # Versi tanpa lock: rentan race condition (untuk pengujian B3)
        stok_cukup = await db.potong_stok_tanpa_lock(data.plant_id, data.qty)

    if not stok_cukup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stok tidak mencukupi untuk transaksi ini"
        )

    # Hitung total harga
    total_harga = plant["harga"] * data.qty

    # Simpan transaksi dengan status awal 'pending'
    trx_id = await db.insert_transaction(
        plant_id=data.plant_id,
        qty=data.qty,
        total_harga=total_harga,
        status="pending"
    )

    # Jalankan pemrosesan di latar belakang menggunakan BackgroundTasks.
    # Response HTTP dikembalikan SEGERA tanpa menunggu fungsi ini selesai.
    # BackgroundTasks akan mengeksekusi proses_transaksi_background()
    # setelah response dikirim ke client.
    bg.add_task(proses_transaksi_background, trx_id, data.plant_id, data.qty)

    return {
        "id": trx_id,
        "status": "pending",
        "message": "Transaksi sedang diproses di latar belakang"
    }


@router.get("", response_model=list[TransactionResponse],
            status_code=status.HTTP_200_OK)
async def get_all_transactions(
    status_filter: str | None = Query(
        default=None, alias="status",
        description="Filter berdasarkan status: pending, processing, completed, failed"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Mengambil daftar transaksi dengan opsional filter status.
    Contoh: GET /transactions?status=pending&skip=0&limit=10
    """
    transactions = await db.get_all_transactions(
        status_filter=status_filter, skip=skip, limit=limit
    )
    return transactions


@router.get("/{trx_id}", response_model=TransactionResponse,
            status_code=status.HTTP_200_OK)
async def get_transaction(trx_id: int):
    """
    Mengambil detail satu transaksi beserta status terkini.
    Digunakan untuk memantau perubahan status dari pending -> processing -> completed.
    """
    transaction = await db.get_transaction_by_id(trx_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaksi dengan ID {trx_id} tidak ditemukan"
        )
    return transaction

