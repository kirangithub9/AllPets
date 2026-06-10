# SQL AI Agent — FastAPI + GPT-4o + MySQL + TokenLens

Natural language → SQL → Results → Charts + Business Strategy recommendations.

---

## Architecture

```
User Query (natural language)
        │
        ▼
  Master AI Agent
  ┌─────────────────────────────────────────┐
  │  Intent Classifier (GPT-4o)             │
  │     ├─ data_query  → SQL Tool           │
  │     │                 └─ Viz Tool       │
  │     ├─ strategy    → Strategy Tool      │
  │     └─ chart_only  → Viz Tool           │
  │                                         │
  │  Response Synthesizer (GPT-4o)          │
  └─────────────────────────────────────────┘
        │
        ▼
  TokenLens (token tracking per user)
        │
        ▼
  Structured Response (text + SQL + chart config + recommendations)
```

---

## Project structure

```
sql_agent/
├── main.py                        # FastAPI app entry point
├── requirements.txt
├── .env.example
├── routers/
│   └── api.py                     # All endpoints
├── agents/
│   ├── master_agent.py            # Orchestrator
│   └── tools/
│       ├── sql_tool.py            # NL → SQL → execute
│       ├── viz_tool.py            # Results → chart recommendation
│       └── strategy_tool.py      # Sales/inventory → strategy
├── services/
│   ├── database.py                # MySQL connection + schema extraction
│   └── session.py                 # Session state management
├── middleware/
│   └── tokenlens.py               # Auth + token tracking
└── models/
    └── schemas.py                 # Pydantic request/response models
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
```
Fill in:
- `OPENAI_API_KEY` — from platform.openai.com
- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- `TOKENLENS_API_URL` + `TOKENLENS_API_KEY` — when available

### 3. Run
```bash
uvicorn main:app --reload --port 8000
```

Swagger docs: http://localhost:8000/docs

---

## API Endpoints

### POST /chat
Main conversational endpoint. Send any natural language query.

**Request:**
```json
{
  "session_id": "user-session-123",
  "message": "What are the top 5 products by revenue this month?"
}
```

**Response:**
```json
{
  "session_id": "user-session-123",
  "response": "Your top 5 products this month are...",
  "intent": "data_query",
  "sql": "SELECT product_name, SUM(revenue) FROM sales WHERE ...",
  "query_result": {
    "columns": ["product_name", "revenue"],
    "rows": [...],
    "row_count": 5
  },
  "visualization": {
    "chart_type": "bar",
    "reason": "Comparing revenue across categories",
    "chartjs_config": { ... },
    "insight": "Product A accounts for 40% of total revenue"
  },
  "usage": {
    "input_tokens": 842,
    "output_tokens": 210,
    "total_tokens": 1052
  }
}
```

---

### POST /strategy
Full business strategy analysis — analyzes sales + inventory data automatically.

**Response:**
```json
{
  "sales_analysis": {
    "top_products": ["Product A", "Product B"],
    "trend": "growing",
    "key_insight": "Revenue up 23% MoM"
  },
  "inventory_insights": {
    "overstocked": ["SKU-001", "SKU-045"],
    "understocked": ["SKU-102"],
    "turnover_health": "moderate"
  },
  "recommendations": [
    {
      "title": "Reduce overstock on slow-moving SKUs",
      "action": "Run a 20% discount campaign on SKU-001 and SKU-045",
      "impact": "High",
      "timeline": "Immediate",
      "expected_outcome": "Free up ₹2L in working capital within 30 days"
    }
  ],
  "growth_opportunities": ["..."],
  "summary": "Business is growing steadily but inventory inefficiencies..."
}
```

---

### GET /schema
View extracted database schema (tables, columns, relationships).

---

### GET /session/{session_id}
View session stats (message count, last SQL, user).

### DELETE /session/{session_id}
Clear session history.

---

## TokenLens Integration

Token tracking is built in and activates automatically when you add:
```env
TOKENLENS_API_URL=https://your-tokenlens-backend.com
TOKENLENS_API_KEY=your-api-key
TOKENLENS_ENABLED=true
```

Until then, all token usage is logged locally in DRY_RUN mode.

Every `/chat` request tracks:
- `user_id` (from TokenLens auth)
- `session_id`
- `input_tokens` + `output_tokens` per query
- `model` used
- `query_preview` (first 120 chars)

---

## Example queries the agent handles

| User says | Intent | Tools used |
|---|---|---|
| "Show me total sales by region" | data_query | SQL → Viz |
| "Which products are low in stock?" | data_query | SQL → Viz |
| "How should I grow my business?" | strategy | Strategy |
| "Show me a chart of last result" | chart_only | Viz |
| "What were sales last quarter?" | data_query | SQL → Viz |
| "Which customers buy the most?" | data_query | SQL → Viz |
