# models.py
# Skema Pydantic untuk validasi request body dan serialisasi response.
# Pydantic memastikan data yang masuk sesuai tipe dan constraint yang ditentukan.

from pydantic import BaseModel, Field
from typing import Optional


# ==================== Skema Resource Utama (Tanaman) ====================

class PlantCreate(BaseModel):
    """Skema validasi untuk membuat tanaman baru (request body POST)."""
    nama: str = Field(..., min_length=1, max_length=100, description="Nama tanaman")
    jenis: str = Field(..., min_length=1, max_length=50, description="Jenis/kategori tanaman")
    harga: float = Field(..., gt=0, description="Harga tanaman (Rupiah)")
    stok: int = Field(..., ge=0, description="Jumlah stok tersedia")
    deskripsi: str = Field(..., min_length=1, max_length=500, description="Deskripsi tanaman")
    asal: str = Field(..., min_length=1, max_length=100, description="Asal/daerah tanaman")


class PlantUpdate(BaseModel):
    """Skema validasi untuk memperbarui tanaman (request body PUT)."""
    nama: str = Field(..., min_length=1, max_length=100)
    jenis: str = Field(..., min_length=1, max_length=50)
    harga: float = Field(..., gt=0)
    stok: int = Field(..., ge=0)
    deskripsi: str = Field(..., min_length=1, max_length=500)
    asal: str = Field(..., min_length=1, max_length=100)


class PlantResponse(BaseModel):
    """Skema serialisasi response untuk data tanaman."""
    id: int
    nama: str
    jenis: str
    harga: float
    stok: int
    deskripsi: str
    asal: str


# ==================== Skema Transaksi ====================

class TransactionCreate(BaseModel):
    """Skema validasi untuk membuat transaksi baru (request body POST)."""
    plant_id: int = Field(..., gt=0, description="ID tanaman yang dibeli")
    qty: int = Field(..., gt=0, description="Jumlah tanaman yang dibeli")


class TransactionResponse(BaseModel):
    """Skema serialisasi response untuk data transaksi."""
    id: int
    plant_id: int
    qty: int
    total_harga: float
    status: str
    created_at: str

