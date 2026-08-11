# Handout: Panduan Membuat Mock Prototype Frontend BiteBuddy

Handout ini merupakan panduan konseptual dan teknis awal untuk membuat purwarupa (*prototype*) dari sisi klien (Mobile App & Web Dashboard). Tujuannya agar sistem backend yang telah selesai dapat langsung dirasakan dan diuji secara visual.

---

## 1. Arsitektur Prototype

Kita akan memecah *Frontend* menjadi dua repositori/folder terpisah:
1. **`bitebuddy-mobile`** (React Native via Expo) → Untuk di-test langsung di HP Android/iOS.
2. **`bitebuddy-web`** (Next.js) → Untuk dibuka di *browser* laptop sebagai Dashboard Dokter.

Kedua aplikasi ini akan berbicara dengan:
- **Supabase (BaaS):** Hanya untuk urusan Registrasi, Login (Auth), dan Real-time Websocket (mendengarkan perubahan status *Pet*).
- **FastAPI (Backend Kita):** Menangani logika berat seperti AI Scan, kalkulasi nutrisi, dan Gamifikasi.

---

## 2. Sisi Mobile App (Expo)

### A. Persiapan (Setup)
Gunakan Expo agar kamu bisa langsung melakukan *testing* di HP (lewat aplikasi Expo Go) tanpa perlu setup Android Studio yang berat.

```bash
npx create-expo-app bitebuddy-mobile -t blank-typescript
cd bitebuddy-mobile
npx expo install expo-image-picker expo-camera @supabase/supabase-js axios
```

### B. Alur Layar (Screen Flow) Sederhana
1. **Login Screen:** Memanggil `supabase.auth.signInWithPassword()`. Setelah berhasil, simpan `access_token`.
2. **Home Screen (Pet View):** 
   - Tampilkan gambar dummy anjing/kucing.
   - Panggil GET `http://localhost:8000/api/v1/users/me` dengan header `Authorization: Bearer <token>` untuk mendapatkan status *Happiness* & *Hunger* terkini.
3. **Scan Screen (Camera):**
   - Gunakan `expo-image-picker` untuk mengambil foto dari galeri/kamera.
   - Kirim foto tersebut ke backend.

### C. Contoh Integrasi API Upload Gambar (React Native)
Karena kita mengirim _file_ gambar, kita harus menggunakan `FormData`:

```javascript
import axios from 'axios';

const uploadFoodImage = async (imageUri, childId, token) => {
  // 1. Siapkan form data
  const formData = new FormData();
  formData.append('file', {
    uri: imageUri,
    name: 'food.jpg',
    type: 'image/jpeg',
  });
  formData.append('child_id', childId);
  formData.append('meal_type', 'lunch');

  // 2. Tembak ke Backend (Ganti localhost dengan IP Wi-Fi laptopmu jika test di HP fisik)
  const response = await axios.post('http://192.168.1.xxx:8000/api/v1/scan/food/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      'Authorization': `Bearer ${token}`
    }
  });
  
  console.log("Hasil Deteksi AI:", response.data);
};
```

---

## 3. Sisi Web Dashboard (Next.js)

### A. Persiapan (Setup)
Gunakan Next.js (App Router) dengan TailwindCSS untuk membuat dashboard dengan sangat cepat.

```bash
npx create-next-app@latest bitebuddy-web --typescript --tailwind --eslint
cd bitebuddy-web
npm install @supabase/supabase-js axios
```

### B. Alur Layar (Screen Flow) Sederhana
1. **Login Screen (Role Dokter):** Login via Supabase.
2. **Dashboard (Daftar Pasien):** 
   - Tarik data pasien (anak) dari database (bisa langsung dari Supabase Client JS untuk sekadar membaca data `users` dengan `role=child`).
3. **Detail Pasien & Edit Nutrisi:**
   - Dokter melihat BMR dan target kalori pasien.
   - Dokter mengisi target "Max Sugar" manual lalu menyimpannya.

### C. Contoh Integrasi API Kalkulasi Nutrisi (Next.js)

```javascript
import axios from 'axios';

const updateClinicalTarget = async (childId, weight, diabetesType, token) => {
  const payload = {
    child_id: childId,
    weight_kg: weight,
    height_cm: 120, // dummy
    diabetes_type: diabetesType
    // Note: target_daily_calories kosong agar dihitung otomatis oleh AI Backend
  };

  const response = await axios.post('http://localhost:8000/api/v1/clinical/', payload, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  console.log("Nutrisi terhitung:", response.data);
};
```

---

## 4. Langkah Eksekusi Berikutnya (Rekomendasi)

Jika kamu ingin mulai merakit prototipe ini, **saranku kita mulai dari sisi Mobile App (Expo) terlebih dahulu.** 

Kenapa? Karena inti inovasi (WOW Factor) dari aplikasi BiteBuddy ada pada **Pemindaian Makanan (Scan) dan Gamifikasi Peliharaan (Virtual Pet)**, yang mana keduanya terjadi di genggaman pasien (aplikasi Mobile). Dashboard web untuk dokter bisa dikerjakan belakangan sebagai pelengkap *monitoring*.

**Siapkan hal ini sebelum membuat frontend:**
1. Pastikan IP Address lokal komputermu (misal `192.168.1.X`). Karena HP fisik tidak mengerti apa itu `localhost`, URL backend di aplikasi *React Native* harus mengarah ke IP komputermu.
2. Buka Supabase Dashboard, dapatkan `SUPABASE_URL` dan `SUPABASE_ANON_KEY` untuk ditaruh di *frontend*.

*Jika kamu sudah membuat folder untuk frontend, kabari aku dan kita bisa mulai _pair-programming_ merakit UI-nya!*
