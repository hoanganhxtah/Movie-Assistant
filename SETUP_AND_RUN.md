# Setup and Run Guide

This project contains two services:

- `agent-service`: FastAPI backend on port `8001`
- `ui`: Streamlit interface on port `8501`

The commands below must be run from the repository root.

## Prerequisites

Choose one of these options:

- Docker Desktop with Docker Compose, or
- Python 3.11 or newer

The MovieLens dataset must be available at
`data/ml-latest-small-filtered`. It is already included in the submitted
repository.

## Environment configuration

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux, use:

```bash
cp .env.example .env
```

The default configuration uses Groq. Add a key to `.env`:

```dotenv
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=your_key_here
```

`LLM_API_KEY` may be used instead of the provider-specific key. Other
supported providers are `openai`, `openai-compatible`, `gemini`, `anthropic`,
and `bedrock`; update `LLM_PROVIDER`, `LLM_MODEL`, and the corresponding key in
`.env` when switching providers. Do not commit the populated `.env` file.

## Option 1: Run with Docker (recommended)

Build and start both services:

```powershell
docker compose up --build
```

Open:

- UI: <http://localhost:8501>
- Backend health check: <http://localhost:8001/health>
- API documentation: <http://localhost:8001/api/v1/docs>

Stop the application with `Ctrl+C`, then remove the containers:

```powershell
docker compose down
```

## Option 2: Run locally

Create and activate a virtual environment on Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install the backend and UI dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r agent_service/requirements.txt -r ui/requirements.txt
```

Verify the dataset:

```powershell
python scripts/verify_dataset.py
```

Start the backend in the first terminal:

```powershell
python -m agent_service.main_dev
```

Open a second terminal, activate the same virtual environment, and start the
UI:

```powershell
python -m streamlit run ui/app.py
```

Then visit <http://localhost:8501>.

## Using the application

1. Enter a MovieLens `userId`, for example `1`, and select **Log in**.
2. Ask for a recommendation or search for a movie in the chat box.
3. Use **New conversation** to clear the current conversation while keeping the
   same user.
4. Use **Logout** to select a different `userId`.

The selected `userId` is fixed for the current login session so that one
conversation cannot accidentally mix the profiles of different users.

## Tests and evaluation

Install pytest if it is not already available:

```powershell
python -m pip install pytest
```

Run the automated tests:

```powershell
python -m pytest tests -q
```

Run the offline recommendation evaluation for up to 100 users:

```powershell
python -m scripts.evaluate --max-users 100
```

The evaluation output is written to `evaluation/results.json`.

## Troubleshooting

- **Backend unavailable in the UI:** confirm that
  <http://localhost:8001/health> returns `{"status":"ok"}`.
- **API key error:** check that the selected provider has either
  `LLM_API_KEY` or its provider-specific key set in `.env`.
- **Dataset not found:** run `python scripts/verify_dataset.py` and confirm that
  `DATA_DIR=data/ml-latest-small-filtered` is present in `.env`.
- **PowerShell blocks virtual-environment activation:** run
  `Set-ExecutionPolicy -Scope Process Bypass`, then activate `.venv` again.
- **Port already in use:** stop the process using port `8001` or `8501`, or
  change the relevant port configuration before restarting the services.
