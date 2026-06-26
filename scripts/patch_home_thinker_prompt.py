import json
import sqlite3


DB_PATH = "/app/backend/data/webui.db"
MODEL_ID = "home-thinker"

ATTACHMENT_BLOCK = """

ATTACHMENT HANDLING (HIGH PRIORITY)
- If OpenWebUI shows retrieved sources or attached files for the current user turn, treat that as the target document by default.
- For prompts like summarize it, extract, list, do NOT ask which document unless zero sources are retrieved.
- First provide the best possible answer from retrieved content, then optionally ask one concise follow-up only if critical fields are missing.
""".rstrip()


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT params FROM model WHERE id = ?", (MODEL_ID,))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: model id '{MODEL_ID}' not found")
        return 1

    params = json.loads(row[0]) if row[0] else {}
    system_prompt = params.get("system", "")

    if "ATTACHMENT HANDLING (HIGH PRIORITY)" in system_prompt:
        print("No change needed: attachment block already present.")
    else:
        params["system"] = f"{system_prompt}{ATTACHMENT_BLOCK}"
        cur.execute(
            "UPDATE model SET params = ? WHERE id = ?",
            (json.dumps(params), MODEL_ID),
        )
        conn.commit()
        print("Updated Home Thinker system prompt.")

    cur.execute("SELECT params FROM model WHERE id = ?", (MODEL_ID,))
    updated = json.loads(cur.fetchone()[0])
    preview = updated.get("system", "")[-700:]
    print("--- Prompt Tail Preview ---")
    print(preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
