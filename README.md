# Telecom API LangGraph Orchestrator

End-to-end demo that turns a user story into a Cucumber/Behave BDD suite, generates feature and steps, executes against public demo APIs (`reqres.in`), performs basic diagnostics/self-healing, and outputs a report.

## Quick start

1. Create a Python 3.10+ venv and install deps:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the workflow:

```
python telecom_ai_langgraph.py "As a telecom user, I want to verify mobile data usage API"
```

Artifacts will be created under `/workspace/telecom_api_bdd` by default:
- `features/*.feature`
- `step_definitions/*.py`
- `support/environment.py`
- `reports/*`

To customize the API under test, edit `telecom_config.json` or pass `--config` to the CLI.