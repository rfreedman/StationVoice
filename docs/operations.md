# Operations and deployment

How StationVoice is deployed to the station's Linux host, how operators reach
it, and what restarts do. This covers the systemd service, the deploy helper
scripts, remote access (Caddy + Tailscale), and process-restart behavior.
For host hardware setup see [Hardware and radio setup](hardware-setup.md);
for the backend the deployed app runs see [Radio backend](radio-backend.md).

Note that some information here is specific to the production installation
at the [DVRA](https://www.w2zq.com), including Linux service setup and
installation-specific scripts held in a scripts-local folder, which is 
not committed to the git repository.

## URLs and access

The app itself listens on **`:8000`** (`HOST` / `PORT`; default
`0.0.0.0:8000`). HTTPS for the public name is terminated by **Caddy**, not
by the app.

| Path | URL | Notes |
| --- | --- | --- |
| LAN / public name (HTTPS) | `https://announcements.w2zq.com` | Caddy on LAN IP `192.168.1.189:443` → `127.0.0.1:8000` |
| Direct app (HTTP) | `http://announcements.w2zq.com:8000` | Bypasses Caddy; useful when diagnosing proxy/TLS |
| Tailscale MagicDNS | `http://dvra-announcements.tail40e61e.ts.net:8000` | Same app port over the tailnet; Caddy is **not** bound on the Tailscale interface |

Access remotely via VPN (Tailscale); the web UI is intended for the local
network, not for public internet exposure.

```text
Browser ──HTTPS──► Caddy (192.168.1.189:443) ──► 127.0.0.1:8000  (app)
Tailnet ──HTTP───► host:8000  (app; MagicDNS name)
```

SSH (deploy scripts, etc.) uses the MagicDNS name, e.g. host
`dvra-announcements` → `dvra-announcements.tail40e61e.ts.net` (user
`announce`).

## Deployment

The Linux host runs the app from a git clone via a **systemd** unit whose
`ExecStart` is `./serve.sh` (uv sync + venv). Install uv once on that host
(it goes in `~/.local/bin`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Station-specific deploy helpers live in gitignored **`scripts-local/`**
(`deploy`, `start-remote`, `stop-remote`, `tail-remote`). Defaults:

| Env | Default |
| --- | --- |
| `DEPLOY_HOST` | `dvra-announcements` |
| `DEPLOY_PATH` | `/home/announce/StationVoice` |
| `SERVICE_NAME` | `dvra-announcements` |

From the dev machine, deploy whatever is pushed to `origin/main`:

```bash
scripts-local/deploy                         # default host dvra-announcements
scripts-local/deploy other-host              # or DEPLOY_HOST=other-host; DEPLOY_PATH / SERVICE_NAME override
```

### systemd start / stop

`scripts-local/start-remote` and `scripts-local/stop-remote` call
`sudo -n systemctl start|stop` with the bare unit name
(`dvra-announcements`, no `.service` suffix). Deploy stops the unit,
fast-forwards git, then starts the unit again. Startup success is
`Startup complete` in the unit journal (not `data/logs/serve.out`).
Admin → Environment → **Restart application** uses the same passwordless
`systemctl restart` rule.

The unit uses **`Restart=no`**: handled startup failures and crashes leave
the service inactive (no restart/email loop). After changing the unit file,
refresh it on the host with `scripts-local/install-systemd-service` (or
equivalent).

Non-interactive SSH cannot enter a sudo password. On the Linux host, allow
passwordless sudo **only** for this unit (as root / `tempadmin`):

```bash
sudo visudo -f /etc/sudoers.d/dvra-announcements
```

Example (use the paths from `command -v systemctl journalctl` on that host —
often `/usr/bin/...`):

```
announce ALL=(root) NOPASSWD: \
  /usr/bin/systemctl start dvra-announcements, \
  /usr/bin/systemctl stop dvra-announcements, \
  /usr/bin/systemctl restart dvra-announcements, \
  /usr/bin/journalctl -u dvra-announcements *
```

Match the **exact** binary path and argv. Use the bare unit name
**`dvra-announcements`** (no `.service` suffix) — sudo treats
`dvra-announcements` and `dvra-announcements.service` as different. `status`
is optional; it often works without root.

**Important:** a recent interactive `sudo` can cache credentials, so
`sudo -n …` may succeed in that SSH session even when NOPASSWD is wrong.
Clear the cache, then test the commands the scripts actually run:

```bash
command -v systemctl journalctl
sudo -k
sudo -n "$(command -v systemctl)" stop dvra-announcements
sudo -n "$(command -v systemctl)" start dvra-announcements
sudo -n "$(command -v journalctl)" -u dvra-announcements -n 5 --no-pager
sudo -l
```

If `stop` still asks for a password after `sudo -k`, the sudoers line for
`stop` is missing or the path/argv does not match. Fix the drop-in with
`visudo`, then re-test with `sudo -k` again.

Install or refresh the unit on the host with
`scripts/install-systemd-service` (run there; see
[`scripts/README.md`](../scripts/README.md)).

### Deploy behavior

The script refuses to run with uncommitted or unpushed local changes. On the
Linux host it checks that uv is present, that the systemd unit exists, that
the clone is clean, and that `origin/main` fast-forwards, all before stopping
the app. If `origin/main` has new commits, its `pyproject.toml` version must
be greater than the one the Linux host is running (bump with
`uv version --bump patch`, commit, push); otherwise the deploy stops and
leaves the app running. A redeploy with no new commits just restarts the
unit. It waits for `Startup complete` in the journal and warns if the radio
mode is `stub`. If the app does not stop within `DEPLOY_STOP_TIMEOUT` seconds
(default 30), the deploy aborts without updating; it never SIGKILLs the
app, because that can leave PTT keyed. Startup must log `Startup complete`
within `DEPLOY_START_TIMEOUT` seconds (default 180) or the deploy reports
failure. Both values are positive integer seconds.

If deploy reports **Linux host working tree has local changes** and
`git status` shows only `uv.lock`, an older `./serve.sh` may have rewritten
the lock on Linux. On the Linux host, discard that change, then redeploy
after `origin/main` includes `./serve.sh` with `uv sync --frozen`:

```bash
ssh dvra-announcements 'cd /home/announce/StationVoice && git restore uv.lock'
```

After `./serve.sh` is frozen, restarts should not modify `uv.lock` again;
confirm with `git status` on the Linux host if you want to be sure.

`./serve.sh` runs `uv sync --frozen --inexact --no-dev` before starting
(when uv is installed), so the venv matches the committed `uv.lock` and the
lock file itself is left unchanged.

### Installing locked versions by hand

Without uv on the Linux host, generate a pinned `requirements.txt` on the
dev machine and install it with pip:

```bash
uv sync --frozen --no-dev          # with uv
uv export --format requirements-txt --no-dev -o requirements.txt   # dev machine
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt  # Linux host, from the repo root
```

The exported file pins every package (with hashes) and keeps platform
markers, so the macOS-only `pyobjc-framework-Cocoa` is skipped on Linux. It
ends with `-e .`, which installs this project in editable mode (that is
where the app gets its version), so run the `pip install` from the repo
root. It is gitignored: regenerate it after any dependency change rather
than editing it.

### Versioning

The version is written once, in `pyproject.toml`, and the deploy requires a
version bump when `origin/main` has new commits. Details in
[Development — versioning](development.md#versioning).

### Optional admin email after deploy

Admin email is optional: copy a notifier from `plugin-examples/` into
`plugins/` and install that plugin's packages into the venv. For the Bird
example: `cp plugin-examples/bird_email.py plugins/` then
`uv pip install 'messagebird-sdk>=0.137.0'`. Full plugin and secret-file
configuration is in
[Configuration reference — admin email](configuration.md#admin-email-optional-plugin).

The first run downloads the default voice into `voices/` (gitignored):

```bash
python -m app download
python -m app download amy ryan
```

## Process restart and in-memory state

Deploy and any manual restart start a **new process**. Nothing below is
written to disk:

- **Busy retries** — APScheduler `defer:` jobs and in-flight manual-trigger
  retries are dropped. A slot whose fire time has already passed is **not**
  played late after restart. After an outage or restart, use **Trigger
  now** (see [Manual operation](manual-operations.md)) or wait for the next
  slot if something did not air; check logs for deferred fires that will not
  run until you trigger again.
- **Login rate limit** — Failed sign-in counters (`429` after
  `LOGIN_MAX_FAILURES` failures, default five, per username from the same
  client within `LOGIN_WINDOW_SECONDS`, default 300 seconds) reset.
  Legitimate sessions in cookies may still work until they expire.

Other fatal startup errors log, notify once, and exit; the systemd unit uses
**`Restart=no`**, so it stays inactive until you `systemctl start` / deploy /
Admin restart. Confirm the radio mode with the
**`Startup complete … (radio mode: dra)`** log line — see
[Radio backend](radio-backend.md).

## Caddy (HTTPS on the LAN)

### Files on the host

| Path | Role |
| --- | --- |
| `/etc/caddy/Caddyfile` | Site + ACME DNS config |
| `/etc/caddy/dreamhost.env` | `DREAMHOST_API_KEY=…` (not in git; loaded by the unit) |
| `/etc/systemd/system/caddy.service` | Main unit |
| `/etc/systemd/system/caddy.service.d/override.conf` | Restart-on-failure drop-in |

### Caddyfile (as deployed)

Do not put the DreamHost API key in the Caddyfile; use
`{env.DREAMHOST_API_KEY}` and the unit `EnvironmentFile`.

```caddyfile
{
        acme_dns dreamhost {
                api_key {env.DREAMHOST_API_KEY}
        }
}

announcements.w2zq.com {
        bind 192.168.1.189
        tls {
                dns dreamhost {
                        api_key {env.DREAMHOST_API_KEY}
                }
                propagation_delay 10m
                propagation_timeout 45m
                resolvers ns1.dreamhost.com ns2.dreamhost.com
        }
        reverse_proxy 127.0.0.1:8000
}
```

The binary must include the DreamHost DNS module (`caddy-dns/dreamhost`,
typically an `xcaddy` build). Confirm with:

```bash
caddy list-modules | rg -i dreamhost
```

### systemd unit (essentials)

- `After=` / `Requires=network-online.target` (already set).
- `EnvironmentFile=/etc/caddy/dreamhost.env`
- `ExecStart=/usr/bin/caddy run --config /etc/caddy/Caddyfile`
- Drop-in override:

```ini
[Service]
Restart=on-failure
RestartSec=5
```

Caddy binds only the **Wi-Fi LAN address** so it does not fight Tailscale
(or anything else) for `:443` on other interfaces. Let's Encrypt uses
**DNS-01** via DreamHost (no need to expose 80/443 to the public internet
for HTTP-01).

### Boot race (Wi-Fi IP)

After reboot, Caddy can fail with:

`listen tcp 192.168.1.189:443: bind: cannot assign requested address`

when `network-online.target` is reached before `wlp1s0` has `192.168.1.189`.
Symptom: `http://…:8000` works, `https://announcements.w2zq.com` does not;
`sudo systemctl status caddy` shows failed. The `Restart=on-failure` /
`RestartSec=5` drop-in retries until the address exists. Manual recovery:

```bash
ip -4 addr show | grep 192.168.1.189   # confirm address is up
sudo systemctl restart caddy
curl -I https://announcements.w2zq.com
```

Useful checks (these need `sudo` on this host for the unit):

```bash
sudo systemctl status caddy --no-pager
sudo journalctl -u caddy -n 50 --no-pager
sudo cat /etc/caddy/Caddyfile
```

## Tailscale

- Device name / MagicDNS: **`dvra-announcements.tail40e61e.ts.net`**
- Used for SSH and for reaching the app on **port 8000** over the tailnet
- Caddy's `bind 192.168.1.189` means **HTTPS for `announcements.w2zq.com`
  is LAN-side**, not via the Tailscale IP
- This host is not documented as using `tailscale serve` / Funnel for the
  UI; if that changes, update this section from
  `sudo tailscale serve status` / `sudo tailscale funnel status`

## DNS (DreamHost)

- Name: `announcements.w2zq.com` → LAN IP `192.168.1.189` for clients that
  should use Caddy HTTPS (hosts file, LAN DNS, or whatever you use for split
  resolution)
- ACME DNS-01 updates TXT records through the DreamHost API
  (`DREAMHOST_API_KEY` in `/etc/caddy/dreamhost.env`)
- Propagation is intentionally slow in the Caddyfile (`propagation_delay
  10m`, `propagation_timeout 45m`) with DreamHost nameservers as resolvers

## See also

- [Troubleshooting](troubleshooting.md) — symptom-first runbook
- [Manual operation](manual-operations.md) — Trigger now and restart recovery
- [Backup and recovery](backup-recovery.md) — what to back up on the host
- [Development — versioning](development.md#versioning)
