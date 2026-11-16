# test_race.py
# Skrip pengujian mandiri untuk mendeteksi race condition pada
# operasi pemotongan stok saat dua transaksi masuk secara bersamaan.
#
# Pengujian ini mengirimkan 2 request POST /transactions secara
# serentak (concurrent) ke server FastAPI menggunakan asyncio.gather().
#
# Skenario pengujian:
# - Stok tanaman diatur menjadi 1
# - Dua pembeli mencoba membeli tanaman yang sama (qty=1) secara bersamaan
# - TANPA lock: kedua transaksi berhasil -> stok menjadi negatif (overselling)
# - DENGAN lock: hanya satu transaksi berhasil, yang lain ditolak 409 Conflict
#
# Cara menjalankan:
#   Terminal 1: uvicorn main:app --port 8000
#   Terminal 2: python test_race.py

import asyncio
import httpx


async def main():
    """Mengirim 2 request pembelian secara serentak untuk menguji race condition."""
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/transactions"

    # Payload: membeli tanaman ID 1 sebanyak 1 unit
    payload = {"plant_id": 1, "qty": 1}

    print("=" * 60)
    print("🧪 Pengujian Race Condition - Toko Tanaman Hias")
    print("=" * 60)

    # Cek stok awal sebelum transaksi
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{base_url}/plants/1")
        if res.status_code == 200:
            plant = res.json()
            print(f"\n📦 Stok awal '{plant['nama']}': {plant['stok']}")
        else:
            print("❌ Gagal mengambil data tanaman. Pastikan server berjalan dan seed.py sudah dijalankan.")
            return

    print(f"\n🚀 Mengirim 2 request POST /transactions secara serentak...")
    print(f"   Payload: {payload}\n")

    async with httpx.AsyncClient() as client:
        # Kirim dua request secara serentak dalam milidetik yang sama
        # menggunakan asyncio.gather() agar kedua request berjalan concurrent
        req1 = client.post(url, json=payload)
        req2 = client.post(url, json=payload)

        res1, res2 = await asyncio.gather(req1, req2)

    # Tampilkan hasil kedua request
    print(f"📨 Respon Request 1: [{res1.status_code}] {res1.json()}")
    print(f"📨 Respon Request 2: [{res2.status_code}] {res2.json()}")

    # Cek stok akhir setelah transaksi
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{base_url}/plants/1")
        if res.status_code == 200:
            plant = res.json()
            stok_akhir = plant["stok"]
            print(f"\n📦 Stok akhir '{plant['nama']}': {stok_akhir}")

            # Analisis hasil
            print("\n" + "=" * 60)
            if stok_akhir < 0:
                print("⚠️  RACE CONDITION TERDETEKSI!")
                print("   Stok menjadi negatif (overselling).")
                print("   Kedua request berhasil karena tidak ada mekanisme lock.")
            elif res1.status_code == 201 and res2.status_code == 201:
                print("⚠️  Kedua request berhasil. Periksa apakah stok negatif.")
            else:
                print("✅ LOCK BERHASIL MENCEGAH RACE CONDITION!")
                print("   Hanya satu transaksi yang berhasil.")
                print("   Transaksi kedua ditolak dengan 409 Conflict.")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

