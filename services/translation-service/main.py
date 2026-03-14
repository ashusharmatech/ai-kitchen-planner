"""
translation-service  —  Hindi NLG rendering via OpenAI.
Takes structured meal objects and returns cook-friendly Hindi prose.
Port: 8003
"""
import os, json
from typing import Optional
from openai import OpenAI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
oai = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="translation-service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class MealTranslateRequest(BaseModel):
    name_en: str
    description_en: Optional[str] = None
    ingredients: Optional[list[str]] = None
    meal_type: Optional[str] = None

class TextTranslateRequest(BaseModel):
    text: str
    target_language: str = "hindi"
    style: str = "simple"

@app.get("/health")
def health():
    return {"status": "ok", "service": "translation-service"}

@app.post("/api/translate/meal")
def translate_meal(req: MealTranslateRequest):
    prompt = f"""Translate this meal into simple Hindi for a household cook reading on a mobile phone.
Use warm, everyday language — not formal or literary Hindi.

Meal: {req.name_en}
Description: {req.description_en or 'A delicious vegetarian dish.'}
Ingredients: {', '.join(req.ingredients or [])}
Meal type: {req.meal_type or 'meal'}

Respond ONLY with JSON:
{{
  "name_hi": "Hindi name of the dish",
  "description_hi": "1-2 simple Hindi sentences describing how to make it",
  "meal_type_hi": "नाश्ता / दोपहर का खाना / शाम की चाय / रात का खाना"
}}"""
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=400,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a Hindi language expert. Respond only with valid JSON."},
            {"role": "user",   "content": prompt},
        ]
    )
    return json.loads(resp.choices[0].message.content)

@app.post("/api/translate/text")
def translate_text(req: TextTranslateRequest):
    prompt = f"Translate into {req.target_language} ({req.style} style). Reply with ONLY the translation:\n\n{req.text}"
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=500,
        messages=[
            {"role": "system", "content": "You are a professional translator. Output only the translation, nothing else."},
            {"role": "user",   "content": prompt},
        ]
    )
    return {"translated": resp.choices[0].message.content.strip(), "target_language": req.target_language}
