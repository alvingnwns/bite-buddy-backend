import { createClient } from '@supabase/supabase-js';

// Menggunakan Supabase URL & Key aslimu agar Expo Go tidak crash
const supabaseUrl = 'https://anrwnglqqosbkxwiktid.supabase.co';
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFucnduZ2xxcW9zYmt4d2lrdGlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE5NTk4NTEsImV4cCI6MjA5NzUzNTg1MX0.dF-hhjIVUkMqUOV9g_dsa14s7ScfnJ-umAsOoENYTms';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
