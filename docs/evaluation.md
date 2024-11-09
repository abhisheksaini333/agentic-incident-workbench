# Choosing a diagnosis approach

**Runbook rules are the operational default.** The controlled comparison recovered all 11 held-out cases with rules, 1 with a single model reviewer and 4 with the specialist graph. The extra model coordination improves this weak model baseline but does not justify replacing the rules path. Model approaches remain an opt-in experiment for investigating orchestration and abstention.

| Approach | Recovered / cases | Unnecessary actions | Effects | Model calls | Input / output tokens | Median / p95 seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rules | 11 / 11 | 0 | 15 | 0 | 0 / 0 | 0.097 / 0.323 |
| Single model | 1 / 11 | 0 | 2 | 10 | 630 / 42 | 0.075 / 0.630 |
| Specialist graph | 4 / 11 | 0 | 6 | 30 | 1290 / 131 | 0.267 / 0.775 |

The single model's sole complete recovery was the healthy case, which correctly needed no model call or effect. Some failed compound incidents received a supported partial remediation and then escalated because verification still failed. Fast abstention is not successful recovery. No unnecessary actions means no accepted simulator action changed an unrelated fault; it is not a claim that the model never proposed incorrect diagnoses. Unsupported labels were rejected before planning.

## Method

`fixtures/evaluation.json` freezes six calibration cases and eleven held-out cases. The held-out set includes all six fault families, three two-fault cases, one three-fault case and a healthy case. Calibration uses one log wording; held-out cases use alternate wording and compound combinations. Fault families and numerical runbooks are shared, so this is a bounded simulator test, not an out-of-domain benchmark.

Two prompt formats were tested only on calibration cases. Numeric JSON prompting was ineffective for this small checkpoint; bounded log classification produced some useful labels and was selected before held-out execution. All modes receive the same service state and share deterministic evidence checks, bounded actions, approval rules, receipt handling and workload verification. Mode order rotates by case to reduce consistent ordering bias. An explicit benchmark reviewer approves supported proposed plans in the disposable evaluation tenant; the application does not automatically approve user incidents.

Measurements use real PostgreSQL, the HTTP simulator and original `google/flan-t5-small` weights with deterministic decoding, two CPU threads, Torch 1.13.1 and Transformers 4.25.1. Hardware: Apple M3 Pro, 11 logical CPUs, 18 GiB memory, macOS ARM64. Timings cover diagnosis, benchmark approval and execution after setup. Model weights were already loaded. Each case has one measured run; these figures establish behavior, not statistical significance or production capacity. Container emulation is checked separately and is not mixed into these timings.

[Machine-readable results](evaluation-results.json) include every case, token counts, the corpus hash and measured source revision. Raw incident traces contain generated text, evidence digests, rejected labels and effect receipts.

## Reproduce

Start the optional model profile as described in the README, then:

```sh
mkdir -p artifacts
docker compose exec -T api python -m incident.evaluation --output /tmp/comparison.json
docker compose cp api:/tmp/comparison.json artifacts/comparison.json
```

Each run creates a unique PostgreSQL schema and unique simulator tenants. Existing application incidents are retained. Review the report's `database_schema` before explicitly removing a disposable run; do not remove the application `public` schema. New models or prompts must be selected on calibration data and measured on a newly frozen held-out set.
