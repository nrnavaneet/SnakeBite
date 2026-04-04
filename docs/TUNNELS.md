# Tunnels: quick vs permanent access

## Quick lab + tunnel (browser only)

For **`/ui/lab.html`** without the full Flutter stack:

```bash
make lab
```

**Kills** previous SnakeBite/tunnel PIDs and frees ports, then starts API + tunnel fresh. Prints local + public URLs and **opens the public HTTPS lab** (`…trycloudflare.com/ui/lab.html`) in your browser (falls back to localhost if the URL is not ready yet). `LAB_OPEN=0 make lab` skips the browser. By default the script **waits 10 seconds** (`LAB_OPEN_DELAY_SEC`, e.g. `LAB_OPEN_DELAY_SEC=15 make lab`) before opening the URL so the tunnel and first load can settle. Logs: `/tmp/snakebite_lab_tunnel.log`, `/tmp/snakebite_lab_api.log`. See `scripts/lab.sh`.

**`make dev-all`** does the same cleanup, then opens the **Flutter web** tunnel URL only (not the lab — use **`make lab`** for `/ui/lab.html`). `--no-tunnels` uses localhost for the opened tab.

Use **`make dev-all`** when you need API + tunnels **+ Flutter web** (heavier “full” dev).

---

## What the repo uses today

`scripts/dev_tunnel.sh` runs **Cloudflare quick tunnels**:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

- The **HTTPS URL changes every time** you start a new tunnel (e.g. `*.trycloudflare.com`).
- The tunnel **dies when you stop** `cloudflared` or close the terminal.
- So you **cannot** “leave it open forever” as a single fixed link with this command alone — it’s meant for **temporary** phone/QA access while you’re developing.

Your **Mac/PC must also be running** the API (`make api`) and the tunnel process. If the machine sleeps or goes offline, the URL stops working.

---

## If you want a **stable URL** you can bookmark

You need a **named tunnel** (or a similar product), not the quick-tunnel one-liner.

### Option A — Cloudflare Named Tunnel (stable hostname)

1. Cloudflare account + (optional) a domain on Cloudflare.
2. In **Zero Trust → Networks → Tunnels**, create a tunnel and install `cloudflared`.
3. Map a hostname like `snakebite-api.yourdomain.com` → `http://localhost:8000`.
4. Run `cloudflared` as a **system service** so it restarts on boot (see Cloudflare docs: “Run as a service” for macOS/Linux/Windows).

The **hostname stays the same**; you still must keep the machine (or a small always-on server) **online** with the API listening.

### Option B — ngrok reserved domain

Paid ngrok can attach a **fixed subdomain**. Same idea: run `ngrok` as a background service pointing at port 8000.

### Option C — Tailscale (no public URL, but “always there” on your devices)

Install **Tailscale** on your dev machine and phone. Use the machine’s **Tailscale IP** and port 8000, e.g. `http://100.x.x.x:8000`, only on your tailnet. No public internet exposure; good for personal use.

---

## “Always on” checklist

| Requirement | Why |
|-------------|-----|
| Machine awake or a small VPS | Tunnel endpoint must run somewhere |
| API running (`uvicorn` / `make api`) | Tunnel only forwards to localhost |
| `cloudflared` (or ngrok) as a **service** | Survives logout/reboot if configured |
| **Auth / HTTPS** for anything public | Dev APIs should not be wide open |

---

## Summary

- **Quick tunnel** (`dev_tunnel.sh`): **temporary**, random URL — fine for a session.
- **Permanent bookmarkable URL**: configure a **named Cloudflare Tunnel** or **ngrok reserved domain** + run the tunnel as a **service** on an **always-on** host.

Official references: [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), [cloudflared service install](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/local-management/as-a-service/).
