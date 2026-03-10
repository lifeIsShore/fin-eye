"""Binary search: test each router import to find AssertionError."""
import sys
import traceback

imports_to_test = [
    ("app.api.v1.health", "health_router"),
    ("app.api.v1.data", "data_router"),
    ("app.api.v1.auth", "auth_router"),
    ("app.api.v1.endpoints.macro", "macro"),
    ("app.api.v1.endpoints.sentiment", "sentiment"),
    ("app.api.v1.endpoints.technical", "technical"),
    ("app.api.v1.endpoints.explanation", "explanation"),
    ("app.api.v1.endpoints.hedging", "hedging"),
    ("app.api.v1.endpoints.portfolios", "portfolios"),
    ("app.api.v1.endpoints.backtesting", "backtesting"),
    ("app.api.v1.endpoints.events", "events"),
    ("app.api.v1.endpoints.watchlist", "watchlist"),
    ("app.api.v1.endpoints.legal", "legal"),
    ("app.api.v1.endpoints.gdpr", "gdpr"),
    ("app.api.v1.endpoints.cms", "cms"),
    ("app.api.v1.endpoints.alerts", "alerts"),
    ("app.api.v1.endpoints.strategies", "strategies"),
    ("app.api.v1.endpoints.showcase", "showcase"),
    ("app.api.v1.endpoints.ops", "ops"),
    ("app.api.v1.endpoints.analytics", "analytics"),
    ("app.api.v1.endpoints.experiments", "experiments"),
    ("app.api.v1.endpoints.email", "email"),
    ("app.api.v1.endpoints.api_keys", "api_keys"),
    ("app.api.v1.endpoints.risk", "risk"),
    ("app.api.v1.endpoints.admin_gas", "admin_gas"),
    ("app.api.v1.endpoints.options", "options"),
    ("app.api.v1.endpoints.sectors", "sectors"),
    ("app.api.v1.endpoints.insiders", "insiders"),
    ("app.api.v1.endpoints.earnings", "earnings"),
    ("app.api.v1.endpoints.shorts", "shorts"),
    ("app.api.v1.endpoints.adv_sentiment", "adv_sentiment"),
    ("app.api.v1.endpoints.fed_policy", "fed_policy"),
    ("app.api.v1.endpoints.indicators", "indicators"),
    ("app.api.public.v1", "public_v1_router"),
    ("app.middleware.metrics_middleware", "MetricsMiddleware"),
    ("app.services.scheduler", "setup_scheduler"),
]

results = []
for module_path, name in imports_to_test:
    try:
        import importlib
        m = importlib.import_module(module_path)
        results.append(f"OK: {module_path}")
    except AssertionError as e:
        results.append(f"ASSERTION_ERROR: {module_path} => {e}")
        import traceback
        results.append(traceback.format_exc())
    except Exception as e:
        results.append(f"ERROR ({type(e).__name__}): {module_path} => {str(e)[:200]}")

with open("import_search.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print("Done. Check import_search.txt")
