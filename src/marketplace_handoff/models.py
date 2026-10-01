from typing import Literal

from pydantic import BaseModel, Field


class SellerAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    seller_name: str = Field(min_length=1)
    item_title: str = Field(min_length=1)


class BuyerUpdate(BaseModel):
    buyer_id: str = Field(min_length=1)
    phone: str = Field(min_length=7)
    sms_opted_out: bool = False
    state: Literal["ready_for_handoff"]


class OrderHandoff(BaseModel):
    order_id: str = Field(min_length=1)
    carrier: str = Field(min_length=1)
    tracking_reference: str = Field(min_length=1)
    event_id: str = Field(min_length=1)


class HandoffRequest(BaseModel):
    asset: SellerAsset
    buyer_update: BuyerUpdate
    handoff: OrderHandoff


class HandoffResult(BaseModel):
    order_id: str
    decision: Literal["sent", "suppressed"]
    reason: Literal["buyer_opt_out", "suppression_list"] | None = None
    message_id: str | None = None


class OptOutRequest(BaseModel):
    phone: str = Field(min_length=7)
    source: str = Field(min_length=1)
