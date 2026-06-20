# Handout: Scan Medicine & Insulin Endpoint (Fase 2)

## Konsep Keamanan Medis (Medical Safety)

Pada fase ini, kita mengimplementasikan endpoint `/api/v1/scan/medicine` untuk mengenali pen insulin. Berbeda dengan deteksi makanan di Fase 1 di mana AI menebak **kalori**, pada deteksi obat ini kita menerapkan **aturan keamanan medis yang ketat**:

1. **AI Hanya Menebak Jenis Obat**: Model AI (misal: YOLOv8) hanya bertugas menebak *jenis* insulin dari bungkus/pen-nya (misal: "NovoRapid", "Lantus").
2. **Dosis Wajib Manual**: AI **tidak boleh** dan tidak diizinkan menebak berapa dosis (dosage) yang akan disuntikkan. Dosis ini terlalu berisiko (fatal jika salah baca angka dari gambar). Oleh karena itu, parameter `dosage` pada endpoint ini di-set sebagai parameter *form* wajib (`Form(..., gt=0)`).

## Komponen yang Diperbarui

1. **`app/services/ai_service.py`**:
   - Menambahkan fungsi `detect_medicine(image_bytes)`.
   - Menggunakan URL model Hugging Face khusus deteksi objek/obat (saat ini menggunakan model ResNet/klasifikasi umum sebagai placeholder/mock).
   - Mempertahankan fitur ketahanan yang sama: *Exponential Backoff Retry* (menunggu 2, 4, 8 detik jika server AI merespons 503 Cold Start).

2. **`app/api/v1/scan.py`**:
   - Menambahkan `POST /api/v1/scan/medicine`.
   - Menerapkan arsitektur paralel `asyncio.gather` untuk mengirim gambar ke *Supabase Storage* (bucket: `medicine-photos`) sekaligus meminta *AI Service* mendeteksi jenis obat.
   - Karena tabel `medication_logs` secara default tidak memiliki kolom `photo_url`, URL publik dari gambar disisipkan ke dalam kolom `notes` menggunakan format `[Photo URL: ...]`.

## Bagaimana Cara Mengetesnya?

1. Pastikan server berjalan: `uvicorn app.main:app --reload`
2. Buka Swagger UI di browser: `http://127.0.0.1:8000/docs`
3. Cari endpoint `POST /api/v1/scan/medicine`.
4. Isi data:
   - `child_id`: UUID sembarang (contoh: `123e4567-e89b-12d3-a456-426614174000`)
   - `administered_by`: UUID parent
   - `dosage`: Masukkan angka dosis (misal: `12.5`)
   - `dosage_unit`: Masukkan satuan (misal: `IU`)
   - `route`: `subcutaneous` (suntikan bawah kulit)
   - `file`: Pilih gambar botol atau pen insulin dari komputermu.
5. Klik **Execute**.
6. Cek Supabase Dashboard mu:
   - Apakah gambar muncul di Storage `medicine-photos`?
   - Apakah data masuk ke tabel `medication_logs` dengan dosis yang kamu inputkan secara manual?

> **Catatan Penting untuk Supabase Storage:**
> Fitur ini HANYA akan bekerja jika kamu sudah membuat bucket bernama `medicine-photos` secara manual di Dashboard Supabase dan mengaturnya ke Public. Jika belum, API akan melempar error HTTP 500 saat mencoba mengunggah.
