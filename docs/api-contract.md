# MarketAtlas API Contract

**Base URL:** `http://localhost:8000`

**Auth:** None (open API for development)

---

## 1. Events

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/events` | Create a new event |
| GET    | `/events/{id}` | Get event by ID |
| GET    | `/events/{id}/entities` | Get event with related entities |
| GET    | `/events` | List all events (paginated) |
| GET    | `/events/filter/type/{type}` | Filter by event type |
| GET    | `/events/filter/severity/{sev}` | Filter by severity |
| GET    | `/events/filter/status/{status}` | Filter by status |
| GET    | `/events/filter/recent/{days}` | Recent events (last N days) |
| PUT    | `/events/{id}` | Partial update |
| DELETE | `/events/{id}` | Delete event |
| POST   | `/events/{id}/entities/{entity_id}` | Link entity to event |
| DELETE | `/events/{id}/entities/{entity_id}` | Unlink entity from event |

### POST /events/{id}/entities/{entity_id}
- **204 No Content** on success
- **404** if event or entity not found
- **409** if already linked

## 2. Entities

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/entities` | Create entity (409 on duplicate name) |
| GET    | `/entities/{id}` | Get entity by ID |
| GET    | `/entities` | List all entities (paginated) |
| GET    | `/entities/filter/type/{type}` | Filter by entity type |
| GET    | `/entities/filter/country/{code}` | Filter by ISO country code |
| GET    | `/entities/search/name/{name}` | Search by exact name |
| GET    | `/entities/search/ticker/{ticker}` | Search by ticker (substring) |
| PUT    | `/entities/{id}` | Partial update (409 on name collision) |
| DELETE | `/entities/{id}` | Delete entity |

## 3. Market Prices

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/market-prices` | Create price record (409 on duplicate) |
| GET    | `/market-prices/{id}` | Get price record by ID |
| GET    | `/market-prices/entity/{id}` | List by entity (paginated) |
| GET    | `/market-prices/entity/{id}/latest` | Latest price for entity |
| GET    | `/market-prices/entity/{id}/recent` | Prices from last N days |
| GET    | `/market-prices/entity/{id}/range` | Prices in date range |
| POST   | `/market-prices/fetch/{entity_id}` | **Fetch + store via yfinance** |

### POST /market-prices/fetch/{entity_id}
Fetches historical price data from Yahoo Finance for the entity's ticker symbol and stores it in the database.

**Query Parameters:**
- `period` (default: `1mo`): 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
- `interval` (default: `1d`): 1m, 2m, 5m, 15m, 30m, 60m, 1d, 5d, 1wk, 1mo

**Response:**
```json
{
  "entity_id": 1,
  "records_fetched": 21,
  "records_stored": 20,
  "source": "yfinance"
}
```

- **200** on success (records_stored may be less than records_fetched due to dedup)
- **400** if entity has no ticker symbols or yfinance returns empty data
- **404** if entity not found

## 4. Signals

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/signals` | Create signal (404 if event/entity FK missing) |
| GET    | `/signals/{id}` | Get signal by ID |
| GET    | `/signals` | List all signals (paginated) |
| GET    | `/signals/filter/event/{id}` | Filter by event |
| GET    | `/signals/filter/entity/{id}` | Filter by entity |
| GET    | `/signals/filter/type/{type}` | Filter by signal type |
| GET    | `/signals/filter/status/{status}` | Filter by status |
| GET    | `/signals/filter/active` | Active signals only |
| GET    | `/signals/filter/high-confidence` | Signals above 0.75 confidence |
| PUT    | `/signals/{id}` | Partial update |
| DELETE | `/signals/{id}` | Delete signal |

## 5. AI Analysis — Event → Signal Workflow

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/events/{event_id}/analyze` | **Run AI analysis on event** |

### POST /events/{event_id}/analyze
Triggers the end-to-end Event → AI → Signal pipeline:
1. Fetches the event
2. For each linked entity (or specified entity_ids), runs mock AI analysis
3. Generates and stores trading signals
4. Returns the event with generated signals

**Request Body (optional):**
```json
{
  "entity_ids": [1, 2, 3]
}
```
If omitted, analyzes all entities linked to the event.

**Response:**
```json
{
  "event": { "...event fields..." },
  "signals": [ "...generated SignalRead objects..." ]
}
```

- **200** on success
- **400** if no entities linked (and none provided)
- **404** if event not found

## 6. Health

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health` | Health check |

**Response:** `{"status": "healthy", "service": "MarketAtlas", "version": "1.0.0"}`

---

## Error Response Format

All errors return JSON:
```json
{
  "detail": "Human-readable error message"
}
```

Common status codes:
- **400** Bad Request (validation, date range, missing entities)
- **404** Resource not found
- **409** Conflict (duplicate name, duplicate market price, already linked)
- **422** Validation error (Pydantic schema fields)

## Pagination

Paginated endpoints accept `skip` (default 0) and `limit` (default 100, max 1000) query parameters.

**Response format:**
```json
{
  "total": 150,
  "skip": 0,
  "limit": 100,
  "items": [ "...array of results..." ]
}
```
