# Isolated inference runtime

The application and original model dependencies use different environments. The model process has no incident database, approval or simulator credentials.

On macOS with Python 3.10:

```sh
python3.10 -m venv .venv-model
.venv-model/bin/pip install -r model/requirements.txt
python3 scripts/fetch_model.py
MODEL_KEY=YOUR_PRIVATE_MODEL_KEY .venv-model/bin/python model/server.py
```

On Linux AMD64, install the original CPU wheel before the pinned requirements to avoid the CUDA distribution:

```sh
python3.10 -m venv .venv-model
.venv-model/bin/pip install --no-deps 'torch==1.13.1+cpu' --extra-index-url https://download.pytorch.org/whl/cpu
.venv-model/bin/pip install -r model/requirements.txt
```

The Dockerfile performs this CPU installation and uses a writable temporary cache with offline model loading. `models/manifest.json` fixes the original checkpoint, tokenizer and SHA256 hashes. `scripts/fetch_model.py` checks existing files and refuses mismatches. Loading requires those exact files. A model or dependency upgrade needs a new identity, manifest, calibration and held-out comparison.

The authenticated `/generate` endpoint accepts at most 8,000 characters, 512 model input tokens and 48 generated tokens; requests cannot choose a model, file path or tool. Generation is deterministic and serial. Client timeouts are bounded. Model output is an untrusted diagnosis suggestion and is independently validated by the application.
