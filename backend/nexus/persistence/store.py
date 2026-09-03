from __future__ import annotations
import json, sqlite3, time
from contextlib import closing

from ..config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY, created_at REAL, scenario TEXT, status TEXT,
  root_class TEXT, root_service TEXT, confidence REAL, severity TEXT,
  ranker TEXT, mttr_s REAL, payload TEXT
);
CREATE TABLE IF NOT EXISTS eval_runs (
  id TEXT PRIMARY KEY, created_at REAL, payload TEXT
);
"""


def conn():
    c = sqlite3.connect(settings.db_path, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with closing(conn()) as c:
        c.executescript(SCHEMA)
        c.commit()


def upsert_incident(inc: dict) -> None:
    with closing(conn()) as c:
        c.execute(
            """INSERT INTO incidents (id, created_at, scenario, status, root_class,
               root_service, confidence, severity, ranker, mttr_s, payload)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET status=excluded.status,
                 root_class=excluded.root_class, root_service=excluded.root_service,
                 confidence=excluded.confidence, severity=excluded.severity,
                 ranker=excluded.ranker, mttr_s=excluded.mttr_s,
                 payload=excluded.payload""",
            (inc["id"], inc.get("created_at", time.time()), inc.get("scenario"),
             inc.get("status"), (inc.get("root_cause") or {}).get("class"),
             (inc.get("root_cause") or {}).get("service"),
             (inc.get("root_cause") or {}).get("confidence"),
             (inc.get("impact") or {}).get("severity"),
             (inc.get("root_cause") or {}).get("ranker"),
             (inc.get("verification") or {}).get("mttr_s"),
             json.dumps(inc, default=str)))
        c.commit()


def list_incidents(limit: int = 50) -> list[dict]:
    with closing(conn()) as c:
        rows = c.execute("SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?",
                         (limit,)).fetchall()
    return [{k: r[k] for k in r.keys() if k != "payload"} for r in rows]


def get_incident(iid: str) -> dict | None:
    with closing(conn()) as c:
        r = c.execute("SELECT payload FROM incidents WHERE id=?", (iid,)).fetchone()
    return json.loads(r["payload"]) if r else None


def save_eval(run: dict) -> None:
    with closing(conn()) as c:
        c.execute("INSERT OR REPLACE INTO eval_runs VALUES (?,?,?)",
                  (run["run_id"], run["created_at"], json.dumps(run, default=str)))
        c.commit()
    settings.eval_path.write_text(json.dumps(run, indent=2, default=str))


def latest_eval() -> dict | None:
    if settings.eval_path.exists():
        try:
            return json.loads(settings.eval_path.read_text())
        except Exception:
            pass
    with closing(conn()) as c:
        r = c.execute("SELECT payload FROM eval_runs ORDER BY created_at DESC LIMIT 1"
                      ).fetchone()
    return json.loads(r["payload"]) if r else None
