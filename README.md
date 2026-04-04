# SnakeBiteRx

Multimodal **prototype** for **venom-type estimation** from a **wound photo** + **symptoms** + **region** + **context** (time since bite, circumstance, age, weight). Outputs a **probability distribution** over five classes — not a diagnosis.

**Educational / research only — not a medical device.** Always follow local emergency care.

---

## Documentation index

| Doc | Contents |
|-----|----------|
| [docs/README.md](docs/README.md) | Index of all topic docs |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Step-by-step first run |
| [docs/MODELS_AND_SCORES.md](docs/MODELS_AND_SCORES.md) | Checkpoints, confidence, fusion |
| [docs/WHY_AND_WEIGHTS.md](docs/WHY_AND_WEIGHTS.md) | Why ensemble + modality weights |
| [docs/DATA_LAYOUT.md](docs/DATA_LAYOUT.md) | `data/` layout, assets |
| [docs/TUNNELS.md](docs/TUNNELS.md) | Quick tunnels vs **stable** URLs (Cloudflare named tunnel, ngrok, Tailscale) |

---

## Prerequisites

| Tool | Notes |
|------|--------|
| **Git** | Clone this repository |
| **Python 3.10+** | `python3 --version` |
| **pip** | Usually bundled with Python |
| **Flutter SDK** | For the mobile/web app (`flutter doctor`). Optional if you only run the HTTP API |

**Disk / RAM:** PyTorch + training data are large; allow several GB for a full dev install.

---

## New machine: one script (after `git clone`)

From the **repository root**:

```bash
git clone <your-repo-url> SnakeBite
cd SnakeBite
make setup
```

Or equivalently:

```bash
bash scripts/setup_dev.sh
```

This will:

1. Create **`.venv`** (if missing) and `pip install -r requirements.txt`
2. Run **`python3 -m ml.build_assets`** (same as `make assets`) — symptom/geo JSON and `geo_index.pkl`
3. Run **`flutter pub get`** in `mobile/snakebite_rx` if `flutter` is on your `PATH`

Then start the stack manually (two terminals):

**Terminal A — API**

```bash
cd /path/to/SnakeBite
source .venv/bin/activate   # Windows: .venv\Scripts\activate
make api
```

**Terminal B — Flutter app**

```bash
cd /path/to/SnakeBite/mobile/snakebite_rx
flutter run --dart-define=API_BASE=http://127.0.0.1:8000
```

**Web (Chrome):**

```bash
cd mobile/snakebite_rx
flutter run -d chrome --dart-define=API_BASE=http://127.0.0.1:8000
```

**Android emulator** (API on host): use `http://10.0.2.2:8000` instead of `127.0.0.1`.

**Physical phone on same Wi‑Fi:** use your computer’s LAN IP, e.g. `http://192.168.1.10:8000`, or set the URL in **Settings** inside the app. For public HTTPS URLs, see `make dev-all` / tunnel scripts below.

---

## Manual setup (same as the script)

If you prefer not to use `make setup`:

```bash
cd SnakeBite
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
make assets                        # or: python3 -m ml.build_assets
cd mobile/snakebite_rx && flutter pub get && cd ../..
make api                           # in another terminal after activate
```

---

## Wound model checkpoint (optional but recommended)

The API works without a local checkpoint (image branch becomes a uniform prior), but for real image-driven behaviour you need **`models/wound_ensemble.pt`** (or **`models/wound_mobilenet.pt`**).

| Option | How |
|--------|-----|
| Copy file | Place `wound_ensemble.pt` under `models/` |
| Download on startup | Set env **`WOUND_ENSEMBLE_URL`** or **`WOUND_CHECKPOINT_URL`** to an HTTPS URL of the `.pt` file (see `backend/checkpoint_bootstrap.py`) |
| Train locally | `make train` or `make train-fast` (slow on CPU) |

---

## Full Makefile command reference

Run all commands from the **repo root** with `source .venv/bin/activate` (except pure `make` targets that invoke tools directly).

| Command | Purpose |
|---------|---------|
| `make setup` | **Bootstrap:** venv, `pip install`, `make assets`, `flutter pub get` if available (`scripts/setup_dev.sh`) |
| `make verify` | Smoke-test stack (requires checkpoint + `data/` samples — see script output) |
| `make assets` | Rebuild symptom/geo JSON + `geo_index.pkl` (`python3 -m ml.build_assets`) |
| `make train` | Train wound ensemble → `models/wound_ensemble.pt` |
| `make train-fast` | Shorter training run |
| `make train-both` | Ensemble + MobileNet (`scripts/train_both_checkpoints.sh`) |
| `make api` | Start FastAPI with **uvicorn** on **0.0.0.0:8000** (reload) |
| `make web-build` | Release Flutter web build → `mobile/snakebite_rx/build/web` (`scripts/build_web.sh`) |
| `make serve-web` | Static server for `build/web` (default port **8090**; needs API separately) |
| `make tunnel-api` | Public HTTPS tunnel to local port 8000 (`scripts/dev_tunnel.sh`; needs `cloudflared` etc.) |
| `make tunnel-web` | Tunnel Flutter web-server port (see script) |
| `make dev-all` | Multi-process dev (API + tunnels + Flutter; `scripts/dev_all.sh`) |

Underlying scripts live in **`scripts/`**.

---

## API (local defaults)

| Item | Value |
|------|--------|
| Base URL | `http://127.0.0.1:8000` |
| Health | `GET /health` |
| Predict | `POST /predict` (multipart image + form fields) |
| OpenAPI / Swagger | `GET /docs` |
| Browser test UI | `GET /ui/` · lab: `/ui/lab.html` |

---

## Repository layout

```
SnakeBite/
├── README.md
├── Makefile
├── requirements.txt
├── requirements-core.txt
├── requirements-render.txt
├── scripts/
│   ├── setup_dev.sh          # clone → ready dev env
│   ├── verify_stack.py
│   ├── dev_all.sh
│   ├── dev_tunnel.sh
│   ├── build_web.sh
│   ├── serve_web.sh
│   └── train_both_checkpoints.sh
├── ml/
├── backend/
├── models/                   # checkpoints + generated JSON/PKL (see .gitattributes)
├── data/
├── mobile/snakebite_rx/
├── tests/
└── docs/
```

---

## Flutter web / configuration

- Default API for web builds: **`mobile/snakebite_rx/web/api_config.json`** (often `http://127.0.0.1:8000`).
- Override: **Settings** in the app, or `--dart-define=API_BASE=...` when running/building.

---

## Tests

```bash
source .venv/bin/activate
python3 -m pytest tests/ -v
```

Quick quiet run:

```bash
python3 -m pytest tests/ -q
```

---

## Fusion tuning

Edit **`ml/fusion.py`** (modality weights, symptom smoothing, conflict handling). Do not tune on real patients without proper validation.

---

## License / ethics

Use only for learning and research. Models err; geography is not clinical incidence; wound labels follow your dataset rubric. Emergency: call local emergency services.
