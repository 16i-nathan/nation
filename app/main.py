import sqlite3
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import clear_session, create_session, hash_password, verify_password
from .database import get_connection, init_db

app = FastAPI(title="NUR Online Learning MVP")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def to_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
    }


def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("session_token")
    if not token:
        return None

    conn = get_connection()
    row = conn.execute(
        """
        SELECT u.id, u.full_name, u.email, u.role
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return to_user(row)


def require_user(user: Optional[dict]) -> dict:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def require_role(user: dict, allowed: set[str]) -> None:
    if user["role"] not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        request=request, name="index.html", context={"user": user, "title": "NUR Online Learning"}
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="register.html", context={"title": "Create account", "error": None}
    )


@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    if role not in {"admin", "lecturer", "student"}:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"title": "Create account", "error": "Invalid role selected."},
            status_code=400,
        )
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users(full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (full_name.strip(), email.strip().lower(), hash_password(password), role),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"title": "Create account", "error": "Email is already registered."},
            status_code=409,
        )
    conn.close()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"title": "Sign in", "error": None}
    )


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        conn.close()
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"title": "Sign in", "error": "Invalid email or password."},
            status_code=401,
        )
    token = create_session(conn, row["id"])
    conn.close()
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("session_token", token, httponly=True, samesite="lax")
    return response


@app.post("/logout")
def logout(request: Request):
    token = request.cookies.get("session_token")
    if token:
        conn = get_connection()
        clear_session(conn, token)
        conn.close()
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_token")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = require_user(get_current_user(request))
    conn = get_connection()
    available_courses = []
    manageable_courses = []
    submissions = []
    assignment_params: tuple = ()
    if user["role"] == "lecturer":
        courses = conn.execute(
            "SELECT id, code, title, description FROM courses WHERE lecturer_id = ? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()
        manageable_courses = courses
        assignments_query = """
            SELECT a.id, a.title, a.due_date, c.code as course_code
            FROM assignments a
            JOIN courses c ON c.id = a.course_id
            WHERE c.lecturer_id = ?
            ORDER BY a.due_date ASC
            LIMIT 10
            """
        assignment_params = (user["id"],)
    elif user["role"] == "student":
        courses = conn.execute(
            """
            SELECT c.id, c.code, c.title, c.description
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.student_id = ?
            ORDER BY c.id DESC
            """,
            (user["id"],),
        ).fetchall()
        available_courses = conn.execute(
            """
            SELECT c.id, c.code, c.title
            FROM courses c
            WHERE c.id NOT IN (
                SELECT course_id FROM enrollments WHERE student_id = ?
            )
            ORDER BY c.code ASC
            """,
            (user["id"],),
        ).fetchall()
        submissions = conn.execute(
            """
            SELECT s.assignment_id, s.submitted_at, a.title, c.code AS course_code
            FROM submissions s
            JOIN assignments a ON a.id = s.assignment_id
            JOIN courses c ON c.id = a.course_id
            WHERE s.student_id = ?
            ORDER BY s.submitted_at DESC
            LIMIT 10
            """,
            (user["id"],),
        ).fetchall()
        assignments_query = """
            SELECT a.id, a.title, a.due_date, c.code as course_code
            FROM assignments a
            JOIN courses c ON c.id = a.course_id
            JOIN enrollments e ON e.course_id = c.id
            WHERE e.student_id = ?
            ORDER BY a.due_date ASC
            LIMIT 10
            """
        assignment_params = (user["id"],)
    else:
        courses = conn.execute(
            "SELECT id, code, title, description FROM courses ORDER BY id DESC"
        ).fetchall()
        manageable_courses = courses
        assignments_query = """
            SELECT a.id, a.title, a.due_date, c.code as course_code
            FROM assignments a
            JOIN courses c ON c.id = a.course_id
            ORDER BY a.due_date ASC
            LIMIT 10
            """

    assignments = conn.execute(assignments_query, assignment_params).fetchall()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "title": "Dashboard",
            "user": user,
            "courses": courses,
            "assignments": assignments,
            "available_courses": available_courses,
            "manageable_courses": manageable_courses,
            "submissions": submissions,
        },
    )


@app.post("/courses")
def create_course(
    request: Request,
    code: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
):
    user = require_user(get_current_user(request))
    require_role(user, {"lecturer", "admin"})
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO courses(code, title, description, lecturer_id) VALUES (?, ?, ?, ?)",
            (code.strip().upper(), title.strip(), description.strip(), user["id"]),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Course code already exists.")
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/courses/enroll")
def enroll_course(request: Request, course_id: int = Form(...)):
    user = require_user(get_current_user(request))
    require_role(user, {"student"})
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO enrollments(course_id, student_id) VALUES (?, ?)", (course_id, user["id"])
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Enrollment already exists or invalid course.")
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/assignments")
def create_assignment(
    request: Request,
    course_id: int = Form(...),
    title: str = Form(...),
    instructions: str = Form(...),
    due_date: str = Form(...),
):
    user = require_user(get_current_user(request))
    require_role(user, {"lecturer", "admin"})
    conn = get_connection()
    course = conn.execute(
        "SELECT id, lecturer_id FROM courses WHERE id = ?",
        (course_id,),
    ).fetchone()
    if not course:
        conn.close()
        raise HTTPException(status_code=404, detail="Course not found.")
    if user["role"] == "lecturer" and course["lecturer_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="You can only create assignments for your courses.")

    conn.execute(
        "INSERT INTO assignments(course_id, title, instructions, due_date, created_by) VALUES (?, ?, ?, ?, ?)",
        (course_id, title.strip(), instructions.strip(), due_date.strip(), user["id"]),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/submissions")
def submit_assignment(
    request: Request,
    assignment_id: int = Form(...),
    content: str = Form(...),
):
    user = require_user(get_current_user(request))
    require_role(user, {"student"})
    conn = get_connection()
    assignment = conn.execute(
        """
        SELECT a.id, a.course_id
        FROM assignments a
        WHERE a.id = ?
        """,
        (assignment_id,),
    ).fetchone()
    if not assignment:
        conn.close()
        raise HTTPException(status_code=404, detail="Assignment not found.")

    enrollment = conn.execute(
        "SELECT id FROM enrollments WHERE course_id = ? AND student_id = ?",
        (assignment["course_id"], user["id"]),
    ).fetchone()
    if not enrollment:
        conn.close()
        raise HTTPException(status_code=403, detail="You are not enrolled in this course.")

    try:
        conn.execute(
            "INSERT INTO submissions(assignment_id, student_id, content) VALUES (?, ?, ?)",
            (assignment_id, user["id"], content.strip()),
        )
    except sqlite3.IntegrityError:
        conn.execute(
            "UPDATE submissions SET content = ?, submitted_at = CURRENT_TIMESTAMP WHERE assignment_id = ? AND student_id = ?",
            (content.strip(), assignment_id, user["id"]),
        )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/api/health")
def health():
    return {"status": "ok", "system": "NUR Online Learning MVP"}
