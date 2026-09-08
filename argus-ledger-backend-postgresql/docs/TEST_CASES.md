# ARGUS Test Cases

Backend coverage. Run: `.venv\Scripts\python -m pytest` (needs the `argus_test`
database — `scripts/setup_db.ps1`).

| #  | Case                | Covered by (backend)                                              | Notes |
| -- | ------------------- | ---------------------------------------------------------------- | ----- |
| 1  | Normal decision     | `test_decisions.py::test_normal_decision_roundtrip`             | create → nested read-back |
| 2  | Missing evidence    | `test_decisions.py::test_missing_evidence_is_allowed`          | evidence optional |
| 3  | Conflicting evidence| _AI concern_ — backend stores whatever evidence it is given    | Member 3 |
| 4  | Low confidence      | `test_decisions.py::test_low_confidence_auto_flags_human_review` | forces `human_review_required` |
| 5  | Model failure       | `test_generate.py::test_model_failure_returns_502`             | provider raises → 502, nothing persisted |
| 6  | Human override      | `test_review.py::test_human_override_updates_decision_and_ledger` | + `HUMAN_REVIEW` audit event |
| 7  | Invalid input       | `test_decisions.py::test_invalid_input_rejected_with_422`      | bad confidence / empty fields |
| 8  | Missing document    | `test_decisions.py::test_unknown_decision_returns_404`         | unknown id → 404 |
| 9  | Database failure    | `app/main.py` `SQLAlchemyError` handler → 503                  | manual: stop Postgres, hit `/health` |
| 10 | Duplicate decision  | allowed by design — each POST is a new ledger row              | dedupe is an AI/integration concern |
| 11 | Model version change| `test_contract.py::test_ai_contract` (+ `model_version` stored) | version travels with every row |
| 12 | Replay comparison   | `test_contract.py::test_stub_is_deterministic_for_replay`      | stub output is a pure fn of input |

Extra backend tests: health + CORS preflight (`test_health.py`), dashboard
aggregates (`test_dashboard.py`), list + pagination (`test_decisions.py`),
generate → list/dashboard visibility (`test_generate.py`).

For the hackathon: the normal path (1) is green end-to-end; failure cases
(4, 5, 7, 8) are covered. Cases 3 and 10 are explicitly AI/integration scope.
