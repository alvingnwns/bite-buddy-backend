from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.auth import get_current_user
from app.core.supabase import get_supabase_service_client

router = APIRouter()

@router.get("/activity-logs")
def get_activity_logs(
    month: str = Query(..., description="Format YYYY-MM"),
    timezone: str = Query("Asia/Jakarta"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """
    Mendapatkan riwayat aktivitas berdasarkan partisi bulan.
    Mematuhi rule global: "generate activitylogs per bulan".
    """
    client = get_supabase_service_client()
    user_id = current_user["id"]
    
    try:
        # Karena kita menggunakan partitioned table di PostgreSQL (activity_logs_YYYY_MM),
        # query ke tabel parent 'activity_logs' dengan filter created_at otomatis akan mem-prune 
        # (hanya mencari di partisi bulan tersebut).
        
        # Parse month bounds
        from datetime import datetime
        import calendar
        year, mth = map(int, month.split("-"))
        _, last_day = calendar.monthrange(year, mth)
        
        start_date = f"{year}-{mth:02d}-01T00:00:00Z"
        end_date = f"{year}-{mth:02d}-{last_day}T23:59:59Z"
        
        resp = client.table("activity_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("created_at", start_date) \
            .lte("created_at", end_date) \
            .order("created_at", desc=True) \
            .limit(100) \
            .execute()
            
        return {
            "month": month,
            "timezone": timezone,
            "logs": resp.data if resp.data else []
        }
    except Exception as e:
        # Jika tabel belum ada, kita bisa kembalikan kosong untuk MVP
        if "relation \"public.activity_logs\" does not exist" in str(e):
            return {"month": month, "timezone": timezone, "logs": [], "warning": "Migration 008_activity_logs.sql has not been executed."}
        raise HTTPException(status_code=500, detail=str(e))
