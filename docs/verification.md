# Verification scope

The product has been exercised with real PostgreSQL, separate API/worker/simulator processes, the original FLAN-T5 checkpoint and a real browser. Deterministic model fixtures used by unit tests are separate from actual inference evidence.

| Boundary | Observed check |
| --- | --- |
| Browser workflow | Operator opens an incident; another account requests changes; operator saves plan version 2; reviewer approves its exact digest; actual worker recovers the service and records one receipt |
| Model path | Three real specialist calls appear in the timeline with accepted/rejected output, snapshot binding and token usage; healthy work avoids unnecessary model calls |
| Access | Viewer has no creation control; a second tenant cannot see the incident; same signed session loses write authority after role change and all access after account revocation |
| Persistence | Six concurrent PostgreSQL connections initialize safely; stale leases and optimistic revisions cannot publish over a new owner |
| Process loss | One process receives SIGKILL while awaiting approval; another exits after the remote effect; a fresh process waits for the real lease expiry and resolves with one external effect and one receipt |
| Outages | Receipt transport errors retain pending uncertainty, use bounded retry and allow an unrelated incident to advance |
| Comparison | Thirty-three held-out runs compare identical cases across rules, a single model and the specialist graph; forty real model calls are recorded |
| Containers | API, worker, PostgreSQL, simulator and the optional original model become healthy; the model browser journey completes across the packaged stack |
| Backup | Quiesced PostgreSQL dump restored into a separate database with matching table counts/content digests; paired simulator backup passes SQLite integrity checking |

The screenshot in the README comes from the packaged graph workflow with local demo accounts. Desktop and mobile layouts were inspected. Browser polling keeps queue status consistent with a newer detail snapshot.

Measured model quality is limited and explicitly reported in [evaluation.md](evaluation.md). Tests and local container proof do not establish production deployment, real infrastructure remediation, throughput capacity or a successful hosted CI run. CI configuration is included; its hosted status must be read from an actual provider run.

Repeat the behavioral suite, browser harness, comparison and process-crash probe after changing model identities, action handlers, authorization or receipt semantics. Use the coordinated backup procedure before resetting local volumes.
