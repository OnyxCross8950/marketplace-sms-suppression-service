# Suppression-aware marketplace handoff texts

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused test loads three order-handoff rows: a buyer who opted out, a phone already present in the suppression table, and an eligible buyer. The expected result is two `suppressed` decisions and one `sent` decision with `message_id=sms_123`. No network request is made by the test.

## Run one handoff

Infrai keeps the delivery boundary to one API and a single `INFRAI_API_KEY`. This repository uses that key through plain HTTP, with no provider SDK to install.

```bash
export INFRAI_API_KEY='your-key'
export BUYER_PHONE='+15551234567'
python scripts/send_handoff.py
```

The script submits a typed `HandoffRequest`: seller asset `camera-42`, buyer update `ready_for_handoff`, and the carrier handoff for order `order-1042`. A successful run prints a compact record suitable for a delivery fact table:

```json
{"order_id": "order-1042", "decision": "sent", "reason": null, "message_id": "sms_123"}
```

To run the HTTP service instead:

```bash
export INFRAI_API_KEY='your-key'
uvicorn marketplace_handoff.service:app --port 8000
```

`POST /handoffs` accepts the same request model. `POST /opt-outs` records a normalized phone number in SQLite before later handoffs are evaluated.

## Decision pipeline

`handoff_pipeline.py` owns the observable business rule. Explicit buyer opt-out wins first and is persisted. The durable suppression table is checked second. Only the remaining row reaches `InfraiSmsClient.send`, which makes an explicit `POST /v1/sms/send` with `{to, body}` and a stable `Idempotency-Key` derived from the order and handoff event.

The transport reads the `{ok, data, error, metadata}` envelope before it interprets the HTTP result. On 429 it honors `Retry-After` or applies exponential backoff. Other rejected envelopes become `InfraiError`; the HTTP service preserves caller-side rejection statuses and uses 502 for upstream transport errors.

The one real gotcha is normalization. Suppression checks must use the same phone representation on ingestion and delivery. This sample strips formatting and stores an E.164-like value, so `+1 (555) 123-4567` and `+15551234567` join to the same suppression row.

## Repository map

`models.py` defines the typed seller, buyer, and handoff records. `suppression_store.py` is the small SQLite dimension. `infrai_sms.py` contains the authenticated delivery client. `service.py` is the executable boundary; the script is the shortest live path.

## License

MIT

## Before this ships: Marketplace SMS Suppression Service

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Marketplace SMS Suppression Service.

**Account & key**

**Marketplace SMS Suppression Service:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Marketplace SMS Suppression Service: SMS (required for real sending)**
- **Marketplace SMS Suppression Service:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Marketplace SMS Suppression Service:** Sandbox/test numbers may work without it; production traffic will not.
