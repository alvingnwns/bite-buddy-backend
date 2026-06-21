# Handout: Compliance Worker (Fase 4)

## Apa itu Compliance Worker?

Sistem backend kita tidak hanya pasif menunggu aksi (seperti saat *user* mengunggah foto makanan), tetapi juga **aktif mengawasi**. Fitur ini disebut *Background Job* atau *Worker*.

Pada aplikasi medis anak seperti BiteBuddy, kepatuhan (*compliance*) meminum obat adalah hal yang paling krusial. Worker ini bertugas untuk memastikan tidak ada anak yang melewatkan jadwal obatnya.

## Arsitektur: APScheduler

Kita menggunakan pustaka `apscheduler` (`AsyncIOScheduler`) yang diikatkan (*binding*) langsung ke siklus hidup (*lifespan*) FastAPI. 
1. Saat server FastAPI dijalankan (`uvicorn app.main:app`), fungsi `start_scheduler()` di `app/workers/scheduler.py` akan langsung berjalan di latar belakang (tanpa memblokir API).
2. Sesuai *Plan* (untuk demo), Worker ini disetel berjalan **Setiap 1 Menit**. Pada level produksi, ia harusnya berjalan 1 kali sehari di tengah malam (`cron`).
3. Saat FastAPI dimatikan (Ctrl+C), fungsi `stop_scheduler()` dipanggil agar memori tidak bocor (*memory leak*).

## Logika Pengecekan Hukuman (Penalty Rule)

Di dalam file `app/workers/compliance_worker.py` terdapat fungsi utama `check_daily_compliance()`. Algoritmanya bekerja dengan cara:
1. Mengambil semua anak yang memiliki *Virtual Pet* di database.
2. Mengecek apakah pada **Hari Ini** ada *log* obat (*Medication Log*) baru yang masuk untuk anak tersebut.
3. Jika ternyata HARI INI tidak ada *log* obat sama sekali, maka *Worker* secara otomatis akan memberikan penalti (*Health-to-Play* Gamification):
   - **-20 Happiness** (Sangat berdampak pada status Pet yang bisa berubah menjadi "Sad" atau "Sick").
   - **+5 Hunger** (Pet jadi lebih cepat lapar).

## Cara Mengetes Fitur Ini Secara Langsung

Karena jadwal disetel 1 menit sekali, kamu bisa melihat aksinya dengan mudah:
1. Jalankan server (`uvicorn app.main:app --reload`).
2. Perhatikan log di terminalmu. Setiap 1 menit, kamu akan melihat log:
   ```
   INFO:     [Compliance Worker] Memulai pengecekan kepatuhan medis...
   ```
3. Jika di databasemu ada anak yang memiliki Pet tetapi dia belum diberi log obat hari ini, kamu akan melihat log:
   ```
   INFO:     [Compliance Worker] Anak <UUID> melewatkan obat! Memberikan Penalty.
   ```
4. Cek *Supabase Dashboard* mu di tabel `virtual_pets` dan refresh setiap menit, kamu akan melihat angka `happiness` terus merosot setiap 1 menit! Ini membuktikan sistem otomatis kita berjalan dengan sukses.
