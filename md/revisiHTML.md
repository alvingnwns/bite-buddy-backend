1B. Orang tua buat akun anak
ini kayaknya belum lengkap data apa aja yang diperlukan ya?
So far sih data anak yang diperlukan itu:
    1. Nama Lengkap
    2. Tempat/Tanggal Lahir
    3. Jenis Kelamin
    4. Berat Badan (kg)
    5. Tinggi Badan (cm)
    6. Alergi
    lalu ada beberapa data yang langsung dihitung aja by system seperti:
    6. Target Daily Calories
    7. Target Daily Carbs
    8. Max Sugar Intake (ini yang di input dokter, tapi sistem kasi rekomendasi)

1D. Lahirkan Virtual Pet
ini tolong bikinin max 5 macam pet_type ya
untuk current_status petnya akan diset dari dokter dari 0/100 hunger dan 0/100 happiness (kita bkin klo ++hunger itu artinya makin kenyang)

2. Daily Loop - Aktivitas Harian Anak
ini nanti kita jadinya pake 1 LLM aja, 1 API key LLM which is maybe Gemini dari AI Studio, gajadi pake model-model klasifikasi gitu karena dirasa API gemini bisa melakukan semuanya. Paling nanti kita pake beberapa model Gemini yang berbeda kemudian system prompt nya beda-beda untuk tiap task

Untuk cek kalori dan makronutrien nanti akan kukasi base datanya sebagai ground truth

3. Skenario Penalty - Ketika Anak Tidak Patuh
Saat ini penalty dicek SETIAP 1 MENIT. Dalam produksi, sebaiknya dicek sekali per periode jadwal (trigger: saat end_time lewat) untuk mencegah penalty berulang. Ini adalah known limitation dari implementasi demo saat ini.

6. Sistem Level & Evolusi Pet --> Ini bisa diabaikan dulu, tapi jadikan future feature