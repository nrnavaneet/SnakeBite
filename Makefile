# SnakeBiteRx — common tasks (run from repo root)
.PHONY: verify assets train train-fast api web-build

verify:
	python3 scripts/verify_stack.py

assets:
	python3 -m ml.build_assets

# -u = unbuffered stdout (you see each epoch as it finishes; otherwise logs look "stuck")
train:
	python3 -u -m ml.train_wound --ensemble --epochs 20 --batch-size 8

train-fast:
	python3 -u -m ml.train_wound --ensemble --epochs 5 --batch-size 8

api:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Flutter web for Vercel / static hosting. Set API_BASE to your public HTTPS API, e.g.:
#   make web-build API_BASE=https://snakebite-api.onrender.com
web-build:
	cd mobile/snakebite_rx && flutter pub get && flutter build web --release --dart-define=API_BASE=$(API_BASE) --base-href /
