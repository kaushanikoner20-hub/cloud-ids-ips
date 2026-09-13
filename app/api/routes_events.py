"""Event ingest endpoint.

Phase 0 scope (ARCHITECTURE.md, "PHASE 0 requirements"):
  - validate NetworkEvent
  - generate event_id if missing
  - add server-side received_at in UTC
  - store the raw event in MongoDB collection "events"
  - return an ingest acknowledgement
  - does NOT run detection, ML, alerts, or IPS

Section 1.4 ("Request lifecycle") describes the full pipeline including
detection and IPS; those steps are deliberately not implemented here and
will be added in later phases without changing this route's ingest
contract.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pymongo.errors import DuplicateKeyError

from app.dependencies import get_events_collection, require_api_token
from app.schemas.event import EventStored, IngestResult, NetworkEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    response_model=IngestResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_token)],
)
async def ingest_event(
    event: NetworkEvent,
    response: Response,
    events: Any = Depends(get_events_collection),
) -> IngestResult:
    event_id = event.event_id or uuid4()
    received_at = datetime.now(timezone.utc)

    stored = EventStored(
        **event.model_dump(exclude={"event_id"}),
        event_id=event_id,
        received_at=received_at,
    )

    # Keep datetimes as native Python datetime objects so Mongo stores them
    # as BSON dates (required for the received_at/occurred_at indexes to be
    # useful for range queries in later phases). IP addresses, the UUID,
    # and the protocol enum have no native BSON representation, so those
    # are converted to strings explicitly rather than JSON-dumping the
    # whole document (which would also stringify the datetimes).
    document = stored.model_dump(mode="python")
    document["event_id"] = str(document["event_id"])
    document["src_ip"] = str(document["src_ip"])
    document["dst_ip"] = str(document["dst_ip"])
    document["protocol"] = document["protocol"].value
    document["_id"] = document["event_id"]

    try:
        await events.insert_one(document)
    except DuplicateKeyError:
        logger.info("duplicate_event_id", extra={"event_id": str(event_id)})
        # Nothing was created, so override the decorator's default 201
        # with 200 rather than misreporting a duplicate as "Created".
        response.status_code = status.HTTP_200_OK
        return IngestResult(event_id=event_id, accepted=False, received_at=received_at)
    except Exception as exc:  # noqa: BLE001
        logger.exception("event_insert_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to store event",
        ) from exc

    # response.status_code must be set explicitly: injecting `Response`
    # gives us an object that already defaults to 200, which silently
    # overrides the decorator's status_code=201 on any path that doesn't
    # set it by hand.
    response.status_code = status.HTTP_201_CREATED
    return IngestResult(event_id=event_id, accepted=True, received_at=received_at)