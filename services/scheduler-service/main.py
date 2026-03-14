"""
scheduler-service  —  Pre-generates meal plans for all households.
Designed to run as a GKE CronJob at 6:00 AM IST (00:30 UTC).
Exit 0 = success, Exit 1 = partial/full failure.
"""
import os, sys, json, asyncio, logging
from datetime import date
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scheduler")

PLANNER_SVC  = os.getenv("PLANNER_SVC_URL",   "http://planner-service:8002")
HOUSEHOLD_SVC= os.getenv("HOUSEHOLD_SVC_URL",  "http://household-service:8001")
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

async def get_all_household_ids() -> list[str]:
    """Fetch all active household IDs from Supabase REST."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/households",
            params={"select": "id"},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        )
        r.raise_for_status()
        return [row["id"] for row in r.json()]

async def generate_for_household(client: httpx.AsyncClient, hid: str, today: str) -> bool:
    try:
        log.info(f"Generating plan for {hid} on {today}")
        r = await client.post(
            f"{PLANNER_SVC}/api/generate-plan",
            json={"household_id": hid, "plan_date": today, "regenerate": False},
            timeout=90
        )
        r.raise_for_status()
        data = r.json()
        log.info(f"  OK — cached={data.get('cached')} plan_id={data.get('plan_id')}")
        return True
    except Exception as e:
        log.error(f"  FAILED for {hid}: {e}")
        return False

async def main():
    today = date.today().isoformat()
    log.info(f"Scheduler starting for date {today}")
    household_ids = await get_all_household_ids()
    log.info(f"Found {len(household_ids)} households")
    if not household_ids:
        log.warning("No households found, exiting.")
        sys.exit(0)
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[
            generate_for_household(client, hid, today)
            for hid in household_ids
        ])
    ok = sum(results)
    log.info(f"Done: {ok}/{len(household_ids)} succeeded")
    sys.exit(0 if ok == len(household_ids) else 1)

if __name__ == "__main__":
    asyncio.run(main())
