import os

import requests
from fastapi import FastAPI, HTTPException

from .handoff_pipeline import process_handoff
from .infrai_sms import InfraiError, InfraiSmsClient
from .models import HandoffRequest, HandoffResult, OptOutRequest
from .suppression_store import SuppressionStore


app = FastAPI(title="Marketplace handoff SMS")
store = SuppressionStore(os.environ.get("SUPPRESSION_DB", "marketplace-suppressions.sqlite3"))


@app.post("/opt-outs", status_code=201)
def record_opt_out(request: OptOutRequest) -> dict[str, str]:
    return {"phone": store.add(request.phone, request.source), "status": "suppressed"}


@app.post("/handoffs", response_model=HandoffResult)
def send_handoff(request: HandoffRequest) -> HandoffResult:
    try:
        return process_handoff(request, store, InfraiSmsClient())
    except InfraiError as error:
        status = error.status if 400 <= error.status < 500 else 502
        raise HTTPException(status_code=status, detail=error.detail) from error
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail="SMS transport request failed") from error
