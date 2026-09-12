"""
Tool definitions that Grok can call.
Each tool maps to a real backend function.
"""

# =========================================================
# ADMIN TOOLS — create/manage users, courses
# =========================================================
ADMIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_student",
            "description": "Create a new student account. Requires email, password, full name, and roll number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email":       {"type": "string", "description": "Student's email"},
                    "password":    {"type": "string", "description": "Initial password (min 6 chars)"},
                    "full_name":   {"type": "string", "description": "Student's full name"},
                    "roll_number": {"type": "string", "description": "Unique roll number, e.g. UNI-2024-8842"},
                    "batch_year":  {"type": "integer", "description": "Enrollment batch year"},
                },
                "required": ["email", "password", "full_name", "roll_number", "batch_year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_teacher",
            "description": "Create a new teacher account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email":         {"type": "string", "description": "Teacher's email"},
                    "password":      {"type": "string", "description": "Initial password"},
                    "full_name":     {"type": "string", "description": "Teacher's full name"},
                    "employee_code": {"type": "string", "description": "Unique employee code"},
                    "designation":   {"type": "string", "description": "e.g. Professor, Lecturer"},
                },
                "required": ["email", "password", "full_name", "employee_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_course",
            "description": "Add a new course to the catalog.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code":    {"type": "string", "description": "Course code, e.g. CS301"},
                    "title":   {"type": "string", "description": "Course title"},
                    "credits": {"type": "integer", "description": "Credit hours (1-6)"},
                },
                "required": ["code", "title", "credits"],
            },
        },
    },
]

# =========================================================
# TEACHER TOOLS — mark attendance, view students
# =========================================================
TEACHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_my_courses",
            "description": "List all courses this teacher is assigned to teach.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_students",
            "description": "Get the list of students enrolled in a specific course, with their attendance percentages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_code": {"type": "string", "description": "Course code, e.g. CS301"},
                },
                "required": ["course_code"],
            },
        },
    },
]

# =========================================================
# STUDENT TOOLS — view attendance, timetable, courses
# =========================================================
STUDENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_my_attendance",
            "description": "Get the student's overall attendance percentage and per-course breakdown.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_timetable",
            "description": "Get the student's weekly class schedule.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_courses",
            "description": "List courses the student is enrolled in, with attendance percentage for each.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]