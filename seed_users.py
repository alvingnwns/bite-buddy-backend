import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

supabase: Client = create_client(url, key)

users_to_create = [
    {"email": "dokter@test.com", "password": "password123", "role": "doctor", "name": "Dr. Test"},
    {"email": "ayah@test.com", "password": "password123", "role": "parent", "name": "Ayah Test"},
    {"email": "anak@test.com", "password": "password123", "role": "child", "name": "Anak Test"}
]

created_ids = {}

for u in users_to_create:
    user_id = None
    try:
        # Create auth user
        res = supabase.auth.admin.create_user({
            "email": u["email"],
            "password": u["password"],
            "email_confirm": True,
            "user_metadata": {"role": u["role"], "full_name": u["name"]}
        })
        user_id = res.user.id
    except Exception as e:
        if "already been registered" in str(e):
            # Fetch existing user id
            auth_users_res = supabase.auth.admin.list_users()
            for existing_user in auth_users_res:
                if existing_user.email == u["email"]:
                    user_id = existing_user.id
                    break
        else:
            print(f"Failed to create auth user for {u['email']}: {e}")
            continue

    if user_id:
        created_ids[u["role"]] = user_id
        try:
            # Ensure public.users exists
            supabase.table("users").upsert({
                "id": user_id,
                "email": u["email"],
                "full_name": u["name"],
                "role": u["role"],
                "password_hash": "supabase_managed",
                "is_active": True
            }).execute()
            print(f"Created/Updated {u['email']} (ID: {user_id}) in public.users")
        except Exception as db_e:
            print(f"Failed to upsert public.users for {u['email']}: {db_e}")

# Link them
if "child" in created_ids and "parent" in created_ids and "doctor" in created_ids:
    try:
        supabase.table("users").update({
            "parent_id": created_ids["parent"],
            "doctor_id": created_ids["doctor"]
        }).eq("id", created_ids["child"]).execute()
        print("Linked Child to Parent and Doctor successfully!")
    except Exception as e:
        print(f"Failed to link: {e}")
