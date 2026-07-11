# Handout Fitur: API Endpoints Tambahan (CRUD) - Fase 6

## 📌 Ringkasan
Semua endpoint dasar untuk kebutuhan CRUD (Create, Read, Update, Delete) entitas-entitas utama telah ditambahkan. Endpoint-endpoint ini dikelompokkan ke dalam rute tersendiri di bawah `/api/v1/`.

Karena kita belum masuk ke Fase 7 (Autentikasi Supabase), fungsi autentikasi saat ini adalah **MOCK** (tiruan).
Mock user `me` selalu mengembalikan UUID `00000000-0000-0000-0000-000000000000`.

> **⚠️ PERHATIAN**: UUID `00000000-0000-0000-0000-000000000000` harus terdaftar di tabel `users` database Supabase agar endpoint `GET /api/v1/users/me` tidak mengembalikan *Error 404*.

## 📡 Daftar Endpoints

### 1. User & Profile (`/api/v1/users`)
- `GET /me`: Mendapatkan profil user yang sedang login (saat ini menggunakan Mock User).
- `GET /{user_id}/children`: Mengambil daftar profil anak dari user tersebut (bisa diberi parameter `?limit=10&offset=0`).
- `PATCH /{user_id}`: Memperbarui profil. Body (JSON): `{"name": "string", "avatar_url": "string"}`.

### 2. Clinical Parameters (`/api/v1/clinical`)
- `POST /`: Membuat catatan parameter klinis baru (TB, BB, dll).
- `GET /{child_id}`: Riwayat parameter klinis (pagination `limit` & `offset`).
- `GET /{child_id}/latest`: Mengambil 1 catatan parameter klinis yang paling baru.

### 3. Meal Schedules (`/api/v1/schedules`)
- `POST /`: Membuat jadwal makan.
- `GET /{child_id}`: Daftar jadwal makan (pagination).
- `PATCH /{schedule_id}`: Memperbarui jadwal makan (hanya update *field* yang disertakan).
- `DELETE /{schedule_id}`: Menghapus jadwal makan secara permanen.

### 4. Virtual Pet (`/api/v1/pets`)
- `POST /`: Mendaftarkan profil pet (jika belum ada). Peliharaan secara otomatis memiliki stat bawaan (exp=0, level=1, dst).
- `GET /{child_id}`: Mengecek detail status peliharaan saat ini.
- `PATCH /{pet_id}`: Mengubah *name* atau *pet_type*.

### 5. Logs & History (`/api/v1/logs`)
- `GET /food/{child_id}`: Daftar riwayat makan anak (urut terbaru, ada pagination).
- `GET /medication/{child_id}`: Daftar riwayat minum obat anak (urut terbaru, ada pagination).

## 📄 Cara Testing
Karena semua rute ini merupakan standar REST, kamu dapat dengan mudah mengakses dokumentasi dan *playground*-nya di URL:
**`http://localhost:8000/docs`** (Swagger UI).
