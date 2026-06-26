# Cline Workspace Rules

## Task Execution
- Do NOT generate generic TO-DO checklists or task plans before using tools
- Do NOT say "the task was interrupted and needs to be resumed" — just proceed with the current request
- Use tools immediately and directly. Do not describe what you will do before doing it
- If you need to explore files or run commands, just do it — do not announce it with a checklist first

## Tool Usage
- Always prefer actual tool calls over generating text descriptions of actions
- Never output placeholder responses like "Analyze requirements", "Set up necessary files", etc.
- If a task is unclear, ask a single clarifying question — do not generate a generic multi-step plan

## Behavior
- Treat each new message as a fresh task unless explicitly told to resume something
- Do not reference previous interrupted sessions unless the user explicitly asks to resume one
