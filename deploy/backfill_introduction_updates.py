"""Run once inside the API container to restore missing introduction feed events.

Idempotent: keeps existing IDs/read flags, uses original creation timestamps,
does not resend introductions or emails, and does not change their status.
"""
import json
from app.database import SessionLocal
from app.introduction_updates import backfill_introduction_updates

with SessionLocal() as db:
    created = backfill_introduction_updates(db)
    db.commit()
print(json.dumps({'introduction_updates_restored': created}))
