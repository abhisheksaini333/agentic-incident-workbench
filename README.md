# Incident Workbench

An incident desk that gathers service evidence, prepares a reviewable recovery plan and verifies the outcome. Operators investigate; an independent reviewer approves exact actions before they can run.

The console includes an incident queue, evidence history, diagnosis records, a plan editor, reviewer change requests, approval controls, recovery actions and an audit timeline. PostgreSQL preserves progress and effect receipts across worker restarts. Six local service faults make recovery measurable without touching production infrastructure.

**Runbook rules are the default.** Optional FLAN-T5 reviewers and an original LangGraph specialist workflow support controlled experiments. On the same eleven held-out incidents, rules recovered 11, a single model recovered 1 and the graph recovered 4. [Read the comparison](docs/evaluation.md) before enabling model modes.

## Start the local stack

Requirements: Docker with Compose, Python 3.10+ for setup and enough free memory for the optional model. The original model container targets Linux AMD64; Apple Silicon uses Docker emulation.

```sh
python3 scripts/init_demo.py
docker compose up -d --build
docker compose --profile setup run --rm seed
```

Open **http://localhost:8085**. `scripts/init_demo.py` creates a private `.env` and refuses to overwrite existing secrets. Use its `DEMO_PASSWORD` with one of these local accounts:

| Account | What it can do |
| --- | --- |
| `acme.operator` | Open incidents, edit plans, recollect evidence, cancel or resume work |
| `acme.approver` | Review an independent plan, request changes and approve exact actions |
| `acme.viewer` | Read the company's incidents and evidence |
| `acme.admin` | Manage account roles and inject local simulator faults |

Equivalent `beta.*` accounts belong to a separate tenant. Demo seeding is idempotent and preserves existing passwords, roles and recovered services.

1. Sign in as the operator and open an incident for `heap-api`.
2. Review the collected metrics, logs and proposed restart.
3. In another browser context, sign in as the approver. Request changes or approve the exact plan after inspecting its evidence.
4. Watch the worker apply the approved action and record the receipt, then collect fresh metrics and check the workload.
5. Use the administrator's simulator panel to exercise the other fault families.

| Service | Local fault | Bounded recovery |
| --- | --- | --- |
| `heap-api` | Memory pressure | Restart the simulated process |
| `busy-api` | CPU saturation | Throttle requests by 10–50% |
| `release-api` | Bad release | Return to the stable release |
| `catalog-api` | Dependency outage | Restore the catalog dependency |
| `storage-api` | Disk pressure | Rotate logs, retaining 1–10 files |
| `queue-api` | Queue backlog | Scale consumers to 2–4 replicas |

## Optional model experiments

Download the original checkpoint and verify every file against `models/manifest.json`:

```sh
python3 scripts/fetch_model.py
```

Set `ENABLE_MODEL_MODES=1` in `.env`, then:

```sh
docker compose --profile models up -d --build
docker compose --profile models ps
```

Wait for the model service to become healthy. The incident form now offers one model reviewer or three specialist reviewers. Unsupported diagnoses stop for investigation. The model does not approve or execute actions. To use an existing verified cache, set `MODEL_WEIGHTS_DIR` to that directory for Compose; it is mounted read-only.

## Develop and verify

Use separate Python environments for the application and original model packages:

```sh
python3.10 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests -q
npm ci --prefix frontend
npm test --prefix frontend
npm run build --prefix frontend
```

Set `INCIDENT_TEST_DATABASE` to a disposable PostgreSQL connection URL to run real database tests, including concurrent bootstrap and stale worker fencing. Without it those tests are explicitly skipped. Tests using deterministic model fixtures do not establish actual model quality; the comparison command performs real inference.

For native components, load the private `.env`, start its PostgreSQL service, and run `python -m incident simulator`, `python -m incident seed`, `python -m incident api` and `python -m incident worker` in separate terminals. The API serves the built console. `npm run dev --prefix frontend` serves the development UI on port 5185 and proxies to the API on 8085. Model-native installation uses a separate environment with `model/requirements.txt`; launch `python model/server.py --directory models/flan-t5-small` and enable model modes explicitly.

The real browser journey uses seeded accounts and `DEMO_PASSWORD`:

```sh
node frontend/e2e/journey.cjs
```

It uses installed Chrome by default. Set `BROWSER_CHANNEL=bundled` after installing Playwright Chromium to use the pinned browser. `DIAGNOSIS_MODE=graph` exercises actual specialist records when the model profile is enabled. Screenshots and reports go to `artifacts/browser`.

See the [architecture](docs/architecture.md), [recovery and backup runbook](docs/runbook.md), [evaluation](docs/evaluation.md) and [dependency/model notices](THIRD_PARTY_NOTICES.md). CI defines PostgreSQL tests, the browser approval journey and a container build; hosted CI results require a run on the hosting provider.
