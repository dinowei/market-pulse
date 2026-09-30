import os

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("MARKET_PULSE_ENVIRONMENT", "local")
os.environ.setdefault("MARKET_PULSE_DEMO_ALLOW_RECREATE", "true")

# get_catalog() switches to the seeded demo.* read model when demo_enabled is true,
# which hides the MASTER_CATALOG identities most tests assert against. A developer's
# local apps/api/.env may enable DEMO mode, so pin it off here (os.environ outranks
# the dotenv file) to keep runs deterministic and identical to CI. Assigned, not
# setdefault, precisely to neutralize that .env. The DEMO integration gate opts back
# in via MARKET_PULSE_DEMO_INTEGRATION=true; those tests also set what they need
# through monkeypatch.
if os.environ.get("MARKET_PULSE_DEMO_INTEGRATION") != "true":
    os.environ["MARKET_PULSE_DEMO_ENABLED"] = "false"
os.environ.setdefault(
    "MARKET_PULSE_DATABASE_URL",
    "postgresql://market_pulse:market_pulse_local_only@127.0.0.1:5432/market_pulse_demo",
)
os.environ.setdefault(
    "MARKET_PULSE_DEMO_DATABASE_URL",
    "postgresql://market_pulse:market_pulse_local_only@127.0.0.1:5432/market_pulse_demo",
)
os.environ.setdefault("MARKET_PULSE_REDIS_URL", "redis://127.0.0.1:6379/15")
