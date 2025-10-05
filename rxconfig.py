"""Reflex configuration file for TraceAI Web UI."""

import reflex as rx

config = rx.Config(
    app_name="traceai.webui",
    db_url="sqlite:///./data/webui.db",
    env=rx.Env.DEV,
)
