# locustfile.py
# Skrip pengujian beban (load testing) menggunakan Locust.
#
# Dua skenario pengujian:
# 1. ReadUser  : GET /plants          – simulasi pembacaan data tanaman
# 2. WriteUser : POST /transactions   – simulasi transaksi pembelian
#
# Cara menjalankan:
#   1 Worker : uvicorn main:app --workers 1 --port 8000
#   4 Workers: uvicorn main:app --workers 4 --port 8000
#
# Jalankan Locust:
#   locust -f locustfile.py --host=http://127.0.0.1:8000
#
# Atau tanpa UI (headless mode):
#   Skenario Read  (100 request, konkurensi 20):
#     locust -f locustfile.py --host=http://127.0.0.1:8000 ReadUser --headless -u 20 -r 20 --run-time 30s
#
#   Skenario Write (50 request, konkurensi 10):
#     locust -f locustfile.py --host=http://127.0.0.1:8000 WriteUser --headless -u 10 -r 10 --run-time 30s

from locust import HttpUser, task, between
import random


class ReadUser(HttpUser):
    """
    Skenario Read: mengakses endpoint GET /plants.
    Mensimulasikan pengguna yang browsing katalog tanaman.
    """
    wait_time = between(0.1, 0.5)

    @task(3)
    def get_all_plants(self):
        """Mengambil daftar tanaman dengan pagination acak."""
        skip = random.randint(0, 5)
        limit = random.randint(5, 10)
        self.client.get(f"/plants?skip={skip}&limit={limit}", name="/plants")

    @task(1)
    def get_single_plant(self):
        """Mengambil detail satu tanaman secara acak."""
        plant_id = random.randint(1, 12)
        self.client.get(f"/plants/{plant_id}", name="/plants/[id]")


class WriteUser(HttpUser):
    """
    Skenario Write: mengakses endpoint POST /transactions.
    Mensimulasikan pengguna yang melakukan pembelian tanaman.
    """
    wait_time = between(0.5, 1.0)

    @task
    def create_transaction(self):
        """Membuat transaksi pembelian dengan data acak."""
        payload = {
            "plant_id": random.randint(1, 12),
            "qty": random.randint(1, 3)
        }
        self.client.post("/transactions", json=payload, name="/transactions")



# ============================================================
# Pembatas jumlah request (untuk benchmark C1).
# Jika variabel lingkungan MAX_REQUESTS diisi (mis. 100 untuk Read,
# 50 untuk Write), Locust berhenti otomatis setelah jumlah request
# tersebut tercapai, lalu mencetak total waktu, throughput, dan
# rata-rata latensi. Tanpa MAX_REQUESTS, perilaku Locust tidak berubah.
# ============================================================
import os
import json
import time
from locust import events

_MAX_REQUESTS = int(os.getenv("MAX_REQUESTS", "0"))
_state = {"count": 0, "t0": None, "env": None, "done": False}


@events.init.add_listener
def _on_init(environment, **kwargs):
    _state["env"] = environment


@events.request.add_listener
def _on_request(**kwargs):
    if not _MAX_REQUESTS or _state["done"]:
        return
    if _state["t0"] is None:
        _state["t0"] = time.time() - (kwargs.get("response_time") or 0) / 1000
    _state["count"] += 1
    if _state["count"] >= _MAX_REQUESTS:
        _state["done"] = True
        total = time.time() - _state["t0"]
        stats = _state["env"].stats.total
        print("RESULT " + json.dumps({
            "requests": _state["count"],
            "failures": stats.num_failures,
            "total_time_s": round(total, 3),
            "throughput_rps": round(_state["count"] / total, 2),
            "avg_latency_ms": round(stats.avg_response_time, 2),
        }), flush=True)
        _state["env"].runner.quit()
