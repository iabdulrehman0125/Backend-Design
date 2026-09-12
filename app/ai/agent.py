"""
Runs the Grok-powered conversation with role-specific tools.
"""

import os
import json
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models import User
from app.ai.tools import ADMIN_TOOLS, TEACHER_TOOLS, STUDENT_TOOLS
from app.ai.executors import (
    exec_create_student, exec_create_teacher, exec_add_course,
    exec_get_my_courses_teacher, exec_get_course_students,
    exec_get_my_attendance, exec_get_my_timetable, exec_get_my_courses_student,
    exec_list_users, exec_delete_user,      
)

client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY", ""),   # ← keeps your existing Vercel var
    base_url="https://api.groq.com/openai/v1",   # ← point to Groq instead of xAI
)

MODEL = "openai/gpt-oss-20b"            # ← Groq's best free model with tool calling

# Role → tools mapping
ROLE_TOOLS = {
    "admin":   ADMIN_TOOLS,
    "teacher": TEACHER_TOOLS,
    "student": STUDENT_TOOLS,
}
ROLE_TOOL_NAMES = {
    role: {
        tool["function"]["name"]
        for tool in tools
    }
    for role, tools in ROLE_TOOLS.items()
}
TOOL_EXECUTORS = {
    "admin": {
        "create_student": lambda db, user, args: exec_create_student(db, args),
        "create_teacher": lambda db, user, args: exec_create_teacher(db, args),
        "add_course": lambda db, user, args: exec_add_course(db, args),
        "list_users": lambda db, user, args: exec_list_users(db, args),
        "delete_user": lambda db, user, args: exec_delete_user(db, args),
    },
    "teacher": {
        "get_my_courses": lambda db, user, args: exec_get_my_courses_teacher(db, user),
        "get_course_students": lambda db, user, args: exec_get_course_students(db, user, args),
    },
    "student": {
        "get_my_attendance": lambda db, user, args: exec_get_my_attendance(db, user),
        "get_my_timetable": lambda db, user, args: exec_get_my_timetable(db, user),
        "get_my_courses": lambda db, user, args: exec_get_my_courses_student(db, user),
    },
}
# Role → system prompt
SYSTEM_PROMPTS = {
      "admin": (
        "You are UniAgent, an AI assistant for the university administrator.\n"
        "You can create students, teachers, and courses, and you can delete students "
        "or teachers when explicitly asked.\n\n"
        "RESPONSE FORMAT RULES:\n"
        "- Keep replies short and scannable.\n"
        "- Use plain text with simple line breaks.\n"
        "- For lists, use '• ' at the start of each line (no markdown asterisks).\n"
        "- Never use ** ** or ## headings.\n\n"
        "DELETION RULES (IMPORTANT):\n"
        "- Before calling delete_user, ALWAYS show the user's full name and email "
        "and ask: 'Confirm deletion of <name> (<email>)? Reply YES to proceed.'\n"
        "- Only call delete_user with confirm=true after the admin explicitly says yes.\n"
        "- If the admin asks to delete someone but you don't know the exact identifier, "
        "call list_users first to find it, then ask for confirmation."
    ),
    "teacher": (
        "You are UniAgent, an AI assistant for a university teacher.\n"
        "You can look up the teacher's assigned courses and their enrolled students.\n\n"
        "RESPONSE FORMAT RULES:\n"
        "- Keep replies short and scannable.\n"
        "- When listing courses, use this exact format on separate lines:\n"
        "    • CS301 — Artificial Intelligence (4 credits, 12 students)\n"
        "- When listing students, use:\n"
        "    • Ali Khan (UNI-2024-8842) — 92% attendance\n"
        "- Use plain text with simple line breaks. No markdown.\n"
        "- If there is nothing to show, say so in one short sentence."
    ),
    "student": (
        "You are UniAgent, an AI assistant for a university student.\n"
        "You can look up the student's attendance, timetable, and enrolled courses.\n\n"
        "RESPONSE FORMAT RULES:\n"
        "- Be friendly but brief — no walls of text.\n"
        "- When listing attendance, use:\n"
        "    • CS301 — 92% (11/12 sessions)\n"
        "- When listing timetable, use:\n"
        "    • Monday 09:00–10:30 — CS301 in Room 401\n"
        "- Use plain text with simple line breaks. No markdown symbols.\n"
        "- If attendance is below 75%, add a short friendly warning at the end."
    ),
}

def run_agent(db: Session, current_user: User, user_message: str) -> str:
    """
    1. Pick tools based on role.
    2. Send to Grok.
    3. Loop: if Grok requests a tool, execute it and send the result back.
    4. Return the final natural-language reply.
    """
    role = current_user.role
    tools = ROLE_TOOLS.get(role, [])
    system_prompt = SYSTEM_PROMPTS.get(role, "You are UniAgent, a helpful university assistant.")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]

    # Max 5 tool-call rounds to prevent infinite loops
    for _ in range(5):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        # No tool call → return the final text
        if not msg.tool_calls:
            return msg.content or "I'm not sure how to help with that."

        # Append the assistant's tool-call message
        messages.append(msg)

        # Execute each requested tool
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            result = _execute_tool(db, current_user, name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    return "I hit a limit while processing your request. Please try rephrasing."


def _execute_tool(db: Session, current_user: User, name: str, args: dict) -> dict:
    """Dispatch a tool call only if the user's role allows it."""

    role = current_user.role

    if role not in ROLE_TOOL_NAMES:
        return {"error": "Your account has an invalid role."}

    if name not in ROLE_TOOL_NAMES[role]:
        return {
            "error": f"Tool '{name}' is not allowed for the {role} role."
        }

    executor = TOOL_EXECUTORS.get(role, {}).get(name)

    if executor is None:
        return {
            "error": f"Tool '{name}' is not configured for the {role} role."
        }

    try:
        return executor(db, current_user, args)

    except Exception:
        db.rollback()
        return {
            "error": "Something went wrong while processing this request."
        }
