# BiteBuddy E2E and Checklist Reconciliation

Verified: 2026-08-13 20:41 WIB (GMT+7)  
Live run: `0813204154c22af`  
Environment: configured Supabase migrations 001-016 and configured Gemini provider.

## Status definitions

- **Implemented**: FastAPI route and persistence/domain behavior exist.
- **Wired**: Flutter repository/state/UI or Doctor web service/state/UI calls the route.
- **Tested**: automated backend/client tests cover the contract or behavior.
- **Live**: the cleanup-safe live runner exercised the route in the successful run above.
- `-` under Live means implemented/wired/tested but not individually called by the final live scenario.

## Shared authentication

| Route | Implemented | Wired | Tested | Live |
|---|---:|---:|---:|---:|
| `POST /auth/register` | yes | yes | yes | yes: Doctor, Child claim, Parent |
| `POST /auth/login` | yes | yes | yes | yes: all roles |
| `GET /auth/me` | yes | yes | yes | yes: Doctor |
| `POST /auth/refresh` | yes | yes | yes | yes: Child |
| `POST /auth/logout` | yes | yes | yes | yes: all test identities |

When `SUPABASE_JWT_SECRET` is absent, bearer tokens are now verified through
Supabase Auth. Unverified local JWT decoding is no longer used.

## Child mobile

| Route | Implemented | Wired | Tested | Live |
|---|---:|---:|---:|---:|
| `GET/PATCH /children/me/profile` | yes | yes | yes | - |
| `GET /children/me/dashboard` | yes | yes | yes | - |
| `GET /children/me/schedules` | yes | yes | yes | - |
| `POST /children/me/food-analyses` | yes | yes | yes | yes: real image + Gemini + Storage |
| `POST /children/me/food-analyses/{analysisId}/confirm` | yes | yes | yes | yes: atomic RPC + persisted history |
| `POST /children/me/medicine-analyses` | yes | yes | yes | yes: real image + Gemini + Storage |
| `POST /children/me/medicine-analyses/{analysisId}/confirm` | yes | yes | yes | yes: atomic RPC + persisted history |
| `GET /children/me/history` | yes | yes | yes | yes: food |
| `GET /children/me/history/{historyId}` | yes | yes | yes | - |
| `GET /children/me/notifications` | yes | yes | yes | yes: Doctor and Parent delivery |
| `PATCH /children/me/notifications/{id}/read` | yes | yes | yes | yes |

## Parent mobile

| Route | Implemented | Wired | Tested | Live |
|---|---:|---:|---:|---:|
| `GET /parents/me/children` | yes | yes | yes | - |
| `POST /parents/me/children/link` | yes | yes | yes | yes |
| `GET /parents/me/children/{childId}` | yes | yes | yes | authorization denial verified |
| `GET /parents/me/children/{childId}/dashboard` | yes | yes | yes | - |
| `GET /parents/me/children/{childId}/schedules` | yes | yes | yes | yes |
| `POST /parents/me/children/{childId}/schedules` | yes | yes | yes | yes |
| `PATCH /parents/me/children/{childId}/schedules/{scheduleId}` | yes | yes | yes | yes |
| `DELETE /parents/me/children/{childId}/schedules/{scheduleId}` | yes | yes | yes | yes |
| `GET /parents/me/children/{childId}/history` | yes | yes | yes | yes: medicine |
| `GET /parents/me/children/{childId}/history/{historyId}` | yes | yes | yes | yes: food |
| `GET /parents/me/children/{childId}/notifications` | yes | yes | yes | yes: Doctor delivery |
| `POST /parents/me/children/{childId}/reminders` | yes | yes | yes | yes: visible in Child inbox |

## Doctor web

All 17 Doctor MVP endpoints are implemented, wired, locally tested, and live
verified: Doctor register/login/me/logout; patient list/create/read/update;
glucose list/create; nutrition; medication adherence; appointment list/create;
diagnosis create; AI summary; and notification create.

The live journey also proved:

- Doctor notification to Child appears only in the Child inbox and can be marked read.
- Doctor notification to Parent appears in the linked Parent inbox.
- A second Doctor receives `403` for the first Doctor's patient.
- A second Parent receives `403` for the linked Child.
- Child and Parent roles receive `403` on wrong-role APIs.

## Activity logs and time

The live run verified `GET /activity-logs` using the `2026-08` WIB partition and
confirmed Doctor and Parent login, patient, notification, AI, link, and schedule
CRUD actions. Application timestamps remain UTC; calendar boundaries use
`Asia/Jakarta`.

## Verification evidence

```powershell
# Live schema
.\bbb-venv\Scripts\python.exe scripts\verify_supabase_schema.py
# PASS: 17 table/column groups and 6 RPCs

# Live cross-app journey; generated records and uploaded fixtures are cleaned
.\bbb-venv\Scripts\python.exe -u scripts\run_live_e2e.py
# PASS: 54 checks
# Post-run verification: E2E_MARKER_ROWS 0

# Backend
.\bbb-venv\Scripts\python.exe -m pytest -q
# 45 passed, 4 skipped

# Doctor web
npm.cmd test -- --run
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
# 13 passed; lint, typecheck, and production build passed

# Flutter
flutter analyze --no-pub
flutter test --no-pub
# no issues; 24 passed
```

## Remaining maintenance

- Migrate deprecated `google.generativeai` to `google.genai`.
- Migrate deprecated Starlette `TestClient`/`httpx` compatibility path.

These warnings do not block the verified MVP journeys.
