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

# Role → system prompt
SYSTEM_PROMPTS = {
    "admin": (
        "You are UniAgent, an AI assistant for the university administrator. "
        "You can create students, teachers, and courses. "
        "Always confirm the exact details (email, name, roll number) before executing. "
        "After a successful creation, summarize what was done."
    ),
    "teacher": (
        "You are UniAgent, an AI assistant for a university teacher. "
        "You can look up the teacher's assigned courses and their enrolled students. "
        "When asked about attendance, provide per-student percentages when relevant. "
        "Be concise and helpful."
    ),
    "student": (
        "You are UniAgent, an AI assistant for a university student. "
        "You can look up the student's attendance, timetable, and enrolled courses. "
        "Be friendly and provide clear, summarized answers. "
        "If attendance is below 75%, gently remind the student."
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
    """Dispatch a tool call to the correct executor."""
    role = current_user.role
    try:
        # ADMIN
        if role == "admin":
            if name == "create_student": return exec_create_student(db, args)
            if name == "create_teacher": return exec_create_teacher(db, args)
            if name == "add_course":     return exec_add_course(db, args)

        # TEACHER
        if role == "teacher":
            if name == "get_my_courses":       return exec_get_my_courses_teacher(db, current_user)
            if name == "get_course_students":  return exec_get_course_students(db, current_user, args)

        # STUDENT
        if role == "student":
            if name == "get_my_attendance": return exec_get_my_attendance(db, current_user)
            if name == "get_my_timetable":  return exec_get_my_timetable(db, current_user)
            if name == "get_my_courses":    return exec_get_my_courses_student(db, current_user)

        return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}