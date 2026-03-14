"""
planner-service  —  Orchestrates meal plan generation.
1. Fetches household snapshot from household-service
2. Calls OpenAI GPT-4o-mini to generate structured plan JSON
3. Calls translation-service to get Hindi text
4. Persists to Supabase + caches in Redis
Port: 8002
"""
import os, json, redis
from datetime import date, datetime
from typing import Optional
from openai import OpenAI
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

SUPABASE_URL   = os.environ["SUPABASE_URL"]
SUPABASE_KEY   = os.environ["SUPABASE_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
HOUSEHOLD_SVC  = os.getenv("HOUSEHOLD_SVC_URL", "http://household-service:8001")
TRANSLATION_SVC= os.getenv("TRANSLATION_SVC_URL", "http://translation-service:8003")
REDIS_URL      = os.getenv("REDIS_URL", "redis://redis:6379")

db    = create_client(SUPABASE_URL, SUPABASE_KEY)
oai   = OpenAI(api_key=OPENAI_API_KEY)
cache = redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="planner-service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class GenerateRequest(BaseModel):
    household_id: str
    plan_date: Optional[str] = None
    regenerate: bool = False

class ContextRequest(BaseModel):
    household_id: str
    context_date: Optional[str] = None
    context_type: str = "normal"
    notes: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "planner-service"}

def cache_key(household_id: str, plan_date: str) -> str:
    return f"plan:{household_id}:{plan_date}"

def build_prompt(ctx: dict) -> str:
    pd = ctx["plan_date"]
    dow = datetime.strptime(pd, "%Y-%m-%d").strftime("%A")
    ingr_list = ", ".join(f"{i['name_en']}({i.get('name_hi','')})" for i in ctx["ingredients"]) or "standard pantry"
    hist_lines = "\n".join(
        f"  {h['plan_date']}: B={h.get('breakfast_en','?')} L={h.get('lunch_en','?')} S={h.get('snack_en','?')} D={h.get('dinner_en','?')}"
        for h in ctx["history"]
    ) or "  No history."
    return f"""You are an expert Indian vegetarian cook planning meals for {ctx['household'].get('name','a family')} ({ctx['household'].get('member_count',4)} members).

DATE: {pd} ({dow})
CONTEXT: {ctx['daily_context'].get('context_type','normal')} {('— ' + ctx['daily_context']['notes']) if ctx['daily_context'].get('notes') else ''}
DIETARY: {', '.join(ctx['preferences']) or 'standard vegetarian'}
AVAILABLE INGREDIENTS: {ingr_list}

RECENT HISTORY (avoid repeating):
{hist_lines}

Rules:
- If fasting: grain-free / fruit-based options
- If guests: impressive, elaborate dishes
- If weekend: slightly indulgent
- Always use available ingredients first

Respond ONLY with a JSON object (no markdown):
{{
  "breakfast": {{"name_en":"...","name_hi":"...","description_hi":"...","prep_time_mins":15,"ingredients_needed":[]}},
  "lunch":     {{"name_en":"...","name_hi":"...","description_hi":"...","prep_time_mins":30,"ingredients_needed":[]}},
  "snack":     {{"name_en":"...","name_hi":"...","description_hi":"...","prep_time_mins":5, "ingredients_needed":[]}},
  "dinner":    {{"name_en":"...","name_hi":"...","description_hi":"...","prep_time_mins":30,"ingredients_needed":[]}},
  "day_note_hi": "आज का खाना..."
}}"""

@app.post("/api/generate-plan")
async def generate_plan(req: GenerateRequest):
    plan_date = req.plan_date or date.today().isoformat()
    ck = cache_key(req.household_id, plan_date)

    # Redis cache hit
    if not req.regenerate:
        cached = cache.get(ck)
        if cached:
            return {"plan": json.loads(cached), "cached": True, "source": "redis"}

    # DB hit
    if not req.regenerate:
        existing = db.table("meal_plans").select("*").eq("household_id", req.household_id).eq("plan_date", plan_date).execute()
        if existing.data:
            plan = existing.data[0]["full_plan_json"]
            cache.setex(ck, 86400, json.dumps(plan))
            return {"plan": plan, "cached": True, "source": "db", "plan_id": existing.data[0]["id"]}

    # Fetch snapshot from household-service
    async with httpx.AsyncClient(timeout=30) as client:
        snap_r = await client.get(f"{HOUSEHOLD_SVC}/api/household/{req.household_id}/snapshot", params={"plan_date": plan_date})
        snap_r.raise_for_status()
        ctx = snap_r.json()

    # Call OpenAI — response_format guarantees valid JSON, no stripping needed
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1500,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an expert Indian vegetarian cook. Always respond with valid JSON only."},
            {"role": "user",   "content": build_prompt(ctx)},
        ]
    )
    plan = json.loads(resp.choices[0].message.content)

    # Persist to Supabase
    row = {
        "household_id": req.household_id,
        "plan_date": plan_date,
        "breakfast_en": plan["breakfast"]["name_en"],
        "breakfast_hi": plan["breakfast"]["name_hi"],
        "lunch_en":     plan["lunch"]["name_en"],
        "lunch_hi":     plan["lunch"]["name_hi"],
        "snack_en":     plan["snack"]["name_en"],
        "snack_hi":     plan["snack"]["name_hi"],
        "dinner_en":    plan["dinner"]["name_en"],
        "dinner_hi":    plan["dinner"]["name_hi"],
        "full_plan_json": plan,
        "context_used": ctx,
        "generated_at": datetime.utcnow().isoformat(),
    }
    result = db.table("meal_plans").upsert(row, on_conflict="household_id,plan_date").execute()
    plan_id = result.data[0]["id"] if result.data else None

    # Cache in Redis for 24h
    cache.setex(ck, 86400, json.dumps(plan))
    return {"plan": plan, "cached": False, "plan_id": plan_id}

@app.get("/api/plan/{household_id}")
def get_plan(household_id: str, plan_date: Optional[str] = None):
    pd = plan_date or date.today().isoformat()
    ck = cache_key(household_id, pd)
    cached = cache.get(ck)
    if cached:
        return {"plan": json.loads(cached), "source": "redis"}
    r = db.table("meal_plans").select("*").eq("household_id", household_id).eq("plan_date", pd).execute()
    if not r.data:
        raise HTTPException(404, "No plan found. Generate one first.")
    return r.data[0]

@app.post("/api/context")
async def forward_context(req: ContextRequest):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{HOUSEHOLD_SVC}/api/context", json=req.model_dump())
        return r.json()
