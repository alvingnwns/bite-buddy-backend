# Handout: Scan Food Endpoint (Fase 1)

## Arsitektur Endpoint: Paralel Asinkron

Fase 1 ini mengajarkan konsep penting dalam *Backend Engineering*: **Concurrency** menggunakan `asyncio.gather`. 

Bayangkan alur tradisional (Sequential):
1. User upload gambar makanan.
2. Server kirim gambar ke Cloud Storage (butuh waktu 1 detik).
3. Setelah selesai, server kirim gambar ke AI (butuh waktu 2 detik).
4. **Total waktu tunggu user:** 3 detik.

Di endpoint kita (`/api/v1/scan/food`), kita menggunakan alur Paralel:
1. User upload gambar.
2. Server mengirim gambar ke Cloud Storage **BERSAMAAN** dengan mengirim gambar ke AI.
3. Waktu selesai ditentukan oleh tugas yang paling lambat (AI = 2 detik).
4. **Total waktu tunggu user:** Hanya 2 detik! (Hemat 1 detik, sangat krusial untuk performa aplikasi).

Ini dicapai melalui blok kode di `scan.py`:
```python
upload_task = storage_service.upload_image(...)
ai_task = ai_service.detect_food(...)

# Keduanya berjalan bersamaan
public_url, detected_foods = await asyncio.gather(upload_task, ai_task)
```

## Komponen yang Dibangun

1. **`app/services/storage_service.py`**:
   - Memvalidasi agar file benar-benar gambar (jpg, png, webp).
   - Menolak file raksasa (>10MB).
   - Menyimpan ke bucket `food-photos` di Supabase.

2. **`app/services/ai_service.py`**:
   - Menghubungi Hugging Face Inference API menggunakan `httpx` yang non-blocking.
   - Mengatasi kasus "Cold Start" (Server AI sedang loading/status 503).
   - (Catatan: Saat token belum diatur, fungsi ini menggunakan *mock output* / hasil palsu agar endpoint tetap bisa diuji coba).

3. **`app/services/reasoning_service.py`**:
   - Mengambil hasil AI (seperti "apple", "sandwich") dan mengubahnya menjadi nilai nutrisi konkret (Kalori dan Karbohidrat).
   - Saat ini menggunakan dictionary statis sebagai *Proof of Concept* (POC).

## Bagaimana Cara Mengetesnya?

1. Pastikan server berjalan: `uvicorn app.main:app --reload`
2. Buka Swagger UI di browser: `http://127.0.0.1:8000/docs`
3. Cari endpoint `POST /api/v1/scan/food`.
4. Isi data:
   - `child_id`: UUID sembarang (contoh: `123e4567-e89b-12d3-a456-426614174000`)
   - `logged_by`: UUID parent
   - `meal_type`: Pilih `lunch`
   - `file`: Pilih gambar makanan apa saja dari komputermu.
5. Klik **Execute**.
6. Cek Supabase Dashboard mu:
   - Apakah gambar muncul di Storage `food-photos`?
   - Apakah data log muncul di tabel database `food_logs`?

> **Catatan Penting untuk Supabase Storage:**
> Fitur ini HANYA akan bekerja jika kamu sudah membuat bucket bernama `food-photos` secara manual di Dashboard Supabase dan mengaturnya ke Public. Jika belum, API akan melempar error HTTP 500 saat mencoba mengunggah.
