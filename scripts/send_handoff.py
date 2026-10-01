import json
import os

from marketplace_handoff.handoff_pipeline import process_handoff
from marketplace_handoff.infrai_sms import InfraiSmsClient
from marketplace_handoff.models import HandoffRequest
from marketplace_handoff.suppression_store import SuppressionStore


def main() -> None:
    request = HandoffRequest.model_validate(
        {
            "asset": {
                "asset_id": "camera-42",
                "seller_name": "North Loop Camera",
                "item_title": "35mm rangefinder",
            },
            "buyer_update": {
                "buyer_id": "buyer-73",
                "phone": os.environ["BUYER_PHONE"],
                "sms_opted_out": False,
                "state": "ready_for_handoff",
            },
            "handoff": {
                "order_id": "order-1042",
                "carrier": "Parcel Post",
                "tracking_reference": "PP-2048",
                "event_id": "evt-20260906-01",
            },
        }
    )
    with SuppressionStore(":memory:") as store:
        result = process_handoff(request, store, InfraiSmsClient())
    print(json.dumps(result.model_dump(), separators=(",", ":")))


if __name__ == "__main__":
    main()
