# Security

StationVoice is built to be administered from the **local network or a
VPN**, not from the public internet (as it is not meant to be exposed 
to the public internet). This page collects the security model
in one place: where it is safe to expose, how accounts and sessions work,
and where secrets live.

## Network exposure

- The app itself listens on `0.0.0.0:8000` (`HOST` / `PORT`) and serves
  **plain HTTP**. Treat port 8000 as reachable by anything on the LAN /
  tailnet.
- On the DVRA host, public-name HTTPS is terminated by **Caddy**
  (for example, `https://announcements.w2zq.com`), which binds **only the LAN Wi-Fi
  address** — it is not exposed to the public internet. The Let's Encrypt
  certificate uses DNS-01, so no inbound 80/443 is needed. See
  [Operations — Caddy](operations.md#caddy-https-on-the-lan).
- Remote administration goes over **Tailscale** (MagicDNS name, port 8000,
  tailnet-only). Caddy's HTTPS is LAN-side and not reachable over the
  tailnet IP. See [Operations — remote access](operations.md#urls-and-access).
- If you deploy elsewhere, put the app behind a reverse proxy with TLS on a
  trusted network, or restrict `HOST` to a private interface. Do not port-
  forward 8000 to the internet.

## Accounts and roles

StationVoice uses local username/password accounts — there is no OAuth, no
external identity provider, and no internet-facing login.

- The **first account** created on a fresh install is always **Admin**; do
  the first-run setup from a trusted network.
- Three roles: **Admin**, **Editor**, **Read-Only**. Capability matrix:
  [Getting started — user roles](getting-started.md#user-roles).
- Only Admins see the Admin section (Users, Environment, Branding) and can
  call `/api/users`; server-side checks redirect or reject Editors and
  Read-Only users from admin routes.
- The store refuses to demote or delete the **last remaining Admin**, so
  the station cannot be locked out of user management.

## Sessions

- Login state is a **signed session cookie** (`SESSION_SECRET`; auto-
  generated and stored in `data/.session_secret`). Losing the secret
  invalidates existing sessions — everyone signs in again.
- **Idle logout:** sessions expire after `SESSION_IDLE_SECONDS` (default 30
  minutes) of no activity. The UI's automatic 15-second refreshes do **not**
  count as activity — requests from its background polls carry an
  `X-Background-Poll` header, and the server only checks that the header is
  present (no secret value that must match). A tab left open still logs out.
- Sign out is explicit via the UI (`/api/auth/logout`).
- **Brute-force limit:** failed sign-ins for the same username from the same
  client address return `429` after `LOGIN_MAX_FAILURES` (default 5) failures
  within `LOGIN_WINDOW_SECONDS` (default 300 s). The counter is **in
  memory**: it clears on process restart (see
  [Operations — process restart](operations.md#process-restart-and-in-memory-state)).

## API surface

- Most `/api/*` routes require a login session cookie; browser **Play**
  previews and sign-in helpers are the main exceptions.
- Writes (announcements, schedules, settings, phoneme dictionary, Newsline
  check) require Admin or Editor; user management requires Admin.
- The OpenAPI schema is at `/docs` and `/openapi.json` on the same host.
  Full route list: [API overview](api-overview.md).

## Secrets handling

| Secret | Where it lives | Never |
|---|---|---|
| App configuration | `.env` (gitignored) | Commit `.env` |
| Plugin credentials (e.g. `BIRD_API_KEY`) | `.env.secrets` (gitignored; loaded at startup, shell env wins) | Paste into the main `.env` or docs |
| DreamHost DNS API key (Caddy ACME) | `/etc/caddy/dreamhost.env` on the host (unit `EnvironmentFile`); referenced as `{env.DREAMHOST_API_KEY}` | Put it in the Caddyfile or git |
| Session signing | `data/.session_secret` (auto) | Copy between installs casually — it invalidates sessions, so do it deliberately |
| Account passwords | `data/users.json` (hashed) | Treat the file as sensitive in backups |

Do not commit station-specific secrets, credentials, or private
configuration (see [Development — contributing](development.md#contributing)).

## Operational notes

- The systemd unit runs with **`Restart=no`** — a crashed or failed app
  stays down rather than auto-restarting in a loop. This is deliberate
  (avoids restart/alert storms and half-verified states); you restart via
  deploy or Admin → Environment → Restart.
- Admin email alerts (optional plugin) can notify on startup failures and
  operational problems; duplicate alerts are debounced 15 minutes. See
  [Configuration — admin email](configuration.md#admin-email-optional-plugin).
- Logs (`data/logs/`) contain operational history, including schedule and
  radio activity. Keep the 30-day rotation in mind when sharing them.
