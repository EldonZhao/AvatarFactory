# API Reference

AvatarFactory provides a REST API via FastAPI. Start the service with:

```bash
avatarfactory serve --host 0.0.0.0 --port 8000
```

Interactive API docs (Swagger UI) available at: `http://localhost:8000/docs`

---

## System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (returns status and version) |
| GET | `/` | API info and available endpoints |
| GET | `/topology` | Agent system topology (nodes and edges) |
| GET | `/connectors/status` | Status of all platform connectors |

---

## Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Process a natural language message |

**Body:** `{ "message": "Create a persona for...", "persona_id": "optional" }`

---

## Personas

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/personas` | List all personas |
| GET | `/personas/{persona_id}` | Get persona details |
| POST | `/personas` | Create a new persona |
| DELETE | `/personas/{persona_id}` | Delete a persona |

---

## Content

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/content/generate` | Generate content for a persona |
| GET | `/content` | List all content |
| GET | `/content/{content_id}` | Get content details |
| GET | `/content/{content_id}/view` | Render content as HTML |
| GET | `/content/{content_id}/image` | Generate content card image |
| GET | `/content/{content_id}/images` | List generated images |

---

## Scheduler

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/scheduler/status` | Scheduler running status |
| GET | `/scheduler/tasks` | List all scheduled tasks |
| POST | `/scheduler/tasks/{persona_id}/setup` | Set up proactive tasks for a persona |
| DELETE | `/scheduler/tasks/{persona_id}` | Remove scheduled tasks |
| POST | `/scheduler/tasks/{task_id}/run` | Manually run a task |

---

## Connectors

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/connectors/` | List all connectors and their config status |
| GET | `/api/connectors/{platform}` | Get config for a specific connector |
| PUT | `/api/connectors/{platform}` | Update connector configuration |
| DELETE | `/api/connectors/{platform}` | Clear connector configuration |
| POST | `/api/connectors/{platform}/test` | Test connector connectivity |

---

## Evolution

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/personas/{persona_id}/evolution/suggestions` | Get evolution suggestions |
| POST | `/personas/{persona_id}/evolution/analyze` | Analyze persona for improvement |
| POST | `/personas/{persona_id}/evolution/suggest` | Generate evolution suggestions |
| POST | `/personas/{persona_id}/evolution/suggestions/{id}/review` | Approve/reject a suggestion |
| POST | `/personas/{persona_id}/evolution/rollback` | Rollback to previous version |
| GET | `/personas/{persona_id}/evolution/history` | Get evolution history |
| GET | `/personas/{persona_id}/agents/{agent_type}/config` | Get agent config for persona |
| PUT | `/personas/{persona_id}/agents/{agent_type}/config` | Update agent config for persona |

---

## Chronicle & Journal Routes

Additional routes are registered via `chronicle_routes` and `journal_routes` routers. See the Swagger UI at `/docs` for the full list.

---

## Admin & Auth Routes

| Prefix | Description |
|--------|-------------|
| `/api/admin/` | Admin management endpoints |
| `/api/admin/auth/` | Authentication (login, verify, logout) |

---

## Authentication

The web-admin frontend uses cookie-based auth (`admin_token`). API calls from the frontend are proxied through the Astro middleware and include the auth cookie automatically.

For direct API access, no authentication is required by default (single-tenant mode). Enable multi-tenancy for auth middleware.
