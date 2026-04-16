"""
Stripe Payment Routes
Handles checkout session creation and webhook fulfillment for series access.
"""

import os
import stripe
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from typing import Optional

stripe_router = APIRouter(prefix='/api', tags=['payments'])

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def _get_db():
    from app import get_db_connection
    return get_db_connection()


# ============================================================================
# CREATE CHECKOUT SESSION
# ============================================================================

@stripe_router.post('/payments/series/{series_id}/checkout')
async def create_checkout_session(
    series_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    Create a Stripe Checkout Session for a user to pay for series access.
    Returns {checkout_url} — frontend redirects to this URL.
    """
    from app import get_current_user
    user = await get_current_user(authorization)
    user_id = user['user_id']
    user_email = user.get('email', '')

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail='Stripe is not configured on this server')

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch series info
        cursor.execute(
            'SELECT id, name, price_cents, payment_message FROM fantasy_series WHERE id = %s AND is_active = 1',
            (series_id,)
        )
        series = cursor.fetchone()
        if not series:
            raise HTTPException(status_code=404, detail='Series not found')

        if not series['price_cents'] or series['price_cents'] <= 0:
            raise HTTPException(status_code=400, detail='This series does not require payment')

        # Check if user already has access
        cursor.execute(
            'SELECT 1 FROM fantasy_series_access WHERE user_id = %s AND series_id = %s',
            (user_id, series_id)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail='You already have access to this series')

        # Create Stripe Checkout Session
        success_url = f"{FRONTEND_URL}/#/fantasy?payment=success&series_id={series_id}"
        cancel_url = f"{FRONTEND_URL}/#/fantasy?payment=cancelled&series_id={series_id}"

        session = stripe.checkout.Session.create(
            mode='payment',
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': series['price_cents'],
                    'product_data': {
                        'name': f"Access to {series['name']}",
                        'description': series.get('payment_message') or f"Join the {series['name']} fantasy league",
                    },
                },
                'quantity': 1,
            }],
            metadata={
                'user_id': str(user_id),
                'series_id': str(series_id),
            },
            customer_email=user_email if user_email else None,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        # Record pending payment for audit trail
        cursor.execute(
            '''INSERT INTO stripe_payments (user_id, series_id, stripe_session_id, amount_cents, currency, status)
               VALUES (%s, %s, %s, %s, %s, 'pending')''',
            (user_id, series_id, session.id, series['price_cents'], 'usd')
        )
        conn.commit()

        return {'checkout_url': session.url}

    finally:
        cursor.close()
        conn.close()


# ============================================================================
# STRIPE WEBHOOK
# ============================================================================

@stripe_router.post('/stripe/webhook')
async def stripe_webhook(request: Request):
    """
    Webhook endpoint called by Stripe after payment events.
    Grants series access when checkout.session.completed fires.
    Must read raw body before any parsing.
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature', '')

    if not STRIPE_WEBHOOK_SECRET:
        # In dev without a webhook secret, skip signature verification
        # This should never happen in production
        try:
            import json
            event = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid payload')
    else:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail='Invalid webhook signature')
        except Exception:
            raise HTTPException(status_code=400, detail='Webhook error')

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        _fulfill_checkout(session)

    return JSONResponse(content={'received': True}, status_code=200)


def _fulfill_checkout(session):
    """
    Grant series access after successful payment.
    Safe to call multiple times (idempotent via ON DUPLICATE KEY UPDATE).
    """
    metadata = session.get('metadata', {})
    user_id = metadata.get('user_id')
    series_id = metadata.get('series_id')
    session_id = session.get('id')

    if not user_id or not series_id:
        return  # Missing metadata — nothing to fulfill

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Idempotency check — skip if already fulfilled
        cursor.execute(
            "SELECT status FROM stripe_payments WHERE stripe_session_id = %s",
            (session_id,)
        )
        row = cursor.fetchone()
        if row and row['status'] == 'completed':
            return  # Already processed

        # Grant access — ON DUPLICATE KEY UPDATE is safe if user somehow already has a row
        cursor.execute(
            '''INSERT INTO fantasy_series_access (user_id, series_id, access_type, whitelist_acknowledged)
               VALUES (%s, %s, 'paid', 0)
               ON DUPLICATE KEY UPDATE access_type = 'paid'
            ''',
            (int(user_id), int(series_id))
        )

        # Mark payment as completed
        cursor.execute(
            '''UPDATE stripe_payments
               SET status = 'completed', fulfilled_at = NOW()
               WHERE stripe_session_id = %s
            ''',
            (session_id,)
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
