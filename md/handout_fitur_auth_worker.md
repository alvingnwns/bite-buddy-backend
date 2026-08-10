# Handout Fitur: JWT Authentication & Compliance Worker

## Apa yang Telah Dikerjakan?
Pada fase ini (Fase 5), kita telah memperkuat keamanan backend sekaligus menyempurnakan fitur *background worker* untuk kepatuhan medis:

1. **Deduplikasi Penalty (Compliance Worker):** 
   - Modul `compliance_worker.py` sekarang memiliki mekanisme pengecekan `last_penalty_date`.
   - Ini memecahkan masalah di mana anak bisa mendapatkan penalti *Health/Happiness* berulang-ulang untuk jadwal makan yang sama dalam satu hari. Penalti kini dipastikan hanya berlaku satu kali per jadwal yang dilewatkan per harinya.
2. **Stateless JWT Authentication:**
   - Telah ditambahkan modul `app/core/auth.py` yang memverifikasi JSON Web Token (JWT) dari Supabase.
   - Endpoint profil (`/api/v1/users/me`) kini dilindungi oleh dependensi FastAPI `Depends(get_current_user)`.
   - Jika pengguna mengirimkan token yang kedaluwarsa atau tidak valid pada header `Authorization`, backend akan menolaknya dengan status `HTTP 401 Unauthorized`.
3. **Pengaturan Konfigurasi (Environment Variables):**
   - Variabel `SUPABASE_JWT_SECRET` kini wajib ada untuk memvalidasi _signature_ token dari Supabase (menggunakan algoritma HS256).

## Apa yang Harus Dikerjakan dari Handout Ini?
Dari sisi **Frontend (Mobile App / Web Dashboard)**, Developer harus:
1. Menangani proses Login & Register menggunakan **Supabase Client SDK** secara langsung dari perangkat pengguna (tanpa melalui API backend kita).
2. Setelah pengguna berhasil login, ekstrak `access_token` dari sesi Supabase.
3. Sisipkan token tersebut pada setiap HTTP Request ke backend (FastAPI) yang membutuhkan *authentication*, dengan format *header*:
   ```http
   Authorization: Bearer <access_token>
   ```
4. Pastikan variabel lingkungan `SUPABASE_JWT_SECRET` di *production server* Backend sama persis dengan yang ada di *Project Settings > API* di dashboard Supabase milikmu.
5. Coba lakukan HTTP GET ke `/api/v1/users/me` dengan membawa token untuk mengetes apakah integrasinya sudah benar.

---
**Status Fitur:** SELESAI ✅
**Catatan untuk Developer:** Arsitektur *Auth* ini sepenuhnya bergantung pada Supabase untuk mengurangi beban database kita secara signifikan.
