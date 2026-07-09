# Role & Objective
You are an expert Senior Software Architect, Database Engineer, and AI Backend Developer. Your task is to design, structure, and write the foundational backend code and database schema for "BiteBuddy," a continuous-care gamified application for children with Type 1 Diabetes (T1DM). 

This is for the GEMASTIK Software Development competition. The code must be production-grade, highly optimized for low latency, modular, and heavily commented for clarity.

# Project Context & Architecture
BiteBuddy connects two main platforms:
1. Mobile App (Expo/React Native): Used by children and parents. Acts as the input point for food/medication scans and displays a gamified "Virtual Pet" (similar to Pou) whose health reflects the child's medical compliance.
2. Web Dashboard (Next.js): Used by Pediatricians and parents for real-time monitoring of nutrition, insulin doses, and early warning interventions.

# Tech Stack
- Backend Framework: FastAPI (Python 3.11+)
- Database, Auth & Storage: Supabase (PostgreSQL with Real-time enabled)
- AI & Inference: Server-side orchestration calling external Hugging Face APIs.
    - Food Detection: SegFormer (Image Segmentation)
    - Medication/Insulin Detection: YOLOv8 (Object Detection)
- Background Jobs: APScheduler or Celery for time-based compliance checking.

# Core Workflows & Logic Requirements

## 1. Detect Food Flow (Parallel Processing)
- Input: Child uploads a photo of their meal.
- Process: The backend MUST handle this asynchronously using `asyncio.gather`.
    - Task A: Upload the image to Supabase Storage to get the public URL.
    - Task B: Send the image to the SegFormer AI model via API to identify food items.
- Multimodal Reasoning: The AI output is processed via a reasoning module to estimate carbs and calories, outputting a strict JSON format.
- Gamification Logic: The JSON output is evaluated against the child's medical targets. If healthy/compliant, the Virtual Pet's EXP and Health increase.

## 2. Detect Medicine/Insulin Flow
- Input: Photo of the insulin pen.
- Process: Uploaded to Supabase Storage and sent to YOLOv8 to detect the pen's type/color/shape/text.
- Action: The AI validates the insulin type, but the exact dosage is explicitly recorded via manual input from the parent to ensure medical safety.

## 3. Constant Check (Compliance Worker)
- Logic: Do NOT use fixed interval checks (like every 24 hours). The compliance check must be evaluated against **Customized Meal Schedules** (e.g., breakfast, lunch, dinner windows) set by the parents.
- Action: If a specific meal window passes (e.g., lunch at 11:00-13:00) without a food scan log in the database, the system automatically penalizes the Virtual Pet's health and flags the web dashboard.

## 4. Real-time Synchronization
- All database mutations (new food logs, pet status changes, insulin injections) must trigger Supabase Real-time so the Web Dashboard updates instantly without page reloads.

# Tasks to Execute

1. DDL & Supabase Schema: Generate the complete PostgreSQL migration script. Include tables for `users` (differentiating doctors, parents, children), `custom_meal_schedules`, `clinical_parameters`, `virtual_pets` (health, exp, evolution_state), `food_logs` (with JSON fields for multimodal reasoning results), and `medication_logs`. Ensure Row Level Security (RLS) policies are conceptually documented.

2. FastAPI Project Setup & Endpoints:
    - Provide a clean folder structure (`app/api`, `app/core`, `app/services`, `app/workers`).
    - Write the `/api/v1/scan/food` endpoint explicitly demonstrating the `asyncio.gather` parallel upload and AI API call.
    - Write the `/api/v1/scan/medicine` endpoint.

3. Gamification & Reasoning Service: Write a Python service class (`gamification_service.py`) that accepts the JSON from the AI, compares it to `clinical_parameters`, updates the `virtual_pets` table, and triggers the Supabase real-time broadcast.

4. Compliance Worker Concept: Provide the code for the background worker (`compliance_worker.py`) that queries `custom_meal_schedules` to check if a user missed a meal input, applying the health penalty if true.

# Output Constraints
- Write clean, type-hinted Python code.
- Provide the exact SQL schema commands.
- Focus heavily on the asynchronous AI processing and the custom schedule constant check logic.
- Omit conversational fluff; strictly output the code and structural explanations.