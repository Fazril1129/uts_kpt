# seed.py
# Skrip inisialisasi data awal (seeding) untuk database toko tanaman hias.
# Memasukkan minimal 10 data tanaman agar endpoint dapat langsung diuji.
#
# Cara menjalankan:
#   python seed.py

import asyncio
import aiosqlite
from database import DATABASE, init_db

# Data awal: 12 tanaman hias dengan variasi jenis dan asal
SEED_DATA = [
    ("Monstera Deliciosa", "Daun Hias", 150000, 25, "Tanaman hias tropis dengan daun berlubang yang ikonik", "Amerika Tengah"),
    ("Aglonema Red Valentine", "Daun Hias", 85000, 40, "Aglonema dengan daun merah menyala yang cantik", "Filipina"),
    ("Kaktus Gymnocalycium", "Kaktus", 35000, 60, "Kaktus mini berbunga dengan perawatan mudah", "Amerika Selatan"),
    ("Sansevieria Trifasciata", "Daun Hias", 45000, 50, "Lidah mertua, tanaman pembersih udara terbaik", "Afrika Barat"),
    ("Calathea Orbifolia", "Daun Hias", 120000, 15, "Tanaman hias dengan motif daun garis-garis silver", "Bolivia"),
    ("Succulent Echeveria", "Sukulen", 25000, 80, "Sukulen berbentuk roset dengan warna pastel", "Meksiko"),
    ("Philodendron Pink Princess", "Daun Hias", 250000, 10, "Philodendron langka dengan variegasi pink alami", "Kolombia"),
    ("Lavender French", "Bunga Hias", 55000, 35, "Tanaman bunga aromatik berwarna ungu menenangkan", "Prancis"),
    ("Bonsai Serut", "Bonsai", 200000, 8, "Bonsai serut miniatur dengan bentuk artistik", "Jawa Tengah"),
    ("Anggrek Bulan Putih", "Bunga Hias", 95000, 20, "Phalaenopsis putih elegan, bunga nasional Indonesia", "Indonesia"),
    ("Pilea Peperomioides", "Daun Hias", 65000, 30, "Tanaman koin Cina dengan daun bulat menggemaskan", "Tiongkok"),
    ("Adenium Obesum", "Bunga Hias", 75000, 18, "Kamboja jepang dengan bunga merah muda cerah", "Afrika Timur"),
]


async def seed():
    """Memasukkan data awal ke tabel plants."""
    await init_db()

    async with aiosqlite.connect(DATABASE) as db:
        # Cek apakah tabel sudah berisi data
        cursor = await db.execute("SELECT COUNT(*) FROM plants")
        count = (await cursor.fetchone())[0]

        if count > 0:
            print(f"⚠️  Database sudah berisi {count} data tanaman. Seed dibatalkan.")
            print("   Hapus file toko_tanaman.db terlebih dahulu jika ingin seed ulang.")
            return

        # Insert semua data seed
        await db.executemany(
            """INSERT INTO plants (nama, jenis, harga, stok, deskripsi, asal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            SEED_DATA
        )
        await db.commit()
        print(f"✅ Berhasil memasukkan {len(SEED_DATA)} data tanaman ke database.")

    # Tampilkan data yang telah dimasukkan
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, nama, jenis, harga, stok FROM plants")
        rows = await cursor.fetchall()

        print("\n📋 Daftar Tanaman:")
        print("-" * 70)
        print(f"{'ID':<4} {'Nama':<30} {'Jenis':<12} {'Harga':>10} {'Stok':>5}")
        print("-" * 70)
        for row in rows:
            print(f"{row['id']:<4} {row['nama']:<30} {row['jenis']:<12} Rp{row['harga']:>8,.0f} {row['stok']:>5}")
        print("-" * 70)


if __name__ == "__main__":
    asyncio.run(seed())

