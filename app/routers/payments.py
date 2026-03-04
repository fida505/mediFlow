from fastapi import APIRouter, Request, HTTPException
from app.utils.stripe_client import verify_webhook_signature

router = APIRouter()

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = verify_webhook_signature(payload, sig)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Webhook verification failed")

    # handle event types
    if event.type == "payment_intent.succeeded":
        # update booking, etc.
        pass
    elif event.type == "charge.refunded":
        # logic
        pass

    return {"received": True}
