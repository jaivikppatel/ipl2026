-- Migration 013: Stripe Payments for Series Access
--
-- NOTE: price_cents, payment_message, access_type, whitelist_acknowledged columns
-- were already applied to the DB in a partial run. This migration only creates
-- the stripe_payments table which is the remaining piece.

-- ============================================================================
-- stripe_payments — one row per Checkout Session attempt
-- ============================================================================

CREATE TABLE IF NOT EXISTS stripe_payments (
    id                  INT          NOT NULL AUTO_INCREMENT,
    user_id             BIGINT UNSIGNED NOT NULL,
    series_id           INT          NOT NULL,
    stripe_session_id   VARCHAR(255) NOT NULL COMMENT 'Stripe cs_... checkout session ID',
    amount_cents        INT          NOT NULL,
    currency            VARCHAR(3)   NOT NULL DEFAULT 'usd',
    status              ENUM('pending', 'completed', 'failed') NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fulfilled_at        TIMESTAMP    NULL DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_stripe_session (stripe_session_id),
    KEY idx_user_series (user_id, series_id),
    CONSTRAINT fk_sp_user   FOREIGN KEY (user_id)   REFERENCES users(id)          ON DELETE CASCADE,
    CONSTRAINT fk_sp_series FOREIGN KEY (series_id) REFERENCES fantasy_series(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
