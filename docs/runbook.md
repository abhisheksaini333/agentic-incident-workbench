# Operations and recovery

## Readiness and normal use

`docker compose ps` should show healthy PostgreSQL, simulator and API services. The optional `model` profile has its own health check after weights load. API `/health` checks the process; `/ready` checks storage and reports whether simulator configuration exists. It does not claim an end-to-end model or service recovery check. The incident's fresh workload verification establishes recovery for that service.

Local HTTP bindings are loopback-only. Simulator and model ports stay inside the Compose network. Keep `.env` private; do not commit, share or print it in bug reports. Model mode is disabled in generated setup until `ENABLE_MODEL_MODES=1`. Model files are mounted read-only and verified at startup. Service keys are separate from login sessions, and the simulator uses different worker and fault-injection authorities.

## Pending approvals, changes and cancellation

- **Awaiting approval:** review the displayed evidence snapshot and every action argument. The author needs an independent approver. A browser checkbox acknowledges that exact plan digest, so a replacement plan cannot reuse the checkbox.
- **Changes requested:** the operator must save a new plan version. The outstanding request blocks approval of the unchanged plan.
- **Service changed:** use Recollect evidence. The old plan and approval are invalidated. A stale simulator generation cannot authorize a mutation.
- **Cancelled:** no further effects can start. Existing receipts remain visible. Check pending receipts records facts about an already dispatched effect without granting permission for another one.
- **Escalated after transport loss:** investigate the simulator, inspect pending receipts, then use Check pending receipts. Resume approved plan preserves the original action keys and requires a still-valid exact approval. Recollecting instead creates a new evidence/plan review cycle.
- **Budget exhausted:** investigate outside the stopped run. Recollecting does not reset consumed step, time, model or effect budgets. Do not modify persisted counters to force more actions.

The worker uses a 60-second lease and checks ownership before publishing results or effects. A lost worker's lease time is charged before recovery. Receipt transport failures use durable exponential backoff and escalate after three failed checks. The pending outbox remains available for investigation. PostgreSQL connection loss can terminate a worker; Compose allows up to three automatic restarts. Restore the database and explicitly restart the worker if those attempts are exhausted. Restarting does not erase progress.

## Reproduce process crash and receipt recovery

With the model profile healthy:

```sh
mkdir -p artifacts
docker compose exec -T api python scripts/crash_probe.py --output /tmp/process-crash.json
docker compose exec -T api cat /tmp/process-crash.json > artifacts/process-crash.json
```

The probe creates a disposable schema and tenant, kills one real worker process while it waits for a decision, approves the persisted plan, exits another process after the actual simulator effect but before local acknowledgement, waits for the real lease to expire, then resumes from a new process. Acceptance requires one external effect, one durable receipt, a recovered workload and no repeated completed model calls. It does not alter existing application incidents. Preserve a failed report or process log before retrying.

## Consistent backups

Back up **both** the incident database and the simulator receipt database while effects and fault injection are stopped. Restoring only one can leave uncertainty about completed mutations. Preserve the environment secrets separately with appropriate access controls.

```sh
umask 077
mkdir -p backups
docker compose stop api worker
docker compose exec -T postgres pg_dump -U incident -d incident -Fc > backups/incidents.dump
docker compose exec -T simulator python -c 'import sqlite3; source=sqlite3.connect("/app/data/simulator.db"); target=sqlite3.connect("/tmp/simulator-backup.db"); source.backup(target); target.close(); source.close()'
docker compose exec -T simulator cat /tmp/simulator-backup.db > backups/simulator.db
docker compose start api worker
```

Test the PostgreSQL dump in a separate database before considering a restore:

```sh
docker compose exec -T postgres createdb -U incident incident_restore
docker compose exec -T postgres pg_restore -U incident -d incident_restore < backups/incidents.dump
```

Compare row counts and document contents across incidents, accounts, sessions and outbox; check SQLite `PRAGMA integrity_check` and compare services/receipts. Do not point the live API at a restored database until its matching simulator snapshot is ready and you have reviewed pending effects. These commands retain the live database. Removing a restore database or backup is an explicit operator action.

## Identity and service-key changes

An administrator can replace a local account's roles from the console, including removing all roles. Existing JWTs are checked against current roles; the console refreshes roles periodically and the API enforces them immediately. Removing an approver's permission blocks newly dispatched effects using that approval. Logout revokes the session ID.

Changing `JWT_SECRET` invalidates signed sessions and requires users to sign in again. Stop API/worker before rotating simulator keys, update both ends, then restart and check readiness. Keep worker and injection keys different. Model workers receive only their own model key. Existing evidence and receipts remain stored through key changes.

## Local scope and capacity

PostgreSQL writes are serialized through an advisory lock, including the bounded effect call. This reference design favors a clear authorization boundary over throughput. The local model handles one bounded request at a time. There is no measured production capacity claim. The simulator has six fixed fault families and handlers; adding a real adapter requires its own receipt, permission, cancellation and recovery verification.

Use `docker compose stop` to preserve containers and volumes. `docker compose down` removes the project's containers/network while retaining named volumes by default. Removing volumes discards the local incident and simulator histories; preserve backups before choosing that action.
