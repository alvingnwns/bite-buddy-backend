# Handout Fitur: Real-time Synchronization (Fase 5)

## 📌 Ringkasan Arsitektur
Aplikasi BiteBuddy telah menggunakan arsitektur **Database-Driven Real-time** melalui fitur **Supabase Postgres Changes** untuk komunikasi Real-time via *WebSocket*.

Backend API tidak lagi membuka server WebSocket secara mandiri. Sebaliknya, Backend (FastAPI) maupun Background Worker (seperti Compliance Worker) akan meng-insert data ke dalam tabel `alerts`. Semua pembaruan di database akan secara otomatis disiarkan (di-broadcast) oleh infrastruktur Supabase langsung ke aplikasi Frontend.

## 📡 Panduan Frontend (Client Subscription)

Di aplikasi Frontend (misalnya React Native / Web), kalian dapat mendengarkan secara *real-time* perubahan pada berbagai tabel.
Pastikan kalian menggunakan library `@supabase/supabase-js`.

### 1. Mendengarkan Notifikasi / Alert (Tabel `alerts`)
Gunakan tabel ini untuk mendapatkan peringatan seketika saat Pet sedang sakit, lapar, atau saat anak terlewat jadwal makan dan minum obat.
```javascript
import { supabase } from './supabaseClient'

const channel = supabase
  .channel('public:alerts')
  .on(
    'postgres_changes',
    { event: 'INSERT', schema: 'public', table: 'alerts' },
    (payload) => {
      console.log('🚨 Alert Baru Diterima!', payload.new)
      // Contoh isi payload.new:
      // { id: 'uuid', child_id: 'uuid', type: 'compliance_violation', message: 'Kamu belum minum obat hari ini!', is_read: false }
      
      // Tampilkan notifikasi atau pop-up alert ke pengguna di sini
    }
  )
  .subscribe()
```

### 2. Mendengarkan Perubahan Status Pet (Tabel `virtual_pets`)
Untuk membuat animasi Pet langsung merespon saat mereka diberi makan/obat.
```javascript
const petChannel = supabase
  .channel('public:virtual_pets')
  .on(
    'postgres_changes',
    { event: 'UPDATE', schema: 'public', table: 'virtual_pets' },
    (payload) => {
      console.log('🐶 Status Pet Berubah!', payload.new)
      // Update UI bar Happiness, Hunger, dan Level di sini
    }
  )
  .subscribe()
```

---
💡 **Catatan untuk Frontend:** 
Untuk efisiensi, kalian bisa menggabungkan konfigurasi `channel` menjadi satu *subscription* tunggal, atau men-filter *event* berdasarkan `child_id` (menggunakan properti `filter` di opsi postgres_changes) agar kalian tidak mendapatkan alert milik user lain (meskipun RLS Supabase tetap akan mengamankannya jika token pengguna digunakan).
