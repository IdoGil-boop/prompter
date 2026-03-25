<!-- managed by claude-code-starter -->
# Integration Data Architecture

## Core Principle: Data Isolation via Lookup Table

Integration-sourced data (from OAuth-connected third parties) is **never mixed with user tables** and **never filtered by user ownership**. Instead, a lookup/attribution table maps users to integration data.

## Three-Layer Model

### 1. Identity Layer (User-Owned)
- User credentials, JWT tokens, sessions
- User profile and preferences
- OAuth connection records (which user linked which integration)

### 2. Integration Data Layer (Integration-Owned)
- Dedicated tables per integration source (e.g., `google_ads_campaigns`, `slack_channels`)
- **No user FK or user-based filters** on these tables
- Data reflects the third-party source of truth
- Changes in the third party only affect these dedicated tables
- Keyed by the integration's own identifiers (e.g., `external_id`, `account_id`)

### 3. Attribution Layer (Lookup Table)
- Maps users to integration data via a junction/lookup table
- OAuth flow is responsible for populating and maintaining attribution
- Attribution changes (e.g., user reconnects, transfers ownership) only modify the lookup table
- Integration data remains untouched when attribution changes

## Schema Pattern

```sql
-- Identity layer
CREATE TABLE users (
  id UUID PRIMARY KEY,
  -- credentials, JWT, profile...
);

-- Integration data layer (example)
CREATE TABLE integration_campaigns (
  id UUID PRIMARY KEY,
  external_id TEXT NOT NULL,          -- third-party identifier
  integration_account_id TEXT NOT NULL, -- third-party account
  source TEXT NOT NULL,               -- e.g., 'google_ads'
  data JSONB,                         -- integration-specific payload
  synced_at TIMESTAMPTZ
);

-- Attribution layer (lookup)
CREATE TABLE user_integration_access (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  integration_account_id TEXT NOT NULL,
  source TEXT NOT NULL,
  granted_via TEXT DEFAULT 'oauth',   -- how attribution was established
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## Access Pattern

To query integration data for a user:
```sql
SELECT ic.*
FROM integration_campaigns ic
JOIN user_integration_access uia
  ON uia.integration_account_id = ic.integration_account_id
  AND uia.source = ic.source
WHERE uia.user_id = :current_user_id;
```

**Never** apply `WHERE user_id = ...` directly on integration tables.

## Rules

1. **Sync changes are isolated** — third-party data updates only touch integration tables
2. **Attribution changes are isolated** — ownership changes only touch the lookup table
3. **No cascading deletes** from users to integration data (a user leaving doesn't delete shared data)
4. **OAuth manages attribution** — the OAuth callback creates/updates lookup entries
5. **Stale attribution** — implement periodic reconciliation to detect revoked OAuth tokens and mark lookup entries accordingly
6. **Row-level security** — if using RLS (e.g., Supabase/Postgres), apply it on the lookup table, not integration tables

## Anti-Patterns to Avoid

- Adding `user_id` columns to integration data tables
- Filtering integration queries with `WHERE user_id = ...`
- Duplicating integration data per user
- Cascading deletes from user records to integration data
- Mixing attribution logic into sync/ingestion code
