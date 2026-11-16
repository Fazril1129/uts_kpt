# routes/resource.py
# Endpoint CRUD untuk resource utama: Tanaman Hias (plants)
# Setiap endpoint menggunakan operasi asinkron (async/await)
# untuk mengakses database SQLite via aiosqlite secara non-blocking.

from fastapi import APIRouter, HTTPException, Query, status
from models import PlantCreate, PlantUpdate, PlantResponse
import database as db

router = APIRouter(prefix="/plants", tags=["Plants"])


@router.get("", response_model=list[PlantResponse], status_code=status.HTTP_200_OK)
async def get_all_plants(
    skip: int = Query(default=0, ge=0, description="Jumlah data yang dilewati"),
    limit: int = Query(default=10, ge=1, le=100, description="Jumlah data per halaman")
):
    """
    Mengambil daftar semua tanaman dengan pagination.
    Parameter ?skip=0&limit=10 wajib didukung.
    """
    plants = await db.get_all_plants(skip=skip, limit=limit)
    return plants


@router.get("/{plant_id}", response_model=PlantResponse, status_code=status.HTTP_200_OK)
async def get_plant(plant_id: int):
    """Mengambil detail satu tanaman berdasarkan ID."""
    plant = await db.get_plant_by_id(plant_id)
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tanaman dengan ID {plant_id} tidak ditemukan"
        )
    return plant


@router.post("", response_model=PlantResponse, status_code=status.HTTP_201_CREATED)
async def create_plant(data: PlantCreate):
    """
    Menambahkan tanaman baru.
    Validasi dilakukan otomatis oleh model Pydantic (PlantCreate).
    Mengembalikan data tanaman yang baru dibuat dengan status 201 Created.
    """
    plant_id = await db.create_plant(
        nama=data.nama,
        jenis=data.jenis,
        harga=data.harga,
        stok=data.stok,
        deskripsi=data.deskripsi,
        asal=data.asal
    )
    plant = await db.get_plant_by_id(plant_id)
    return plant


@router.put("/{plant_id}", response_model=PlantResponse, status_code=status.HTTP_200_OK)
async def update_plant(plant_id: int, data: PlantUpdate):
    """
    Memperbarui data tanaman berdasarkan ID.
    Mengembalikan data tanaman yang telah diperbarui.
    """
    existing = await db.get_plant_by_id(plant_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tanaman dengan ID {plant_id} tidak ditemukan"
        )
    await db.update_plant(
        plant_id=plant_id,
        nama=data.nama,
        jenis=data.jenis,
        harga=data.harga,
        stok=data.stok,
        deskripsi=data.deskripsi,
        asal=data.asal
    )
    updated = await db.get_plant_by_id(plant_id)
    return updated


@router.delete("/{plant_id}", status_code=status.HTTP_200_OK)
async def delete_plant(plant_id: int):
    """
    Menghapus tanaman secara permanen (hard delete) dari basis data.
    Mengembalikan pesan konfirmasi penghapusan.
    """
    existing = await db.get_plant_by_id(plant_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tanaman dengan ID {plant_id} tidak ditemukan"
        )
    await db.delete_plant(plant_id)
    return {"message": f"Tanaman '{existing['nama']}' berhasil dihapus"}

