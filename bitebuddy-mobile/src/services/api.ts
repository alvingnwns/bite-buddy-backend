import axios from 'axios';
import { supabase } from './supabase';

// Gunakan alamat IP lokal WiFi-mu (misal 192.168.1.5) bukan localhost 
// jika ingin test di HP sungguhan.
const BASE_URL = 'http://192.168.1.8:8000/api/v1'; // Contoh IP 

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor untuk menyisipkan Bearer Token secara otomatis
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});
