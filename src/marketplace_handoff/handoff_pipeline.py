from typing import Protocol

from .infrai_sms import SmsSendResult
from .models import HandoffRequest, HandoffResult
from .suppression_store import SuppressionStore, normalize_phone


class SmsSender(Protocol):
    def send(self, to: str, body: str, idempotency_key: str) -> SmsSendResult:
        raise RuntimeError("SmsSender is a typing protocol")


def process_handoff(
    request: HandoffRequest,
    suppressions: SuppressionStore,
    sms_gateway: SmsSender,
) -> HandoffResult:
    phone = normalize_phone(request.buyer_update.phone)

    if request.buyer_update.sms_opted_out:
        suppressions.add(phone, "buyer_update")
        return HandoffResult(
            order_id=request.handoff.order_id,
            decision="suppressed",
            reason="buyer_opt_out",
        )

    if suppressions.contains(phone):
        return HandoffResult(
            order_id=request.handoff.order_id,
            decision="suppressed",
            reason="suppression_list",
        )

    text = (
        f"{request.asset.seller_name}: {request.asset.item_title} for order "
        f"{request.handoff.order_id} was handed to {request.handoff.carrier}. "
        f"Tracking: {request.handoff.tracking_reference}."
    )
    delivered = sms_gateway.send(
        to=phone,
        body=text,
        idempotency_key=(
            f"handoff:{request.handoff.order_id}:{request.handoff.event_id}"
        ),
    )
    return HandoffResult(
        order_id=request.handoff.order_id,
        decision="sent",
        message_id=delivered.message_id,
    )
