# Handout Fitur: Perbaikan Spesifikasi (Phase 1-4) & Refactoring

## 1. Apa yang Telah Dikerjakan?
Pada fase ini, kita melakukan peninjauan ulang (*code-review*) dan perbaikan terhadap spesifikasi inti yang ada pada Fase 1 sampai 4. Berikut rinciannya:

### A. Perubahan Skema Database (DDL & Model)
- **Tabel `custom_meal_schedules`**: Menambahkan kolom `start_time` dan `end_time`. Ini bertujuan agar sistem bisa mengetahui secara pasti kapan "jendela waktu makan" untuk seorang anak berakhir.
- **Tabel `clinical_parameters`**: Menambahkan kolom `target_daily_calories` (kalori harian) dan `target_daily_carbs` (karbohidrat harian). Tujuannya agar perhitungan nutrisi tidak lagi menggunakan angka mutlak yang asal (seperti <= 500), namun menyesuaikan kondisi klinis unik masing-masing anak.

### B. Perbaikan Logika Gamification & Compliance
- **Gamification Service**: Kini saat menghitung *reward* setelah anak makan, fungsi akan otomatis mencari `target_daily_calories` dari *clinical parameters* anak tersebut di *database*. Ia memberikan poin berdasarkan batas toleransi.
- **Compliance Worker**: Pada *worker* latar belakang (APScheduler), ia sekarang tidak hanya mengecek minum obat, tapi juga mengambil daftar `custom_meal_schedules` pada hari ini. Jika waktu batas akhir (`end_time`) terlewat dan tidak ada log makan (`food_logs`), Virtual Pet langsung diberi penalti poin *happiness* dan penambahan kelaparan (*hunger*).

### C. Refactoring (Pembersihan Kode)
- **LogService**: Memisahkan semua logika yang bertugas merakit data (*DTO*) dan melakukan *insert* ke Supabase ke dalam servis mandiri (`app/services/log_service.py`). Akibatnya, `app/api/v1/scan.py` menjadi sangat bersih.
- **AI Service**: Menyatukan logika perulangan pemanggilan HTTP (*exponential backoff* dan penanganan server sibuk / *cold start*) ke dalam satu fungsi tersembunyi `_call_hf_api`. Ini membuat ukuran file mengecil dan membasmi kode duplikat.

## 2. Penjelasan Kode Secara Sederhana (Untuk Pembelajaran)
1. **Pydantic & Optional**: Pada file `database.py`, kamu akan melihat banyak pemakaian `Optional[time] = None`. `Optional` artinya field tersebut boleh diisi `None` (Null di database). Hal ini penting untuk menjaga agar kode yang sudah ada sebelumnya tidak error saat kolom baru ditambahkan, sebelum diisi secara manual.
2. **Asynchronous HTTP & Gather**: Walaupun *router* di `scan.py` dibersihkan, konsep `asyncio.gather(upload_task, ai_task)` tetap utuh. Ini artinya API tetap memproses *upload* gambar ke Supabase dan pemanggilan Hugging Face di saat yang **bersamaan** tanpa harus menunggu satu sama lain. Kecepatannya berlipat ganda.
3. **Pemisahan Tanggung Jawab (Separation of Concerns)**: Kini `scan.py` bertugas sebatas gerbang masuk (*Router*). Jika ia butuh memanggil AI, ia pakai `AIService`. Jika butuh menyimpan, ia panggil `LogService`. Jika butuh main *game*, ia panggil `GamificationService`. Pemisahan ini membuat kode mudah dilacak kalau ada *bug* (kalau gagal simpan DB, cek log service!).

## 3. Apa yang Harus Dikerjakan Selanjutnya?
- Kita harus **menjalankan migrasi SQL** yang ada di `migrations/003_spec_fixes.sql` ke dalam *dashboard* Supabase agar tabelnya sesuai dengan model Python terbaru.
- Setelah *database* tersinkronisasi, kita akhirnya bisa **melangkah ke Fase 5 (Real-time Synchronization)** dengan damai dan tenang.
