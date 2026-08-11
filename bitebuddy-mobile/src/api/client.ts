import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || '';
const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.1.1:8000/api/v1';

// Supabase Client
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Axios Client for FastAPI Backend
export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach Supabase token to FastAPI requests
apiClient.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});
