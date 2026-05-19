"""Reconciliation job: finds journey_summaries rows missing a lead_summaries row and recomputes."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.background.registry import registry

import structlog

logger = structlog.get_logger()


@registry.job("reconcile_leads", sweep_interval_minutes=60)
class ReconcileLeads:
    """Hourly sweep that catches client_ids whose lead_summaries row is missing.

    This handles the case where a recompute_journey job was lost (e.g. server
    restart) after the watermark already advanced past their events.  The sweep
    ignores `since` — it always does a full consistency check.
    """

    def sweep(self, db: Session, since: datetime) -> List[Dict[str, Any]]:
        rows = db.execute(text("""
            SELECT js.client_id
            FROM journey_summaries js
            LEFT JOIN lead_summaries ls ON ls.client_id = js.client_id
            WHERE js.has_captured_data = 1
              AND ls.client_id IS NULL
            LIMIT 500
        """)).fetchall()

        if rows:
            logger.info("reconcile_leads found orphaned journeys", count=len(rows))

        return [{"client_id": row[0]} for row in rows]

    def handle(self, db: Session, payload: Dict[str, Any]) -> None:
        from app.background.registry import registry as _registry
        handler = _registry.get_handler("recompute_journey")
        handler.handle(db, payload)
