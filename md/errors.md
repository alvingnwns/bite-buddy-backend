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

### Error 6: Pet HP/XP tidak berubah, Level mulai dari 5
- **Penyebab**: `child/index.tsx` fetch data dari `/users/me` bukan dari `/pets/{child_id}`, dan menggunakan hardcoded fallback `{ health: 96, exp: 67, level: 5 }`
- **Solusi**: Fetch dari `/pets/${user.id}` dan gunakan default level 1
- **Status**: Fixed

### Error 7: Login page overlap pada layar kecil
- **Penyebab**: Footer menggunakan `position: 'absolute', bottom: 50` yang bisa overlap dengan form card
- **Solusi**: Wrap dalam ScrollView, gunakan flexbox centering bukan absolute positioning
- **Status**: Fixed

### Error 8: CORS blocking mobile requests
- **Penyebab**: `CORS_ORIGINS` hanya mengizinkan `localhost:3000` dan `localhost:8081`, tapi mobile mengirim request dari IP `192.168.1.10`
- **Solusi**: Set `CORS_ORIGINS=*` di `.env` untuk development
- **Status**: Fixed

### Error 9: `SUPABASE_JWT_SECRET` tidak diatur
- **Penyebab**: Field `supabase_jwt_secret` kosong di `.env` backend
- **Dampak**: Token di-decode tanpa verifikasi signature (tidak aman untuk production)
- **Solusi**: Ambil JWT secret dari Supabase Dashboard → Project Settings → API → JWT Secret, tambahkan ke `.env`
- **Status**: Pending (user perlu menambahkan)
