"""
api-gateway  —  Single entry point for all client traffic.
Routes requests to downstream microservices via internal K8s DNS.
"""
import os
import httpx
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Kitchen Planner — API Gateway", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Internal K8s service DNS names (cluster-local)
HOUSEHOLD_SVC  = os.getenv("HOUSEHOLD_SVC_URL",   "http://household-service:8001")
PLANNER_SVC    = os.getenv("PLANNER_SVC_URL",     "http://planner-service:8002")
TRANSLATION_SVC= os.getenv("TRANSLATION_SVC_URL", "http://translation-service:8003")
FEEDBACK_SVC   = os.getenv("FEEDBACK_SVC_URL",    "http://feedback-service:8004")

ROUTE_TABLE = {
    "/api/household":     HOUSEHOLD_SVC,
    "/api/ingredients":   HOUSEHOLD_SVC,
    "/api/preferences":   HOUSEHOLD_SVC,
    "/api/generate-plan": PLANNER_SVC,
    "/api/plan":          PLANNER_SVC,
    "/api/context":       PLANNER_SVC,
    "/api/translate":     TRANSLATION_SVC,
    "/api/feedback":      FEEDBACK_SVC,
    "/api/history":       FEEDBACK_SVC,
}

def resolve(path: str) -> str:
    for prefix, base in ROUTE_TABLE.items():
        if path.startswith(prefix):
            return base + path
    raise HTTPException(status_code=404, detail=f"No route for {path}")

@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway"}

@app.api_route("/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy(path: str, request: Request):
    full_path = "/" + path
    target = resolve(full_path)
    body = await request.body()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.request(
            method=request.method,
            url=target,
            content=body,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            params=dict(request.query_params),
        )
    return Response(content=resp.content, status_code=resp.status_code,
                    media_type=resp.headers.get("content-type", "application/json"))
