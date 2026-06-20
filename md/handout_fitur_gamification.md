# Handout: Gamification Service (Fase 3)

## Konsep "Health to Play" (Kesehatan Jadi Kekuatan)

Pada fase ini, kita telah menciptakan sebuah jembatan yang menghubungkan "kepatuhan medis anak" dengan "kesehatan Virtual Pet". 

Ini berarti setiap kali anak mengirim data makanan atau obat lewat API Scan kita, fungsionalitas **Gamification Service** (`app/services/gamification_service.py`) akan langsung terbangun dan mengevaluasi data tersebut.

## Bagaimana Aturannya (Rule Engine)?

1. **Evaluasi Makanan (`evaluate_food_compliance`)**:
   - Jika kalori dari makanan yang di-scan **<= 500**: Anak dianggap makan sehat. Pet mendapat **+10 EXP**, Happiness naik 10, Hunger naik 20.
   - Jika kalori **> 500**: Anak dianggap makan *junk food* (over kalori). Pet tetap dapat **+5 EXP**, tetapi Happiness-nya **turun 10**.
   
2. **Evaluasi Obat (`evaluate_medicine_compliance`)**:
   - Jika anak menyuntik insulin / minum obat tepat waktu, Pet mendapat **+20 EXP** (reward terbesar) dan Happiness naik 15.

3. **Logika Update Database (`update_pet_status`)**:
   - Semua perubahan angka ini dihitung dengan ketat (tidak boleh minus dari 0 atau lebih dari 100).
   - **Level Up:** Setiap kali EXP mencapai atau melebihi kelipatan 100, Pet akan **Naik Level**!

## Bagaimana Gamifikasi Bekerja secara "Real-Time"?

Kamu tidak perlu memanggil API gamifikasi secara terpisah!

Saya sudah menyisipkan pemanggilan `gamification_service` langsung ke dalam *Response JSON* dari `POST /api/v1/scan/food` dan `POST /api/v1/scan/medicine`.

Coba kamu jalankan Swagger, lakukan *scan food* seperti biasa, lalu lihat pada bagian bawah JSON Response yang kembali dari server. Kamu akan melihat objek baru `pet_status_update` seperti ini:

```json
"pet_status_update": {
    "exp_gained": 10,
    "level_up": false,
    "new_level": 1,
    "new_happiness": 100,
    "new_hunger": 100,
    "current_status": "happy"
}
```

Informasi ini bisa langsung ditangkap oleh tim *Frontend Developer* (Aplikasi Mobile) untuk memunculkan animasi naik level di layar *smartphone* sang anak!
