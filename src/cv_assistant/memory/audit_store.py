from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Any

import psycopg

from cv_assistant.config import get_settings


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PostgresAuditStore:
    """Append-only operational audit events. Event values must never contain source text."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ping(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("SELECT 1")

    def setup(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS public.cv_audit_events (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                node TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                input_hash CHAR(64) NOT NULL,
                output_hash CHAR(64) NOT NULL,
                model TEXT NOT NULL,
                latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
                event_json JSONB NOT NULL
            )""")
            connection.execute("""CREATE OR REPLACE FUNCTION public.cv_reject_audit_mutation()
                RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
                BEGIN RAISE EXCEPTION 'audit events are append-only'; END; $$""")
            connection.execute("""DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'cv_audit_no_update' AND tgrelid = 'public.cv_audit_events'::regclass) THEN
                    CREATE TRIGGER cv_audit_no_update BEFORE UPDATE ON public.cv_audit_events
                    FOR EACH ROW EXECUTE FUNCTION public.cv_reject_audit_mutation();
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'cv_audit_no_delete' AND tgrelid = 'public.cv_audit_events'::regclass) THEN
                    CREATE TRIGGER cv_audit_no_delete BEFORE DELETE ON public.cv_audit_events
                    FOR EACH ROW EXECUTE FUNCTION public.cv_reject_audit_mutation();
                END IF;
            END $$""")

    def append(self, event: dict[str, Any]) -> None:
        required = {"node", "timestamp", "input_hash", "output_hash", "model", "latency_ms"}
        if set(event) != required:
            raise ValueError("Audit event has missing or unexpected fields")
        if any(len(event[key]) != 64 for key in ("input_hash", "output_hash")):
            raise ValueError("Audit input and output hashes must be SHA-256 hex digests")
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                "INSERT INTO public.cv_audit_events(node,timestamp,input_hash,output_hash,model,latency_ms,event_json) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (event["node"], event["timestamp"], event["input_hash"], event["output_hash"],
                 event["model"], event["latency_ms"], json.dumps(event)),
            )


@lru_cache(maxsize=1)
def get_audit_store() -> PostgresAuditStore:
    return PostgresAuditStore(get_settings().database_url.get_secret_value())
