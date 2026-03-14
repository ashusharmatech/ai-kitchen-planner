"""
household-service  —  Manages household profiles, dietary preferences,
ingredient inventory, and daily context records.
Port: 8001
"""
import os
from datetime import date, datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="household-service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Models ────────────────────────────────────────────────────────────────
class IngredientToggle(BaseModel):
    available: bool

class IngredientCreate(BaseModel):
    household_id: str
    name_en: str
    name_hi: Optional[str] = None
    quantity: Optional[str] = None
    available: bool = True

class PreferenceCreate(BaseModel):
    household_id: str
    preference_key: str

class DailyContextUpsert(BaseModel):
    household_id: str
    context_date: Optional[str] = None
    context_type: str = "normal"
    notes: Optional[str] = None

# ── Health ────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "household-service"}

# ── Household ─────────────────────────────────────────────────────────────
@app.get("/api/household/{household_id}")
def get_household(household_id: str):
    r = db.table("households").select("*").eq("id", household_id).execute()
    if not r.data:
        raise HTTPException(404, "Household not found")
    return r.data[0]

# ── Ingredients ───────────────────────────────────────────────────────────
@app.get("/api/ingredients/{household_id}")
def list_ingredients(household_id: str):
    r = db.table("ingredients").select("*").eq("household_id", household_id).order("name_en").execute()
    return r.data

@app.post("/api/ingredients")
def create_ingredient(body: IngredientCreate):
    r = db.table("ingredients").insert(body.model_dump()).execute()
    return r.data[0] if r.data else {}

@app.patch("/api/ingredients/{ingredient_id}/toggle")
def toggle_ingredient(ingredient_id: str, body: IngredientToggle):
    r = db.table("ingredients").update({
        "available": body.available,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", ingredient_id).execute()
    return r.data[0] if r.data else {}

@app.delete("/api/ingredients/{ingredient_id}")
def delete_ingredient(ingredient_id: str):
    db.table("ingredients").delete().eq("id", ingredient_id).execute()
    return {"deleted": ingredient_id}

# ── Preferences ───────────────────────────────────────────────────────────
@app.get("/api/preferences/{household_id}")
def list_preferences(household_id: str):
    r = db.table("dietary_preferences").select("*").eq("household_id", household_id).execute()
    return r.data

@app.post("/api/preferences")
def add_preference(body: PreferenceCreate):
    r = db.table("dietary_preferences").insert(body.model_dump()).execute()
    return r.data[0] if r.data else {}

@app.delete("/api/preferences/{preference_id}")
def delete_preference(preference_id: str):
    db.table("dietary_preferences").delete().eq("id", preference_id).execute()
    return {"deleted": preference_id}

# ── Daily context ─────────────────────────────────────────────────────────
@app.post("/api/context")
def upsert_context(body: DailyContextUpsert):
    ctx_date = body.context_date or date.today().isoformat()
    row = {"household_id": body.household_id, "context_date": ctx_date,
           "context_type": body.context_type, "notes": body.notes}
    r = db.table("daily_context").upsert(row, on_conflict="household_id,context_date").execute()
    return r.data[0] if r.data else row

@app.get("/api/context/{household_id}")
def get_context(household_id: str, context_date: Optional[str] = None):
    d = context_date or date.today().isoformat()
    r = db.table("daily_context").select("*").eq("household_id", household_id).eq("context_date", d).execute()
    return r.data[0] if r.data else {"context_type": "normal", "notes": None, "context_date": d}

# ── Full household snapshot (used by planner-service) ────────────────────
@app.get("/api/household/{household_id}/snapshot")
def get_snapshot(household_id: str, plan_date: Optional[str] = None):
    pd = plan_date or date.today().isoformat()
    hh   = db.table("households").select("name,member_count").eq("id", household_id).execute()
    ingr = db.table("ingredients").select("name_en,name_hi,quantity").eq("household_id", household_id).eq("available", True).execute()
    prefs= db.table("dietary_preferences").select("preference_key").eq("household_id", household_id).execute()
    ctx  = db.table("daily_context").select("context_type,notes").eq("household_id", household_id).eq("context_date", pd).execute()
    hist = db.table("meal_plans").select("plan_date,breakfast_en,lunch_en,snack_en,dinner_en").eq("household_id", household_id).lt("plan_date", pd).order("plan_date", desc=True).limit(7).execute()
    return {
        "household":    hh.data[0] if hh.data else {},
        "ingredients":  ingr.data or [],
        "preferences":  [p["preference_key"] for p in (prefs.data or [])],
        "daily_context": ctx.data[0] if ctx.data else {"context_type": "normal"},
        "history":      hist.data or [],
        "plan_date":    pd,
    }
