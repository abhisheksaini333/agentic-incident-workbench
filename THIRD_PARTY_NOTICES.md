# Runtime and model notices

This project uses original dependencies and model artifacts. Installed packages retain their upstream license files. The local simulator, incident workflows, evidence guards and console are application code; using a dependency does not imply affiliation with its authors.

| Component | Pinned version / artifact | Upstream license and source |
| --- | --- | --- |
| LangGraph | 0.0.21 | MIT; [source tag](https://github.com/langchain-ai/langgraph/tree/0.0.21) |
| FastAPI | 0.104.1 | MIT; [source](https://github.com/tiangolo/fastapi) |
| React / React DOM | 18.2.0 | MIT; [source](https://github.com/facebook/react) |
| PostgreSQL | 16.1 | PostgreSQL License; [release notes](https://www.postgresql.org/docs/release/16.1/) |
| PyTorch | 1.13.1, original CPU wheel on Linux | BSD-style; [source](https://github.com/pytorch/pytorch/tree/v1.13.1) |
| Transformers | 4.25.1 | Apache-2.0; [source](https://github.com/huggingface/transformers/tree/v4.25.1) |
| FLAN-T5-small | revision `371f99f1df1429771f01227c93bd662f5eec2480` | Apache-2.0; [model card](https://huggingface.co/google/flan-t5-small/tree/371f99f1df1429771f01227c93bd662f5eec2480) |

`requirements.txt`, `model/requirements.txt` and `frontend/package-lock.json` fix complete application dependency versions for the tested profiles. `docs/runtime-provenance.json` records official package release metadata and immutable CI action references. Native artifact hashes in that record describe the selected native verification profile; platform-specific wheels and Docker base-image digests can differ. Model files have a separate immutable SHA256 manifest. The original Linux CPU torch wheel retains its local version suffix `+cpu`.

The application runtime is the LangGraph 0.0.21 generation and uses its original graph interfaces. The original small checkpoint has limited incident-classification accuracy; the measured comparison is published in `docs/evaluation.md`. Changes to runtime versions, tokenizers or weights should be accompanied by a new measured report.
