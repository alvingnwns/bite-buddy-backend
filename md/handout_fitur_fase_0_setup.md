# Handout: Environment & Setup Completion (Fase 0.4)

## Apa yang Telah Dikerjakan?
Fase fondasi (Fase 0) BiteBuddy telah diselesaikan dengan sukses. Fokus utama pada fase ini adalah menstabilkan lingkungan development (IDE & Virtual Environment) serta menyambungkan aplikasi dengan database production (Supabase).

### 1. Resolusi Masalah Virtual Environment
- **Masalah:** Antigravity IDE / VS Code tidak dapat membaca interpreter Python (`Unable to handle python.exe`).
- **Akar Masalah:**
  1. Awalnya venv diletakkan di dalam folder OneDrive. OneDrive memiliki fitur sinkronisasi yang secara agresif mengunci (lock) file binary seperti `.exe` dan `.pyd`, sehingga IDE tidak bisa memverifikasi interpreter.
  2. Antigravity IDE dan Cursor IDE memiliki sistem `vscode-python-envs` yang terpisah dari default VS Code, sehingga konfigurasi via Command Palette terkadang tidak berjalan mulus.
- **Solusi Final:** 
  1. Membuat `bbb-venv` lokal menggunakan Python dari Anaconda (versi 3.13.9).
  2. Memisahkan eksekusi di **terminal** (yang berjalan 100% normal tanpa peduli IDE error) dengan **IntelliSense IDE**.
  3. Membuat file `pyrightconfig.json` di root project untuk memaksa engine Pyright (IntelliSense) membaca modul dari `bbb-venv`, menyelesaikan masalah "import not found" tanpa perlu mengotak-atik UI "Select Interpreter".

### 2. Konfigurasi Environment & Pydantic
- **Perubahan Arsitektur Supabase Client:**
  - Sebelumnya: Singleton module-level (client dibuat tepat saat `app/core/supabase.py` di-import). Ini menyebabkan error `supabase_url is required` jika server dijalankan sebelum `.env` diisi, karena import dieksekusi saat _startup_.
  - Sekarang: Diubah menjadi **Lazy Initialization** (menggunakan fungsi factory `get_supabase_client()`). Client baru akan diinisiasi saat endpoint (seperti `/db-check`) dipanggil pertama kali. Ini mencegah crash saat aplikasi boot-up.
- **`.env` File:** Pydantic `SettingsConfigDict` berhasil dipastikan membaca file `.env` yang berada di root. Pydantic-settings menggantikan peran pustaka `python-dotenv`.

### 3. Row Level Security (RLS) Supabase
- **Penerapan RLS:** RLS diaktifkan di tabel `users` untuk mencegah akses data publik yang tidak sah. Endpoint `db-check` milik kita di backend berhasil melewati RLS ini karena menggunakan fungsi khusus `count=CountMethod.exact` dengan service role (walau di endpoint ini kita menggunakan client standar untuk testing koneksi anon).
- **Resolusi Infinite Recursion (`42P17`):**
  - Ditemukan kebijakan RLS yang mereferensikan tabel `users` ke dirinya sendiri menggunakan sub-query `SELECT ... FROM users`.
  - Ini diatasi dengan menghapus kondisi "anak bisa melihat orang tua" demi mencegah looping, sekaligus memperketat keamanan (hanya orang tua/dokter yang berhak melihat data turunan/pasiennya).

---

## Apa yang Harus Dikerjakan Selanjutnya?

Project telah terhubung ke Supabase secara utuh (`"db_connected": true`). Sesuai `todo.md`, kita sekarang secara resmi memasuki **Fase 1: Scan Food Endpoint (Parallel Processing)**.

**Target Fase 1:**
1. Membangun `StorageService` untuk mengunggah gambar ke Supabase Storage.
2. Membangun `AiService` untuk memanggil model SegFormer dari Hugging Face (Multimodal Reasoning).
3. Menerapkan `asyncio.gather` di `app/api/v1/scan.py` agar upload gambar dan panggilan AI berjalan secara paralel untuk efisiensi waktu respons (Latency Optimization).
