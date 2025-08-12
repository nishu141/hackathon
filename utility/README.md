# Telecom API LangGraph Orchestrator

End-to-end demo that turns a user story into a Cucumber/Behave BDD suite, generates feature and steps, executes against public demo APIs (`reqres.in`), performs basic diagnostics/self-healing, and outputs a report.

## 🚀 Quick Start (Automatic Dependency Management)

### Option 1: Windows Batch File (Easiest)
Simply double-click `run_telecom_ai.bat` - it will automatically:
- Check Python installation
- Install missing dependencies
- Launch the application

### Option 2: Python Launcher
```bash
python run_telecom_ai.py
```

### Option 3: Manual Dependency Installation
```bash
python dependency_installer.py
python telecom_ai_langgraph.py
```

## 🔧 Manual Setup (Traditional)

1. Create a Python 3.8+ venv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the workflow:

```bash
python telecom_ai_langgraph.py "As a telecom user, I want to verify mobile data usage API"
```

## 📁 Project Structure

- `telecom_ai_langgraph.py` — Main entry point (remains in project root)
- `utility/` — Contains all supporting modules and files:
    - `agents/` — All agent modules
    - `telecom_test_orchestrator.py` — Orchestrator logic
    - `state.py` — State management
    - `logging_config.py` — Logging setup
    - `dependency_installer.py` — Dependency management
    - `test_framework_creation.py` — (if used)
    - `README.md` — Project documentation
    - `requirements.txt` — Python dependencies
    - `run_telecom_ai.bat` — Windows launcher
    - `run_telecom_ai.py` — Python launcher
    - `telecom_config.json` — API/configuration file

## 🎯 Features

- **Automatic Dependency Management**: No more "ModuleNotFoundError" issues!
- **Self-Healing**: Automatically fixes syntax and runtime errors
- **BDD Generation**: Converts user stories to Cucumber/Behave features
- **API Testing**: Tests against configurable APIs
- **Smart Diagnostics**: AI-powered error analysis and resolution

## 🔍 Configuration

Artifacts will be created under `./telecom_api_bdd` by default:
- `features/*.feature` - BDD feature files
- `step_definitions/*.py` - Step definitions
- `support/environment.py` - Test environment setup
- `reports/*` - Test execution reports

To customize the API under test, edit `telecom_config.json` or pass `--config` to the CLI.

## 🛠️ Troubleshooting

### Common Issues:

1. **"ModuleNotFoundError: No module named 'langgraph'"**
   - Solution: Run `python dependency_installer.py` or double-click `run_telecom_ai.bat`

2. **Python version issues**
   - Required: Python 3.8 or higher
   - Check with: `python --version`

3. **Permission errors**
   - Run as administrator or use virtual environment

### Getting Help:
- Check the console output for detailed error messages
- Ensure you're in the project root directory
- Verify Python is in your system PATH

## 🎉 Success!

When everything works, you'll see:
```
✅ Dependencies installed successfully!
🚀 Launching Telecom AI LangGraph...
```

The application will automatically generate BDD tests, execute them, and provide detailed reports!

## HTML Report Generation

After each test run, an HTML report will be generated automatically using the Behave HTML Formatter. You can find the report at `./telecom_api_bdd/report.html` (or your specified output directory).

## Passing User Story

You can pass a custom user story to be used for feature generation by adding the `--user-story` argument to your run command. For example:

```
python telecom_ai_langgraph.py --user-story "As a telecom admin, I want to verify the billing API."
```

Or using the launcher script:

```
python run_telecom_ai.py --user-story "As a telecom admin, I want to verify the billing API."
```

The user story will be included in the generated feature files and reports.