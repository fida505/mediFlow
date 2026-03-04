import stripe
from app.config import settings

stripe.api_key = settings.STRIPE_API_KEY


def verify_webhook_signature(payload: bytes, sig_header: str) -> stripe.Event:
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
