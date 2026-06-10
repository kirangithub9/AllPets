import json
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Color palette used for datasets
COLOR_PALETTE = ["#534AB7", "#1D9E75", "#D85A30", "#185FA5", "#BA7517", "#A32D2D"]


def _detect_date(value: str) -> bool:
    """Simple heuristic to detect if a string looks like a date.
    Tries common ISO and date formats.
    """
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            datetime.strptime(value, fmt)
            return True
        except Exception:
            continue
    return False


def _infer_schema(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """Return a mapping column -> inferred type ('numeric', 'date', 'categorical')."""
    schema = {}
    for col in columns:
        col_type = "categorical"  # default fallback
        for row in rows:
            val = row.get(col)
            if val is None:
                continue
            if isinstance(val, (int, float)):
                col_type = "numeric"
                break
            if isinstance(val, str):
                if _detect_date(val):
                    col_type = "date"
                else:
                    # try to parse as number
                    try:
                        float(val)
                        col_type = "numeric"
                    except Exception:
                        col_type = "categorical"
                break
        schema[col] = col_type
    return schema


def _select_chart(schema: Dict[str, str]) -> str:
    """Select chart type based on simple heuristic rules.
    Returns one of: bar, line, doughnut, pie, scatter, horizontalBar, combo, stat.
    """
    dimensions = [c for c, t in schema.items() if t in ("categorical", "date")]
    measures = [c for c, t in schema.items() if t == "numeric"]
    # Time series detection – a date column plus at least one measure
    has_time = any(t == "date" for t in schema.values())

    if len(dimensions) == 0 and len(measures) == 1:
        return "stat"
    if has_time and len(measures) >= 2:
        return "combo"
    if has_time and len(measures) == 1:
        return "line"
    if len(dimensions) == 1 and len(measures) == 1:
        return "bar"
    if len(dimensions) >= 1 and len(measures) >= 2:
        return "combo"
    if len(dimensions) >= 1 and len(measures) == 1:
        return "bar"
    # Fallback
    return "bar"


def _build_chartjs_config(chart_type: str, columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a minimal Chart.js configuration based on the chosen chart type.
    For simplicity, we assume the first dimension column provides labels and the
    remaining numeric columns become datasets.
    """
    # Identify label column (first non‑numeric)
    schema = _infer_schema(columns, rows)
    label_col = None
    for col in columns:
        if schema[col] in ("categorical", "date"):
            label_col = col
            break
    if not label_col:
        label_col = columns[0]
    labels = [row.get(label_col) for row in rows]
    datasets = []
    numeric_cols = [c for c in columns if schema[c] == "numeric"]
    for idx, col in enumerate(numeric_cols):
        data = [row.get(col) for row in rows]
        dataset = {
            "label": col,
            "data": data,
            "backgroundColor": COLOR_PALETTE[idx % len(COLOR_PALETTE)],
        }
        # For combo charts we need to indicate type per dataset
        if chart_type == "combo":
            dataset["type"] = "bar" if idx == 0 else "line"
            if dataset["type"] == "line":
                dataset["borderColor"] = COLOR_PALETTE[idx % len(COLOR_PALETTE)]
                dataset["fill"] = False
        datasets.append(dataset)

    config = {
        "type": chart_type if chart_type != "combo" else "bar",
        "data": {
            "labels": labels,
            "datasets": datasets,
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": True}},
        },
    }
    return config


def recommend_visualization(
    columns: List[str],
    rows: List[Dict[str, Any]],
    sql: str = "",
    question: str = "",
) -> Dict[str, Any]:
    """Analyze SQL query results and recommend a chart.
    This implementation uses deterministic heuristics and does **not** call any LLM.
    Returns a JSON‑compatible dict matching the schema used by the LLM based tool.
    """
    try:
        if not columns:
            raise ValueError("Columns list cannot be empty")
        # Infer schema and pick chart type
        schema = _infer_schema(columns, rows)
        chart_type = _select_chart(schema)
        config = _build_chartjs_config(chart_type, columns, rows)
        # Simple insight generation – first numeric column stats
        insight = ""
        numeric_cols = [c for c in columns if schema[c] == "numeric"]
        if numeric_cols:
            first_measure = numeric_cols[0]
            values = [row.get(first_measure) for row in rows if isinstance(row.get(first_measure), (int, float))]
            if values:
                insight = f"{first_measure} ranges from {min(values)} to {max(values)}."
        result = {
            "chart_type": chart_type,
            "reason": f"Heuristic selection based on {len(numeric_cols)} numeric column(s) and {len(columns) - len(numeric_cols)} dimension column(s).",
            "chartjs_config": config,
            "insight": insight,
            "input_tokens": 0,
            "output_tokens": 0,
            "error": None,
        }
        logger.info("Recommended %s chart", chart_type)
        return result
    except Exception as e:
        logger.error("Chart recommendation error: %s", e)
        return {
            "chart_type": "bar",
            "reason": "Default fallback due to error",
            "chartjs_config": {},
            "insight": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "error": str(e),
        }
