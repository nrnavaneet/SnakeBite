# SnakeBiteRx — common tasks (run from repo root)
.PHONY: setup verify assets train train-fast train-both api api-dev lab web-build serve-web tunnel-api tunnel-web dev-all stop kill

ifeq ($(OS),Windows_NT)
PY := py -3
VENV_PY := .venv/Scripts/python.exe
VENV_UVICORN := .venv/Scripts/uvicorn.exe
BASH := bash
else
PY := python3
VENV_PY := .venv/bin/python
VENV_UVICORN := .venv/bin/uvicorn
BASH := bash
endif

# Fresh clone runtime setup: venv, pip install, flutter pub get (no asset build by default)
setup:
	$(PY) scripts/setup_runtime.py

verify:
	$(PY) scripts/verify_stack.py

assets:
	$(PY) -m ml.build_assets

# -u = unbuffered stdout (you see each epoch as it finishes; otherwise logs look "stuck")
train:
	$(PY) -u -m ml.train_wound --ensemble --epochs 20 --batch-size 8

train-fast:
	$(PY) -u -m ml.train_wound --ensemble --epochs 5 --batch-size 8

# Full ensemble, then MobileNet single (models/wound_ensemble.pt + models/wound_mobilenet.pt)
train-both:
	$(BASH) scripts/train_both_checkpoints.sh

api:
	@if [ -x "$(VENV_UVICORN)" ]; then \
		"$(VENV_UVICORN)" backend.main:app --host 0.0.0.0 --port 8000; \
	else \
		echo "ERROR: $(VENV_UVICORN) not found. Run: make setup"; \
		exit 1; \
	fi

api-dev:
	@if [ -x "$(VENV_UVICORN)" ]; then \
		"$(VENV_UVICORN)" backend.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "ERROR: $(VENV_UVICORN) not found. Run: make setup"; \
		exit 1; \
	fi

# Lab browser UI (/ui/lab.html) + Cloudflare tunnel — no Flutter. Lighter than dev-all (full stack).
lab:
	$(BASH) scripts/lab.sh

# Clean scratch files, free ports, start API + tunnels + Flutter web, open Terminal tails (see script for flags).
dev-all:
	$(BASH) scripts/dev_all.sh

# Kill API + tunnels + Flutter + static serve (pid files + ports 8000/37555/8090). Same as cleanup before lab/dev-all.
stop:
	$(BASH) scripts/stop.sh

kill: stop

# Public HTTPS URL to local API (needs: brew install cloudflared). Run in a second terminal after `make api`.
tunnel-api:
	$(BASH) scripts/dev_tunnel.sh 8000

# Tunnel a Flutter web-server port (run `flutter run -d web-server --web-hostname 0.0.0.0 --web-port 37555` first).
tunnel-web:
	$(BASH) scripts/dev_tunnel.sh 37555

# Flutter web release build → mobile/snakebite_rx/build/web (default API http://127.0.0.1:8000)
web-build:
	API_BASE="$(API_BASE)" $(BASH) scripts/build_web.sh

# Serve Flutter build/web (like static hosting). Default PORT=8090. Needs: make api in another terminal.
serve-web:
	$(BASH) scripts/serve_web.sh
