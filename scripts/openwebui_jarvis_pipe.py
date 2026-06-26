from typing import Any
from pydantic import BaseModel, Field
from fastapi import Request

from open_webui.models.users import Users
from open_webui.utils.chat import generate_chat_completion


class Pipe:
    class Valves(BaseModel):
        VISION_MODEL: str = Field(default="Vision")
        DEFAULT_MODEL: str = Field(default="thinker-pro")
        THINKER_MIN_MAX_TOKENS: int = Field(default=800)
        THINKER_LONG_TASK_MIN_MAX_TOKENS: int = Field(default=1800)
        THINKER_CRM_MIN_MAX_TOKENS: int = Field(default=2400)

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        return [{"id": "jarvis", "name": "Jarvis"}]

    def _has_image(self, body: dict) -> bool:
        messages = body.get("messages", [])
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and (
                        part.get("type") == "image_url" or "image_url" in part
                    ):
                        return True

        files = body.get("files") or []
        for f in files:
            ftype = (f.get("type") or "").lower()
            if "image" in ftype:
                return True

        return False

    def _last_user_text(self, body: dict) -> str:
        messages = body.get("messages", [])
        for msg in reversed(messages):
            if msg.get("role") != "user":
                continue

            content = msg.get("content", "")
            if isinstance(content, str):
                return content

            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                return " ".join(parts)

        return ""

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        t = text.lower()
        return any(k in t for k in keywords)

    def _image_needs_text_output(self, text: str) -> bool:
        image_to_text_keywords = [
            "describe",
            "what is in",
            "caption",
            "transcribe",
            "ocr",
            "extract text",
            "read text",
            "summarize image",
            "explain this image",
            "analyze this image",
            "convert image to text",
            "translate image",
        ]
        return self._contains_any(text, image_to_text_keywords)

    def _strip_images_from_body(self, body: dict) -> dict:
        messages = body.get("messages", [])
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                msg["content"] = [
                    part
                    for part in content
                    if not (
                        isinstance(part, dict)
                        and (part.get("type") == "image_url" or "image_url" in part)
                    )
                ]

        files = body.get("files") or []
        body["files"] = [
            f for f in files if "image" not in (f.get("type") or "").lower()
        ]
        return body

    def _ensure_min_max_tokens(self, body: dict) -> dict:
        mt = body.get("max_tokens")
        if isinstance(mt, int):
            if mt < self.valves.THINKER_MIN_MAX_TOKENS:
                body["max_tokens"] = self.valves.THINKER_MIN_MAX_TOKENS
        else:
            body["max_tokens"] = self.valves.THINKER_MIN_MAX_TOKENS
        return body

    def _is_structured_business_analysis_request(self, text: str) -> bool:
        keywords = [
            "business process analysis",
            "roles and responsibilities",
            "workflow stages and decision points",
            "inputs, outputs, and handoffs",
            "risks, controls, and compliance",
            "bottlenecks and improvement opportunities",
            "concise structured report",
        ]
        return self._contains_any(text, keywords)

    def _is_crm_expansion_request(self, text: str) -> bool:
        keywords = [
            "expand",
            "new crm",
            "crm type of app",
            "law firm crm",
            "gap",
            "business process",
            "implement",
        ]
        return self._contains_any(text, keywords)

    def _apply_analysis_completion_guard(self, body: dict) -> dict:
        guard = (
            "Return one complete structured report with all requested sections. "
            "Do not ask follow-up questions unless a required file is missing. "
            "If a file is missing, state only which file is missing, then stop."
        )
        messages = body.get("messages") or []
        if not messages:
            body["messages"] = [{"role": "system", "content": guard}]
            return body

        first = messages[0]
        if (
            isinstance(first, dict)
            and first.get("role") == "system"
            and isinstance(first.get("content"), str)
        ):
            if guard not in first["content"]:
                first["content"] = f"{first['content'].strip()}\n\n{guard}"
        else:
            messages.insert(0, {"role": "system", "content": guard})

        body["messages"] = messages
        return body

    def _apply_crm_concise_template_guard(self, body: dict) -> dict:
        guard = (
            "For CRM-expansion requests, return one concise structured report with exactly these sections: "
            "1) Current-State Gaps, 2) Target CRM Capabilities, 3) End-to-End CRM Business Process for Law Firm, "
            "4) Role-by-Role Responsibilities, 5) Data Model and Objects, 6) Controls and Compliance, "
            "7) 90-Day Implementation Plan, 8) KPIs. "
            "Limit each section to 2-4 short bullets, each bullet to one sentence, no examples, no extra sections, "
            "no follow-up questions, and stop immediately after section 8. Keep the total answer under 900 words."
        )
        messages = body.get("messages") or []
        if not messages:
            body["messages"] = [{"role": "system", "content": guard}]
            return body

        first = messages[0]
        if (
            isinstance(first, dict)
            and first.get("role") == "system"
            and isinstance(first.get("content"), str)
        ):
            if guard not in first["content"]:
                first["content"] = f"{first['content'].strip()}\n\n{guard}"
        else:
            messages.insert(0, {"role": "system", "content": guard})

        body["messages"] = messages
        return body

    def _ensure_long_task_tokens(self, body: dict) -> dict:
        mt = body.get("max_tokens")
        if isinstance(mt, int):
            if mt < self.valves.THINKER_LONG_TASK_MIN_MAX_TOKENS:
                body["max_tokens"] = self.valves.THINKER_LONG_TASK_MIN_MAX_TOKENS
        else:
            body["max_tokens"] = self.valves.THINKER_LONG_TASK_MIN_MAX_TOKENS
        return body

    def _ensure_crm_task_tokens(self, body: dict) -> dict:
        mt = body.get("max_tokens")
        if isinstance(mt, int):
            if mt < self.valves.THINKER_CRM_MIN_MAX_TOKENS:
                body["max_tokens"] = self.valves.THINKER_CRM_MIN_MAX_TOKENS
        else:
            body["max_tokens"] = self.valves.THINKER_CRM_MIN_MAX_TOKENS
        return body

    async def pipe(self, body: dict, __user__: dict, __request__: Request) -> Any:
        prompt = self._last_user_text(body)

        # Default to thinker-pro for all requests. Only route to Vision when an image
        # is present and the user explicitly asks for image-to-text style output.
        if self._has_image(body) and self._image_needs_text_output(prompt):
            body["model"] = self.valves.VISION_MODEL
        else:
            body = self._strip_images_from_body(body)
            body["model"] = self.valves.DEFAULT_MODEL
            body = self._ensure_min_max_tokens(body)
            if self._is_structured_business_analysis_request(prompt):
                body = self._ensure_long_task_tokens(body)
                body = self._apply_analysis_completion_guard(body)
            if self._is_crm_expansion_request(prompt):
                body = self._ensure_crm_task_tokens(body)
                body = self._apply_crm_concise_template_guard(body)

        user = await Users.get_user_by_id(__user__["id"])
        return await generate_chat_completion(__request__, body, user)
