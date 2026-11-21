# AgriTwin source audit and rebuild notes

## Executive result

The supplied archive contained a substantial Python agent codebase, but it was not a single launch-ready multi-agent web application. The core engines existed, while the Coordinator's instructions and runtime lifecycle prevented several registered specialists from being used reliably. A separate FastAPI/PostgreSQL/Redis authentication scaffold was present but did not call the AgriTwin engines.

This rebuilt package preserves the working AgriTwin agent modules and exposes them through one local FastAPI application and browser UI. It does not claim that unfinished agent folders are fully implemented.

## Faults found and actions taken

| Finding in supplied bundle | Why it mattered | Action in this release |
|---|---|---|
| A Groq-looking credential was embedded in `.env.example` | A credential in a distributable example file must be considered exposed | Replaced it with a blank `GROQ_API_KEY`; documented key rotation |
| `runtime/llm.py` imported the OpenAI SDK and created a client at module import | Test collection and app startup failed when the SDK was absent or credentials were missing | Made the provider client lazy; missing SDK/key now produces an actionable error at request time |
| Coordinator prompt allowed only `run_harvest` and `run_climate` | Market and Logistics were registered but explicitly forbidden by the Coordinator prompt | Rebuilt the Coordinator prompt using all four registered specialist tools |
| `CoordinatorWorkflow.handle_tool_result` was defined twice | The later method replaced the earlier one; specialist outputs were not retained and the method called methods that did not exist on CoordinatorWorkflow | Consolidated into one handler that stores outputs and records specialist participation |
| Coordinator returned immediately after some Harvest/Climate text results | Multi-domain questions could stop after the first specialist instead of asking another relevant specialist | Removed the early-return behavior so the Coordinator can inspect results, call another specialist and synthesize an answer |
| Each agent module exposed one process-global engine | Multiple browser users could otherwise share the same conversation memory | Added per-session engine factories, bounded session caching and per-session locking |
| Market CSV path depended on the current working directory | Running the service from another folder could make the Market Agent fail to locate its data | Resolved the dataset path relative to the project package |
| Market tool schema required transport/storage/profit inputs for any forecast | A simple market-price question could be blocked by optional economics fields | Marked only commodity and market as required; economics parameters remain optional |
| Current-price requests followed the full market-economics path | Users asking only for a mandi rate were asked for unrelated profit and storage inputs | Added a price-only path, including side-by-side lookups for multiple named mandis |
| Market parser did not preserve both requested mandi names or common plural crop names | Queries such as `onions in Nashik or Lasangaon mandi` were not parsed reliably | Added plural commodity aliases and ordered multi-market extraction; Lasangaon aliases to Lasalgaon for this mandi workflow |
| Market data was presented without a sufficiently explicit freshness signal | An old observation could be mistaken for today's live mandi price | Price results now expose observation date, data age, freshness status and a warning when older than three days |
| Forecast could be requested from a single market observation date | A future price estimate would be unsupported by the available history | Require at least 30 distinct daily observations; otherwise return a clear data insufficiency error |
| Logistics geocoder could resolve `Lasangaon` to a distant place in Madhya Pradesh from a Nashik origin | A valid-looking but wrong route and cost could be produced | Added a Nashik-region alias-resolution retry for Lasalgaon and use resolved coordinates in the Google Maps URL; the result flags when a destination was interpreted |
| Map follow-up was treated as a brand-new logistics task | `open the map and show me route` lost origin/destination and requested all details again | Cache the latest logistics result per session and serve a map-link response on route/map follow-ups |
| Harvest evaluator did not recognize normalized `day_after_tomorrow` | The requested date could be ignored and a different best day selected | Normalize underscores/spaces and evaluate the explicitly requested date only |
| Harvest response described minimum and maximum temperatures as both being inside the ideal range | This overstated the weather fit when min/max crossed the configured range | Added day-level min/max/average detail, clarified the mean-based scoring criterion and added field-maturity/condition caveats |
| Dependency lock file was UTF-16 and included a large unrelated dependency snapshot | Common `pip` requirements parsing could fail; unrelated infrastructure made setup heavier | Removed the old lock file and supplied a focused `requirements.txt` |
| Database/Redis backend was separate from the agent runtime | A normal agent session was unnecessarily tied to PostgreSQL and Redis configuration | The integrated local launch path uses the agent runtime directly; the disconnected auth scaffold is not required |

## Implemented interface

- Coordinator auto-routing and direct specialist selection.
- Four wired specialist agents: Harvest, Climate, Market and Logistics.
- Browser conversation sessions isolated from other sessions.
- Specialist-activity panel based on actual Coordinator tool results.
- API health and agent metadata endpoints.
- Responsive desktop/mobile dashboard with sample prompts.
- Explicit warning that the included market CSV is historical.
- Price-only market lookups, multi-mandi comparisons and a stale-snapshot warning that includes the source observation date.
- Market forecast guardrail that refuses to forecast when fewer than 30 distinct daily observations exist.
- Multi-mandi planner fan-out for current-price lookups and forecasts, so `Nashik or Lasalgaon` triggers separate tool calls in both browser and terminal paths.
- A current-price clarification explicitly supersedes a pending future date/horizon, preventing the previous forecast date from leaking into the replacement request.
- Session-level route reuse for `show/open the map` follow-ups in both Coordinator and direct Logistics modes, with resolved coordinates and a visible location-interpretation note.
- Requested-day harvest evaluation for natural-language dates normalized by the Understanding Layer, plus accurate min/max/average temperature reporting.

## Actual scope in the supplied source

The supplied code contains working implementations for Coordinator, Harvest, Climate, Market and Logistics. Disease is a package placeholder, Storage has some knowledge/decision utilities but no complete standalone coordinator-wired agent, and no Equity Agent implementation was present. Those are marked as planned/unavailable rather than represented as finished agents.

## Included market data

`data/market/processed/market_records.csv` has 18,367 rows, 248 unique commodity names and 1,906 unique market names. Its latest date is **2026-09-09** and its source field identifies OGD/AGMARKNET. This is a historical snapshot, not current live mandi data. The UI displays its snapshot date and warns about this limitation.

## Validation performed

The current source passes the AgriTwin unit suite: **216 passed, 3 warnings**. The added regression coverage exercises the specific failure modes from the first Windows run: plural crop names, current-price-only tool selection, multi-mandi price lookup, market clarification memory, current-price overrides, multi-mandi planner fan-out, historical snapshot warnings, forecast minimum-history checks, Nashik-to-Lasalgaon alias resolution, map follow-up reuse in Coordinator/direct Logistics modes, and explicit requested-day harvest evaluation.

The user's supplied Windows log demonstrates that their local server started, browser assets loaded, the health endpoint returned 200, and the configured Groq-backed agents called weather, routing, harvest and market tools. That log also showed the specific incorrect destination and follow-up failures addressed in this patch. Unit tests use fake providers for the geocoder and route flow; run an actual route request on the target machine to validate the live geocoding provider's current response. Public weather, geocoding and route providers can rate-limit or become unavailable.

## Remaining production work

This package is ready for local development and demonstration after dependency installation and API-key configuration. Before public deployment, add authentication, HTTPS, rate limiting, durable session storage, observability, provider health probes and an explicit data-refresh pipeline. The bundled market CSV needs daily refresh with trustworthy source timestamps before market forecasts can be enabled. Do not expose the local development server directly to the public internet.
