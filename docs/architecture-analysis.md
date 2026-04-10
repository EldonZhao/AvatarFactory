# AvatarFactory — Architecture Analysis

> **Audience**: Maintainers and contributors  
> **Branch**: `main`  
> **Date**: 2026-04-10

---

## Table of Contents

1. [Codebase Structure](#1-codebase-structure)  
2. [Runtime Architecture & Data Flow](#2-runtime-architecture--data-flow)  
3. [Key Abstractions & Extension Points](#3-key-abstractions--extension-points)  
4. [Cross-Cutting Concerns](#4-cross-cutting-concerns)  
5. [ASCII Architecture Diagram](#5-ascii-architecture-diagram)  
6. [Architectural Risks, Tech Debt & Improvement Proposals](#6-architectural-risks-tech-debt--improvement-proposals)  

---

## 1. Codebase Structure

```
AvatarFactory/
├── avatarfactory/          # Core Python package
│   ├── cli.py              # Typer CLI entrypoint (avatarfactory command)
│   ├── daemon_runner.py    # Process-level service launcher
│   ├── agents/             # All AI agents
│   │   ├── base.py         # BaseAgent ABC
│   │   ├── orchestrator.py # OrchestratorAgent (intent routing)
│   │   ├── proactive_orchestrator.py  # Scheduler-aware orchestrator
│   │   ├── persona.py      # PersonaAgent (CRUD + versioning)
│   │   ├── content.py      # ContentAgent (generation, adaptation)
│   │   ├── review.py       # ReviewAgent (4-dimension scoring)
│   │   ├── simulation.py   # SimulationAgent (engagement prediction)
│   │   ├── discovery.py    # DiscoveryAgent (trend analysis)
│   │   ├── evolution.py    # EvolutionAgent (suggest/apply persona changes)
│   │   └── recommendation.py  # RecommendationAgent
│   ├── connectors/         # Platform connectors (live API I/O)
│   │   ├── base.py         # BasePlatformConnector + ConnectorConfig
│   │   ├── registry.py     # ConnectorRegistry (decorator registration, factory)
│   │   ├── bluesky.py, twitter.py, xiaohongshu.py, wecom.py, ...
│   │   └── bing_search.py, brave_search.py  # Search connectors
│   ├── adapters/           # Platform content-format adapters (offline, no I/O)
│   │   ├── base.py         # BasePlatformAdapter ABC
│   │   └── xiaohongshu.py, twitter.py, bluesky.py, linkedin.py, ...
│   ├── core/               # Shared infrastructure
│   │   ├── knowledges.py   # KnowledgeBase (YAML/JSON file persistence)
│   │   ├── llm_provider.py # BaseLLMProvider + factory (Anthropic, Azure, OpenAI)
│   │   ├── credentials.py  # Fernet-encrypted credential store
│   │   ├── tenant.py       # Multi-tenant models & TenantManager
│   │   ├── tenant_kb.py    # Per-tenant KnowledgeBase scoping
│   │   └── agent_config.py # Per-persona agent behaviour tuning
│   ├── models/
│   │   └── schemas.py      # All Pydantic data models and enums
│   ├── scheduler/
│   │   ├── engine.py       # APScheduler wrapper + ScheduledTask model
│   │   └── tasks.py        # TaskRegistry + individual task implementations
│   ├── service/
│   │   ├── app.py          # FastAPI application factory + all REST routes
│   │   └── cache.py        # Simple in-process cache invalidation
│   ├── middleware/
│   │   └── auth.py         # TenantAuthMiddleware (API-key validation)
│   ├── notifications/
│   │   ├── base.py         # NotificationProvider ABC
│   │   └── webhook.py      # Slack/Discord/Feishu/WeCom webhook notifier
│   ├── video/              # TTS & avatar video generation
│   │   ├── base.py         # VideoProvider ABC
│   │   ├── azure_tts.py, edge_tts.py, azure_avatar.py
│   │   ├── composer.py     # Assembles audio + images into video
│   │   └── generator.py    # Orchestrates the video pipeline
│   ├── dashboard/          # Streamlit dashboard
│   └── templates/          # Jinja2 prompt templates
├── web-admin/              # Astro.js admin SPA (TypeScript)
├── web-journal/            # Astro.js public journal SPA (TypeScript)
├── docs/                   # Markdown documentation + connector guides
├── tests/                  # pytest test suite
│   ├── unit/
│   └── integration/
└── scripts/                # Utility / deployment scripts
```

### Major Entrypoints

| Entrypoint | Module | Description |
|---|---|---|
| `avatarfactory chat` | `cli.py` → `ProactiveOrchestrator` | Interactive REPL (primary UX) |
| `avatarfactory serve` | `daemon_runner.py` → `service/app.py` | FastAPI REST API + scheduler |
| `avatarfactory serve --mode scheduler` | `daemon_runner.py` | Scheduler-only background daemon |
| `avatarfactory <cmd>` | `cli.py` | One-shot CLI commands (create-persona, generate, discover, publish-draft, …) |
| `uvicorn avatarfactory.service.app:app` | `service/app.py` | Direct ASGI entrypoint |

---

## 2. Runtime Architecture & Data Flow

### 2.1 CLI / Interactive Chat Path

```
User types a message
    │
    ▼
cli.py  (Typer / Rich)
    │  wraps input as AgentMessage {receiver="orchestrator", task_type=CHAT}
    ▼
ProactiveOrchestrator.process()
    │
    ├─► _understand_intent()  ──── LLM call to classify intent ────►
    │         returns Intent {intent_type, parameters, confidence}
    │
    ├─► route to handler (e.g. _handle_generate_content)
    │         │
    │         ├─► PersonaAgent.process()      ──► KnowledgeBase (load/save YAML)
    │         ├─► DiscoveryAgent.process()    ──► ConnectorRegistry ──► Platform APIs
    │         ├─► ContentAgent.process()      ──► LLM call (generate text/variants)
    │         ├─► ReviewAgent.process()       ──► LLM call (4-dimension scoring)
    │         └─► SimulationAgent.process()   ──► LLM call (engagement prediction)
    │
    └─► aggregate results, format Rich output, present to user
            │
            ▼  (human confirms → publish-draft command or HITL approval)
        ConnectorRegistry.create_connector(platform)
            ▼
        Platform Connector (e.g. BlueskyConnector.publish())
            ▼
        PublishResult {success, post_url}
```

### 2.2 FastAPI / REST Path

```
HTTP request  (POST /chat  or  POST /personas/{id}/content  etc.)
    │
    ▼
FastAPI app (service/app.py)
    │  Optional: TenantAuthMiddleware validates X-API-Key header
    │  injects TenantContext into request.state
    │
    ▼
Route handler (async def)
    │  calls get_orchestrator() → global ProactiveOrchestrator singleton
    ▼
Same agent pipeline as CLI path (see §2.1)
    │
    ▼
JSON response   (or BackgroundTasks for async operations)
    │
    ▼ (side-effect)
WebhookNotifier.send()  ──► Slack / WeCom / Discord / Feishu
```

### 2.3 Scheduler / Proactive Path

```
APScheduler (SchedulerEngine) fires cron trigger
    │
    ▼
tasks.py  TaskRegistry.run(task_type)
    │  e.g. run_discovery_task(), run_content_generation_task()
    │
    ▼
ProactiveOrchestrator (shared singleton with FastAPI process)
    │  calls same agent methods as interactive path
    ▼
Results stored in KnowledgeBase  +  WebhookNotifier sends summary
```

### 2.4 Persistence Layer (KnowledgeBase)

All runtime state is stored as files inside `./knowledges/` (configurable via `AVATARFACTORY_KB_PATH`):

```
knowledges/
├── personas/
│   └── {persona_id}/
│       ├── config.yaml          # Current persona definition (Pydantic model dump)
│       ├── history.json         # PersonaVersion records
│       ├── versions/            # One YAML per version tag
│       ├── content/
│       │   ├── draft/           # {datetime}_{content_id}.json
│       │   └── published/
│       └── discovery/           # {datetime}_{platform}.json
├── experiments/
│   └── {experiment_id}/
│       └── experiment.json
├── platform_rules/
│   └── {platform}/rules.yaml
├── evolution/
│   └── {persona_id}/suggestions.json
└── scheduler/
    └── state.json               # APScheduler job states
```

**Read path**: `KnowledgeBase.load_*()` → `yaml.safe_load` / `json.load` → Pydantic model  
**Write path**: Pydantic model `.model_dump(mode='json')` → `yaml.dump` / `json.dump`

There is **no database** in the current implementation; all data is flat files.

### 2.5 Connector vs. Adapter Distinction

| Layer | Purpose | I/O | Examples |
|---|---|---|---|
| **Connector** (`connectors/`) | Live network I/O to platform APIs | ✅ Network calls | BlueskyConnector, TwitterConnector, XiaohongshuConnector |
| **Adapter** (`adapters/`) | Offline format validation & transformation | ❌ No network | XiaohongshuAdapter, TwitterAdapter, LinkedInAdapter |

Connectors are used at publish / fetch time; adapters are used during content generation to enforce platform guidelines.

---

## 3. Key Abstractions & Extension Points

### 3.1 `BaseAgent` (agents/base.py)

```
BaseAgent (ABC)
    agent_id: str
    kb: KnowledgeBase
    llm_provider: BaseLLMProvider

    + process(message: AgentMessage) → Any   [abstract]
    + call_llm(prompt, system, ...)          [LLM convenience]
    + validate_message(message)              [routing guard]
    + get_persona_context(persona_id)        [KB accessor]
    + log(level, message)                   [structured logging]
```

**To add a new agent**: subclass `BaseAgent`, implement `process()`, register in the orchestrator's handler map.

### 3.2 `ConnectorRegistry` (connectors/registry.py)

```
ConnectorRegistry (class-level dict)
    _connectors: Dict[str, Type[BasePlatformConnector]]
    _instances:  Dict[str, BasePlatformConnector]

    + register_decorator(platform)  → @decorator
    + create_connector(platform, config, use_cache)
    + list_platforms()
    + is_registered(platform)
```

**To add a platform connector**: subclass `BasePlatformConnector`, decorate with `@ConnectorRegistry.register_decorator("yourplatform")`.

### 3.3 `BasePlatformAdapter` (adapters/base.py)

```
BasePlatformAdapter (ABC)
    platform: PlatformType

    + get_content_guidelines() → dict  [abstract]
    + validate_content(content) → dict [abstract]
    + format_for_export(content) → dict[abstract]
    + get_best_posting_times()
    + get_hashtag_strategy()
```

**To add an adapter**: subclass `BasePlatformAdapter`, implement the three abstract methods, use it in `ContentAgent.adapt_to_platform()`.

### 3.4 `BaseLLMProvider` + `LLMProviderFactory` (core/llm_provider.py)

```
BaseLLMProvider (ABC)
    model: str
    + generate(prompt, system, temperature, max_tokens, images) → str  [abstract]
    + validate_config() → bool                                          [abstract]

LLMProviderFactory
    _providers: {"anthropic": AnthropicProvider, "azure_openai": ..., "openai": ...}
    + create(provider_type, model, **kwargs)
    + from_env()
    + create_for_tenant(tenant_id, kb_path)   # multi-tenancy path
```

**To add a new LLM provider**: subclass `BaseLLMProvider`, add to `LLMProviderFactory._providers`.

### 3.5 `NotificationProvider` (notifications/base.py)

Supports pluggable webhook notification backends (Slack, Discord, Feishu, WeCom, generic). Extend by subclassing `NotificationProvider` and implementing `send()`.

### 3.6 `VideoProvider` (video/base.py)

TTS / avatar video pipeline is abstracted behind a `VideoProvider` ABC with implementations for Azure TTS, Edge TTS, and Azure Avatar.

---

## 4. Cross-Cutting Concerns

### 4.1 Configuration

All configuration is environment-variable driven (see `.env.example`):

| Category | Key env vars |
|---|---|
| LLM provider | `AVATARFACTORY_LLM_PROVIDER`, `AVATARFACTORY_MODEL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_*` |
| Storage | `AVATARFACTORY_KB_PATH` |
| Platform connectors | `BLUESKY_USERNAME/PASSWORD`, `TWITTER_API_KEY/SECRET/ACCESS_TOKEN*`, `XIAOHONGSHU_COOKIE/USER_ID` |
| Notifications | `AVATARFACTORY_WEBHOOK_URL`, `AVATARFACTORY_WEBHOOK_FORMAT` |
| Video/TTS | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `AVATARFACTORY_VIDEO_PROVIDER` |
| Multi-tenancy | `AVATARFACTORY_MASTER_KEY`, `AVATARFACTORY_ENABLE_MULTI_TENANCY` |

There is **no centralised config object** — each module reads `os.getenv()` independently. Pydantic `BaseModel` is used for in-memory config objects (e.g. `SchedulerConfig`, `ConnectorConfig`).

### 4.2 Logging / Telemetry

- Standard Python `logging` is used throughout with per-module loggers named `avatarfactory.<module>`.
- `BaseAgent.log(level, message)` is a thin wrapper around the module logger.
- There is **no structured telemetry** (no OpenTelemetry, no distributed tracing, no metrics export) beyond what `uvicorn` emits by default.
- Scheduler task outcomes (last_status, last_error, last_run, next_run) are persisted in `knowledges/scheduler/state.json`.

### 4.3 Error Handling

- Agent methods return domain objects (e.g. `ReviewReport`, `Content`) or raise `ValueError` / `Exception` on bad inputs.
- FastAPI route handlers translate exceptions to HTTP responses via standard `HTTPException`.
- Connector operations return `PublishResult` / `FetchResult` with `success: bool` and `error: str` fields — errors are **not** raised as exceptions, which means callers must check `.success` explicitly.
- No global error handler or circuit-breaker pattern is implemented.

### 4.4 Authentication & Credentials

- **Single-tenant mode**: platform credentials are stored as plain environment variables.
- **Multi-tenant mode**: `CredentialManager` encrypts credentials at rest using Fernet symmetric encryption (AES-128-CBC). The master key is loaded from `AVATARFACTORY_MASTER_KEY` env var or auto-generated and stored in a local key file.
- **API authentication**: `TenantAuthMiddleware` validates `X-API-Key` headers against tenant-scoped keys stored in `KnowledgeBase`; unauthenticated requests are accepted on the "default tenant" path.
- **Admin UI**: `web-admin` uses a cookie-based `admin_token` validated by a `/api/admin/auth/verify` backend endpoint.

### 4.5 Rate Limiting & Retries

- **No application-level rate limiting** is implemented in connectors. The docs explicitly advise implementors to handle this at the application layer.
- The scheduler has a configurable `max_retries` (default 3) and `retry_delay_seconds` (default 60), but individual connector calls have no built-in retry/back-off logic.
- Platform-specific connectors handle some edge cases (e.g. Xiaohongshu cookie expiry), but do so ad hoc.

### 4.6 Human-in-the-Loop (HITL) Review

All **write operations** (publishing content) require explicit human action:

1. Content is generated and saved as a **draft** in KnowledgeBase.
2. ReviewAgent scores it on four dimensions (Persona Consistency, Platform Fit, Compliance, Engagement Potential).
3. The user must explicitly call `avatarfactory publish-draft <content_id>` or approve via the chat interface / REST API.
4. Persona evolution suggestions (from EvolutionAgent) require explicit `review_suggestion` approval before being applied.

This HITL gate is enforced by workflow convention, not by a hard technical lock.

---

## 5. ASCII Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════════╗
║                        INTERACTION LAYER                                 ║
║                                                                          ║
║  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────────┐ ║
║  │  CLI (Typer/    │  │  FastAPI REST   │  │  Streamlit Dashboard /   │ ║
║  │  Rich)          │  │  Service        │  │  Astro Admin / Journal   │ ║
║  │  avatarfactory  │  │  :8000          │  │  Web UIs                 │ ║
║  └────────┬────────┘  └────────┬────────┘  └────────────────┬─────────┘ ║
╚═══════════╪════════════════════╪═══════════════════════════╪════════════╝
            │                   │                           │
            │     AgentMessage  │                           │ HTTP/REST
            ▼                   ▼                           ▼
╔══════════════════════════════════════════════════════════════════════════╗
║                        ORCHESTRATION LAYER                               ║
║                                                                          ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │          ProactiveOrchestrator (extends OrchestratorAgent)       │   ║
║  │                                                                  │   ║
║  │  intent = _understand_intent(user_input) ── LLM call ──►        │   ║
║  │                                                                  │   ║
║  │  route → handler → dispatch AgentMessage to sub-agent           │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                │              │              │              │            ║
╚════════════════╪══════════════╪══════════════╪══════════════╪════════════╝
                 │              │              │              │
        ┌────────▼──┐  ┌────────▼──┐  ┌───────▼──┐  ┌───────▼──────────┐
        │  Persona  │  │  Content  │  │  Review  │  │  Discovery /     │
        │  Agent    │  │  Agent    │  │  Agent   │  │  Simulation /    │
        │           │  │           │  │          │  │  Evolution Agents│
        └────────┬──┘  └────────┬──┘  └───────┬──┘  └───────┬──────────┘
                 │              │              │              │
                 └──────────────┴──────┬───────┴──────────────┘
                                       │  call_llm()
                        ╔══════════════▼════════════════╗
                        ║       LLM PROVIDER LAYER      ║
                        ║  BaseLLMProvider (ABC)        ║
                        ║  ┌────────────┐ ┌──────────┐ ║
                        ║  │Anthropic   │ │ Azure /  │ ║
                        ║  │Claude      │ │ OpenAI   │ ║
                        ║  └────────────┘ └──────────┘ ║
                        ╚═══════════════════════════════╝
                                       │
                 ┌─────────────────────┼──────────────────────┐
                 │  KnowledgeBase      │  ConnectorRegistry   │  Adapters
                 │  (file storage)     │  (platform I/O)      │  (formatting)
╔════════════════▼════════════╗  ╔═════▼═══════════════════╗  ╔▼════════════╗
║  PERSISTENCE LAYER          ║  ║  CONNECTOR LAYER        ║  ║ ADAPTER     ║
║  knowledges/                ║  ║  BasePlatformConnector  ║  ║ LAYER       ║
║  ├─ personas/               ║  ║  ┌──────────┐           ║  ║ Platform-   ║
║  │  └─ {id}/                ║  ║  │ Bluesky  │ AT Proto  ║  ║ specific    ║
║  │     ├─ config.yaml       ║  ║  ├──────────┤           ║  ║ content     ║
║  │     ├─ versions/         ║  ║  │ Twitter  │ API v2    ║  ║ guidelines  ║
║  │     └─ content/          ║  ║  ├──────────┤           ║  ║ & format    ║
║  ├─ experiments/            ║  ║  │ XHS      │ cookie+   ║  ║ validation  ║
║  ├─ platform_rules/         ║  ║  │          │ signing   ║  ║             ║
║  └─ scheduler/state.json    ║  ║  ├──────────┤           ║  ╚════════════╝
╚═════════════════════════════╝  ║  │ WeCom    │ webhook   ║
                                 ║  ├──────────┤           ║
                                 ║  │ Bing /   │ REST API  ║
                                 ║  │ Brave    │ search    ║
                                 ║  └──────────┘           ║
                                 ╚═════════════════════════╝

                     ┌─────────────────────────────────┐
                     │       SCHEDULER LAYER           │
                     │  APScheduler (cron triggers)    │
                     │  TaskRegistry → task functions  │
                     │  → ProactiveOrchestrator        │
                     │  → WebhookNotifier (results)    │
                     └─────────────────────────────────┘

                     ┌─────────────────────────────────┐
                     │  CROSS-CUTTING INFRASTRUCTURE   │
                     │  CredentialManager (Fernet)     │
                     │  TenantManager (multi-tenancy)  │
                     │  TenantAuthMiddleware (API key) │
                     │  VideoGenerator (TTS + avatar)  │
                     └─────────────────────────────────┘
```

---

## 6. Architectural Risks, Tech Debt & Improvement Proposals

### Risk 1: File-Based Persistence Does Not Scale

**Problem**: All data (personas, content, experiments, scheduler state) lives on the local filesystem as YAML/JSON files. This blocks:
- Horizontal scaling (multiple service instances)
- Concurrent writes (no locking)
- Efficient queries (no indexing)
- Operational backup / restore workflows

**Proposal**: Introduce a thin `StorageBackend` abstraction in front of `KnowledgeBase` with implementations for:
1. `FileStorageBackend` (current — keep for dev/single-user)
2. `SQLiteStorageBackend` (low-overhead upgrade for single-machine multi-process)
3. `PostgreSQLStorageBackend` (production multi-tenant)

The `KnowledgeBase` public API is already reasonably clean (`save_persona`, `load_persona`, `list_personas`, …) so this refactor could be done without touching agent code.

---

### Risk 2: No Rate Limiting or Retry Logic in Connectors

**Problem**: Connectors call platform APIs without built-in back-off or rate-limit awareness. A single runaway scheduled task could exhaust quota or get the account banned.

**Proposal**:
1. Add a thin `RateLimiter` utility (token-bucket or leaky-bucket) that connectors can call before each API request.
2. Add exponential back-off retry logic as a decorator (e.g. `@retry(max_attempts=3, backoff=2)`) applied at the connector base class level.
3. Surface rate-limit state in `ConnectorCapabilities` so the scheduler can space requests.

---

### Risk 3: Global Singleton Orchestrator in the Service Layer

**Problem**: `service/app.py` stores `_orchestrator` and `_scheduler` as module-level globals initialised once at startup. This:
- Makes unit testing very hard (state bleeds between tests)
- Prevents per-tenant orchestrator instances in multi-tenant mode
- Makes the lifespan function responsible for too much initialisation logic

**Proposal**:
1. Wrap the global state in a `AppContext` dataclass and inject it via FastAPI's dependency injection (`Depends(get_app_context)`).
2. In multi-tenant mode, create per-tenant `OrchestratorAgent` instances scoped to request lifetime (or cached by tenant ID).

---

### Risk 4: Intent Routing Is a Fragile LLM-Parsed Enum

**Problem**: `OrchestratorAgent._understand_intent()` asks an LLM to return a JSON object with an `intent_type` field from a fixed enum. If the model hallucinates an unknown value, the orchestrator falls back to `"create_persona"` silently. Adding a new intent type requires editing a long string prompt and testing it empirically.

**Proposal**:
1. Extract the intent enum and prompt into a structured config file (YAML) so new intents can be registered without code changes.
2. Add a confidence threshold: if confidence < 0.6, ask the user for clarification rather than silently guessing.
3. Consider using structured-output / function-calling (Anthropic tool use / OpenAI function calling) to get typed intent objects — eliminates the manual JSON parsing and fallback logic.

---

### Risk 5: No Application-Level Observability

**Problem**: There is no tracing, metrics, or log aggregation beyond Python's standard `logging`. In production it is hard to answer: Which agent calls are slow? Which LLM calls fail? How many content items are generated per persona per day?

**Proposal**:
1. Add OpenTelemetry instrumentation to `BaseAgent.call_llm()` (trace spans) and connector methods.
2. Expose a `/metrics` endpoint (Prometheus format) from the FastAPI service.
3. At minimum, add structured JSON logging (e.g. `python-json-logger`) so logs can be ingested by Loki or CloudWatch without custom parsing.

---

### Risk 6: Human-in-the-Loop Is Enforced Only by Convention

**Problem**: The HITL gate (draft → human review → publish) is a workflow convention, not a hard technical guarantee. A developer could call `connector.publish()` directly from agent code, bypassing the review step.

**Proposal**:
1. Add a `PublishGate` service that connectors must go through. The gate checks KnowledgeBase for an approved `ReviewReport` before allowing a publish.
2. Alternatively, require a `review_token` (a signed JWT from `ReviewAgent`) to be passed to `connector.publish()`, making bypass impossible without forging the token.

---

### Risk 7: Multi-Tenancy Is a Bolted-On Afterthought

**Problem**: The `tenant.py` / `tenant_kb.py` / `TenantAuthMiddleware` stack exists but is **disabled by default** (`enable_multi_tenancy=False`). The `KnowledgeBase` class is not tenant-aware — a mis-configuration could allow one tenant to read another's data.

**Proposal**:
1. Make `KnowledgeBase` always accept a `tenant_id` parameter (defaulting to `"default"`) so the file path is `knowledges/{tenant_id}/personas/…` from day one.
2. Enable the `TenantAuthMiddleware` by default, with a "default admin key" generated on first run and printed to stdout — so developers don't notice a difference but the security model is consistent.

---

### Risk 8: Connector Auth Uses Raw Cookies / Unsupported APIs

**Problem**: XiaohongshuConnector (and potentially WeibOConnector, ZhihuConnector) rely on browser session cookies and unofficial signing algorithms. These approaches:
- Break without notice when platforms update their signing logic
- May violate platform Terms of Service
- Cannot be covered by stable integration tests

**Proposal**:
1. Mark these connectors clearly as `IntegrationType.UNOFFICIAL` in their `ConnectorCapabilities`.
2. Add automated health-check pings (scheduled) that verify cookies are still valid and alert via webhook when they expire.
3. Evaluate official API options (Xiaohongshu has a creator open-platform beta) and migrate when available.

---

### Minor Tech Debt Items

| Item | Location | Suggested Fix |
|---|---|---|
| Deprecated `anthropic_client` / `model` kwargs kept for backward compat | `agents/base.py` | Remove in v1.0; add deprecation warning now |
| `ConnectorConfig` uses `dataclasses.field` inside a Pydantic model | `connectors/base.py` | Replace with `Field(default_factory=...)` throughout |
| No pagination support in `KnowledgeBase.list_*()` methods | `core/knowledges.py` | Add `limit`/`offset` parameters before content counts grow large |
| `AgentMessage.receiver` equality check is case-sensitive string match | `agents/base.py` | Normalise agent IDs to a registry enum |
| `OrchestratorAgent._understand_intent` prompt is duplicated for "has persona" / "no persona" paths | `agents/orchestrator.py` | Extract shared parts into a template, parametrise the difference |
| `web-admin` and `web-journal` use Astro but share no component library | `web-admin/`, `web-journal/` | Extract a shared `@avatarfactory/ui` package |

---

*This document was generated by analysing the `main` branch of `EldonZhao/AvatarFactory` as of 2026-04-10. Update as the architecture evolves.*
