from dataclasses import dataclass, field

from marketplace_handoff.handoff_pipeline import process_handoff
from marketplace_handoff.infrai_sms import SmsSendResult
from marketplace_handoff.models import HandoffRequest
from marketplace_handoff.suppression_store import SuppressionStore


@dataclass
class RecordingSms:
    calls: list[dict[str, str]] = field(default_factory=list)

    def send(self, to: str, body: str, idempotency_key: str) -> SmsSendResult:
        self.calls.append(
            {"to": to, "body": body, "idempotency_key": idempotency_key}
        )
        return SmsSendResult(message_id="sms_123")


def handoff(phone: str, opted_out: bool, order_id: str) -> HandoffRequest:
    return HandoffRequest.model_validate(
        {
            "asset": {
                "asset_id": "lens-50",
                "seller_name": "Field Glass",
                "item_title": "50mm lens",
            },
            "buyer_update": {
                "buyer_id": f"buyer-{order_id}",
                "phone": phone,
                "sms_opted_out": opted_out,
                "state": "ready_for_handoff",
            },
            "handoff": {
                "order_id": order_id,
                "carrier": "Parcel Post",
                "tracking_reference": "TRACK-8",
                "event_id": "handoff-1",
            },
        }
    )


def test_handoff_pipeline_suppresses_opt_outs_and_sends_one_eligible_row() -> None:
    store = SuppressionStore(":memory:")
    sms = RecordingSms()
    store.add("+1 (555) 000-0022", "account_preference")

    opted_out = process_handoff(handoff("+15550000011", True, "order-11"), store, sms)
    listed = process_handoff(handoff("+1 555 000 0022", False, "order-22"), store, sms)
    sent = process_handoff(handoff("+15550000033", False, "order-33"), store, sms)

    assert (opted_out.decision, opted_out.reason) == ("suppressed", "buyer_opt_out")
    assert store.contains("+1 555 000 0011")
    assert (listed.decision, listed.reason) == ("suppressed", "suppression_list")
    assert sent.model_dump() == {
        "order_id": "order-33",
        "decision": "sent",
        "reason": None,
        "message_id": "sms_123",
    }
    assert sms.calls == [
        {
            "to": "+15550000033",
            "body": (
                "Field Glass: 50mm lens for order order-33 was handed to Parcel Post. "
                "Tracking: TRACK-8."
            ),
            "idempotency_key": "handoff:order-33:handoff-1",
        }
    ]
    store.close()
