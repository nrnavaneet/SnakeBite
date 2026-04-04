# SnakeBiteRx

Multi-modal prototype: **wound CNN** + **symptom knowledge base** + **country/state geo prior** + **context** (time since bite, bite circumstance, age, weight) → fused venom-type distribution.

**Not a medical device** — research / education only.

## Repository layout

```
SnakeBite/
├── README.md                 # this file
├── Makefile                  # verify | assets | train | api
├── requirements.txt          # Python deps (local dev; includes `-r requirements-core.txt`)
├── requirements-render.txt   # CPU-only PyTorch for Render (`pip install -r requirements-render.txt`)
├── requirements-core.txt     # Shared deps (no torch)
├── .gitignore
├── data/                     # datasets — do not delete (geo / symptom / wound CSVs)
│   └── geo_data/             # GBIF CSV, `snake_wounds_labels.json`, `categories/<label>/*.jpg`
├── models/                   # generated artifacts (see checklist below)
├── ml/                       # training, fusion, inference
├── backend/                  # FastAPI (`uvicorn backend.main:app`)
├── mobile/snakebite_rx/      # Flutter client
├── scripts/                  # labeling utilities, `verify_stack.py`
├── data_pipeline_snakebite/  # WHO/symptom CSV builders (optional tooling)
└── docs/                     # e.g. `SnakeBiteRx_Labeling_Rubric.pdf`
```

## Is everything ready?

| Component | Status | Notes |
|-----------|--------|--------|
| **Wound CNN** | Trained checkpoint present | Prefer `models/wound_ensemble.pt`: **EfficientNet-B3 + ResNet50 + DenseNet121**, softmax fused with equal weights (see `ml/infer.py`). Fallback: `wound_mobilenet.pt` (single backbone). Train with `make train` (`--ensemble`). |
| **Symptom engine** | Built | `models/symptom_catalog.json` (87 symptoms from KB) |
| **Geo prior** | Built | `geo_region_prior.json` (venom-type by region); `geo_species_table.json` (species × region × venom from GBIF); `geo_index.pkl` legacy BallTree |
| **Fusion + context** | Code | `ml/fusion.py` (time / circumstance / age / weight) |
| **Backend API** | Ready | FastAPI; run `make api` |
| **Flutter app** | Code ready | Install Flutter SDK, then `flutter pub get` + `flutter run` |

One-command check (loads models, runs fusion on a sample image):

```bash
make verify
# or: python3 scripts/verify_stack.py
```

Automated tests (probabilities sum to 1, geo table lookups, fusion):

```bash
python3 -m pytest tests/ -v
```

**Geo note:** `data/geo_data/snake_geo_clean.csv` includes **`scientific_name`**, **`generic_name`**, **`common_name`** (plus `family`, lat/lon, `country`, `state`, `venom_type`). After editing this file, run **`make assets`** so `geo_region_prior.json` and `geo_species_table.json` refresh. Species suggestions in the API prefer **common / generic** labels for display, with scientific names attached. Counts are occurrence-based, not bite registries — **not** a guarantee of clinical diagnosis.

**Wound CNN note:** Training uses only images labeled with one of the five venom classes in `data/wound_data/training_data.csv`. Files under `data/geo_data/categories/unknown/` are **not** used as supervision — testing on those images is out-of-distribution for the classifier.

## Python setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Regenerate assets / retrain

```bash
make assets      # symptom_catalog + geo_region_prior + geo_species_table + geo_index.pkl
make train       # ensemble → models/wound_ensemble.pt (long on CPU; logs use unbuffered `-u` so epochs print live)
make train-fast  # shorter run (5 epochs) for a quicker checkpoint
# If the terminal looks “stuck” after weight download: the first epoch on CPU can take many minutes; you should see “first batch done” then epoch lines.
```

## API

```bash
make api
# → http://127.0.0.1:8000
```

### Test in the browser (no Flutter needed)

With the server running, open:

**http://127.0.0.1:8000/ui/** — simple flow · **http://127.0.0.1:8000/ui/lab.html** — temporary lab (wound / geo / symptom / fusion step-by-step)

Upload a wound image, pick **country** and optional **state**, set time/circumstance/age/weight, optional symptoms JSON (e.g. `["ptosis"]`), then **Analyze**.  
Swagger docs: **http://127.0.0.1:8000/docs**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Links to docs + `/ui/` |
| `/ui/` | GET | Static test page |
| `/ui/lab.html` | GET | Lab: wound / geo / symptoms / fusion separately + pipeline |
| `/test/sample_wound_image` | GET | Sample JPG from `data/geo_data/categories/hemotoxic/` |
| `/health` | GET | Model loaded?, class list |
| `/symptoms` | GET | JSON list of symptom strings for UI |
| `/geo/regions` | GET | `countries` + `states_by_country` for dropdowns |
| `/predict` | POST | multipart: … → **`wound_probability`** (fused) + **`wound_detail`** (per-backbone probs when ensemble loaded) + **`snake_species_top`** |
| `/test/wound` | POST | fused wound probabilities (+ `wound_detail` per backbone when ensemble) |
| `/test/wound/backbone` | POST | one backbone: `backbone` = efficientnet_b3 \| resnet50 \| densenet121 |
| `/test/geo` | POST | geo venom prior + species from that prior |
| `/test/symptoms` | POST | symptom KB only (no image) |

## Flutter app

Requires [Flutter](https://flutter.dev/) installed.

```bash
cd mobile/snakebite_rx
flutter pub get
flutter analyze
flutter run --dart-define=API_BASE=http://127.0.0.1:8000
```

- **Android emulator:** use `--dart-define=API_BASE=http://10.0.2.2:8000`

### Web app — entirely on Render (no Vercel)

You need **two** Render resources: a **Web Service** (API) and a **Static Site** (Flutter web). Vercel is not required.

**A) One-shot: Blueprint (both from `render.yaml`)**

1. [Dashboard](https://dashboard.render.com) → **New** → **Blueprint** → connect **SnakeBite** → apply **`render.yaml`**.
2. After deploy, open the **API** service → **Connect** → copy its **HTTPS** URL (it may look like `https://snakebite-api-xxxx.onrender.com`, not always the short name).
3. Open the **static** service **`snakebite-web`** → **Environment** → set **`API_BASE`** to that **exact** API URL (no trailing slash) → **Save** → **Manual Deploy** so the Flutter build bakes in the right API.

**B) You already created the API by hand (e.g. “SnakeBite”) — add only the static site**

1. **New** → **Static Site** → same repo and branch as the API.
2. **Build command:** `bash scripts/render_build_web.sh`
3. **Publish directory:** `mobile/snakebite_rx/build/web`
4. **Environment variables:** **`API_BASE`** = your API’s public URL from the API service **Connect** tab (example shape: `https://snakebite-eag1.onrender.com`). This must be the real URL, not a guess.
5. **Redirects / rewrites:** add a **rewrite**: source `/*` → destination `/index.html` (so `/home` works for the SPA).
6. Deploy, then open the static site’s URL in a browser; use **Settings** in the app if an old API URL was saved.

The repo **`render.yaml`** encodes option **A** (service names `snakebite-api` + `snakebite-web`). Option **B** is the same idea with two manual services.

| Piece | Render type | Purpose |
|-------|-------------|---------|
| API | Web Service (Python) | `uvicorn backend.main:app`, build with **`requirements-render.txt`** |
| App | Static Site | Flutter `build/web`, **`API_BASE`** points at the API URL above |

**`scripts/build_web.sh`** is invoked by **`scripts/render_build_web.sh`**. When **`API_BASE`** is set on the static site, it runs `flutter build web` and writes **`api_config.json`**.

Model files (`*.pt`) are gitignored; upload them to the API instance or use an artifact pipeline so **`models/`** exists at runtime on the API service.

**Render CLI (validate + redeploy):** Install the [Render CLI](https://render.com/docs/cli) (`brew install render`), then `render login` and `render workspace set`. Validate: `render blueprints validate render.yaml`. After the Blueprint exists, redeploy both services from the repo root: **`bash scripts/render_deploy.sh`**. The CLI cannot create the initial Blueprint from YAML alone; use the dashboard once (**New → Blueprint**), then use the script for later deploys.

### Web app — Vercel (frontend only, optional)

You can still host only the Flutter static output on [Vercel](https://vercel.com/) and run the API on Render or elsewhere. **Example:** [https://snakebiterx.vercel.app](https://snakebiterx.vercel.app).

**CORS / “Failed to fetch”:** **`vercel.json`** rewrites **`/api/proxy/*`** to your Render API host so the browser calls **the same origin as the site** (e.g. `https://….vercel.app/api/proxy/predict`), which avoids cross-origin issues on **`/predict`**. Edit the **`destination`** URL in **`vercel.json`** if your Render hostname changes. The build script sets **`API_BASE`** to **`https://$VERCEL_URL/api/proxy`** on Vercel unless you set **`API_BASE`** to a full URL that contains **`/api/proxy`** (for a custom domain).

1. Deploy the API on Render and keep **`vercel.json`** proxy **`destination`** in sync with that URL.
2. Deploy from Vercel (Git integration supplies **`VERCEL_URL`** during build). You do **not** need **`API_BASE`** pointing at Render for the default `*.vercel.app` setup.
3. Or commit **`mobile/snakebite_rx/web/api_config.json`** when not using the Vercel env flow.
4. Without a configured API URL, the hosted app shows a configuration message (localhost is not used on public hosts).

On a phone: open the site, **Gallery** / **Camera**, fill fields, **Run analysis**.

**Manual API on Render:** Web Service from this repo: root **`.`**, build **`pip install --no-cache-dir -r requirements-render.txt`** (CPU-only PyTorch; avoids huge CUDA wheels), start `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.

**Full screen (no browser UI):** install the site as an app: **Chrome menu → Install app** or **Safari → Share → Add to Home Screen**. The manifest uses `display: fullscreen` so the installed PWA uses the whole screen. A normal browser tab still shows the address bar (that is expected).

**If symptoms or countries do not load:** open **Settings** in the app and tap **Clear saved** for the API URL, or clear site data. An old `127.0.0.1` URL saved in the browser blocked `web/api_config.json` before; that is fixed in the latest client (production uses `api_config.json` before a loopback saved URL).

Local production-like web build:

```bash
make web-build API_BASE=https://your-api.example.com
# output: mobile/snakebite_rx/build/web
```

`backend/main.py` already enables **CORS** for browser calls from any origin (`allow_origins=["*"]`). Use **HTTPS** for both the site and the API so browsers allow requests.

## Fusion tuning

Edit `ml/fusion.py` for modality weights and context priors when you have validated clinical data.
