# Cappuccino

Cappuccino aims to be a general‑purpose AI assistant. The project follows the design guidelines in `AGENTS.md` which emphasize high quality code, modular architecture and robust asynchronous tooling. Tools are intended to run concurrently and the API is exposed through FastAPI for easy humanoid integration.

## Setup
1. Create a Python environment (Python 3.12 or later recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and add your API keys.

## Running the server
Start the FastAPI server with:
```bash
uvicorn api:app --reload
```
This runs the main API defined in `api.py`.

### Running API and Discord bot together
To launch both the API server and the Discord bot simultaneously use
`run_server_bot.py`:

```bash
python run_server_bot.py
```

## API usage
`api.py` exposes REST endpoints and WebSockets. To stream agent thoughts and tool
outputs connect to `/agent/events` and send a JSON object with a `query` field.

```python
from websockets.sync.client import connect
import json

with connect("ws://localhost:8000/agent/events") as ws:
    ws.send(json.dumps({"query": "hello"}))
    print(ws.recv())  # first chunk
```

## Testing
Install the project dependencies and run the unit tests with `pytest`:
```bash
pip install -r requirements.txt
pytest -q
```

The integration script `test_integration.py` exercises Docker and Discord
features. It requires a running Docker daemon and a valid `DISCORD_BOT_TOKEN`
environment variable in order to fully execute. If these requirements are
missing, the integration tests are skipped while the other unit tests still run.

## Design philosophy
Key principles from `AGENTS.md`:
- Produce readable and maintainable Python code with proper error handling and testing【F:AGENTS.md†L80-L95】.
- Expose the agent core through a high-performance asynchronous API using FastAPI and WebSockets【F:AGENTS.md†L1760-L1776】.
- Ensure state management, sandbox awareness and parallel execution where appropriate【F:AGENTS.md†L1840-L1848】.
## Next steps
Additional development plans in Japanese can be found in [docs/NEXT_STEPS_JA.md](docs/NEXT_STEPS_JA.md).


## Chat CLI
Run a simple interactive chat loop from the terminal:
```bash
python chat_cli.py
```
Exit the session with `exit` or `quit`.

## API CLI
Use `agent_cli.py` to send a prompt directly to the OpenAI API and save any
generated images locally:

```bash
python agent_cli.py "青い空と白い雲の風景画"
```
