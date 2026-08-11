import axios from 'axios';

// Gunakan URL lokal backend FastAPI
const BASE_URL = 'http://127.0.0.1:8000/api/v1';

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Catatan: Karena ini web dashboard khusus dokter, dalam aplikasi nyata kita butuh token JWT.
// Namun untuk prototype/mock testing ini, kita bisa mensimulasikan panggilan API langsung.
