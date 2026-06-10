"""
agents/tools/viz_tool.py
─────────────────────────
Tool 2: SQL Result → Chart/Graph Recommendation

Analyzes query result structure and data patterns to recommend
the most effective visualization with a ready-to-use Chart.js config.
"""

import logging
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# Lazy initialization of OpenAI client to avoid import-time errors
client = None

def _get_client():
    """Create or retrieve a singleton OpenAI client using the API key from environment.
    If the OPENAI_API_KEY is not set, OpenAI will attempt to use its default auth mechanisms.
    """
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            client = OpenAI()
    return client

MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o")

SYSTEM_PROMPT = """You are a data visualization expert.

Given SQL query results (columns + sample rows), recommend the best chart type
and return a complete Chart.js configuration.

Chart selection rules:
- 1 dimension + 1 measure → bar chart
- Time series (date/month/year column) → line chart
- Parts of a whole (%) → doughnut or pie chart
- 2 measures + categories → grouped bar chart
- Trend + comparison → combo (bar + line)
- Geographic/category ranking → horizontal bar
- Correlation between 2 numeric columns → scatter chart
- Single KPI number → stat card (no chart)

Return ONLY a valid JSON object in this exact shape:
{
  "chart_type": "bar|line|doughnut|pie|scatter|horizontalBar|combo|stat",
  "reason": "one sentence explaining why this chart fits",
  "chartjs_config": {
    "type": "...",
    "data": {
      "labels": [...],
      "datasets": [{ "label": "...", "data": [...], "backgroundColor": "..." }]
    },
    "options": {
      "responsive": true,
      "plugins": { "legend": { "display": true } }
    }
  },
  "insight": "one sentence key insight from the data",
  "input_tokens": 0,
  "output_tokens": 0
}

For stat card type, chartjs_config should be:
{ "type": "stat", "value": <number>, "label": "...", "unit": "..." }

Use these colors for datasets (cycle if multiple):
["#534AB7", "#1D9E75", "#D85A30", "#185FA5", "#BA7517", "#A32D2D"]
"""


def recommend_visualization(
    columns:  list[str],
    rows:     list[dict],
    sql:      str = "",
    question: str = "",
) -> dict:
    """
    Analyze query result and recommend the best chart.

    Returns:
    {
      "chart_type": str,
      "reason": str,
      "chartjs_config": dict,
      "insight": str,
      "input_tokens": int,
      "output_tokens": int,
      "error": None | str
    }
    """
    try:
        # Send a sample of rows (max 20) to avoid token bloat
        sample_rows = rows[:20]

        user_content = f"""
SQL Query: {sql}
User Question: {question}

Columns: {json.dumps(columns)}
Sample Data ({len(sample_rows)} of {len(rows)} rows):
{json.dumps(sample_rows, indent=2)}

Total rows returned: {len(rows)}
"""

        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        raw            = response.choices[0].message.content
        input_tokens   = response.usage.prompt_tokens
        output_tokens  = response.usage.completion_tokens

        result = json.loads(raw)
        result["input_tokens"]  = input_tokens
        result["output_tokens"] = output_tokens
        result["error"]         = None

        logger.info("Recommended chart: %s", result.get("chart_type"))
        return result

    except Exception as e:
        logger.error("Viz tool error: %s", e)
        return {
            "chart_type":    "bar",
            "reason":        "Default fallback due to error",
            "chartjs_config": {},
            "insight":       "",
            "input_tokens":  0,
            "output_tokens": 0,
            "error":         str(e),
        }
