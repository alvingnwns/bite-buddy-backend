# Handout Fitur: Evaluator Kualitas Makanan (Healthy vs Junk Food)

## 1. Apa yang Telah Dikerjakan?
Pada iterasi kali ini, kita telah menambahkan indikator "Kualitas Makanan" agar Virtual Pet tidak sekadar menilai "Jumlah Kalori", melainkan juga nutrisi makanan tersebut (tinggi serat vs tinggi gula).

### A. TDD (Test-Driven Development)
- Kita menggunakan pendekatan TDD dengan membuat `tests/test_reasoning.py` dan `tests/test_gamification.py`.
- Uji coba (test) memverifikasi bahwa:
  1. Jika anak memakan Salad (sehat) + Apel (sehat), maka status makanan adalah `is_healthy = True`.
  2. Jika anak memakan Salad (sehat) + Es Krim (tinggi gula), maka status makanan menjadi `is_healthy = False` (karena dietnya dirusak oleh *junk food*).
  3. Jika terdeteksi *junk food*, Pet tidak mendapatkan bonus EXP (`0`) dan *Happiness*-nya berkurang drastis (`-20`), serta kelaparannya bertambah (`+20`).

### B. Perubahan Skema Database
- **Tabel `food_logs`**: Kita menambahkan file migrasi `004_food_health_status.sql` untuk membuat kolom `is_healthy BOOLEAN DEFAULT TRUE`. Kolom ini berguna bagi dokter/orang tua untuk melacak riwayat "hari-hari makan tidak sehat" anak.
- **Model Pydantic**: `FoodLogBase` telah diupdate untuk memasukkan *field* `is_healthy`.

### C. Pembaruan Logika
- **Reasoning Service (`app/services/reasoning_service.py`)**: Bertugas melakukan validasi apakah di dalam daftar makanan (*foods_detected*) terdapat *junk food*. Ia akan mengembalikan properti `is_healthy`.
- **Log Service & Scan Router (`app/services/log_service.py` & `app/api/v1/scan.py`)**: Bertugas menangkap nilai `is_healthy` dan menyimpannya secara fisik ke Supabase.
- **Gamification Service (`app/services/gamification_service.py`)**: *Rule engine* baru telah diimplementasikan. Jika `is_healthy == False`, berapapun kalorinya, pet akan langsung jatuh sakit (sedih dan lapar).

## 2. Penjelasan Kode Sederhana (Untuk Pembelajaran)
1. **Mocking dalam Testing:** Di `test_gamification.py`, kamu akan melihat fungsi `@patch("app.services.gamification_service.get_supabase_service_client")`. Karena saat *testing* kita tidak boleh asal mengubah database asli, kita membuat "database bohongan" (Mock). Mock ini diset agar seolah-olah mengembalikan target kalori anak `1500` saat ditanya, sehingga logika penalti bisa dihitung.
2. **Boolean Trap:** Pada saat menghitung `is_healthy`, kita menggunakan nilai awal `True`. Lalu di dalam iterasi (*for loop*) untuk setiap makanan, jika *satu saja* makanan bernilai `False`, kita menimpa `is_healthy = False`. Ini adalah pola klasik dalam pemrograman.
3. **Pydantic Inheritance:** Dengan menambahkan `is_healthy` di `FoodLogBase`, otomatis *class* turunannya seperti `FoodLogCreate` langsung memiliki *field* tersebut berkat *Inheritance* (pewarisan).

## 3. Apa yang Harus Dikerjakan Selanjutnya?
- Harap jalankan **SQL dari `migrations/004_food_health_status.sql`** di *dashboard* Supabase agar tabel `food_logs` memiliki kolom baru tersebut.
- Uji coba secara *real-time* di Postman atau cURL menggunakan gambar yang terdeteksi sebagai "burger" atau "pizza" untuk melihat penaltinya langsung.
