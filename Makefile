# SnakeBiteRx — common tasks (run from repo root)
.PHONY: setup verify assets train train-fast train-both api lab web-build serve-web tunnel-api tunnel-web dev-all stop kill

# Fresh clone: venv, pip install, build assets, flutter pub get (if flutter on PATH)
setup:
	bash scripts/setup_dev.sh

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

# Lab browser UI (/ui/lab.html) + Cloudflare tunnel — no Flutter. Lighter than dev-all (full stack).
lab:
	bash scripts/lab.sh

# Clean scratch files, free ports, start API + tunnels + Flutter web, open Terminal tails (see script for flags).
dev-all:
	bash scripts/dev_all.sh

# Kill API + tunnels + Flutter + static serve (pid files + ports 8000/37555/8090). Same as cleanup before lab/dev-all.
stop:
	bash scripts/stop.sh

kill: stop

# Public HTTPS URL to local API (needs: brew install cloudflared). Run in a second terminal after `make api`.
tunnel-api:
	bash scripts/dev_tunnel.sh 8000

# Tunnel a Flutter web-server port (run `flutter run -d web-server --web-hostname 0.0.0.0 --web-port 37555` first).
tunnel-web:
	bash scripts/dev_tunnel.sh 37555

# Flutter web release build → mobile/snakebite_rx/build/web (default API http://127.0.0.1:8000)
web-build:
	API_BASE="$(API_BASE)" bash scripts/build_web.sh

# Serve Flutter build/web (like static hosting). Default PORT=8090. Needs: make api in another terminal.
serve-web:
	bash scripts/serve_web.sh
