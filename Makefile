# SnakeBiteRx — common tasks (run from repo root)
.PHONY: verify assets train train-fast train-both api web-build

verify:
	python3 scripts/verify_stack.py

assets:
	python3 -m ml.build_assets

# -u = unbuffered stdout (you see each epoch as it finishes; otherwise logs look "stuck")
train:
	python3 -u -m ml.train_wound --ensemble --epochs 20 --batch-size 8

train-fast:
	python3 -u -m ml.train_wound --ensemble --epochs 5 --batch-size 8

# Full ensemble, then MobileNet single (models/wound_ensemble.pt + models/wound_mobilenet.pt)
train-both:
	bash scripts/train_both_checkpoints.sh

api:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Flutter web (same script as Vercel / Render). Example:
#   make web-build API_BASE=https://snakebite-api.onrender.com
web-build:
	API_BASE="$(API_BASE)" bash scripts/build_web.sh
