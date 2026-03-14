"""
feedback-service  —  Meal ratings, cook feedback, and history queries.
Port: 8004
"""
import os
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="feedback-service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class FeedbackCreate(BaseModel):
    meal_plan_id: str
    meal_type: str       # breakfast | lunch | snack | dinner
    rating: int          # 1-5
    made: bool = False
    notes: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "feedback-service"}

@app.post("/api/feedback")
def submit_feedback(body: FeedbackCreate):
    r = db.table("meal_feedback").insert(body.model_dump()).execute()
    return {"success": True, "feedback": r.data[0] if r.data else {}}

@app.get("/api/feedback/{meal_plan_id}")
def get_feedback(meal_plan_id: str):
    r = db.table("meal_feedback").select("*").eq("meal_plan_id", meal_plan_id).execute()
    return r.data

@app.get("/api/history/{household_id}")
def get_history(household_id: str, limit: int = 7):
    r = db.table("meal_plans")\
        .select("id,plan_date,breakfast_hi,lunch_hi,snack_hi,dinner_hi,full_plan_json")\
        .eq("household_id", household_id)\
        .order("plan_date", desc=True)\
        .limit(limit).execute()
    return r.data

@app.get("/api/history/{household_id}/stats")
def get_stats(household_id: str):
    plans = db.table("meal_plans").select("id,plan_date").eq("household_id", household_id).execute()
    plan_ids = [p["id"] for p in (plans.data or [])]
    total_feedback = 0
    avg_rating = None
    if plan_ids:
        fb = db.table("meal_feedback").select("rating").in_("meal_plan_id", plan_ids).execute()
        ratings = [f["rating"] for f in (fb.data or []) if f.get("rating")]
        total_feedback = len(ratings)
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None
    return {
        "total_plans": len(plans.data or []),
        "total_feedback": total_feedback,
        "avg_rating": avg_rating,
    }
