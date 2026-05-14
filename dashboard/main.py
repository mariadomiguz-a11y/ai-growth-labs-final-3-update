"""AI Growth Labs — Agency Operating System Dashboard v3"""
import os
import json
import secrets
import io
import csv
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional
from functools import wraps

from fastapi import FastAPI, Request, Form, HTTPException, Depends, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from jose import jwt
from passlib.hash import bcrypt

from database import get_db, init_db

app = FastAPI(title="AI Growth Labs OS", docs_url=None, redoc_url=None)

# Security: Rate limiting storage
_rate_limit_store = {}

SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
TOKEN_EXPIRE = 24
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

@app.on_event("startup")
def startup():
    init_db()

# ===== AUTH =====
def create_token(user_id: int, role: str, username: str):
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE)
    return jwt.encode({"sub": str(user_id), "role": role, "username": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id=? AND is_active=1", (payload["sub"],)).fetchone()
        db.close()
        return dict(user) if user else None
    except Exception:
        return None

def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user

def require_role(request: Request, roles: list):
    user = require_auth(request)
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="Access denied")
    return user

# ===== LOGIN =====
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,)).fetchone()
    db.close()
    if not user or not bcrypt.verify(password, user["password_hash"]):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    token = create_token(user["id"], user["role"], user["username"])
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("token", token, httponly=True, max_age=TOKEN_EXPIRE*3600)
    db = get_db()
    db.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user["id"],))
    db.commit()
    db.close()
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("token")
    return response

# ===== SECURITY: Rate Limiting =====
def rate_limit(key_prefix: str, max_requests: int = 10, window_seconds: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            key = f"{key_prefix}:{client_ip}"
            now = time.time()
            if key in _rate_limit_store:
                requests_list = [t for t in _rate_limit_store[key] if now - t < window_seconds]
                if len(requests_list) >= max_requests:
                    raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
                requests_list.append(now)
                _rate_limit_store[key] = requests_list
            else:
                _rate_limit_store[key] = [now]
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def log_activity(db, user_id, action, details=None, entity_type=None, entity_id=None):
    db.execute("INSERT INTO activity_log (user_id, action, details, entity_type, entity_id) VALUES (?,?,?,?,?)",
               (user_id, action, details, entity_type, entity_id))

# ===== DASHBOARD ROUTER =====
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = get_current_user(request)
    if user:
        if user["role"] == "client":
            return RedirectResponse(url="/client-portal")
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    if user["role"] == "client":
        return RedirectResponse(url="/client-portal")
    role = user["role"]
    db = get_db()
    if role == "super_admin":
        data = _get_admin_data(db)
        template = "admin_dashboard.html"
    elif role == "operations_manager":
        data = _get_ops_manager_data(db)
        template = "ops_dashboard.html"
    elif role in ("worker", "tech_seo", "content_writer", "link_builder"):
        data = _get_worker_data(db, user["id"])
        template = "worker_dashboard.html"
    elif role in ("sales", "account_manager"):
        data = _get_sales_data(db, user["id"])
        template = "sales_dashboard.html"
    elif role == "social_media":
        data = _get_social_data(db, user["id"])
        template = "social_dashboard.html"
    elif role == "finance":
        data = _get_finance_data(db)
        template = "finance_dashboard.html"
    else:
        data = {}
        template = "worker_dashboard.html"
    db.close()
    data["user"] = user
    data["request"] = request
    return templates.TemplateResponse(template, data)

# ===== SETTINGS PAGE =====
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = get_current_user(request)
    if not user or user["role"] != "super_admin":
        return RedirectResponse(url="/login")
    db = get_db()
    api_settings = [dict(r) for r in db.execute("SELECT * FROM api_settings ORDER BY provider").fetchall()]
    db.close()
    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "api_settings": api_settings})

# ===== CLIENT DETAIL PAGE =====
@app.get("/client/{client_id}", response_class=HTMLResponse)
async def client_detail(client_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if not client:
        db.close()
        raise HTTPException(status_code=404, detail="Client not found")
    client = dict(client)
    credentials = [dict(r) for r in db.execute("SELECT * FROM client_credentials WHERE client_id=?", (client_id,)).fetchall()]
    projects = [dict(r) for r in db.execute("""
        SELECT p.*, u.full_name as worker_name, tl.full_name as leader_name
        FROM projects p LEFT JOIN users u ON p.assigned_worker_id=u.id LEFT JOIN users tl ON p.team_leader_id=tl.id
        WHERE p.client_id=? ORDER BY p.created_at DESC
    """, (client_id,)).fetchall()]
    tasks_by_project = {}
    for p in projects:
        tasks_by_project[p["id"]] = [dict(r) for r in db.execute("""
            SELECT t.*, u.full_name as assigned_name FROM tasks t LEFT JOIN users u ON t.assigned_to=u.id
            WHERE t.project_id=? ORDER BY t.order_num
        """, (p["id"],)).fetchall()]
    payments = [dict(r) for r in db.execute("SELECT * FROM payments WHERE client_id=? ORDER BY created_at DESC", (client_id,)).fetchall()]
    reports = [dict(r) for r in db.execute("SELECT * FROM client_reports WHERE client_id=? ORDER BY created_at DESC", (client_id,)).fetchall()]
    package_tasks = []
    if client.get("package"):
        package_tasks = [dict(r) for r in db.execute("SELECT * FROM package_tasks WHERE package=? ORDER BY category, order_num", (client["package"],)).fetchall()]
    db.close()
    return templates.TemplateResponse("client_detail.html", {
        "request": request, "user": user, "client": client, "credentials": credentials,
        "projects": projects, "tasks_by_project": tasks_by_project, "payments": payments,
        "reports": reports, "package_tasks": package_tasks
    })

# ===== CLIENT PORTAL =====
@app.get("/client-portal", response_class=HTMLResponse)
async def client_portal(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    if user["role"] != "client":
        return RedirectResponse(url="/dashboard")
    db = get_db()
    # Find client record linked to this user
    client = db.execute("SELECT * FROM clients WHERE email=?", (user["email"],)).fetchone()
    if not client:
        # Fallback: try to find by username match
        client = db.execute("SELECT * FROM clients WHERE contact_name=?", (user["full_name"],)).fetchone()
    data = {"user": user, "request": request}
    if client:
        client = dict(client)
        data["client"] = client
        projects = [dict(r) for r in db.execute("""
            SELECT p.*, u.full_name as worker_name FROM projects p 
            LEFT JOIN users u ON p.assigned_worker_id=u.id WHERE p.client_id=? ORDER BY p.created_at DESC
        """, (client["id"],)).fetchall()]
        data["projects"] = projects
        tasks_all = []
        for p in projects:
            tasks_all += [dict(r) for r in db.execute("SELECT * FROM tasks WHERE project_id=? ORDER BY order_num", (p["id"],)).fetchall()]
        data["tasks"] = tasks_all
        data["reports"] = [dict(r) for r in db.execute("SELECT * FROM client_reports WHERE client_id=? AND sent_to_client=1 ORDER BY created_at DESC", (client["id"],)).fetchall()]
        data["invoices"] = [dict(r) for r in db.execute("SELECT * FROM invoices WHERE client_id=? ORDER BY created_at DESC", (client["id"],)).fetchall()]
        data["rankings"] = [dict(r) for r in db.execute("SELECT * FROM keyword_rankings WHERE client_id=? ORDER BY tracked_date DESC LIMIT 50", (client["id"],)).fetchall()]
        data["approvals"] = [dict(r) for r in db.execute("SELECT * FROM approval_requests WHERE client_id=? ORDER BY created_at DESC", (client["id"],)).fetchall()]
        total_tasks = len(tasks_all)
        completed = sum(1 for t in tasks_all if t["status"] == "completed")
        data["stats"] = {
            "total_projects": len(projects),
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "completion_pct": round(completed/total_tasks*100) if total_tasks else 0,
            "pending_approvals": sum(1 for a in data["approvals"] if a["status"] == "pending"),
        }
    else:
        data["client"] = None
        data["projects"] = []
        data["tasks"] = []
        data["reports"] = []
        data["invoices"] = []
        data["rankings"] = []
        data["approvals"] = []
        data["stats"] = {"total_projects": 0, "total_tasks": 0, "completed_tasks": 0, "completion_pct": 0, "pending_approvals": 0}
    db.close()
    return templates.TemplateResponse("client_portal.html", data)

# ===== TEAM MONITOR PAGE (Admin) =====
@app.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request):
    user = get_current_user(request)
    if not user or user["role"] not in ("super_admin", "operations_manager"):
        return RedirectResponse(url="/login")
    db = get_db()
    workers = [dict(r) for r in db.execute("SELECT * FROM users WHERE role != 'super_admin' AND is_active=1 ORDER BY role, full_name").fetchall()]
    for w in workers:
        w["active_tasks"] = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='in_progress'", (w["id"],)).fetchone()[0]
        w["pending_tasks"] = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='pending'", (w["id"],)).fetchone()[0]
        w["completed_tasks"] = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='completed'", (w["id"],)).fetchone()[0]
        w["total_tasks"] = w["active_tasks"] + w["pending_tasks"] + w["completed_tasks"]
        w["projects"] = [dict(r) for r in db.execute("""
            SELECT p.title, p.progress, p.status, c.business_name FROM projects p 
            LEFT JOIN clients c ON p.client_id=c.id WHERE p.assigned_worker_id=? OR p.team_leader_id=?
        """, (w["id"], w["id"])).fetchall()]
    suggestions = [dict(r) for r in db.execute("""
        SELECT s.*, u.full_name as author_name, p.title as project_title 
        FROM suggestions s LEFT JOIN users u ON s.user_id=u.id LEFT JOIN projects p ON s.project_id=p.id
        ORDER BY s.created_at DESC LIMIT 20
    """).fetchall()]
    chat_requests = [dict(r) for r in db.execute("""
        SELECT cr.*, u.full_name as from_name FROM chat_requests cr 
        LEFT JOIN users u ON cr.from_user_id=u.id WHERE cr.status='pending' ORDER BY cr.created_at DESC
    """).fetchall()]
    db.close()
    return templates.TemplateResponse("monitor.html", {
        "request": request, "user": user, "workers": workers, 
        "suggestions": suggestions, "chat_requests": chat_requests
    })

# ===== CHAT PAGE =====
@app.get("/team-chat", response_class=HTMLResponse)
async def team_chat_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    db = get_db()
    team_members = [dict(r) for r in db.execute("SELECT id, full_name, role, username FROM users WHERE id!=? AND is_active=1 ORDER BY full_name", (user["id"],)).fetchall()]
    # Get approved chat sessions
    approved = [dict(r) for r in db.execute("""
        SELECT cr.*, u1.full_name as from_name, u2.full_name as to_name 
        FROM chat_requests cr 
        LEFT JOIN users u1 ON cr.from_user_id=u1.id LEFT JOIN users u2 ON cr.to_user_id=u2.id
        WHERE cr.status='approved' AND (cr.from_user_id=? OR cr.to_user_id=?)
    """, (user["id"], user["id"])).fetchall()]
    db.close()
    return templates.TemplateResponse("team_chat.html", {
        "request": request, "user": user, "team_members": team_members, "approved_chats": approved
    })

# ===== DATA HELPERS =====
def _get_admin_data(db):
    clients = [dict(r) for r in db.execute("SELECT * FROM clients ORDER BY created_at DESC").fetchall()]
    projects = [dict(r) for r in db.execute("""
        SELECT p.*, c.business_name, c.contact_name, u.full_name as worker_name, tl.full_name as leader_name
        FROM projects p LEFT JOIN clients c ON p.client_id=c.id 
        LEFT JOIN users u ON p.assigned_worker_id=u.id LEFT JOIN users tl ON p.team_leader_id=tl.id
        ORDER BY p.created_at DESC
    """).fetchall()]
    workers = [dict(r) for r in db.execute("SELECT * FROM users WHERE role != 'super_admin' ORDER BY role, full_name").fetchall()]
    tasks = [dict(r) for r in db.execute("""
        SELECT t.*, u.full_name as assigned_name, p.title as project_title
        FROM tasks t LEFT JOIN users u ON t.assigned_to=u.id LEFT JOIN projects p ON t.project_id=p.id
        ORDER BY t.created_at DESC LIMIT 50
    """).fetchall()]
    payments = [dict(r) for r in db.execute("""
        SELECT pay.*, c.business_name FROM payments pay LEFT JOIN clients c ON pay.client_id=c.id ORDER BY pay.created_at DESC
    """).fetchall()]
    suggestions = [dict(r) for r in db.execute("""
        SELECT s.*, u.full_name as author_name, p.title as project_title
        FROM suggestions s LEFT JOIN users u ON s.user_id=u.id LEFT JOIN projects p ON s.project_id=p.id
        ORDER BY s.created_at DESC LIMIT 10
    """).fetchall()]
    chat_requests = [dict(r) for r in db.execute("""
        SELECT cr.*, u.full_name as from_name FROM chat_requests cr 
        LEFT JOIN users u ON cr.from_user_id=u.id WHERE cr.status='pending' ORDER BY cr.created_at DESC
    """).fetchall()]
    unread_chats = db.execute("SELECT COUNT(*) FROM team_chats WHERE to_user_id=1 AND is_read=0").fetchone()[0]
    
    total_revenue = db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid'").fetchone()[0]
    pending_revenue = db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status IN ('pending','overdue')").fetchone()[0]
    active_clients = db.execute("SELECT COUNT(*) FROM clients WHERE status='active'").fetchone()[0]
    active_projects = db.execute("SELECT COUNT(*) FROM projects WHERE status='in_progress'").fetchone()[0]
    total_tasks = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    completed_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status='completed'").fetchone()[0]
    
    return {
        "clients": clients, "projects": projects, "workers": workers, "tasks": tasks, "payments": payments,
        "suggestions": suggestions, "chat_requests": chat_requests, "unread_chats": unread_chats,
        "stats": {
            "total_revenue": total_revenue, "pending_revenue": pending_revenue,
            "active_clients": active_clients, "active_projects": active_projects,
            "total_tasks": total_tasks, "completed_tasks": completed_tasks,
            "task_completion": round(completed_tasks/total_tasks*100) if total_tasks else 0,
            "monthly_recurring": db.execute("SELECT COALESCE(SUM(monthly_payment),0) FROM clients WHERE status='active'").fetchone()[0]
        }
    }

def _get_worker_data(db, user_id):
    my_tasks = [dict(r) for r in db.execute("""
        SELECT t.*, p.title as project_title, c.business_name 
        FROM tasks t LEFT JOIN projects p ON t.project_id=p.id LEFT JOIN clients c ON p.client_id=c.id
        WHERE t.assigned_to=? ORDER BY CASE t.priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, t.order_num
    """, (user_id,)).fetchall()]
    my_projects = [dict(r) for r in db.execute("""
        SELECT p.*, c.business_name, c.website, c.industry, c.location, c.package
        FROM projects p LEFT JOIN clients c ON p.client_id=c.id 
        WHERE p.assigned_worker_id=? OR p.team_leader_id=? ORDER BY p.created_at DESC
    """, (user_id, user_id)).fetchall()]
    notifications = [dict(r) for r in db.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,)).fetchall()]
    audits = [dict(r) for r in db.execute(
        "SELECT a.*, c.business_name FROM seo_audits a LEFT JOIN clients c ON a.client_id=c.id ORDER BY a.created_at DESC LIMIT 10").fetchall()]
    suggestions = [dict(r) for r in db.execute(
        "SELECT s.*, p.title as project_title FROM suggestions s LEFT JOIN projects p ON s.project_id=p.id WHERE s.user_id=? ORDER BY s.created_at DESC", (user_id,)).fetchall()]
    unread_chats = db.execute("SELECT COUNT(*) FROM team_chats WHERE to_user_id=? AND is_read=0", (user_id,)).fetchone()[0]
    
    total = len(my_tasks)
    completed = sum(1 for t in my_tasks if t["status"] == "completed")
    
    return {
        "my_tasks": my_tasks, "my_projects": my_projects, "notifications": notifications, 
        "audits": audits, "suggestions": suggestions, "unread_chats": unread_chats,
        "stats": {
            "total_tasks": total, "completed_tasks": completed, "pending_tasks": total - completed,
            "completion_pct": round(completed/total*100) if total else 0,
            "active_projects": sum(1 for p in my_projects if p["status"] == "in_progress"),
        }
    }

def _get_sales_data(db, user_id):
    leads = [dict(r) for r in db.execute("SELECT * FROM sales_leads ORDER BY created_at DESC").fetchall()]
    recent_clients = [dict(r) for r in db.execute("SELECT * FROM clients ORDER BY created_at DESC LIMIT 10").fetchall()]
    total_leads = len(leads)
    new_leads = sum(1 for l in leads if l["status"] == "new")
    won_leads = sum(1 for l in leads if l["status"] == "won")
    return {
        "leads": leads, "recent_clients": recent_clients,
        "stats": {
            "total_leads": total_leads, "new_leads": new_leads, "won_leads": won_leads,
            "conversion_rate": round(won_leads/total_leads*100) if total_leads else 0,
            "proposals_sent": sum(1 for l in leads if l["status"] == "proposal_sent"),
        }
    }

def _get_social_data(db, user_id):
    posts = [dict(r) for r in db.execute("""
        SELECT sp.*, c.business_name FROM social_posts sp LEFT JOIN clients c ON sp.client_id=c.id ORDER BY sp.created_at DESC LIMIT 50
    """).fetchall()]
    clients = [dict(r) for r in db.execute("SELECT * FROM clients WHERE status='active' ORDER BY business_name").fetchall()]
    # Parse engagement data
    total_likes = 0
    total_comments = 0
    total_shares = 0
    total_reach = 0
    for p in posts:
        if p.get("engagement_data"):
            try:
                eng = json.loads(p["engagement_data"])
                total_likes += eng.get("likes", 0)
                total_comments += eng.get("comments", 0)
                total_shares += eng.get("shares", 0)
                total_reach += eng.get("reach", 0)
            except Exception:
                pass
    return {
        "posts": posts, "clients": clients,
        "stats": {
            "total_posts": len(posts),
            "scheduled": sum(1 for p in posts if p["status"] == "scheduled"),
            "published": sum(1 for p in posts if p["status"] == "published"),
            "drafts": sum(1 for p in posts if p["status"] == "draft"),
            "total_likes": total_likes, "total_comments": total_comments,
            "total_shares": total_shares, "total_reach": total_reach,
        }
    }

def _get_finance_data(db):
    payments = [dict(r) for r in db.execute("""
        SELECT pay.*, c.business_name FROM payments pay LEFT JOIN clients c ON pay.client_id=c.id ORDER BY pay.created_at DESC
    """).fetchall()]
    expenses = [dict(r) for r in db.execute("SELECT * FROM expenses ORDER BY date DESC").fetchall()]
    workers = [dict(r) for r in db.execute("SELECT id, full_name, role, rank, salary FROM users WHERE role != 'super_admin'").fetchall()]
    total_income = sum(p["amount"] for p in payments if p["status"] == "paid")
    total_expenses = sum(e["amount"] for e in expenses)
    pending_payments = sum(p["amount"] for p in payments if p["status"] in ("pending", "overdue"))
    total_salaries = sum(w["salary"] for w in workers)
    return {
        "payments": payments, "expenses": expenses, "workers": workers,
        "stats": {
            "total_income": total_income, "total_expenses": total_expenses,
            "net_profit": total_income - total_expenses, "pending_payments": pending_payments,
            "total_salaries": total_salaries,
            "tools_cost": sum(e["amount"] for e in expenses if e["category"] == "tools"),
        }
    }

# ===== API ENDPOINTS =====
@app.post("/api/clients")
async def create_client(request: Request):
    user = require_role(request, ["super_admin", "sales"])
    data = await request.json()
    db = get_db()
    c = db.cursor()
    c.execute("""INSERT INTO clients (business_name, contact_name, email, phone, website, industry, location, status, package, monthly_payment, notes, source)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
              (data.get("business_name"), data.get("contact_name"), data.get("email"), data.get("phone"),
               data.get("website"), data.get("industry"), data.get("location"), data.get("status", "lead"),
               data.get("package"), data.get("monthly_payment", 0), data.get("notes"), data.get("source")))
    client_id = c.lastrowid
    # Auto-generate package tasks if package selected
    if data.get("package"):
        _auto_generate_package_tasks(db, client_id, data["package"])
    db.commit()
    db.close()
    return {"id": client_id, "message": "Client created"}

def _auto_generate_package_tasks(db, client_id, package):
    """Auto-generate tasks from package template when client is created"""
    pkg_tasks = db.execute("SELECT * FROM package_tasks WHERE package=? ORDER BY category, order_num", (package,)).fetchall()
    # Create a project for this client
    c = db.cursor()
    c.execute("""INSERT INTO projects (client_id, title, description, service_type, status, priority)
                 VALUES (?,?,?,?,?,?)""",
              (client_id, f"{package} Campaign", f"Auto-generated {package} project", "Full Service", "pending", "high"))
    project_id = c.lastrowid
    for i, pt in enumerate(pkg_tasks):
        c.execute("""INSERT INTO tasks (project_id, title, description, status, priority, order_num, is_automated)
                     VALUES (?,?,?,?,?,?,?)""",
                  (project_id, pt["title"], pt["description"], "pending", "medium", i, pt["is_automated"]))

@app.post("/api/projects")
async def create_project(request: Request):
    user = require_role(request, ["super_admin"])
    data = await request.json()
    db = get_db()
    c = db.cursor()
    c.execute("""INSERT INTO projects (client_id, title, description, service_type, status, priority, assigned_worker_id, team_leader_id, start_date, due_date)
                 VALUES (?,?,?,?,?,?,?,?,?,?)""",
              (data.get("client_id"), data.get("title"), data.get("description"), data.get("service_type"),
               data.get("status", "pending"), data.get("priority", "medium"), data.get("assigned_worker_id"),
               data.get("team_leader_id"), data.get("start_date"), data.get("due_date")))
    project_id = c.lastrowid
    if data.get("assigned_worker_id"):
        c.execute("INSERT INTO notifications (user_id, title, message, type) VALUES (?,?,?,?)",
                  (data["assigned_worker_id"], "New Project Assigned", f"You've been assigned: {data.get('title')}", "task"))
    db.commit()
    db.close()
    return {"id": project_id, "message": "Project created"}

@app.post("/api/tasks")
async def create_task(request: Request):
    user = require_role(request, ["super_admin", "worker", "tech_seo"])
    data = await request.json()
    db = get_db()
    c = db.cursor()
    c.execute("""INSERT INTO tasks (project_id, title, description, status, assigned_to, priority, due_date, order_num)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (data.get("project_id"), data.get("title"), data.get("description"),
               data.get("status", "pending"), data.get("assigned_to"), data.get("priority", "medium"),
               data.get("due_date"), data.get("order_num", 0)))
    task_id = c.lastrowid
    if data.get("assigned_to"):
        c.execute("INSERT INTO notifications (user_id, title, message, type) VALUES (?,?,?,?)",
                  (data["assigned_to"], "New Task", f"Task: {data.get('title')}", "task"))
    db.commit()
    db.close()
    return {"id": task_id, "message": "Task created"}

@app.put("/api/tasks/{task_id}/status")
async def update_task_status(task_id: int, request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    db.execute("UPDATE tasks SET status=?, completed_date=CASE WHEN ?='completed' THEN datetime('now') ELSE NULL END WHERE id=?",
               (data["status"], data["status"], task_id))
    task = db.execute("SELECT project_id FROM tasks WHERE id=?", (task_id,)).fetchone()
    if task:
        pid = task["project_id"]
        total = db.execute("SELECT COUNT(*) FROM tasks WHERE project_id=?", (pid,)).fetchone()[0]
        done = db.execute("SELECT COUNT(*) FROM tasks WHERE project_id=? AND status='completed'", (pid,)).fetchone()[0]
        progress = round(done/total*100) if total else 0
        db.execute("UPDATE projects SET progress=?, updated_at=datetime('now') WHERE id=?", (progress, pid))
    db.commit()
    db.close()
    return {"message": "Task updated"}

@app.post("/api/users")
async def create_user(request: Request):
    user = require_role(request, ["super_admin"])
    data = await request.json()
    db = get_db()
    pw_hash = bcrypt.hash(data.get("password", "changeme123"))
    try:
        db.execute("""INSERT INTO users (username, password_hash, full_name, email, role, rank, salary) VALUES (?,?,?,?,?,?,?)""",
                   (data["username"], pw_hash, data["full_name"], data.get("email"), data["role"], data.get("rank", "junior"), data.get("salary", 0)))
        db.commit()
    except Exception as e:
        db.close()
        return JSONResponse({"error": str(e)}, status_code=400)
    db.close()
    return {"message": "User created"}

@app.post("/api/leads")
async def create_lead(request: Request):
    user = require_role(request, ["super_admin", "sales"])
    data = await request.json()
    db = get_db()
    db.execute("""INSERT INTO sales_leads (business_name, contact_name, email, phone, website, industry, location, source, status, assigned_to, notes)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
               (data.get("business_name"), data.get("contact_name"), data.get("email"), data.get("phone"),
                data.get("website"), data.get("industry"), data.get("location"), data.get("source", "other"),
                data.get("status", "new"), data.get("assigned_to"), data.get("notes")))
    db.commit()
    db.close()
    return {"message": "Lead created"}

@app.put("/api/leads/{lead_id}/status")
async def update_lead_status(lead_id: int, request: Request):
    user = require_role(request, ["super_admin", "sales"])
    data = await request.json()
    db = get_db()
    db.execute("UPDATE sales_leads SET status=?, updated_at=datetime('now') WHERE id=?", (data["status"], lead_id))
    db.commit()
    db.close()
    return {"message": "Lead updated"}

@app.post("/api/social-posts")
async def create_social_post(request: Request):
    user = require_role(request, ["super_admin", "social_media"])
    data = await request.json()
    db = get_db()
    db.execute("""INSERT INTO social_posts (client_id, platform, content, status, scheduled_date, created_by)
                  VALUES (?,?,?,?,?,?)""",
               (data.get("client_id"), data.get("platform"), data.get("content"),
                data.get("status", "draft"), data.get("scheduled_date"), user["id"]))
    db.commit()
    db.close()
    return {"message": "Post created"}

@app.post("/api/audit")
async def create_audit(request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    c = db.cursor()
    c.execute("""INSERT INTO seo_audits (client_id, website_url, status, ai_provider, created_by) VALUES (?,?,?,?,?)""",
              (data.get("client_id"), data["website_url"], "pending", data.get("ai_provider", "claude"), user["id"]))
    audit_id = c.lastrowid
    db.commit()
    db.close()
    return {"id": audit_id, "message": "Audit created — processing will begin when AI API key is configured"}

@app.post("/api/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    db.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (notif_id, user["id"]))
    db.commit()
    db.close()
    return {"message": "Marked as read"}

@app.post("/api/expenses")
async def create_expense(request: Request):
    user = require_role(request, ["super_admin", "finance"])
    data = await request.json()
    db = get_db()
    db.execute("""INSERT INTO expenses (category, description, amount, date, approved_by) VALUES (?,?,?,?,?)""",
               (data["category"], data["description"], data["amount"], data.get("date"), user["id"]))
    db.commit()
    db.close()
    return {"message": "Expense recorded"}

# ===== NEW API ENDPOINTS =====

# Client Credentials
@app.post("/api/client-credentials")
async def add_client_credential(request: Request):
    user = require_role(request, ["super_admin", "sales", "worker", "tech_seo"])
    data = await request.json()
    db = get_db()
    db.execute("""INSERT INTO client_credentials (client_id, credential_type, label, username, password_enc, api_key, access_url, notes, added_by)
                  VALUES (?,?,?,?,?,?,?,?,?)""",
               (data["client_id"], data["credential_type"], data.get("label"), data.get("username"),
                data.get("password_enc"), data.get("api_key"), data.get("access_url"), data.get("notes"), user["id"]))
    db.commit()
    db.close()
    return {"message": "Credential saved"}

# API Settings
@app.post("/api/settings/api")
async def update_api_setting(request: Request):
    user = require_role(request, ["super_admin"])
    data = await request.json()
    db = get_db()
    db.execute("""UPDATE api_settings SET api_key=?, is_active=?, config_json=?, updated_by=?, updated_at=datetime('now')
                  WHERE provider=?""",
               (data.get("api_key"), 1 if data.get("api_key") else 0, data.get("config_json"), user["id"], data["provider"]))
    db.commit()
    db.close()
    return {"message": f"{data['provider']} settings updated"}

# Suggestions
@app.post("/api/suggestions")
async def create_suggestion(request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    db.execute("""INSERT INTO suggestions (user_id, project_id, title, description) VALUES (?,?,?,?)""",
               (user["id"], data.get("project_id"), data["title"], data.get("description")))
    db.commit()
    db.close()
    return {"message": "Suggestion submitted"}

@app.put("/api/suggestions/{sugg_id}")
async def update_suggestion(sugg_id: int, request: Request):
    user = require_role(request, ["super_admin"])
    data = await request.json()
    db = get_db()
    db.execute("UPDATE suggestions SET status=?, admin_response=? WHERE id=?", (data["status"], data.get("admin_response"), sugg_id))
    db.commit()
    db.close()
    return {"message": "Suggestion updated"}

# Chat Requests
@app.post("/api/chat-request")
async def create_chat_request(request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    to_id = data["to_user_id"]
    db.execute("INSERT INTO chat_requests (from_user_id, to_user_id) VALUES (?,?)", (user["id"], to_id))
    db.execute("INSERT INTO notifications (user_id, title, message, type) VALUES (?,?,?,?)",
               (to_id, "Chat Request", f"{user['full_name']} wants to chat with you", "chat_request"))
    db.commit()
    db.close()
    return {"message": "Chat request sent"}

@app.put("/api/chat-request/{req_id}")
async def update_chat_request(req_id: int, request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    db.execute("UPDATE chat_requests SET status=?, resolved_at=datetime('now') WHERE id=?", (data["status"], req_id))
    db.commit()
    db.close()
    return {"message": f"Chat request {data['status']}"}

# Team Chat Messages
@app.get("/api/chat-messages/{other_user_id}")
async def get_chat_messages(other_user_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    messages = [dict(r) for r in db.execute("""
        SELECT tc.*, u.full_name as sender_name FROM team_chats tc 
        LEFT JOIN users u ON tc.from_user_id=u.id
        WHERE (tc.from_user_id=? AND tc.to_user_id=?) OR (tc.from_user_id=? AND tc.to_user_id=?)
        ORDER BY tc.created_at ASC LIMIT 100
    """, (user["id"], other_user_id, other_user_id, user["id"])).fetchall()]
    db.execute("UPDATE team_chats SET is_read=1 WHERE to_user_id=? AND from_user_id=?", (user["id"], other_user_id))
    db.commit()
    db.close()
    return {"messages": messages}

@app.post("/api/chat-messages")
async def send_chat_message(request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    db.execute("INSERT INTO team_chats (from_user_id, to_user_id, message) VALUES (?,?,?)",
               (user["id"], data["to_user_id"], data["message"]))
    db.commit()
    db.close()
    return {"message": "Sent"}

# Generate PDF Report
@app.post("/api/reports/generate")
async def generate_report(request: Request):
    user = require_role(request, ["super_admin", "finance", "worker", "tech_seo"])
    data = await request.json()
    client_id = data["client_id"]
    db = get_db()
    client = dict(db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone())
    projects = [dict(r) for r in db.execute("SELECT * FROM projects WHERE client_id=?", (client_id,)).fetchall()]
    tasks_all = []
    for p in projects:
        tasks_all += [dict(r) for r in db.execute("SELECT * FROM tasks WHERE project_id=?", (p["id"],)).fetchall()]
    payments = [dict(r) for r in db.execute("SELECT * FROM payments WHERE client_id=?", (client_id,)).fetchall()]
    
    report_data = json.dumps({
        "client": client, "projects": projects, "tasks": tasks_all, "payments": payments,
        "generated_at": datetime.now().isoformat(), "generated_by": user["full_name"]
    })
    
    c = db.cursor()
    c.execute("""INSERT INTO client_reports (client_id, report_type, title, report_data, created_by) VALUES (?,?,?,?,?)""",
              (client_id, data.get("report_type", "monthly"), f"Report - {client['business_name']} - {datetime.now().strftime('%B %Y')}",
               report_data, user["id"]))
    report_id = c.lastrowid
    db.commit()
    db.close()
    return {"id": report_id, "message": "Report generated"}

# Download report as HTML
@app.get("/api/reports/{report_id}/download")
async def download_report(report_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    report = db.execute("SELECT r.*, c.business_name FROM client_reports r LEFT JOIN clients c ON r.client_id=c.id WHERE r.id=?", (report_id,)).fetchone()
    db.close()
    if not report:
        raise HTTPException(status_code=404)
    report = dict(report)
    rdata = json.loads(report["report_data"]) if report["report_data"] else {}
    client = rdata.get("client", {})
    projects = rdata.get("projects", [])
    tasks = rdata.get("tasks", [])
    payments = rdata.get("payments", [])
    
    completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
    total_tasks = len(tasks)
    total_paid = sum(p.get("amount", 0) for p in payments if p.get("status") == "paid")
    
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{report['title']}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Inter,sans-serif;background:#fff;color:#333;padding:40px}}
.header{{background:linear-gradient(135deg,#0A1628,#1E3A5F);color:#fff;padding:40px;border-radius:12px;margin-bottom:30px}}
.header h1{{font-size:24px;margin-bottom:8px}}.header p{{opacity:.8}}
.section{{margin-bottom:30px}}.section h2{{font-size:18px;color:#0A1628;border-bottom:2px solid #00D4FF;padding-bottom:8px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;margin-top:12px}}th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #eee}}
th{{background:#f7f9fc;font-weight:600}}.stat-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:30px}}
.stat-card{{background:#f7f9fc;padding:20px;border-radius:8px;text-align:center}}.stat-card .num{{font-size:28px;font-weight:700;color:#0A1628}}
.stat-card .label{{font-size:12px;color:#666;margin-top:4px}}.badge{{padding:3px 8px;border-radius:4px;font-size:11px;font-weight:600}}
.badge-paid{{background:#d1fae5;color:#059669}}.badge-pending{{background:#fef3c7;color:#d97706}}.badge-completed{{background:#d1fae5;color:#059669}}
.badge-progress{{background:#dbeafe;color:#2563eb}}.footer{{margin-top:40px;padding-top:20px;border-top:2px solid #eee;text-align:center;color:#999;font-size:12px}}
@media print{{body{{padding:20px}}.header{{break-after:avoid}}}}
</style></head><body>
<div class="header"><h1>AI Growth Labs — Client Report</h1><p>{report['title']}</p><p>Generated: {rdata.get('generated_at','')[:10]} | By: {rdata.get('generated_by','System')}</p></div>
<div class="stat-grid">
<div class="stat-card"><div class="num">{len(projects)}</div><div class="label">Active Projects</div></div>
<div class="stat-card"><div class="num">{completed_tasks}/{total_tasks}</div><div class="label">Tasks Completed</div></div>
<div class="stat-card"><div class="num">{round(completed_tasks/total_tasks*100) if total_tasks else 0}%</div><div class="label">Completion Rate</div></div>
<div class="stat-card"><div class="num">${total_paid:,.0f}</div><div class="label">Total Invested</div></div>
</div>
<div class="section"><h2>Client Information</h2><table>
<tr><td><strong>Business</strong></td><td>{client.get('business_name','')}</td><td><strong>Package</strong></td><td>{client.get('package','')}</td></tr>
<tr><td><strong>Contact</strong></td><td>{client.get('contact_name','')}</td><td><strong>Industry</strong></td><td>{client.get('industry','')}</td></tr>
<tr><td><strong>Website</strong></td><td>{client.get('website','')}</td><td><strong>Location</strong></td><td>{client.get('location','')}</td></tr>
</table></div>
<div class="section"><h2>Projects Overview</h2><table><thead><tr><th>Project</th><th>Service</th><th>Progress</th><th>Status</th></tr></thead><tbody>"""
    for p in projects:
        badge = "badge-completed" if p.get("status") == "completed" else "badge-progress"
        html += f'<tr><td>{p.get("title","")}</td><td>{p.get("service_type","")}</td><td>{p.get("progress",0)}%</td><td><span class="badge {badge}">{p.get("status","")}</span></td></tr>'
    html += """</tbody></table></div>
<div class="section"><h2>Task Breakdown</h2><table><thead><tr><th>Task</th><th>Priority</th><th>Status</th></tr></thead><tbody>"""
    for t in tasks:
        badge = "badge-completed" if t.get("status") == "completed" else ("badge-progress" if t.get("status") == "in_progress" else "badge-pending")
        html += f'<tr><td>{t.get("title","")}</td><td>{t.get("priority","")}</td><td><span class="badge {badge}">{t.get("status","")}</span></td></tr>'
    html += """</tbody></table></div>
<div class="section"><h2>Payment History</h2><table><thead><tr><th>Invoice</th><th>Amount</th><th>Due Date</th><th>Status</th></tr></thead><tbody>"""
    for pay in payments:
        badge = "badge-paid" if pay.get("status") == "paid" else "badge-pending"
        html += f'<tr><td>{pay.get("invoice_number","")}</td><td>${pay.get("amount",0):,.0f}</td><td>{pay.get("due_date","")}</td><td><span class="badge {badge}">{pay.get("status","")}</span></td></tr>'
    html += f"""</tbody></table></div>
<div class="footer"><p>AI Growth Labs | AI-Powered SEO &amp; Reputation Management Agency</p><p>This report is confidential and prepared exclusively for {client.get('business_name','')}.</p></div>
</body></html>"""
    
    return HTMLResponse(content=html)

# Mark report as sent
@app.post("/api/reports/{report_id}/send")
async def send_report(report_id: int, request: Request):
    user = require_role(request, ["super_admin", "finance"])
    db = get_db()
    db.execute("UPDATE client_reports SET sent_to_client=1, sent_date=datetime('now'), sent_by=? WHERE id=?", (user["id"], report_id))
    db.commit()
    db.close()
    return {"message": "Report marked as sent to client"}

# Run automated DNA task
@app.post("/api/tasks/{task_id}/run-auto")
async def run_automated_task(task_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    task = db.execute("SELECT t.*, p.client_id FROM tasks t LEFT JOIN projects p ON t.project_id=p.id WHERE t.id=?", (task_id,)).fetchone()
    if not task:
        db.close()
        raise HTTPException(status_code=404)
    task = dict(task)
    
    # Get client website
    client = db.execute("SELECT * FROM clients WHERE id=?", (task["client_id"],)).fetchone()
    client_url = dict(client)["website"] if client else ""
    
    # Get API settings
    api = db.execute("SELECT * FROM api_settings WHERE is_active=1 LIMIT 1").fetchone()
    
    if not api or not api["api_key"]:
        db.close()
        return JSONResponse({"error": "No AI API key configured. Go to Settings to add one."}, status_code=400)
    
    # For now, store that automation was triggered
    db.execute("UPDATE tasks SET status='in_progress', auto_result=? WHERE id=?",
               (json.dumps({"status": "triggered", "provider": api["provider"], "url": client_url, "triggered_at": datetime.now().isoformat()}), task_id))
    db.commit()
    db.close()
    return {"message": f"Automated task triggered using {api['provider']}. Results will appear when processing completes.", "provider": api["provider"]}

# Website chatbot API
@app.post("/api/chat")
async def save_chat(request: Request):
    data = await request.json()
    db = get_db()
    db.execute("""INSERT INTO chat_messages (session_id, visitor_name, visitor_email, business_name, industry, location, website_url, messages, status)
                  VALUES (?,?,?,?,?,?,?,?,?)""",
               (data.get("session_id"), data.get("visitor_name"), data.get("visitor_email"),
                data.get("business_name"), data.get("industry"), data.get("location"),
                data.get("website_url"), json.dumps(data.get("messages", [])), "active"))
    db.commit()
    db.close()
    return {"message": "Chat saved"}

# ===== TIME TRACKING =====
@app.post("/api/time/start")
async def start_timer(request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    # Check for active timer
    active = db.execute("SELECT id FROM time_entries WHERE user_id=? AND end_time IS NULL", (user["id"],)).fetchone()
    if active:
        db.close()
        return JSONResponse({"error": "You already have an active timer. Stop it first."}, status_code=400)
    task = db.execute("SELECT t.*, p.id as proj_id FROM tasks t LEFT JOIN projects p ON t.project_id=p.id WHERE t.id=?", (data["task_id"],)).fetchone()
    if not task:
        db.close()
        raise HTTPException(status_code=404, detail="Task not found")
    db.execute("INSERT INTO time_entries (user_id, task_id, project_id, start_time) VALUES (?,?,?,datetime('now'))",
               (user["id"], data["task_id"], task["proj_id"]))
    db.execute("UPDATE tasks SET status='in_progress' WHERE id=? AND status='pending'", (data["task_id"],))
    log_activity(db, user["id"], "timer_started", f"Started timer on task #{data['task_id']}", "task", data["task_id"])
    db.commit()
    db.close()
    return {"message": "Timer started"}

@app.post("/api/time/stop")
async def stop_timer(request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    entry = db.execute("SELECT * FROM time_entries WHERE user_id=? AND end_time IS NULL", (user["id"],)).fetchone()
    if not entry:
        db.close()
        return JSONResponse({"error": "No active timer found"}, status_code=400)
    entry = dict(entry)
    start = datetime.fromisoformat(entry["start_time"])
    now = datetime.now()
    hours = round((now - start).total_seconds() / 3600, 2)
    db.execute("UPDATE time_entries SET end_time=datetime('now'), hours=?, notes=? WHERE id=?",
               (hours, data.get("notes", ""), entry["id"]))
    log_activity(db, user["id"], "timer_stopped", f"Logged {hours}h on task #{entry['task_id']}", "task", entry["task_id"])
    db.commit()
    db.close()
    return {"message": f"Timer stopped. {hours} hours logged.", "hours": hours}

@app.get("/api/time/active")
async def get_active_timer(request: Request):
    user = require_auth(request)
    db = get_db()
    entry = db.execute("""SELECT te.*, t.title as task_title, p.title as project_title 
        FROM time_entries te LEFT JOIN tasks t ON te.task_id=t.id LEFT JOIN projects p ON te.project_id=p.id 
        WHERE te.user_id=? AND te.end_time IS NULL""", (user["id"],)).fetchone()
    db.close()
    if entry:
        entry = dict(entry)
        start = datetime.fromisoformat(entry["start_time"])
        entry["elapsed_minutes"] = round((datetime.now() - start).total_seconds() / 60, 1)
    return {"active_timer": dict(entry) if entry else None}

@app.get("/api/time/entries")
async def get_time_entries(request: Request):
    user = require_auth(request)
    db = get_db()
    if user["role"] in ("super_admin", "operations_manager", "finance"):
        entries = [dict(r) for r in db.execute("""
            SELECT te.*, t.title as task_title, u.full_name as worker_name, p.title as project_title
            FROM time_entries te LEFT JOIN tasks t ON te.task_id=t.id LEFT JOIN users u ON te.user_id=u.id 
            LEFT JOIN projects p ON te.project_id=p.id ORDER BY te.created_at DESC LIMIT 100
        """).fetchall()]
    else:
        entries = [dict(r) for r in db.execute("""
            SELECT te.*, t.title as task_title, p.title as project_title
            FROM time_entries te LEFT JOIN tasks t ON te.task_id=t.id LEFT JOIN projects p ON te.project_id=p.id 
            WHERE te.user_id=? ORDER BY te.created_at DESC LIMIT 50
        """, (user["id"],)).fetchall()]
    db.close()
    return {"entries": entries}

# ===== INVOICE SYSTEM =====
def _generate_invoice_number(db):
    year = datetime.now().year
    month = datetime.now().month
    count = db.execute("SELECT COUNT(*) FROM invoices WHERE invoice_number LIKE ?", (f"INV-{year}-%",)).fetchone()[0]
    return f"INV-{year}-{count+1:04d}"

@app.post("/api/invoices")
async def create_invoice(request: Request):
    user = require_role(request, ["super_admin", "finance"])
    data = await request.json()
    db = get_db()
    inv_num = _generate_invoice_number(db)
    items = data.get("items", [])
    subtotal = sum(item.get("quantity", 1) * item.get("rate", 0) for item in items)
    tax_rate = data.get("tax_rate", 0)
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)
    c = db.cursor()
    c.execute("""INSERT INTO invoices (client_id, invoice_number, due_date, subtotal, tax_rate, tax_amount, total, status, notes, created_by)
                 VALUES (?,?,?,?,?,?,?,?,?,?)""",
              (data["client_id"], inv_num, data.get("due_date"), subtotal, tax_rate, tax_amount, total, "draft", data.get("notes"), user["id"]))
    invoice_id = c.lastrowid
    for item in items:
        amount = round(item.get("quantity", 1) * item.get("rate", 0), 2)
        c.execute("INSERT INTO invoice_items (invoice_id, description, quantity, rate, amount) VALUES (?,?,?,?,?)",
                  (invoice_id, item["description"], item.get("quantity", 1), item.get("rate", 0), amount))
    log_activity(db, user["id"], "invoice_created", f"Invoice {inv_num} for ${total}", "invoice", invoice_id)
    db.commit()
    db.close()
    return {"id": invoice_id, "invoice_number": inv_num, "total": total}

@app.get("/api/invoices")
async def list_invoices(request: Request):
    user = require_auth(request)
    db = get_db()
    if user["role"] in ("super_admin", "finance", "operations_manager"):
        invoices = [dict(r) for r in db.execute("""
            SELECT i.*, c.business_name FROM invoices i LEFT JOIN clients c ON i.client_id=c.id ORDER BY i.created_at DESC
        """).fetchall()]
    elif user["role"] == "client":
        client = db.execute("SELECT id FROM clients WHERE email=?", (user["email"],)).fetchone()
        cid = client["id"] if client else 0
        invoices = [dict(r) for r in db.execute("SELECT * FROM invoices WHERE client_id=? ORDER BY created_at DESC", (cid,)).fetchall()]
    else:
        invoices = []
    db.close()
    return {"invoices": invoices}

@app.put("/api/invoices/{invoice_id}/status")
async def update_invoice_status(invoice_id: int, request: Request):
    user = require_role(request, ["super_admin", "finance"])
    data = await request.json()
    db = get_db()
    new_status = data["status"]
    paid_date = "datetime('now')" if new_status == "paid" else "NULL"
    if new_status == "paid":
        db.execute("UPDATE invoices SET status=?, paid_date=datetime('now'), updated_at=datetime('now') WHERE id=?", (new_status, invoice_id))
        # Auto-create payment record
        inv = db.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if inv:
            db.execute("INSERT INTO payments (client_id, amount, status, due_date, paid_date, invoice_number) VALUES (?,?,?,?,datetime('now'),?)",
                       (inv["client_id"], inv["total"], "paid", inv["due_date"], inv["invoice_number"]))
    else:
        db.execute("UPDATE invoices SET status=?, updated_at=datetime('now') WHERE id=?", (new_status, invoice_id))
    log_activity(db, user["id"], "invoice_status_updated", f"Invoice #{invoice_id} → {new_status}", "invoice", invoice_id)
    db.commit()
    db.close()
    return {"message": f"Invoice status updated to {new_status}"}

@app.get("/api/invoices/{invoice_id}/download")
async def download_invoice(invoice_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    inv = db.execute("SELECT i.*, c.business_name, c.contact_name, c.email as client_email, c.phone as client_phone, c.location as client_location FROM invoices i LEFT JOIN clients c ON i.client_id=c.id WHERE i.id=?", (invoice_id,)).fetchone()
    if not inv:
        db.close()
        raise HTTPException(status_code=404)
    inv = dict(inv)
    items = [dict(r) for r in db.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (invoice_id,)).fetchall()]
    db.close()
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Invoice {inv['invoice_number']}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Inter,sans-serif;background:#fff;color:#333;padding:40px;max-width:800px;margin:0 auto}}
.inv-header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px;padding-bottom:20px;border-bottom:3px solid #0891B2}}
.inv-logo{{font-size:24px;font-weight:800;color:#0A1628}}.inv-logo span{{color:#0891B2}}
.inv-title{{font-size:32px;font-weight:800;color:#0A1628;text-align:right}}
.inv-meta{{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-bottom:30px}}
.inv-meta h4{{color:#0891B2;font-size:12px;text-transform:uppercase;margin-bottom:8px}}
.inv-meta p{{font-size:14px;margin:3px 0}}
table{{width:100%;border-collapse:collapse;margin:20px 0}}th{{background:#0A1628;color:#fff;padding:12px;text-align:left;font-size:13px}}
td{{padding:12px;border-bottom:1px solid #eee;font-size:14px}}.text-right{{text-align:right}}
.totals{{margin-top:20px;text-align:right}}.totals div{{margin:6px 0;font-size:14px}}.totals .total{{font-size:22px;font-weight:800;color:#0A1628;border-top:2px solid #0A1628;padding-top:10px;margin-top:10px}}
.badge{{display:inline-block;padding:4px 12px;border-radius:50px;font-size:12px;font-weight:700}}
.badge-paid{{background:#d1fae5;color:#059669}}.badge-draft{{background:#e2e8f0;color:#64748b}}.badge-sent{{background:#dbeafe;color:#2563eb}}.badge-overdue{{background:#fecaca;color:#dc2626}}
.footer{{margin-top:40px;padding-top:20px;border-top:1px solid #eee;text-align:center;color:#999;font-size:12px}}
@media print{{body{{padding:20px}}}}
</style></head><body>
<div class="inv-header"><div><div class="inv-logo">AI Growth<span>Labs</span></div><p style="color:#64748b;font-size:13px">AI-Powered SEO & Reputation Management</p></div><div class="inv-title">INVOICE</div></div>
<div class="inv-meta"><div><h4>Bill To</h4><p><strong>{inv.get('business_name','')}</strong></p><p>{inv.get('contact_name','')}</p><p>{inv.get('client_email','')}</p><p>{inv.get('client_phone','')}</p><p>{inv.get('client_location','')}</p></div>
<div style="text-align:right"><h4>Invoice Details</h4><p><strong>Invoice #:</strong> {inv['invoice_number']}</p><p><strong>Issue Date:</strong> {inv.get('issue_date','')}</p><p><strong>Due Date:</strong> {inv.get('due_date','')}</p><p><strong>Status:</strong> <span class="badge badge-{inv['status']}">{inv['status'].upper()}</span></p></div></div>
<table><thead><tr><th>Description</th><th class="text-right">Qty</th><th class="text-right">Rate</th><th class="text-right">Amount</th></tr></thead><tbody>"""
    for item in items:
        html += f'<tr><td>{item["description"]}</td><td class="text-right">{item["quantity"]}</td><td class="text-right">${item["rate"]:,.2f}</td><td class="text-right">${item["amount"]:,.2f}</td></tr>'
    html += f"""</tbody></table>
<div class="totals"><div>Subtotal: ${inv['subtotal']:,.2f}</div><div>Tax ({inv['tax_rate']}%): ${inv['tax_amount']:,.2f}</div><div class="total">Total: ${inv['total']:,.2f}</div></div>"""
    if inv.get("notes"):
        html += f'<div style="margin-top:30px;background:#f8fafc;padding:16px;border-radius:8px"><h4 style="font-size:13px;color:#64748b;margin-bottom:6px">Notes</h4><p style="font-size:14px">{inv["notes"]}</p></div>'
    html += '<div class="footer"><p>AI Growth Labs | Thank you for your business!</p></div></body></html>'
    return HTMLResponse(content=html)

# ===== FILE UPLOADS =====
@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...), related_type: str = Form(...), related_id: int = Form(...)):
    user = require_auth(request)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    safe_filename = f"{int(time.time())}_{file.filename.replace('..', '').replace('/', '_')}"
    filepath = os.path.join(UPLOAD_DIR, safe_filename)
    with open(filepath, "wb") as f:
        f.write(contents)
    db = get_db()
    db.execute("INSERT INTO file_attachments (related_type, related_id, filename, filepath, filesize, mime_type, uploaded_by) VALUES (?,?,?,?,?,?,?)",
               (related_type, related_id, file.filename, safe_filename, len(contents), file.content_type, user["id"]))
    log_activity(db, user["id"], "file_uploaded", f"Uploaded {file.filename}", related_type, related_id)
    db.commit()
    db.close()
    return {"message": "File uploaded", "filename": safe_filename}

@app.get("/uploads/{filename}")
async def serve_upload(filename: str, request: Request):
    user = require_auth(request)
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404)
    with open(filepath, "rb") as f:
        content = f.read()
    return Response(content=content, media_type="application/octet-stream",
                    headers={"Content-Disposition": f"inline; filename={filename}"})

# ===== APPROVAL REQUESTS =====
@app.post("/api/approvals")
async def create_approval(request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    c = db.cursor()
    c.execute("""INSERT INTO approval_requests (task_id, project_id, client_id, request_type, title, description, requested_by) VALUES (?,?,?,?,?,?,?)""",
              (data.get("task_id"), data.get("project_id"), data.get("client_id"), data.get("request_type", "content"),
               data["title"], data.get("description"), user["id"]))
    approval_id = c.lastrowid
    log_activity(db, user["id"], "approval_requested", f"Approval: {data['title']}", "approval", approval_id)
    db.commit()
    db.close()
    return {"id": approval_id, "message": "Approval request created"}

@app.put("/api/approvals/{approval_id}")
async def respond_approval(approval_id: int, request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    db.execute("UPDATE approval_requests SET status=?, reviewed_by=?, review_notes=?, reviewed_at=datetime('now') WHERE id=?",
               (data["status"], user["id"], data.get("review_notes"), approval_id))
    log_activity(db, user["id"], "approval_responded", f"Approval #{approval_id} → {data['status']}", "approval", approval_id)
    db.commit()
    db.close()
    return {"message": f"Approval {data['status']}"}

# ===== DATA EXPORT =====
@app.get("/api/export/{table_name}")
async def export_data(table_name: str, request: Request):
    user = require_role(request, ["super_admin", "finance", "operations_manager"])
    allowed = {"clients", "payments", "expenses", "invoices", "tasks", "projects", "time_entries"}
    if table_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Export not allowed for '{table_name}'")
    db = get_db()
    rows = [dict(r) for r in db.execute(f"SELECT * FROM {table_name}").fetchall()]
    db.close()
    if not rows:
        return Response(content="No data", media_type="text/plain")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# ===== ACTIVITY TIMELINE =====
@app.get("/api/activity")
async def get_activity(request: Request):
    user = require_auth(request)
    db = get_db()
    if user["role"] in ("super_admin", "operations_manager"):
        activities = [dict(r) for r in db.execute("""
            SELECT al.*, u.full_name as user_name FROM activity_log al LEFT JOIN users u ON al.user_id=u.id ORDER BY al.created_at DESC LIMIT 50
        """).fetchall()]
    else:
        activities = [dict(r) for r in db.execute("""
            SELECT al.*, u.full_name as user_name FROM activity_log al LEFT JOIN users u ON al.user_id=u.id WHERE al.user_id=? ORDER BY al.created_at DESC LIMIT 30
        """, (user["id"],)).fetchall()]
    db.close()
    return {"activities": activities}

# ===== OPS MANAGER DATA =====
def _get_ops_manager_data(db):
    clients = [dict(r) for r in db.execute("SELECT * FROM clients WHERE status='active' ORDER BY business_name").fetchall()]
    projects = [dict(r) for r in db.execute("""
        SELECT p.*, c.business_name, u.full_name as worker_name FROM projects p 
        LEFT JOIN clients c ON p.client_id=c.id LEFT JOIN users u ON p.assigned_worker_id=u.id ORDER BY p.created_at DESC
    """).fetchall()]
    workers = [dict(r) for r in db.execute("SELECT id, full_name, role, rank FROM users WHERE role NOT IN ('super_admin','client','finance') AND is_active=1 ORDER BY role, full_name").fetchall()]
    for w in workers:
        w["active_tasks"] = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='in_progress'", (w["id"],)).fetchone()[0]
        w["total_hours"] = db.execute("SELECT COALESCE(SUM(hours),0) FROM time_entries WHERE user_id=?", (w["id"],)).fetchone()[0]
    tasks = [dict(r) for r in db.execute("""
        SELECT t.*, u.full_name as assigned_name, p.title as project_title FROM tasks t 
        LEFT JOIN users u ON t.assigned_to=u.id LEFT JOIN projects p ON t.project_id=p.id ORDER BY t.created_at DESC LIMIT 50
    """).fetchall()]
    overdue_tasks = [dict(r) for r in db.execute("""
        SELECT t.*, u.full_name as assigned_name, p.title as project_title FROM tasks t 
        LEFT JOIN users u ON t.assigned_to=u.id LEFT JOIN projects p ON t.project_id=p.id 
        WHERE t.due_date IS NOT NULL AND t.due_date < date('now') AND t.status != 'completed' ORDER BY t.due_date
    """).fetchall()]
    pending_approvals = [dict(r) for r in db.execute("SELECT * FROM approval_requests WHERE status='pending' ORDER BY created_at DESC").fetchall()]
    active_projects = db.execute("SELECT COUNT(*) FROM projects WHERE status='in_progress'").fetchone()[0]
    total_tasks = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    completed_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status='completed'").fetchone()[0]
    return {
        "clients": clients, "projects": projects, "workers": workers, "tasks": tasks,
        "overdue_tasks": overdue_tasks, "pending_approvals": pending_approvals,
        "stats": {
            "active_projects": active_projects, "total_tasks": total_tasks, "completed_tasks": completed_tasks,
            "task_completion": round(completed_tasks/total_tasks*100) if total_tasks else 0,
            "overdue_count": len(overdue_tasks), "pending_approvals": len(pending_approvals),
        }
    }

# ===== KEYWORD RANKINGS =====
@app.post("/api/rankings")
async def add_ranking(request: Request):
    user = require_role(request, ["super_admin", "operations_manager", "worker", "tech_seo"])
    data = await request.json()
    db = get_db()
    prev = db.execute("SELECT position FROM keyword_rankings WHERE client_id=? AND keyword=? ORDER BY tracked_date DESC LIMIT 1",
                      (data["client_id"], data["keyword"])).fetchone()
    prev_pos = prev["position"] if prev else None
    db.execute("INSERT INTO keyword_rankings (client_id, keyword, position, previous_position, search_volume, url) VALUES (?,?,?,?,?,?)",
               (data["client_id"], data["keyword"], data["position"], prev_pos, data.get("search_volume", 0), data.get("url")))
    db.commit()
    db.close()
    return {"message": "Ranking recorded"}

@app.get("/api/rankings/{client_id}")
async def get_rankings(client_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    if client_id == 0:
        rankings = [dict(r) for r in db.execute("SELECT * FROM keyword_rankings ORDER BY tracked_date DESC, keyword LIMIT 200").fetchall()]
    else:
        rankings = [dict(r) for r in db.execute("SELECT * FROM keyword_rankings WHERE client_id=? ORDER BY tracked_date DESC, keyword LIMIT 100", (client_id,)).fetchall()]
    db.close()
    return {"rankings": rankings}

# ===== CONTRACTS =====
@app.get("/api/contracts")
async def list_contracts(request: Request):
    user = require_auth(request)
    db = get_db()
    contracts = [dict(r) for r in db.execute("SELECT * FROM contracts ORDER BY created_at DESC").fetchall()]
    db.close()
    return {"contracts": contracts}

@app.post("/api/contracts")
async def create_contract(request: Request):
    user = require_role(request, ["super_admin", "sales", "account_manager"])
    data = await request.json()
    db = get_db()
    c = db.cursor()
    c.execute("""INSERT INTO contracts (client_id, title, start_date, end_date, terms, status, monthly_value, auto_renew, created_by) VALUES (?,?,?,?,?,?,?,?,?)""",
              (data["client_id"], data["title"], data.get("start_date"), data.get("end_date"), data.get("terms"),
               data.get("status", "active"), data.get("monthly_value", 0), data.get("auto_renew", 0), user["id"]))
    contract_id = c.lastrowid
    log_activity(db, user["id"], "contract_created", f"Contract for client #{data['client_id']}", "contract", contract_id)
    db.commit()
    db.close()
    return {"id": contract_id, "message": "Contract created"}

# ===== SECURITY: Change Password =====
@app.post("/api/change-password")
async def change_password(request: Request):
    user = require_auth(request)
    data = await request.json()
    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")
    if len(new_pw) < 8:
        return JSONResponse({"error": "Password must be at least 8 characters"}, status_code=400)
    db = get_db()
    u = db.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
    if not bcrypt.verify(old_pw, u["password_hash"]):
        db.close()
        return JSONResponse({"error": "Current password is incorrect"}, status_code=400)
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (bcrypt.hash(new_pw), user["id"]))
    log_activity(db, user["id"], "password_changed", "User changed password", "user", user["id"])
    db.commit()
    db.close()
    return {"message": "Password changed successfully"}

# ===== PART 2: WHITE-LABEL REPORTS =====
@app.post("/api/reports/white-label")
async def generate_white_label_report(request: Request):
    user = require_role(request, ["super_admin", "finance", "operations_manager", "account_manager"])
    data = await request.json()
    client_id = data["client_id"]
    db = get_db()
    client = dict(db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone())
    projects = [dict(r) for r in db.execute("SELECT * FROM projects WHERE client_id=?", (client_id,)).fetchall()]
    tasks_all = []
    for p in projects:
        tasks_all += [dict(r) for r in db.execute("SELECT * FROM tasks WHERE project_id=?", (p["id"],)).fetchall()]
    payments = [dict(r) for r in db.execute("SELECT * FROM payments WHERE client_id=?", (client_id,)).fetchall()]
    rankings = [dict(r) for r in db.execute("SELECT * FROM keyword_rankings WHERE client_id=? ORDER BY tracked_date DESC LIMIT 20", (client_id,)).fetchall()]
    locations = [dict(r) for r in db.execute("SELECT * FROM client_locations WHERE client_id=?", (client_id,)).fetchall()]
    
    agency_name = data.get("agency_name", "AI Growth Labs")
    agency_tagline = data.get("agency_tagline", "AI-Powered SEO & Reputation Management")
    primary_color = data.get("primary_color", "#0A1628")
    accent_color = data.get("accent_color", "#00D4FF")
    logo_url = data.get("logo_url", "")
    
    report_data = json.dumps({
        "client": client, "projects": projects, "tasks": tasks_all, "payments": payments,
        "rankings": rankings, "locations": locations,
        "branding": {"agency_name": agency_name, "tagline": agency_tagline, "primary_color": primary_color, "accent_color": accent_color, "logo_url": logo_url},
        "generated_at": datetime.now().isoformat(), "generated_by": user["full_name"]
    })
    
    c = db.cursor()
    c.execute("INSERT INTO client_reports (client_id, report_type, title, report_data, created_by) VALUES (?,?,?,?,?)",
              (client_id, "white_label", f"White-Label Report - {client['business_name']} - {datetime.now().strftime('%B %Y')}", report_data, user["id"]))
    report_id = c.lastrowid
    log_activity(db, user["id"], "report_generated", f"White-label report for {client['business_name']}", "report", report_id)
    db.commit()
    db.close()
    return {"id": report_id, "message": "White-label report generated"}

@app.get("/api/reports/{report_id}/white-label")
async def download_white_label_report(report_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    report = db.execute("SELECT r.*, c.business_name FROM client_reports r LEFT JOIN clients c ON r.client_id=c.id WHERE r.id=?", (report_id,)).fetchone()
    db.close()
    if not report:
        raise HTTPException(status_code=404)
    report = dict(report)
    rdata = json.loads(report["report_data"]) if report["report_data"] else {}
    client = rdata.get("client", {})
    projects = rdata.get("projects", [])
    tasks = rdata.get("tasks", [])
    payments = rdata.get("payments", [])
    rankings = rdata.get("rankings", [])
    branding = rdata.get("branding", {})
    
    agency = branding.get("agency_name", "AI Growth Labs")
    tagline = branding.get("tagline", "AI-Powered SEO & Reputation Management")
    pc = branding.get("primary_color", "#0A1628")
    ac = branding.get("accent_color", "#00D4FF")
    logo = branding.get("logo_url", "")
    
    completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
    total_tasks = len(tasks)
    total_paid = sum(p.get("amount", 0) for p in payments if p.get("status") == "paid")
    
    logo_html = f'<img src="{logo}" style="max-height:50px;margin-bottom:12px">' if logo else ""
    
    rankings_html = ""
    if rankings:
        rankings_html = '<div class="section"><h2>Keyword Rankings</h2><table><thead><tr><th>Keyword</th><th>Position</th><th>Change</th><th>Volume</th><th>URL</th></tr></thead><tbody>'
        for r in rankings:
            prev = r.get("previous_position")
            pos = r.get("position", 0)
            if prev and prev > pos:
                change = f'<span style="color:#059669">▲ {prev - pos}</span>'
            elif prev and prev < pos:
                change = f'<span style="color:#dc2626">▼ {pos - prev}</span>'
            else:
                change = '<span style="color:#999">—</span>'
            rankings_html += f'<tr><td><strong>{r.get("keyword","")}</strong></td><td>{pos}</td><td>{change}</td><td>{r.get("search_volume",0)}</td><td style="font-size:11px">{r.get("url","")}</td></tr>'
        rankings_html += '</tbody></table></div>'
    
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{report['title']}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Inter,Arial,sans-serif;background:#fff;color:#333;padding:40px}}
.header{{background:linear-gradient(135deg,{pc},{ac}22);color:#fff;padding:40px;border-radius:12px;margin-bottom:30px;border-left:5px solid {ac}}}
.header h1{{font-size:24px;margin-bottom:4px}}.header p{{opacity:.8;font-size:14px}}
.section{{margin-bottom:30px}}.section h2{{font-size:18px;color:{pc};border-bottom:2px solid {ac};padding-bottom:8px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;margin-top:12px}}th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #eee;font-size:13px}}
th{{background:#f7f9fc;font-weight:600}}.stat-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:30px}}
.stat-card{{background:#f7f9fc;padding:20px;border-radius:8px;text-align:center;border-top:3px solid {ac}}}.stat-card .num{{font-size:28px;font-weight:700;color:{pc}}}
.stat-card .label{{font-size:12px;color:#666;margin-top:4px}}.badge{{padding:3px 8px;border-radius:4px;font-size:11px;font-weight:600}}
.badge-paid,.badge-completed{{background:#d1fae5;color:#059669}}.badge-pending{{background:#fef3c7;color:#d97706}}
.badge-progress,.badge-in_progress{{background:#dbeafe;color:#2563eb}}
.footer{{margin-top:40px;padding-top:20px;border-top:2px solid #eee;text-align:center;color:#999;font-size:12px}}
.confidential{{background:#fef3c7;padding:8px 16px;border-radius:6px;font-size:11px;color:#92400e;margin-bottom:20px;text-align:center}}
@media print{{body{{padding:20px}}.header{{break-after:avoid}}}}
</style></head><body>
<div class="header">{logo_html}<h1>{agency}</h1><p>{tagline}</p><p style="margin-top:8px">Report for: <strong>{client.get('business_name','')}</strong> | {rdata.get('generated_at','')[:10]}</p></div>
<div class="confidential">CONFIDENTIAL — Prepared exclusively for {client.get('business_name','')}</div>
<div class="stat-grid">
<div class="stat-card"><div class="num">{len(projects)}</div><div class="label">Active Projects</div></div>
<div class="stat-card"><div class="num">{completed_tasks}/{total_tasks}</div><div class="label">Tasks Completed</div></div>
<div class="stat-card"><div class="num">{round(completed_tasks/total_tasks*100) if total_tasks else 0}%</div><div class="label">Completion Rate</div></div>
<div class="stat-card"><div class="num">${total_paid:,.0f}</div><div class="label">Total Invested</div></div>
</div>
{rankings_html}
<div class="section"><h2>Projects Overview</h2><table><thead><tr><th>Project</th><th>Service</th><th>Progress</th><th>Status</th></tr></thead><tbody>"""
    for p in projects:
        badge = "badge-completed" if p.get("status") == "completed" else "badge-progress"
        html += f'<tr><td>{p.get("title","")}</td><td>{p.get("service_type","")}</td><td>{p.get("progress",0)}%</td><td><span class="badge {badge}">{p.get("status","")}</span></td></tr>'
    html += """</tbody></table></div>
<div class="section"><h2>Task Breakdown</h2><table><thead><tr><th>Task</th><th>Priority</th><th>Status</th></tr></thead><tbody>"""
    for t in tasks:
        badge = "badge-completed" if t.get("status") == "completed" else ("badge-progress" if t.get("status") == "in_progress" else "badge-pending")
        html += f'<tr><td>{t.get("title","")}</td><td>{t.get("priority","")}</td><td><span class="badge {badge}">{t.get("status","")}</span></td></tr>'
    html += """</tbody></table></div>
<div class="section"><h2>Payment History</h2><table><thead><tr><th>Invoice</th><th>Amount</th><th>Due Date</th><th>Status</th></tr></thead><tbody>"""
    for pay in payments:
        badge = "badge-paid" if pay.get("status") == "paid" else "badge-pending"
        html += f'<tr><td>{pay.get("invoice_number","")}</td><td>${pay.get("amount",0):,.0f}</td><td>{pay.get("due_date","")}</td><td><span class="badge {badge}">{pay.get("status","")}</span></td></tr>'
    html += f"""</tbody></table></div>
<div class="footer"><p>{agency} | {tagline}</p><p>Generated by {rdata.get('generated_by','System')} on {rdata.get('generated_at','')[:10]}</p></div>
</body></html>"""
    return HTMLResponse(content=html)

# ===== PART 2: EMAIL SENDING =====
@app.post("/api/email/send")
async def send_email(request: Request):
    user = require_role(request, ["super_admin", "finance", "operations_manager", "account_manager"])
    data = await request.json()
    db = get_db()
    smtp = db.execute("SELECT * FROM api_settings WHERE provider='smtp'").fetchone()
    if not smtp or not smtp["api_key"]:
        db.close()
        return JSONResponse({"error": "SMTP not configured. Go to Settings → SMTP to configure email sending."}, status_code=400)
    smtp = dict(smtp)
    config = json.loads(smtp.get("config") or "{}")
    
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = data.get("subject", "AI Growth Labs Report")
        msg["From"] = config.get("from_email", smtp["api_key"])
        msg["To"] = data["to_email"]
        
        if data.get("html_body"):
            msg.attach(MIMEText(data["html_body"], "html"))
        elif data.get("body"):
            msg.attach(MIMEText(data["body"], "plain"))
        
        host = config.get("host", "smtp.gmail.com")
        port = int(config.get("port", 587))
        
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(config.get("from_email", smtp["api_key"]), smtp["api_key"])
            server.send_message(msg)
        
        log_activity(db, user["id"], "email_sent", f"Email to {data['to_email']}: {data.get('subject','')}", "email", 0)
        db.commit()
        db.close()
        return {"message": f"Email sent to {data['to_email']}"}
    except Exception as e:
        db.close()
        return JSONResponse({"error": f"Email failed: {str(e)}"}, status_code=500)

@app.post("/api/reports/{report_id}/email")
async def email_report(report_id: int, request: Request):
    user = require_role(request, ["super_admin", "finance", "operations_manager"])
    data = await request.json()
    db = get_db()
    report = db.execute("SELECT r.*, c.business_name, c.email as client_email FROM client_reports r LEFT JOIN clients c ON r.client_id=c.id WHERE r.id=?", (report_id,)).fetchone()
    if not report:
        db.close()
        raise HTTPException(status_code=404)
    report = dict(report)
    
    to_email = data.get("to_email", report.get("client_email", ""))
    if not to_email:
        db.close()
        return JSONResponse({"error": "No email address provided"}, status_code=400)
    
    smtp = db.execute("SELECT * FROM api_settings WHERE provider='smtp'").fetchone()
    if not smtp or not smtp["api_key"]:
        db.close()
        return JSONResponse({"error": "SMTP not configured"}, status_code=400)
    smtp_conf = json.loads(dict(smtp).get("config") or "{}")
    
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        rdata = json.loads(report["report_data"]) if report["report_data"] else {}
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your SEO Report - {report['business_name']} - {report['title']}"
        msg["From"] = smtp_conf.get("from_email", dict(smtp)["api_key"])
        msg["To"] = to_email
        
        text = f"Hi,\n\nPlease find your latest SEO performance report attached.\n\nReport: {report['title']}\nGenerated: {rdata.get('generated_at','')[:10]}\n\nPlease log in to your client portal to view full details.\n\nBest regards,\nAI Growth Labs Team"
        msg.attach(MIMEText(text, "plain"))
        
        host = smtp_conf.get("host", "smtp.gmail.com")
        port = int(smtp_conf.get("port", 587))
        
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(smtp_conf.get("from_email", dict(smtp)["api_key"]), dict(smtp)["api_key"])
            server.send_message(msg)
        
        db.execute("UPDATE client_reports SET sent_to_client=1, sent_date=datetime('now'), sent_by=? WHERE id=?", (user["id"], report_id))
        log_activity(db, user["id"], "report_emailed", f"Report emailed to {to_email}", "report", report_id)
        db.commit()
        db.close()
        return {"message": f"Report emailed to {to_email}"}
    except Exception as e:
        db.close()
        return JSONResponse({"error": f"Email failed: {str(e)}"}, status_code=500)

# ===== PART 2: FILE ATTACHMENTS LIST =====
@app.get("/api/attachments/{related_type}/{related_id}")
async def list_attachments(related_type: str, related_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    files = [dict(r) for r in db.execute("""
        SELECT f.*, u.full_name as uploader_name FROM file_attachments f
        LEFT JOIN users u ON f.uploaded_by=u.id
        WHERE f.related_type=? AND f.related_id=? ORDER BY f.created_at DESC
    """, (related_type, related_id)).fetchall()]
    db.close()
    return {"attachments": files}

# ===== PART 2: CLIENT LOCATIONS =====
@app.post("/api/locations")
async def add_location(request: Request):
    user = require_role(request, ["super_admin", "operations_manager", "account_manager", "sales"])
    data = await request.json()
    db = get_db()
    c = db.cursor()
    c.execute("""INSERT INTO client_locations (client_id, location_name, address, city, state, zip_code, phone, gbp_url, gbp_cid) VALUES (?,?,?,?,?,?,?,?,?)""",
              (data["client_id"], data["location_name"], data.get("address"), data.get("city"), data.get("state"),
               data.get("zip_code"), data.get("phone"), data.get("gbp_url"), data.get("gbp_cid")))
    loc_id = c.lastrowid
    log_activity(db, user["id"], "location_added", f"Location: {data['location_name']} for client #{data['client_id']}", "location", loc_id)
    db.commit()
    db.close()
    return {"id": loc_id, "message": "Location added"}

@app.get("/api/locations/{client_id}")
async def get_locations(client_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    locations = [dict(r) for r in db.execute("SELECT * FROM client_locations WHERE client_id=? ORDER BY location_name", (client_id,)).fetchall()]
    db.close()
    return {"locations": locations}

# ===== PART 2: RANKINGS CHART PAGE =====
@app.get("/rankings/{client_id}", response_class=HTMLResponse)
async def rankings_chart_page(client_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if not client:
        db.close()
        raise HTTPException(status_code=404)
    client = dict(client)
    rankings = [dict(r) for r in db.execute("SELECT * FROM keyword_rankings WHERE client_id=? ORDER BY keyword, tracked_date", (client_id,)).fetchall()]
    locations = [dict(r) for r in db.execute("SELECT * FROM client_locations WHERE client_id=?", (client_id,)).fetchall()]
    db.close()
    
    keywords = {}
    for r in rankings:
        kw = r["keyword"]
        if kw not in keywords:
            keywords[kw] = {"positions": [], "current": r["position"], "previous": r.get("previous_position"), "volume": r.get("search_volume", 0), "url": r.get("url", "")}
        keywords[kw]["positions"].append(r["position"])
        keywords[kw]["current"] = r["position"]
    
    chart_data = json.dumps({"keywords": {k: v["positions"] for k, v in keywords.items()}})
    
    return templates.TemplateResponse("rankings_chart.html", {
        "request": request, "user": user, "client": client,
        "keywords": keywords, "chart_data": chart_data, "locations": locations
    })

# ===== PART 3: ACTIVITY TIMELINE PAGE =====
@app.get("/activity", response_class=HTMLResponse)
async def activity_page(request: Request):
    user = get_current_user(request)
    if not user or user["role"] not in ("super_admin", "operations_manager"):
        return RedirectResponse(url="/login")
    db = get_db()
    activities = [dict(r) for r in db.execute("""
        SELECT al.*, u.full_name as user_name FROM activity_log al LEFT JOIN users u ON al.user_id=u.id ORDER BY al.created_at DESC LIMIT 200
    """).fetchall()]
    db.close()
    return templates.TemplateResponse("activity_timeline.html", {"request": request, "user": user, "activities": activities})

# ===== PART 3: WORKER PERFORMANCE =====
@app.get("/api/performance/{user_id}")
async def get_worker_performance(user_id: int, request: Request):
    user = require_auth(request)
    if user["role"] not in ("super_admin", "operations_manager") and user["id"] != user_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    db = get_db()
    worker = db.execute("SELECT id, username, full_name, role, rank FROM users WHERE id=?", (user_id,)).fetchone()
    if not worker:
        db.close()
        raise HTTPException(status_code=404)
    worker = dict(worker)
    total_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=?", (user_id,)).fetchone()[0]
    completed_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='completed'", (user_id,)).fetchone()[0]
    in_progress = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='in_progress'", (user_id,)).fetchone()[0]
    total_hours = db.execute("SELECT COALESCE(SUM(hours),0) FROM time_entries WHERE user_id=?", (user_id,)).fetchone()[0]
    avg_hours = db.execute("SELECT COALESCE(AVG(hours),0) FROM time_entries WHERE user_id=? AND hours > 0", (user_id,)).fetchone()[0]
    active_projects = db.execute("SELECT COUNT(DISTINCT project_id) FROM tasks WHERE assigned_to=? AND status IN ('in_progress','pending')", (user_id,)).fetchone()[0]
    
    # Recent completed tasks
    recent = [dict(r) for r in db.execute("""
        SELECT t.title, t.status, t.priority, p.title as project_title 
        FROM tasks t LEFT JOIN projects p ON t.project_id=p.id WHERE t.assigned_to=? ORDER BY t.created_at DESC LIMIT 10
    """, (user_id,)).fetchall()]
    
    # Performance score (0-100)
    completion_rate = round(completed_tasks / total_tasks * 100) if total_tasks else 0
    score = min(100, completion_rate + min(20, int(total_hours)))
    
    db.close()
    return {
        "worker": worker,
        "stats": {
            "total_tasks": total_tasks, "completed_tasks": completed_tasks, "in_progress": in_progress,
            "completion_rate": completion_rate, "total_hours": round(total_hours, 1),
            "avg_hours_per_task": round(avg_hours, 1), "active_projects": active_projects,
            "performance_score": score
        },
        "recent_tasks": recent
    }

@app.get("/performance", response_class=HTMLResponse)
async def performance_page(request: Request):
    user = get_current_user(request)
    if not user or user["role"] not in ("super_admin", "operations_manager"):
        return RedirectResponse(url="/login")
    db = get_db()
    workers = [dict(r) for r in db.execute("SELECT id, username, full_name, role, rank, salary FROM users WHERE role NOT IN ('super_admin','client') AND is_active=1").fetchall()]
    for w in workers:
        total = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=?", (w["id"],)).fetchone()[0]
        completed = db.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='completed'", (w["id"],)).fetchone()[0]
        hours = db.execute("SELECT COALESCE(SUM(hours),0) FROM time_entries WHERE user_id=?", (w["id"],)).fetchone()[0]
        w["total_tasks"] = total
        w["completed_tasks"] = completed
        w["completion_rate"] = round(completed / total * 100) if total else 0
        w["total_hours"] = round(hours, 1)
        w["score"] = min(100, w["completion_rate"] + min(20, int(hours)))
    workers.sort(key=lambda x: x["score"], reverse=True)
    db.close()
    return templates.TemplateResponse("performance.html", {"request": request, "user": user, "workers": workers})

# ===== PART 3: NOTIFICATIONS API =====
@app.get("/api/notifications")
async def get_notifications(request: Request):
    user = require_auth(request)
    db = get_db()
    notifs = [dict(r) for r in db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (user["id"],)).fetchall()]
    unread = db.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user["id"],)).fetchone()[0]
    db.close()
    return {"notifications": notifs, "unread_count": unread}

@app.post("/api/notifications/read")
async def mark_notifications_read(request: Request):
    user = require_auth(request)
    db = get_db()
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0", (user["id"],))
    db.commit()
    db.close()
    return {"message": "All notifications marked as read"}

@app.post("/api/notifications/create")
async def create_notification(request: Request):
    user = require_role(request, ["super_admin", "operations_manager"])
    data = await request.json()
    db = get_db()
    db.execute("INSERT INTO notifications (user_id, type, title, message, link) VALUES (?,?,?,?,?)",
               (data["user_id"], data.get("type", "info"), data["title"], data.get("message", ""), data.get("link")))
    db.commit()
    db.close()
    return {"message": "Notification sent"}

# ===== PART 3: BULK TASK CREATION FROM TEMPLATES =====
@app.post("/api/tasks/bulk")
async def create_bulk_tasks(request: Request):
    user = require_role(request, ["super_admin", "operations_manager", "account_manager"])
    data = await request.json()
    project_id = data["project_id"]
    tasks = data.get("tasks", [])
    db = get_db()
    c = db.cursor()
    created = 0
    for i, t in enumerate(tasks):
        c.execute("""INSERT INTO tasks (project_id, title, description, priority, assigned_to, order_num) VALUES (?,?,?,?,?,?)""",
                  (project_id, t["title"], t.get("description", ""), t.get("priority", "medium"), t.get("assigned_to"), i + 1))
        created += 1
    log_activity(db, user["id"], "bulk_tasks_created", f"Created {created} tasks for project #{project_id}", "project", project_id)
    db.commit()
    db.close()
    return {"message": f"{created} tasks created", "count": created}

# ===== PART 3: TASK STATUS UPDATE =====
@app.put("/api/tasks/{task_id}/status")
async def update_task_status(task_id: int, request: Request):
    user = require_auth(request)
    data = await request.json()
    new_status = data["status"]
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        db.close()
        raise HTTPException(status_code=404)
    db.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
    if new_status == "completed":
        db.execute("UPDATE tasks SET completed_date=datetime('now') WHERE id=?", (task_id,))
        # Update project progress
        proj_id = task["project_id"]
        total = db.execute("SELECT COUNT(*) FROM tasks WHERE project_id=?", (proj_id,)).fetchone()[0]
        done = db.execute("SELECT COUNT(*) FROM tasks WHERE project_id=? AND status='completed'", (proj_id,)).fetchone()[0] + 1
        progress = round(done / total * 100) if total else 0
        db.execute("UPDATE projects SET progress=? WHERE id=?", (progress, proj_id))
    log_activity(db, user["id"], "task_status_updated", f"Task #{task_id} → {new_status}", "task", task_id)
    db.commit()
    db.close()
    return {"message": f"Task updated to {new_status}"}

# ===== PART 3: DASHBOARD SEARCH =====
@app.get("/api/search")
async def search(request: Request, q: str = ""):
    user = require_auth(request)
    if not q or len(q) < 2:
        return {"results": []}
    db = get_db()
    results = []
    # Search clients
    for r in db.execute("SELECT id, business_name, contact_name, industry FROM clients WHERE business_name LIKE ? OR contact_name LIKE ? LIMIT 5",
                         (f"%{q}%", f"%{q}%")).fetchall():
        results.append({"type": "client", "id": r["id"], "title": r["business_name"], "subtitle": r["contact_name"], "link": f"/client/{r['id']}"})
    # Search projects
    for r in db.execute("SELECT p.id, p.title, c.business_name FROM projects p LEFT JOIN clients c ON p.client_id=c.id WHERE p.title LIKE ? LIMIT 5",
                         (f"%{q}%",)).fetchall():
        results.append({"type": "project", "id": r["id"], "title": r["title"], "subtitle": r["business_name"] or "", "link": f"/client/{r['id']}"})
    # Search tasks
    for r in db.execute("SELECT t.id, t.title, p.title as project_title FROM tasks t LEFT JOIN projects p ON t.project_id=p.id WHERE t.title LIKE ? LIMIT 5",
                         (f"%{q}%",)).fetchall():
        results.append({"type": "task", "id": r["id"], "title": r["title"], "subtitle": r["project_title"] or "", "link": "#"})
    db.close()
    return {"results": results}

# ===== PART 4: REVENUE FORECASTING =====
@app.get("/api/analytics/revenue")
async def revenue_analytics(request: Request):
    user = require_role(request, ["super_admin", "finance", "operations_manager"])
    db = get_db()
    
    # Current MRR from active clients
    mrr = db.execute("SELECT COALESCE(SUM(monthly_payment),0) FROM clients WHERE status='active'").fetchone()[0]
    
    # Revenue by month (from invoices)
    monthly_rev = [dict(r) for r in db.execute("""
        SELECT strftime('%Y-%m', issue_date) as month, SUM(total) as revenue, COUNT(*) as count 
        FROM invoices WHERE status='paid' GROUP BY month ORDER BY month DESC LIMIT 12
    """).fetchall()]
    
    # Revenue by package
    by_package = [dict(r) for r in db.execute("""
        SELECT package, COUNT(*) as clients, SUM(monthly_payment) as mrr 
        FROM clients WHERE status='active' AND package IS NOT NULL GROUP BY package
    """).fetchall()]
    
    # Pipeline (leads + prospects)
    pipeline = db.execute("SELECT COALESCE(SUM(monthly_payment),0) FROM clients WHERE status IN ('lead','prospect')").fetchone()[0]
    
    # Churn risk (overdue invoices)
    overdue_total = db.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE status='overdue'").fetchone()[0]
    
    # Contract-based forecast (next 6 months)
    active_contracts = db.execute("SELECT COALESCE(SUM(monthly_value),0) FROM contracts WHERE status='active'").fetchone()[0]
    forecast = []
    for i in range(6):
        month_name = (datetime.now() + timedelta(days=30 * i)).strftime("%b %Y")
        projected = mrr + (active_contracts * 0.1 * i)  # Growth estimate
        forecast.append({"month": month_name, "projected": round(projected)})
    
    db.close()
    return {
        "mrr": mrr, "pipeline_value": pipeline, "overdue_total": overdue_total,
        "monthly_revenue": monthly_rev, "by_package": by_package,
        "forecast": forecast, "contract_mrr": active_contracts
    }

# ===== PART 4: DASHBOARD ANALYTICS =====
@app.get("/api/analytics/overview")
async def analytics_overview(request: Request):
    user = require_role(request, ["super_admin", "operations_manager"])
    db = get_db()
    
    # Task stats
    task_by_status = {}
    for r in db.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status").fetchall():
        task_by_status[r["status"]] = r["cnt"]
    
    # Tasks by priority
    task_by_priority = {}
    for r in db.execute("SELECT priority, COUNT(*) as cnt FROM tasks GROUP BY priority").fetchall():
        task_by_priority[r["priority"]] = r["cnt"]
    
    # Projects by service type
    by_service = {}
    for r in db.execute("SELECT service_type, COUNT(*) as cnt FROM projects GROUP BY service_type").fetchall():
        by_service[r["service_type"]] = r["cnt"]
    
    # Clients by industry
    by_industry = {}
    for r in db.execute("SELECT industry, COUNT(*) as cnt FROM clients GROUP BY industry").fetchall():
        by_industry[r["industry"]] = r["cnt"]
    
    # Time logged this week
    weekly_hours = db.execute("SELECT COALESCE(SUM(hours),0) FROM time_entries WHERE start_time >= date('now','-7 days')").fetchone()[0]
    
    # Top performers this week
    top_workers = [dict(r) for r in db.execute("""
        SELECT u.full_name, u.role, COUNT(t.id) as tasks_done 
        FROM tasks t JOIN users u ON t.assigned_to=u.id 
        WHERE t.status='completed' GROUP BY t.assigned_to ORDER BY tasks_done DESC LIMIT 5
    """).fetchall()]
    
    db.close()
    return {
        "task_by_status": task_by_status, "task_by_priority": task_by_priority,
        "by_service": by_service, "by_industry": by_industry,
        "weekly_hours": round(weekly_hours, 1), "top_workers": top_workers
    }

# ===== PART 4: ANALYTICS PAGE =====
@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    user = get_current_user(request)
    if not user or user["role"] not in ("super_admin", "finance", "operations_manager"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("analytics.html", {"request": request, "user": user})

# ===== PART 4: INVOICE DOWNLOAD (PDF-STYLE HTML) =====
@app.get("/api/invoices/{invoice_id}/download")
async def download_invoice(invoice_id: int, request: Request):
    user = require_auth(request)
    db = get_db()
    inv = db.execute("""SELECT i.*, c.business_name, c.contact_name, c.email, c.phone, c.address 
                        FROM invoices i LEFT JOIN clients c ON i.client_id=c.id WHERE i.id=?""", (invoice_id,)).fetchone()
    if not inv:
        db.close()
        raise HTTPException(status_code=404)
    inv = dict(inv)
    items = [dict(r) for r in db.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (invoice_id,)).fetchall()]
    db.close()
    
    items_html = ""
    for it in items:
        items_html += f'<tr><td>{it["description"]}</td><td style="text-align:center">{it["quantity"]}</td><td style="text-align:right">${it["rate"]:,.2f}</td><td style="text-align:right"><strong>${it["amount"]:,.2f}</strong></td></tr>'
    
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Invoice {inv['invoice_number']}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Inter,Arial,sans-serif;background:#fff;color:#333;padding:40px;max-width:800px;margin:0 auto}}
.inv-header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px;padding-bottom:20px;border-bottom:3px solid #0A1628}}
.inv-header h1{{font-size:28px;color:#0A1628}}.inv-header .inv-num{{font-size:14px;color:#666}}
.inv-meta{{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-bottom:30px}}
.inv-meta h3{{font-size:12px;text-transform:uppercase;color:#999;margin-bottom:8px}}
table{{width:100%;border-collapse:collapse;margin-bottom:20px}}th{{background:#0A1628;color:#fff;padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase}}
td{{padding:10px 12px;border-bottom:1px solid #eee;font-size:13px}}
.totals{{text-align:right;margin-top:20px}}.totals .total-row{{display:flex;justify-content:flex-end;gap:30px;padding:6px 0;font-size:14px}}
.totals .grand-total{{font-size:20px;font-weight:700;color:#0A1628;border-top:2px solid #0A1628;padding-top:10px;margin-top:8px}}
.badge{{display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:600}}
.badge-paid{{background:#d1fae5;color:#059669}}.badge-sent,.badge-pending{{background:#fef3c7;color:#d97706}}.badge-overdue{{background:#fee2e2;color:#dc2626}}
.footer{{margin-top:40px;padding-top:20px;border-top:1px solid #eee;text-align:center;color:#999;font-size:11px}}
@media print{{body{{padding:20px}}}}
</style></head><body>
<div class="inv-header"><div><h1>INVOICE</h1><p class="inv-num">{inv['invoice_number']}</p></div>
<div style="text-align:right"><h2 style="color:#0A1628">AI Growth Labs</h2><p style="color:#666;font-size:13px">AI-Powered SEO & Reputation Management</p>
<span class="badge badge-{inv['status']}">{inv['status'].upper()}</span></div></div>
<div class="inv-meta"><div><h3>Bill To</h3><p><strong>{inv.get('business_name','')}</strong></p><p>{inv.get('contact_name','')}</p><p>{inv.get('email','')}</p><p>{inv.get('phone','')}</p></div>
<div style="text-align:right"><h3>Invoice Details</h3><p>Issue Date: <strong>{inv['issue_date']}</strong></p><p>Due Date: <strong>{inv['due_date']}</strong></p>
{f"<p>Paid Date: <strong>{inv['paid_date']}</strong></p>" if inv.get('paid_date') else ''}</div></div>
<table><thead><tr><th>Description</th><th style="text-align:center">Qty</th><th style="text-align:right">Rate</th><th style="text-align:right">Amount</th></tr></thead>
<tbody>{items_html}</tbody></table>
<div class="totals"><div class="total-row"><span>Subtotal:</span><span>${inv['subtotal']:,.2f}</span></div>
{"<div class='total-row'><span>Tax (" + str(inv['tax_rate']) + "%):</span><span>$" + f"{inv['tax_amount']:,.2f}" + "</span></div>" if inv.get('tax_amount') else ""}
<div class="total-row grand-total"><span>Total:</span><span>${inv['total']:,.2f}</span></div></div>
{f"<p style='margin-top:20px;color:#666;font-size:13px'>Notes: {inv['notes']}</p>" if inv.get('notes') else ''}
<div class="footer"><p>AI Growth Labs | Thank you for your business!</p><p>Questions? Contact us at billing@aigrowth-labs.com</p></div>
</body></html>"""
    return HTMLResponse(content=html)

# ===== PART 4: PROJECT PROGRESS UPDATE =====
@app.put("/api/projects/{project_id}/progress")
async def update_project_progress(project_id: int, request: Request):
    user = require_auth(request)
    data = await request.json()
    db = get_db()
    db.execute("UPDATE projects SET progress=? WHERE id=?", (data["progress"], project_id))
    if data["progress"] >= 100:
        db.execute("UPDATE projects SET status='completed' WHERE id=?", (project_id,))
    log_activity(db, user["id"], "project_updated", f"Project #{project_id} progress → {data['progress']}%", "project", project_id)
    db.commit()
    db.close()
    return {"message": f"Project progress updated to {data['progress']}%"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
