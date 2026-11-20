[VIDEO PRESENTASI: https://youtu.be/XrrQo7g5n_g

# 🌿 Toko Tanaman Hias API

REST API untuk manajemen toko tanaman hias yang dibangun menggunakan **FastAPI** (Python 3.10+) dengan database **SQLite** melalui pustaka **aiosqlite** secara asinkron. Aplikasi ini mendukung operasi CRUD tanaman, transaksi pembelian dengan pemrosesan latar belakang (BackgroundTasks), dan mekanisme pencegahan race condition menggunakan `asyncio.Lock`.

## 📋 Fitur Utama

- **CRUD Tanaman**: Tambah, lihat, perbarui, dan hapus data tanaman hias
- **Transaksi Asinkron**: Pemrosesan pembelian di latar belakang dengan alur status `pending → processing → completed`
- **Race Condition Prevention**: Mekanisme `asyncio.Lock` untuk mencegah overselling
- **Validasi Data**: Model Pydantic untuk validasi request dan response
- **Pagination**: Dukungan parameter `?skip=0&limit=10` pada endpoint list

## 🏗️ Arsitektur

```
Klien HTTP ──► FastAPI (Uvicorn) ──► aiosqlite ──► SQLite
                    │
                    ├── BackgroundTasks (proses transaksi)
                    └── asyncio.Lock (pencegahan race condition)
```

## 📁 Struktur Direktori

```
uts-kpt/
├── main.py              # Inisialisasi FastAPI dan registrasi router
├── database.py          # Koneksi aiosqlite dan inisialisasi tabel
├── models.py            # Skema Pydantic (request dan response)
├── routes/
│   ├── __init__.py
│   ├── resource.py      # Endpoint CRUD tanaman hias
│   └── transaction.py   # Endpoint transaksi asinkron
├── seed.py              # Skrip inisialisasi minimal 12 data awal
├── test_race.py         # Skrip pengujian race condition
├── locustfile.py        # Skenario pengujian beban Locust
├── requirements.txt     # Daftar pustaka dependensi Python
└── docs/
    └── laporan_uts.pdf  # Laporan hasil pengujian dan analisis
```

## 🚀 Panduan Instalasi

### Prasyarat
- Python 3.10 atau lebih baru
- pip (Python package manager)

### Langkah Instalasi

1. **Clone repositori:**
   ```bash
   git clone https://github.com/username/toko-tanaman.git
   cd toko-tanaman
   ```

2. **Buat virtual environment (opsional tapi disarankan):**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inisialisasi data awal:**
   ```bash
   python seed.py
   ```

## ▶️ Panduan Eksekusi

### Menjalankan Server

**1 Worker (default):**
```bash
uvicorn main:app --port 8000
```

**4 Workers (multi-worker):**
```bash
uvicorn main:app --workers 4 --port 8000
```

### Mengakses API

- **Swagger UI (Dokumentasi Interaktif):** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc
- **Root Endpoint:** http://127.0.0.1:8000/

### Tabel Endpoint

| Method | Path                  | Keterangan                                |
|--------|-----------------------|-------------------------------------------|
| GET    | `/plants`             | Daftar tanaman (`?skip=0&limit=10`)       |
| GET    | `/plants/{id}`        | Detail satu tanaman                       |
| POST   | `/plants`             | Tambah tanaman baru                       |
| PUT    | `/plants/{id}`        | Perbarui data tanaman                     |
| DELETE | `/plants/{id}`        | Hapus tanaman (hard delete)               |
| POST   | `/transactions`       | Buat transaksi (response: pending)        |
| GET    | `/transactions`       | Daftar transaksi (`?status=pending`)      |
| GET    | `/transactions/{id}`  | Detail & status transaksi                 |

## 🧪 Pengujian Race Condition (B3)

### Tahap 1: Tanpa Lock
1. Buka `routes/transaction.py`, ubah `USE_LOCK = False`
2. Set stok tanaman ID 1 menjadi 1 (via PUT atau reset database)
3. Jalankan server:
   ```bash
   uvicorn main:app --port 8000
   ```
4. Jalankan skrip pengujian di terminal terpisah:
   ```bash
   python test_race.py
   ```
5. **Hasil:** Kedua transaksi berhasil → stok menjadi negatif (overselling)

### Tahap 2: Dengan Lock
1. Buka `routes/transaction.py`, ubah `USE_LOCK = True`
2. Reset stok tanaman ID 1 menjadi 1
3. Jalankan ulang server dan skrip pengujian
4. **Hasil:** Hanya satu transaksi berhasil, yang lain ditolak (409 Conflict)

## 📊 Pengujian Beban (C1)

### Menggunakan Locust

```bash
# Jalankan Locust Web UI
locust -f locustfile.py --host=http://127.0.0.1:8000

# Atau headless mode:
# Skenario Read (100 request, konkurensi 20)
locust -f locustfile.py ReadUser --host=http://127.0.0.1:8000 --headless -u 20 -r 20 --run-time 30s

# Skenario Write (50 request, konkurensi 10)
locust -f locustfile.py WriteUser --host=http://127.0.0.1:8000 --headless -u 10 -r 10 --run-time 30s
```

## 📚 Referensi

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [aiosqlite Documentation](https://aiosqlite.omnilib.dev)
- [Uvicorn](https://www.uvicorn.org)
- [Locust Load Testing](https://locust.io)


### Pengujian

- **Race condition (B3):** jalankan server, lalu `python test_race.py`. Ubah `USE_LOCK` di `routes/transaction.py` (`False` = tanpa lock, `True` = dengan lock) dan atur stok tanaman ID 1 menjadi 1 sebelum tiap pengujian.
- **Beban (C1):** `set MAX_REQUESTS=100` lalu `locust -f locustfile.py --host=http://127.0.0.1:8000 ReadUser --headless -u 20 -r 20`; untuk Write gunakan `MAX_REQUESTS=50`, `WriteUser`, `-u 10 -r 10`. Locust berhenti otomatis dan mencetak baris `RESULT` (total waktu, throughput, latensi).
- **Laporan:** `docs/laporan_uts.pdf`
