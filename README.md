# AgriTwin — Connected Agricultural Supply-Chain Platform

AgriTwin connects farmers, drivers / vehicle owners, storage owners, mandi sellers, mandi operators and FPO managers. Each role has a specialised operational dashboard, while the marketplace, stakeholder directory, connection requests and private messaging connect the full network.

The **AI Assistant** replaces the previous form-based AI Agent Studio with a chat interface powered by the multi-agent runtime supplied in `agritwin_ai/`. It is available to every authenticated stakeholder. The authenticated stakeholder role is injected into each isolated agent session so the same specialist can tailor its priorities for a farmer, driver, warehouse operator, trader, mandi operator or FPO manager. Stakeholder role does not restrict access to any active agent.

## Multi-agent system included

The uploaded multi-agent source currently contains these working chat agents:

| Agent | Chat status | Main responsibility |
|---|---|---|
| Coordinator | Active | Understands a request, selects relevant specialists and synthesizes their results |
| Harvest | Active | Crop knowledge and harvest decisions using weather and crop information |
| Climate | Active | Current weather and multi-day Open-Meteo forecast |
| Market | Active | OGD / AGMARKNET daily observations, nearby mandi discovery, history and labelled price outlooks |
| Logistics | Active | Geocoding, road routing, vehicle suitability, cost estimates and logistics risk |

**Source limitation:** The supplied runtime does not contain six fully implemented conversational specialists. Its README says Storage has some utilities but is not connected as a standalone Coordinator agent; Disease is a placeholder; Equity is not present. Those are shown as in development in the chat sidebar. Existing stakeholder dashboard and platform-level storage / net-realisation functions are retained separately.

All active agents are selectable by all stakeholder roles. Coordinator mode is the recommended default for requests that span more than one domain.

## Main platform features

- JWT authentication and six stakeholder roles.
- Role-specific dashboards and operational tools.
- Crop, transport, storage, buying and service marketplace listings.
- Stakeholder directory, compatibility scores and connection requests.
- Accepted-connection private messaging.
- Farmer crop plots, indicative harvest windows and weather alerts.
- Driver route planning, nearby load discovery and capacity checks.
- Storage intake / dispatch, trader sourcing, mandi arrival workflows and FPO aggregation tools.
- Authenticated AI chat with Coordinator and direct specialist modes.
- Session-isolated agent memory, scoped to the authenticated account and role.

## Requirements

- Python 3.11 or newer (Python 3.13 is supported by the declared dependency range).
- PostgreSQL.
- A Groq API key for conversational reasoning.
- Internet access for live weather, geocoding and routing providers.

Redis is optional for the main platform's current local development workflow; a health check may report `degraded` when Redis is not running.

## Windows setup

1. Extract the ZIP into a new project folder. Do not extract over an existing project or overwrite its `.env`.
2. Copy your existing private `.env` from the current AgriTwin project into the new project root, or create it from `.env.example`.
3. Generate a new `SECRET_KEY` and insert your PostgreSQL details. Add a newly generated `GROQ_API_KEY`. Add `DATA_GOV_API_KEY` to enable live daily OGD / AGMARKNET retrieval; set `GOOGLE_MAPS_API_KEY` for the optional Google routing provider.
4. Create and activate the virtual environment and install dependencies:

   ```powershell
   py -3 -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

5. Apply any new database migrations (existing accounts and marketplace data are preserved):

   ```powershell
   alembic upgrade head
   ```

6. Optionally create fictional development data if you have not already seeded it:

   ```powershell
   python -m backend.scripts.seed_demo --confirm-demo-data
   ```

7. Start the integrated platform (not the standalone AI web app):

   ```powershell
   uvicorn backend.app.main:app --reload --port 8000
   ```

8. Open `http://127.0.0.1:8000/` and sign in. Open **AI Assistant** from the sidebar.

## Environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing secret for platform authentication |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL connection |
| `GROQ_API_KEY` | Required for LLM reasoning and Coordinator synthesis |
| `GROQ_MODEL` | Model name; defaults to `openai/gpt-oss-20b` |
| `GROQ_BASE_URL` | Groq's OpenAI-compatible endpoint |
| `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES` | Provider timeout and retry settings |
| `DATA_GOV_API_KEY` | Live daily OGD / AGMARKNET retrieval used by the uploaded Market Agent |
| `DATA_GOV_IN_API_KEY`, `AGMARKNET_RESOURCE_ID` | Existing platform Market Agent integration |
| `GOOGLE_MAPS_API_KEY` | Optional Google Maps / Routes integration; OSRM is the fallback |
| `LOGISTICS_FUEL_PRICE_INR_PER_LITER` | Logistics cost-model assumption |
| `LOGISTICS_DRIVER_COST_INR_PER_HOUR` | Logistics cost-model assumption |
| `LOGISTICS_HANDLING_COST_INR_PER_TON` | Logistics cost-model assumption |
| `LOGISTICS_ESTIMATED_TOLLS_INR` | Logistics cost-model assumption |

Never commit `.env`, expose API keys in browser JavaScript, or paste provider credentials into chat. `.env.example` contains placeholders only.

## AI chat API

All endpoints require the user's bearer token.

- `GET /ai/health` — safe provider configuration status; never returns keys.
- `GET /ai/agents` — active and planned agent catalogue for the authenticated stakeholder.
- `POST /ai/chat` — runs Coordinator or a selected specialist.

Example request body:

```json
{
  "message": "Should I harvest onions in Nashik tomorrow?",
  "session_id": "farm-session-0001",
  "agent": "coordinator"
}
```

Valid `agent` values: `coordinator`, `harvest`, `climate`, `market`, `logistics`. Session memory is held in a bounded in-memory session manager and scoped by the authenticated user ID, stakeholder role and browser session identifier. Restarting the server clears conversational memory.

## Run tests

```powershell
python -m pytest backend/tests agritwin_ai/tests -q
```

Some AI tests mock external services. Passing local tests cannot guarantee that Groq quotas, OGD publication, Open-Meteo, Nominatim, OSRM or Google APIs are available at runtime.

## Data quality and limitations

- OGD / AGMARKNET is a daily official observation feed, not second-by-second exchange data. The agent labels observation dates and stale quotes.
- The bundled market CSV is a historical snapshot, not a live quote. Use the observation date reported by the API.
- OSRM route duration is based on the road network and is not live traffic. Google traffic-aware routing is available only when configured and supported by the route request.
- Logistics cost results are model estimates, not carrier quotations.
- Harvest recommendations are decision support and require crop-stage and field verification.
- The AI chat is informational. Confirm high-impact crop, market, storage and transport decisions with current local data and qualified operators.

## Project structure

```text
AgriTwin-main/
  backend/               FastAPI authentication, marketplace and stakeholder dashboards
  frontend/              Existing AgriTwin web UI with integrated AI chat
  agritwin_ai/            Uploaded multi-agent system and isolated session runtime
  data/market/            Historical OGD / AGMARKNET datasets and cached observations
  docs/ai-system/         Agent architecture, market guide and source audit
  .env.example            Secret-free environment template
  requirements.txt        Combined platform and AI dependencies
```
