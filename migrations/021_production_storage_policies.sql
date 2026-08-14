-- Production Storage policies.
-- Uploads remain server-only through FastAPI's service_role client.
-- Nutrition ground truth is loaded from the tracked app/data USDA and TKPI files.

DO $$
BEGIN
    CREATE POLICY bitebuddy_food_photos_read
        ON storage.objects FOR SELECT
        TO anon, authenticated
        USING (bucket_id = 'food-photos');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY bitebuddy_medicine_photos_read
        ON storage.objects FOR SELECT
        TO anon, authenticated
        USING (bucket_id = 'medicine-photos');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
