from agents.tools.viz_tool import recommend_visualization

# ---- SAMPLE SQL RESULT ----
sample_data = [
    {"month": "Jan", "sales": 100, "profit": 30, "region": "North"},
    {"month": "Feb", "sales": 150, "profit": 50, "region": "North"},
    {"month": "Mar", "sales": 200, "profit": 70, "region": "North"},
    {"month": "Apr", "sales": 180, "profit": 60, "region": "South"},
    {"month": "May", "sales": 220, "profit": 80, "region": "South"},
]

columns = list(sample_data[0].keys()) if sample_data else []

result = recommend_visualization(columns, sample_data, sql="", question="")

print("\n=== CHART RECOMMENDATION ===")
print(result)