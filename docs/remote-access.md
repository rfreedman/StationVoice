# Remote access (Tailscale + Caddy)

How operators reach the announcements UI on the Linux host. The app itself listens on **`:8000`** (`HOST` / `PORT`; default `0.0.0.0:8000`). HTTPS for the public name is terminated by **Caddy**, not by the app.

## URLs

| Path | URL | Notes |
| --- | --- | --- |
| LAN / public name (HTTPS) | `https://announcements.w2zq.com` | Caddy on LAN IP `192.168.1.189:443` → `127.0.0.1:8000` |
| Direct app (HTTP) | `http://announcements.w2zq.com:8000` | Bypasses Caddy; useful when diagnosing proxy/TLS |
| Tailscale MagicDNS | `http://dvra-announcements.tail40e61e.ts.net:8000` | Same app port over the tailnet; Caddy is **not** bound on the Tailscale interface |

SSH (deploy scripts, etc.) uses the MagicDNS name, e.g. host `dvra-announcements` → `dvra-announcements.tail40e61e.ts.net` (user `announce`). See [Deploying](deploy.md).

## Architecture

```text
Browser ──HTTPS──► Caddy (192.168.1.189:443) ──► 127.0.0.1:8000  (app)
Tailnet ──HTTP───► host:8000  (app; MagicDNS name)
```

Caddy binds only the **Wi‑Fi LAN address** so it does not fight Tailscale (or anything else) for `:443` on other interfaces. Let’s Encrypt uses **DNS-01** via DreamHost (no need to expose 80/443 to the public internet for HTTP-01).

## Caddy

### Files on the host

| Path | Role |
| --- | --- |
| `/etc/caddy/Caddyfile` | Site + ACME DNS config |
| `/etc/caddy/dreamhost.env` | `DREAMHOST_API_KEY=…` (not in git; loaded by the unit) |
| `/etc/systemd/system/caddy.service` | Main unit |
| `/etc/systemd/system/caddy.service.d/override.conf` | Restart-on-failure drop-in |

### Caddyfile (as deployed)

Do not put the DreamHost API key in the Caddyfile; use `{env.DREAMHOST_API_KEY}` and the unit `EnvironmentFile`.

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

The binary must include the DreamHost DNS module (`caddy-dns/dreamhost`, typically an `xcaddy` build). Confirm with:

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

### Boot race (Wi‑Fi IP)

After reboot, Caddy can fail with:

`listen tcp 192.168.1.189:443: bind: cannot assign requested address`

when `network-online.target` is reached before `wlp1s0` has `192.168.1.189`. Symptom: `http://…:8000` works, `https://announcements.w2zq.com` does not; `sudo systemctl status caddy` shows failed.

The `Restart=on-failure` / `RestartSec=5` drop-in retries until the address exists. Manual recovery:

```bash
ip -4 addr show | grep 192.168.1.189   # confirm address is up
sudo systemctl restart caddy
curl -I https://announcements.w2zq.com
```

Useful checks (all need `sudo` on this host for the unit):

```bash
sudo systemctl status caddy --no-pager
sudo journalctl -u caddy -n 50 --no-pager
sudo cat /etc/caddy/Caddyfile
```

## Tailscale

- Device name / MagicDNS: **`dvra-announcements.tail40e61e.ts.net`**
- Used for SSH and for reaching the app on **port 8000** over the tailnet
- Caddy’s `bind 192.168.1.189` means **HTTPS for `announcements.w2zq.com` is LAN-side**, not via the Tailscale IP
- This host is not documented as using `tailscale serve` / Funnel for the UI; if that changes, update this section from `sudo tailscale serve status` / `sudo tailscale funnel status`

## DNS (DreamHost)

- Name: `announcements.w2zq.com` → LAN IP `192.168.1.189` for clients that should use Caddy HTTPS (hosts file, LAN DNS, or whatever you use for split resolution)
- ACME DNS-01 updates TXT records through the DreamHost API (`DREAMHOST_API_KEY` in `/etc/caddy/dreamhost.env`)
- Propagation is intentionally slow in the Caddyfile (`propagation_delay 10m`, `propagation_timeout 45m`) with DreamHost nameservers as resolvers
