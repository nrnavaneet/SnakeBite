# Quickstart (beginners)

You will run **three pieces**: Python environment → **API** → **Flutter app** (or web).

## 0. Fastest path (fresh clone)

From the repo root:

```bash
make setup
```

Then continue from **§4 Start the API** below (activate venv, `make api`, then Flutter).

## 1. Python & dependencies

```bash
cd SnakeBite   # repo root
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Assets (geo + symptom catalogs)

Needed before the API can serve regions and symptoms:

```bash
make assets
```

## 3. Wound model (optional but recommended)

Place **`models/wound_ensemble.pt`** in the repo, or set **`WOUND_ENSEMBLE_URL`** so the API can download it on startup. Without it, the wound branch is a uniform prior (see [MODELS_AND_SCORES.md](MODELS_AND_SCORES.md)).

Train locally (slow on CPU):

```bash
make train-fast    # short run, or `make train` for full ensemble
```

## 4. Start the API

```bash
make api
# → http://127.0.0.1:8000/health
```

## 5. Flutter app

```bash
cd mobile/snakebite_rx
flutter pub get
flutter run --dart-define=API_BASE=http://127.0.0.1:8000
```

- **Web:** `flutter run -d chrome --dart-define=API_BASE=http://127.0.0.1:8000`
- **Android emulator API:** `http://10.0.2.2:8000`
- **Phone on same Wi‑Fi:** use your PC’s LAN IP, e.g. `http://192.168.1.10:8000`, or use `make dev-all` + tunnels (see main README).

## Verify

```bash
make verify
python3 -m pytest tests/ -q
```
