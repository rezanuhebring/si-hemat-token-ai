import json
import sqlite3
import time
from pathlib import Path


DB_PATH = "/app/backend/data/webui.db"
PROMPT_FILE = "/tmp/thinker-pro-system-prompt.md"
ADMIN_USER_ID = "f0c74e14-39c3-49d0-a20f-56449b1b2d99"


def load_prompt() -> str:
    return Path(PROMPT_FILE).read_text(encoding="utf-8").strip()


def upsert_model(cur, model_id: str, base_model_id: str, name: str, params: dict, meta: dict, ts: int):
    cur.execute("SELECT id FROM model WHERE id = ?", (model_id,))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute(
            """
            UPDATE model
            SET user_id = ?,
                base_model_id = ?,
                name = ?,
                params = ?,
                meta = ?,
                updated_at = ?,
                is_active = 1
            WHERE id = ?
            """,
            (
                ADMIN_USER_ID,
                base_model_id,
                name,
                json.dumps(params),
                json.dumps(meta),
                ts,
                model_id,
            ),
        )
        print(f"Updated model profile: {model_id}")
    else:
        cur.execute(
            """
            INSERT INTO model (id, user_id, base_model_id, name, params, meta, updated_at, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                model_id,
                ADMIN_USER_ID,
                base_model_id,
                name,
                json.dumps(params),
                json.dumps(meta),
                ts,
                ts,
            ),
        )
        print(f"Inserted model profile: {model_id}")


def main() -> int:
    prompt = load_prompt()
    now = int(time.time())

    meta = {
        "profile_image_url": "/static/favicon.png",
        "description": None,
        "capabilities": {
            "file_context": True,
            "vision": True,
            "file_upload": True,
            "web_search": True,
            "image_generation": True,
            "code_interpreter": True,
            "terminal": True,
            "citations": True,
            "status_updates": True,
            "builtin_tools": True,
        },
        "suggestion_prompts": None,
        "tags": [],
        "defaultFeatureIds": ["web_search", "code_interpreter"],
    }

    params = {
        "system": prompt,
        "reasoning_tags": False,
        "function_calling": "default",
        "custom_params": {
            "reasoning_tags": False,
        },
    }

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    upsert_model(
        cur,
        model_id="thinker-pro",
        base_model_id="thinker-pro",
        name="Thinker Pro",
        params=params,
        meta=meta,
        ts=now,
    )

    upsert_model(
        cur,
        model_id="home-thinker",
        base_model_id="thinker-pro",
        name="Home Thinker",
        params=params,
        meta=meta,
        ts=now,
    )

    conn.commit()

    cur.execute("SELECT id, base_model_id, name, LENGTH(params), updated_at FROM model WHERE id IN ('thinker-pro','home-thinker') ORDER BY id")
    rows = cur.fetchall()
    print("Verification rows:")
    for r in rows:
        print(r)

    cur.execute("SELECT params FROM model WHERE id='thinker-pro'")
    p = json.loads(cur.fetchone()[0])
    s = p.get("system", "")
    print("thinker-pro has attachment block:", "Attachment and retrieval handling:" in s)
    print("thinker-pro has anti-placeholder guard:", "Never return a placeholder-only response" in s)
    print("thinker-pro reasoning_tags top-level disabled:", p.get("reasoning_tags") is False)
    print("thinker-pro reasoning_tags custom disabled:", p.get("custom_params", {}).get("reasoning_tags") is False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
