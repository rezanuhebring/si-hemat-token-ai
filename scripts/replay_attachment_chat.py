import asyncio
import json
import sqlite3

from fastapi.testclient import TestClient

import open_webui.main as app_main
from open_webui.models.users import Users
from open_webui.utils.auth import get_verified_user


DB_PATH = "/app/backend/data/webui.db"
USER_ID = "f0c74e14-39c3-49d0-a20f-56449b1b2d99"
CHAT_ID = "1c90f3da-ece8-4660-914f-f15277c14018"


def load_user_message_files(chat_id: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT chat FROM chat WHERE id = ?", (chat_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return []

    chat = json.loads(row[0])
    messages = chat.get("history", {}).get("messages", {})
    for _, msg in messages.items():
        if msg.get("role") == "user" and msg.get("content", "").strip().lower() == "summarize it":
            return msg.get("files", [])
    return []


def main() -> int:
    user = asyncio.run(Users.get_user_by_id(USER_ID))
    if not user:
        print("ERROR: user not found")
        return 1

    files = load_user_message_files(CHAT_ID)
    print(f"Loaded files: {len(files)}")

    async def override_user():
        return user

    app_main.app.dependency_overrides[get_verified_user] = override_user

    client = TestClient(app_main.app)

    payload = {
        "model": "thinker-pro",
        "stream": False,
        "chat_id": CHAT_ID,
        "messages": [
            {
                "role": "user",
                "content": "Summarize attached ConflictCheckPLN.xlsx in 8 bullets.",
                "files": files,
            }
        ],
    }

    resp = client.post("/api/chat/completions", json=payload)
    print("STATUS", resp.status_code)
    text = resp.text[:4000]
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
