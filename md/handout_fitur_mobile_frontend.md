# Handout Fitur: Mobile Frontend (BiteBuddy)

## Apa yang Telah Dikerjakan
- **Setup & Dependensi**: Mengintegrasikan `expo-router` sebagai fondasi navigasi utama aplikasi (file-based routing). Mengubah konfigurasi `package.json` dan `app.json` agar mendukung scheme `bitebuddy`.
- **API & State Management**: 
  - Membuat `src/api/client.ts` untuk instansiasi Axios dan Supabase Client. Terdapat interceptor untuk memasukkan Bearer Token pada setiap permintaan HTTP ke FastAPI (backend).
  - Membuat `src/context/AuthContext.tsx` untuk mengelola *state global* autentikasi menggunakan React Context sesuai permintaan (alih-alih Zustand).
- **Layar (Screens)**:
  - `login.tsx`: UI Login yang modern dan premium (menggunakan warna soft blue dan emerald green sesuai tone anak-anak/kesehatan). Menggunakan `signInWithPassword` Supabase.
  - `index.tsx` (Home): Dashboard Pet View. Menampilkan *placeholder* Virtual Pet beserta status *Health* (HP) dan *Level*. Terdapat bar kesehatan visual yang berubah warna sesuai nilai HP.
  - `scan.tsx`: Menggunakan `expo-camera` dan `expo-image-picker`. Mendukung pengambilan foto dari galeri maupun kamera langsung. Gambar dikirim ke backend `/scan/food/analyze` menggunakan `FormData`.
- **Styling**: Ditulis menggunakan `StyleSheet` bawaan yang sudah dioptimalkan untuk UI modern (Shadows, Gradients, Rounding) sesuai referensi desain Figma secara konseptual.

## Apa yang Harus Dikerjakan dari Handout Ini
- **Asset Gambar Asli**: Placeholder emoji dinosaurus (`🦖`) perlu diganti dengan aset animasi Lottie atau gambar `PNG` karakter Virtual Pet yang sesungguhnya.
- **Testing Real Device**: Jalankan `npx expo start` dan scan QR Code menggunakan aplikasi Expo Go di HP Anda. Pastikan laptop dan HP terhubung di Wi-Fi yang sama agar IP lokal (`192.168.1.X`) bisa diakses oleh Axios.
- **Handling Respons API**: Sesuaikan kembali respons data (struktur JSON) dari FastAPI pada `index.tsx` dan `scan.tsx` jika ada perubahan dari sisi server-side.

## Activity Logs (Catatan Aktivitas)
- **[Agustus 2026]**: 
  - Setup Expo Router.
  - Integrasi login (auth context).
  - Integrasi UI Camera (Scan Food).
  - Konektivitas awal `axios` dan Supabase client.
