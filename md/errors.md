# Error Log - BiteBuddy

## 2026-08-12

### Error 1: PGRST205 - Table `public.alerts` not found
- **Penyebab**: SQL migration `005_alerts_table.sql` belum dijalankan di Supabase SQL Editor
- **Solusi**: User harus menjalankan (execute) query tersebut manual di Supabase dashboard
- **Status**: Resolved (user telah run query)

### Error 2: 404 Not Found pada `GET /api/v1/users/me`
- **Penyebab**: Saat register via `supabase.auth.signUp()`, data hanya masuk ke `auth.users`, BUKAN ke `public.users`. Endpoint `/users/me` mencari di `public.users` → tidak ketemu → 404
- **Solusi**: 
  1. Tambah insert ke `public.users` setelah `signUp` di `register.tsx`
  2. Tambah auto-create user di endpoint `/users/me` di `users.py` jika belum ada
- **Status**: Fixed

### Error 3: 405 Method Not Allowed pada `GET /api/v1/schedules/`
- **Penyebab**: Frontend memanggil `GET /schedules/` tanpa `child_id`. Backend hanya punya `POST /` dan `GET /{child_id}`
- **Solusi**: Ubah `schedule.tsx` → `apiClient.get('/schedules/${user.id}')`
- **Status**: Fixed

### Error 4: 500 Internal Server Error pada `GET /api/v1/users/me`
- **Penyebab**: Auto-create user gagal karena kolom `public.users` memiliki constraint NOT NULL pada field yang tidak dikirim (e.g. `password_hash`)
- **Solusi**: Perlu di-cek ulang apakah schema `public.users` mewajibkan `password_hash` atau tidak
- **Status**: Monitoring

### Error 5: Analysis Result selalu menampilkan data yang sama
- **Penyebab**: `scan.tsx` hanya mengirim `food_name` dan `xp_gained` ke `analysis.tsx`, tidak mengirim data nutrisi dari API. `analysis.tsx` menampilkan hardcoded values sebagai default
- **Solusi**: Kirim `ingredients` array dari API response ke analysis page, hitung nutrisi dari data berat riil
- **Status**: Fixed

### Error 6: Pet HP/XP tidak berubah, Level mulai dari 5, 404 pada /pets
- **Penyebab**: Frontend fetch ke endpoint yang salah atau database belum ada pet untuk child tsb.
- **Solusi**: Update `GET /pets/{child_id}` untuk auto-create profil Pet saat pertama kali user membuka dashboard. Level diset default 1.
- **Status**: Fixed

### Error 7: Medicine API 404/Error
- **Penyebab**: Halaman `meds.tsx` memanggil endpoint `/scan/medicine/analyze` yang tidak ada.
- **Solusi**: Ubah ke `/scan/medicine` dan tambahkan field default (`dosage`, `route`, dll).
- **Status**: Fixed

### Error 8: asyncio.exceptions.CancelledError pada Uvicorn
- **Penyebab**: APScheduler (Scheduler background job) dihentikan paksa saat Uvicorn melakukan "hot-reload" karena file berubah.
- **Solusi**: Ini adalah behavior normal dari FastAPI/Uvicorn saat mode `--reload`. Tidak perlu diperbaiki karena hanya muncul saat development.
- **Status**: Ignored (Aman)

### Error 9: Today's Schedule belum berjalan
- **Penyebab**: Belum ada dashboard Parent/Doctor untuk menginput jadwal ke database.
- **Solusi**: Untuk sementara aplikasi memunculkan data *dummy* jika backend me-return data kosong.
- **Status**: Menunggu pengembangan fitur Parent & Doctor.

### Error 9: `SUPABASE_JWT_SECRET` tidak diatur
- **Penyebab**: Field `supabase_jwt_secret` kosong di `.env` backend
- **Dampak**: Token di-decode tanpa verifikasi signature (tidak aman untuk production)
- **Solusi**: Ambil JWT secret dari Supabase Dashboard → Project Settings → API → JWT Secret, tambahkan ke `.env`
- **Status**: Pending (user perlu menambahkan)

### Error 10: 500 Internal Server Error (Foreign Key Constraint on food_logs)
- **Penyebab**: Script `seed_users.py` gagal meng-*upsert* data ke `public.users` saat menemui error "user already registered" pada `auth.users`, sehingga UUID antara `auth.users` dan `public.users` tidak tersinkronisasi/kosong, menyebabkan operasi yang membutuhkan `child_id` (seperti insert ke `food_logs`) gagal di database (violates foreign key constraint).
- **Solusi**: Script `seed_users.py` telah diperbaiki agar menangkap pesan "already been registered", mengambil UUID dari `auth.users`, dan menyimpannya ke `public.users`. Akun lama dengan UUID mismatch (e221edbf-...) di public.users telah dihapus dan di-*seed* ulang.
- **Status**: Fixed

### Error 11: XP dan Level Pet tidak bertambah setelah Scan Makanan
- **Penyebab**: Ada dua faktor utama:
  1. **Race Condition Pet Creation**: User melakukan *Scan* (Confirm Food) **sebelum** profil pet sempat terbuat di dashboard. Service gamifikasi tidak menemukan pet dan membuang EXP tersebut (0 EXP).
  2. **Rule Engine AI**: Makanan yang di-scan (contoh: Spaghetti) dievaluasi oleh Gemini AI sebagai `is_healthy: False` (kurang sehat/tinggi karbo). Berdasarkan *rule engine* di `gamification_service`, makanan tidak sehat memberikan `0 EXP` dan penalti `-20 Happiness`.
- **Solusi**: 
  - Ditambahkan auto-create profil Pet secara langsung di dalam `gamification_service.update_pet_status()` sebagai *fallback* agar EXP tidak hilang meskipun user belum pernah membuka dashboard.
  - Edukasi ke user bahwa makanan tidak sehat (Junk Food/Tinggi Karbo) memang disengaja tidak memberikan EXP.
- **Status**: Fixed
