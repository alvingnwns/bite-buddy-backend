-- 004_food_health_status.sql
-- Menambahkan kolom is_healthy ke tabel food_logs
-- Untuk melacak apakah makanan yang dikonsumsi anak tergolong sehat atau junk food (tinggi gula/kalori kosong).

ALTER TABLE public.food_logs
ADD COLUMN is_healthy BOOLEAN DEFAULT TRUE;
