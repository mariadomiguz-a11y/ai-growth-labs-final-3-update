# AI Growth Labs — Complete Project Documentation

> This file contains the FULL project structure, every file explained, every function documented, 
> every database table described, and every API endpoint listed. If someone needs to understand 
> or modify this project, this file alone is enough to get started.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [File Structure](#2-file-structure)
3. [Tech Stack](#3-tech-stack)
4. [How to Run](#4-how-to-run)
5. [Database Schema (27 Tables)](#5-database-schema-27-tables)
6. [Backend API Endpoints (99 Endpoints)](#6-backend-api-endpoints-99-endpoints)
7. [Frontend Pages (25 Pages)](#7-frontend-pages-25-pages)
8. [Dashboard Templates (16 Templates)](#8-dashboard-templates-16-templates)
9. [User Roles & Permissions (11 Roles)](#9-user-roles--permissions-11-roles)
10. [API Integrations (9 Integrations)](#10-api-integrations-9-integrations)
11. [Security Features](#11-security-features)
12. [Demo Credentials](#12-demo-credentials)
13. [Key Functions Explained](#13-key-functions-explained)
14. [How to Modify](#14-how-to-modify)

---

## 1. Project Overview

**AI Growth Labs** is a complete Agency Operating System — a website + backend dashboard for running an AI-powered SEO & Digital Marketing Agency.

**Two main parts:**
- **Frontend Website** — Client-facing marketing site (static HTML/CSS/JS) with 25 pages, 10 services, 6 industries
- **Backend Dashboard** — Agency operations platform (Python FastAPI) with 99 API endpoints, 27 database tables, 16 role-based dashboards, 9 API integrations

**Total code:** ~9,700 lines across 70+ files

---

## 2. File Structure

```
ai-growth-labs/
├── index.html                          # Homepage (622 lines) — Hero, services, pricing, testimonials, FAQ
├── css/
│   └── style.css                       # Main stylesheet (1193 lines) — Navy+Cyan theme, responsive
├── js/
│   └── main.js                         # Frontend JS (126 lines) — Scroll, nav, FAQ accordion, counters
│
├── pages/                              # 25 Service & Industry Pages
│   ├── local-seo.html                  # Local SEO Service (239 lines) — Most detailed service page
│   ├── gbp-optimization.html           # Google Business Profile (104 lines)
│   ├── reputation-management.html      # Reputation Management (116 lines)
│   ├── ai-seo.html                     # AI SEO Services (83 lines)
│   ├── paid-advertising.html           # Facebook & Google Ads (80 lines)
│   ├── social-media.html               # Social Media Management (89 lines)
│   ├── content-creation.html           # Content Creation (79 lines)
│   ├── video-seo.html                  # Video SEO & YouTube (79 lines) — NEW Part 5
│   ├── cro.html                        # Conversion Rate Optimization (80 lines) — NEW Part 5
│   ├── ecommerce-seo.html              # E-Commerce SEO (80 lines) — NEW Part 5
│   ├── seo-for-dentists.html           # Industry: Dentists (123 lines)
│   ├── seo-for-lawyers.html            # Industry: Lawyers (87 lines)
│   ├── seo-for-restaurants.html        # Industry: Restaurants (87 lines)
│   ├── seo-for-plumbers.html           # Industry: Plumbers (87 lines)
│   ├── seo-for-hvac.html              # Industry: HVAC (79 lines) — NEW Part 5
│   ├── seo-for-medical-spas.html      # Industry: Medical Spas (80 lines) — NEW Part 5
│   ├── about.html                      # About Us (104 lines)
│   ├── blog.html                       # Blog (46 lines)
│   ├── case-studies.html               # Case Studies (46 lines)
│   ├── contact.html                    # Contact Form (69 lines)
│   ├── free-audit.html                 # Free Audit Form (88 lines)
│   ├── privacy-policy.html             # Privacy Policy (61 lines)
│   ├── terms.html                      # Terms of Service (56 lines)
│   └── disclaimer.html                 # Disclaimer (55 lines)
│
├── dashboard/                          # Backend Application
│   ├── main.py                         # FastAPI App (2548 lines) — ALL endpoints, middleware, logic
│   ├── database.py                     # Database Schema (724 lines) — 27 tables, demo data
│   ├── requirements.txt                # Python dependencies
│   ├── pyproject.toml                  # Project config
│   ├── generate_templates.py           # Template generator utility
│   ├── static/
│   │   └── css/
│   │       └── dashboard.css           # Dashboard stylesheet
│   ├── uploads/                        # File upload directory (10MB max per file)
│   └── templates/                      # Jinja2 HTML Templates (16 files)
│       ├── login.html                  # Login page (50 lines)
│       ├── admin_dashboard.html        # Super Admin dashboard (207 lines)
│       ├── client_portal.html          # Client portal (147 lines)
│       ├── client_detail.html          # Client detail view (163 lines)
│       ├── worker_dashboard.html       # Worker dashboard (142 lines)
│       ├── finance_dashboard.html      # Finance dashboard (116 lines)
│       ├── ops_dashboard.html          # Operations Manager dashboard (97 lines)
│       ├── sales_dashboard.html        # Sales dashboard (76 lines)
│       ├── social_dashboard.html       # Social Media dashboard (79 lines)
│       ├── settings.html               # API Settings page (125 lines)
│       ├── analytics.html              # Analytics dashboard (101 lines)
│       ├── activity_timeline.html      # Activity log (81 lines)
│       ├── performance.html            # Worker leaderboard (69 lines)
│       ├── rankings_chart.html         # Keyword ranking charts (122 lines)
│       ├── monitor.html                # Team monitor (61 lines)
│       └── team_chat.html              # Team chat (69 lines)
│
├── templates/                          # Agency Strategy Templates (17 files)
│   ├── discovery-call.html             # Discovery call script
│   ├── onboarding-form.html            # Client onboarding form
│   ├── client-proposal.html            # Proposal template
│   ├── client-reporting.html           # Reporting template
│   ├── kickoff-call.html               # Kickoff call agenda
│   ├── dna-audit-prompt-level1.html    # AI audit prompt (basic)
│   ├── dna-audit-prompt-level2.html    # AI audit prompt (advanced)
│   ├── service-*.html                  # Service delivery templates
│   └── pro-tips-working-patterns.html  # Agency best practices
│
├── site/                               # Deployed copy of frontend (mirror)
│
├── PROJECT_TREE.md                     # THIS FILE — Full project documentation
├── API_GUIDE.md                        # API integration setup guide
├── DATA_TREE.md                        # Database & API reference
├── COMPLETE_STRATEGY.md                # Competitor analysis & positioning
├── COMPLETE_EXECUTION_GUIDE.md         # Step-by-step service delivery guide
├── DEPLOYMENT_GUIDE.md                 # cPanel/VPS deployment instructions
└── .gitignore                          # Git ignore rules
```

---

## 3. Tech Stack

| Component | Technology | Version/Details |
|-----------|-----------|-----------------|
| **Backend Framework** | FastAPI | Python async web framework |
| **Template Engine** | Jinja2 | HTML templates with Python logic |
| **Database** | SQLite | File-based DB (`agency.db`) |
| **Authentication** | JWT | python-jose library, 24hr token expiry |
| **Password Hashing** | bcrypt | passlib library |
| **Frontend CSS** | Custom CSS | Navy (#0A1628) + Cyan (#00D4FF) theme |
| **Frontend JS** | Vanilla JS | No frameworks — scroll effects, forms |
| **Charts** | Chart.js | Keyword rankings, analytics charts |
| **Server** | Uvicorn | ASGI server, port 8000 |

### Python Dependencies
```
fastapi          — Web framework
uvicorn          — ASGI server
jinja2           — Template engine
python-multipart — Form data parsing
python-jose      — JWT tokens
passlib          — Password hashing
bcrypt           — bcrypt backend for passlib
aiofiles         — Async file operations
```

---

## 4. How to Run

### Quick Start
```bash
cd dashboard
pip install -r requirements.txt
python main.py
# Server starts at http://localhost:8000
# Login: admin / admin123
```

### First Run
- `database.py` auto-creates `agency.db` with all 27 tables + demo data
- Demo users, clients, projects, tasks, invoices etc. are auto-populated
- No migrations needed — SQLite file is self-contained

### Frontend
- Open `index.html` directly in browser, or
- Deploy `pages/` folder to any static hosting (Netlify, Vercel, cPanel)

---

## 5. Database Schema (27 Tables)

### Core Tables

#### `users` — System Users (11 demo users)
```sql
id, username, password_hash, full_name, email, role, department, 
is_active, last_login, created_at
```
**Roles:** super_admin, tech_seo, content_writer, link_builder, social_media, finance, sales, account_manager, operations_manager, client, worker

#### `clients` — Agency Clients (4 demo clients)
```sql
id, business_name, contact_name, email, phone, website, industry, city, 
state, address, zip_code, package, monthly_fee, status, notes, 
assigned_to, created_at
```
**Status:** active, inactive, prospect, churned

#### `projects` — Client Projects
```sql
id, client_id, name, description, project_type, status, priority, 
start_date, end_date, budget, progress, created_by, created_at
```
**Types:** local_seo, technical_seo, content, social_media, paid_ads, reputation, gbp, full_service

#### `tasks` — Project Tasks
```sql
id, project_id, title, description, assigned_to, status, priority, 
task_type, due_date, completed_date, auto_result, created_at
```
**Status:** pending, in_progress, review, completed, blocked

### Financial Tables

#### `invoices` — Client Invoices
```sql
id, client_id, invoice_number, issue_date, due_date, subtotal, 
tax_rate, tax_amount, total, status, paid_date, notes, created_by, created_at
```
**Status:** draft, sent, paid, overdue, cancelled

#### `invoice_items` — Invoice Line Items
```sql
id, invoice_id, description, quantity, rate, amount
```

#### `expenses` — Agency Expenses
```sql
id, category, amount, description, vendor, date, approved_by, 
receipt_url, created_at
```

#### `payments` — Payment Records
```sql
id, client_id, amount, method, reference, date, created_at
```

### SEO & Analytics Tables

#### `seo_audits` — SEO Audit Results
```sql
id, client_id, website_url, audit_data(JSON), overall_score, status, 
report_pdf_path, ai_provider, created_by, created_at, completed_at
```

#### `keyword_rankings` — Keyword Position Tracking
```sql
id, client_id, keyword, position, previous_position, search_volume, 
url, tracked_date, created_at
```

#### `client_reports` — Generated Reports
```sql
id, client_id, project_id, title, report_type, report_data(JSON), 
branding_config(JSON), generated_by, generated_at, sent_to_client, 
sent_date, sent_by
```
**Types:** weekly, monthly, audit, custom, white_label

### Operations Tables

#### `contracts` — Client Contracts
```sql
id, client_id, title, start_date, end_date, terms, status, 
monthly_value, auto_renew, created_by, created_at
```

#### `time_entries` — Time Tracking
```sql
id, user_id, task_id, project_id, start_time, end_time, duration_minutes, 
description, billable, created_at
```

#### `file_attachments` — Uploaded Files
```sql
id, related_type, related_id, filename, original_filename, file_size, 
mime_type, uploaded_by, uploaded_at
```
**MIME types allowed:** PDF, images (png/jpg/gif/webp), CSV, text, spreadsheets, docs, zip

#### `approval_requests` — Client Approval Workflow
```sql
id, client_id, project_id, task_id, title, description, content_preview, 
requested_by, status, reviewed_by, review_notes, created_at, reviewed_at
```
**Status:** pending, approved, rejected, revision_requested

#### `client_locations` — Multi-Location Support
```sql
id, client_id, location_name, address, city, state, zip_code, phone, 
gbp_url, is_primary, created_at
```

#### `activity_log` — Audit Trail
```sql
id, user_id, action, details, entity_type, entity_id, ip_address, created_at
```

#### `notifications` — In-App Notifications
```sql
id, user_id, title, message, type, is_read, link, created_at
```

### Communication Tables

#### `chat_messages` — Website Chatbot
```sql
id, session_id, visitor_name, visitor_email, business_name, industry, 
location, website_url, messages(JSON), status, created_at
```

#### `team_chats` — Internal Team Chat
```sql
id, from_user_id, to_user_id, message, is_read, created_at
```

#### `chat_requests` — Chat Request Queue
```sql
id, from_user_id, to_user_id, status, created_at
```

### Other Tables

#### `client_credentials` — Client Credentials Vault
```sql
id, client_id, platform, username, password_encrypted, notes, 
added_by, created_at
```

#### `sales_leads` — Sales Pipeline
```sql
id, business_name, contact_name, email, phone, industry, city, 
website, source, status, estimated_value, notes, assigned_to, created_at
```
**Status:** new, contacted, qualified, proposal_sent, negotiation, won, lost

#### `social_posts` — Social Media Posts
```sql
id, client_id, platform, content, media_url, status, scheduled_date, 
posted_date, engagement_data, created_by, created_at
```

#### `suggestions` — System Suggestions
```sql
id, user_id, client_id, title, description, category, priority, 
status, created_at
```

#### `api_settings` — API Integration Config
```sql
id, provider, api_key, is_active, config_json, updated_by, updated_at
```
**Providers:** claude, chatgpt, gemini, twilio, smtp, stripe, whatsapp, slack, google_search_console

#### `package_tasks` — Package Task Templates
```sql
id, package_name, task_title, task_description, task_type, frequency, 
priority, order_index, created_at
```

---

## 6. Backend API Endpoints (99 Endpoints)

### Authentication & Pages (Lines 90-480)

| # | Method | Endpoint | Auth | Function | What It Does |
|---|--------|----------|------|----------|-------------|
| 1 | GET | `/login` | None | `login_page()` | Renders login form |
| 2 | POST | `/login` | None | `login_submit()` | Validates username/password, sets JWT cookie, redirects to dashboard |
| 3 | GET | `/logout` | None | `logout()` | Clears cookie, redirects to login |
| 4 | GET | `/` | None | `home()` | Redirects to /dashboard |
| 5 | GET | `/dashboard` | Auth | `dashboard()` | Role-based dashboard (admin/client/worker/finance/ops/sales/social) |
| 6 | GET | `/settings` | super_admin | `settings_page()` | API settings page — shows all 9 integrations |
| 7 | GET | `/client/{id}` | Auth | `client_detail()` | Client detail with files, locations, reports, rankings |
| 8 | GET | `/client-portal` | client | `client_portal()` | Client's own projects, invoices, reports |
| 9 | GET | `/monitor` | super_admin | `monitor_page()` | Team monitoring dashboard |
| 10 | GET | `/team-chat` | Auth | `team_chat()` | Internal team chat |
| 11 | GET | `/activity` | Auth | `activity_page()` | Activity timeline with filters |
| 12 | GET | `/performance` | Auth | `performance_page()` | Worker performance leaderboard |
| 13 | GET | `/analytics` | Auth | `analytics_page()` | Revenue analytics with Chart.js |
| 14 | GET | `/rankings/{id}` | Auth | `rankings_page()` | Keyword ranking chart for client |

### CRUD Operations (Lines 484-760)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 15 | POST | `/api/clients` | super_admin, sales, ops | Create new client |
| 16 | POST | `/api/projects` | super_admin, ops | Create new project |
| 17 | POST | `/api/tasks` | Auth | Create task |
| 18 | PUT | `/api/tasks/{id}/status` | Auth | Update task status |
| 19 | POST | `/api/users` | super_admin | Create new user |
| 20 | POST | `/api/leads` | Auth | Create sales lead |
| 21 | PUT | `/api/leads/{id}/status` | Auth | Update lead status |
| 22 | POST | `/api/social-posts` | Auth | Create social media post |
| 23 | POST | `/api/audit` | Auth | Create SEO audit |
| 24 | POST | `/api/notifications/{id}/read` | Auth | Mark notification read |
| 25 | POST | `/api/expenses` | finance | Add expense |
| 26 | POST | `/api/client-credentials` | super_admin | Store client credentials |
| 27 | POST | `/api/settings/api` | super_admin | Save API key/settings |
| 28 | POST | `/api/suggestions` | Auth | Create suggestion |
| 29 | PUT | `/api/suggestions/{id}` | super_admin | Update suggestion status |

### Communication (Lines 711-850)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 30 | POST | `/api/chat-request` | Auth | Send chat request |
| 31 | PUT | `/api/chat-request/{id}` | Auth | Accept/reject chat request |
| 32 | GET | `/api/chat-messages/{uid}` | Auth | Get chat history |
| 33 | POST | `/api/chat-messages` | Auth | Send chat message |
| 34 | POST | `/api/reports/generate` | Auth | Generate client report |
| 35 | GET | `/api/reports/{id}/download` | Auth | Download report as JSON |
| 36 | POST | `/api/reports/{id}/send` | super_admin, finance | Mark report as sent |
| 37 | POST | `/api/chat` | None | Website chatbot save |

### AI & Automation (Lines 866-920)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 38 | POST | `/api/tasks/{id}/run-auto` | Auth | Run AI task (demo result if no key) |

### Time Tracking (Lines 936-1015)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 39 | POST | `/api/time/start` | Auth | Start timer on task |
| 40 | POST | `/api/time/stop` | Auth | Stop active timer |
| 41 | GET | `/api/time/active` | Auth | Get user's active timer |
| 42 | GET | `/api/time/entries` | Auth | Get time entries (filterable) |

### Invoicing (Lines 1018-1150)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 43 | POST | `/api/invoices` | super_admin, finance | Create invoice with line items |
| 44 | GET | `/api/invoices` | Auth | List invoices (client-filtered for client role) |
| 45 | PUT | `/api/invoices/{id}/status` | super_admin, finance | Update invoice status (paid, overdue, etc.) |
| 46 | GET | `/api/invoices/{id}/download` | Auth | Download invoice as styled HTML |

### File Uploads (Lines 1123-1150)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 47 | POST | `/api/upload` | Auth | Upload file (10MB max, MIME validated) |
| 48 | GET | `/uploads/{filename}` | Auth | Serve uploaded file |

### Approvals (Lines 1153-1200)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 49 | POST | `/api/approvals` | Auth | Create approval request |
| 50 | PUT | `/api/approvals/{id}` | client, super_admin | Approve/reject content |

### Data Export (Lines 1181-1250)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 51 | GET | `/api/export/{table}` | super_admin | Export table as CSV |
| 52 | GET | `/api/activity` | Auth | Get activity log (filterable by type) |

### Rankings & Contracts (Lines 1253-1320)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 53 | POST | `/api/rankings` | Auth | Add keyword ranking |
| 54 | GET | `/api/rankings/{id}` | Auth | Get client rankings |
| 55 | GET | `/api/contracts` | Auth | List contracts |
| 56 | POST | `/api/contracts` | super_admin, ops, finance | Create contract |

### Security (Lines 1303-1320)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 57 | POST | `/api/change-password` | Auth | Change own password |

### White-Label Reports (Lines 1323-1545)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 58 | POST | `/api/reports/white-label` | super_admin, finance | Generate white-label report with custom branding |
| 59 | GET | `/api/reports/{id}/white-label` | Auth | View branded report as styled HTML |

### Email (Lines 1449-1545)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 60 | POST | `/api/email/send` | super_admin | Send email via SMTP |
| 61 | POST | `/api/reports/{id}/email` | super_admin, finance | Email report to client |

### Attachments & Locations (Lines 1546-1610)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 62 | GET | `/api/attachments/{type}/{id}` | Auth | Get files for entity |
| 63 | POST | `/api/locations` | super_admin, ops | Add client location |
| 64 | GET | `/api/locations/{id}` | Auth | Get client locations |

### Performance & Notifications (Lines 1627-1760)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 65 | GET | `/api/performance/{uid}` | Auth | Worker performance score (0-100) |
| 66 | GET | `/api/notifications` | Auth | Get user notifications |
| 67 | POST | `/api/notifications/read` | Auth | Mark all notifications read |
| 68 | POST | `/api/notifications/create` | super_admin, ops | Create notification |
| 69 | POST | `/api/tasks/bulk` | super_admin, ops | Bulk create tasks |
| 70 | PUT | `/api/tasks/{id}/status` | Auth | Update task status (v2) |

### Search (Lines 1762-1830)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 71 | GET | `/api/search?q=term` | Auth | Search clients, projects, tasks |

### Analytics & Revenue (Lines 1785-1930)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 72 | GET | `/api/analytics/revenue` | super_admin, finance | Revenue data + 6-month forecast |
| 73 | GET | `/api/analytics/overview` | Auth | Overview stats (clients, revenue, tasks, projects) |
| 74 | PUT | `/api/projects/{id}/progress` | Auth | Update project progress % |

### Part 5: API Integrations (Lines 1940-2548)

| # | Method | Endpoint | Auth | What It Does |
|---|--------|----------|------|-------------|
| 75 | POST | `/api/ai/audit/{client_id}` | super_admin, tech_seo, ops | AI SEO audit (demo or live) |
| 76 | POST | `/api/ai/content/generate` | Auth (content roles) | Generate blog/social content |
| 77 | POST | `/api/ai/competitor-analysis/{id}` | super_admin, tech_seo, ops | AI competitor analysis |
| 78 | POST | `/api/ai/chat-assistant` | Auth | AI Q&A assistant for workers |
| 79 | POST | `/api/voice/incoming` | Public | Twilio IVR webhook |
| 80 | POST | `/api/voice/menu` | Public | Voice menu handler |
| 81 | POST | `/api/voice/recording` | Public | Call recording handler |
| 82 | POST | `/api/voice/outbound` | super_admin, sales, acct_mgr | Make outbound call |
| 83 | POST | `/api/whatsapp/send` | super_admin, sales, acct_mgr, ops | Send WhatsApp message |
| 84 | POST | `/api/whatsapp/webhook` | Public | WhatsApp incoming webhook |
| 85 | GET | `/api/whatsapp/webhook` | Public | WhatsApp verification |
| 86 | POST | `/api/slack/send` | super_admin, ops | Send Slack notification |
| 87 | POST | `/api/slack/events` | Public | Slack events API |
| 88 | GET | `/api/gsc/rankings/{id}` | Auth | Get GSC keyword data |
| 89 | POST | `/api/gsc/sync/{id}` | super_admin, tech_seo, ops | Sync GSC rankings to DB |
| 90 | POST | `/api/billing/create-subscription` | super_admin, finance | Create Stripe subscription |
| 91 | POST | `/api/billing/cancel-subscription` | super_admin, finance | Cancel subscription |
| 92 | POST | `/api/billing/webhook` | Public | Stripe payment webhook |
| 93 | POST | `/api/billing/send-reminder` | super_admin, finance | Send payment reminder |
| 94 | POST | `/api/user/theme` | Auth | Set dark/light mode |
| 95 | GET | `/api/user/theme` | Auth | Get theme preference |
| 96 | POST | `/api/scheduled-tasks/create` | super_admin, ops | Create scheduled task |
| 97 | POST | `/api/email/campaign` | super_admin, social, sales | Send email campaign |
| 98 | GET | `/api/integrations/status` | super_admin | Check all integration status |
| 99 | POST | `/api/email/send` | super_admin | Direct email send via SMTP |

---

## 7. Frontend Pages (25 Pages)

### Services (10 pages)
| Page | File | Pricing Tiers |
|------|------|---------------|
| Local SEO | `pages/local-seo.html` | Starter $497, Growth $997, Dominate $1997 |
| GBP Optimization | `pages/gbp-optimization.html` | Basic $297, Pro $597, Enterprise $997 |
| Reputation Management | `pages/reputation-management.html` | Monitor $497, Defend $997, Dominate $1997 |
| AI SEO Services | `pages/ai-seo.html` | AI Starter $797, AI Growth $1497, AI Enterprise $2997 |
| Paid Advertising | `pages/paid-advertising.html` | Starter $500, Growth $1500, Enterprise $3000 |
| Social Media | `pages/social-media.html` | Starter $497, Growth $997, Premium $1997 |
| Content Creation | `pages/content-creation.html` | Blog $500, Full Content $1200, Authority $2500 |
| Video SEO | `pages/video-seo.html` | Starter $500, Growth $1200, Dominate $2000 |
| CRO | `pages/cro.html` | Audit $800, Growth $1800, Full CRO $3500 |
| E-Commerce SEO | `pages/ecommerce-seo.html` | Starter $997, Growth $2497, Enterprise $4997 |

### Industries (6 pages)
| Page | File | Focus Keywords |
|------|------|----------------|
| SEO for Dentists | `pages/seo-for-dentists.html` | dentist near me, dental clinic SEO |
| SEO for Lawyers | `pages/seo-for-lawyers.html` | attorney SEO, lawyer near me |
| SEO for Restaurants | `pages/seo-for-restaurants.html` | restaurant SEO, food delivery SEO |
| SEO for Plumbers | `pages/seo-for-plumbers.html` | plumber SEO, plumbing services near me |
| SEO for HVAC | `pages/seo-for-hvac.html` | HVAC SEO, AC repair near me |
| SEO for Medical Spas | `pages/seo-for-medical-spas.html` | med spa SEO, Botox near me |

### Other Pages (9 pages)
Homepage, About, Blog, Case Studies, Contact, Free Audit, Privacy Policy, Terms, Disclaimer

### Page Structure Pattern
Every service/industry page follows the same HTML pattern:
```
1. <header> — Nav with Services dropdown + Industries dropdown
2. <section class="page-hero"> — Breadcrumb, H1, description, CTA button
3. <section class="service-detail"> — 2-column grid (text + metrics card)
4. <section class="section-light"> — Feature list (5-6 items with icons)
5. <section> — 3-tier pricing cards
6. <section class="cta-section"> — Final CTA
7. <footer> — Links, copyright
```

---

## 8. Dashboard Templates (16 Templates)

| Template | File | Role Access | Key Features |
|----------|------|-------------|--------------|
| Login | `login.html` | All | Username/password form |
| Admin Dashboard | `admin_dashboard.html` | super_admin | Stats cards, clients table, projects, leads, quick actions |
| Client Portal | `client_portal.html` | client | Own projects, invoices, reports, approval requests |
| Client Detail | `client_detail.html` | admin/worker | Full client view: files, locations, reports, rankings |
| Worker Dashboard | `worker_dashboard.html` | worker/tech_seo | Assigned tasks, timer, time entries |
| Finance Dashboard | `finance_dashboard.html` | finance | Revenue, expenses, invoices, payments |
| Ops Dashboard | `ops_dashboard.html` | operations_manager | All projects, tasks, team overview |
| Sales Dashboard | `sales_dashboard.html` | sales | Leads pipeline, follow-ups |
| Social Dashboard | `social_dashboard.html` | social_media | Scheduled posts, content calendar |
| Settings | `settings.html` | super_admin | 9 API integrations grouped by category |
| Analytics | `analytics.html` | Auth | 6 Chart.js charts: revenue, clients, tasks, projects |
| Activity Timeline | `activity_timeline.html` | Auth | Color-coded activity log with filters |
| Performance | `performance.html` | Auth | Worker leaderboard with scores |
| Rankings Chart | `rankings_chart.html` | Auth | Chart.js keyword position charts |
| Monitor | `monitor.html` | super_admin | Team activity monitor |
| Team Chat | `team_chat.html` | Auth | Internal messaging |

---

## 9. User Roles & Permissions (11 Roles)

| Role | Dashboard | Key Permissions |
|------|-----------|----------------|
| `super_admin` | admin_dashboard | Full access — all endpoints, settings, user management |
| `tech_seo` | worker_dashboard | SEO audits, tasks, rankings, AI tools |
| `content_writer` | worker_dashboard | Content tasks, AI content generation |
| `link_builder` | worker_dashboard | Link building tasks, outreach |
| `social_media` | social_dashboard | Social posts, content calendar, email campaigns |
| `finance` | finance_dashboard | Invoices, expenses, payments, billing, contracts |
| `sales` | sales_dashboard | Leads, outbound calls, WhatsApp, proposals |
| `account_manager` | worker_dashboard | Client communication, outbound calls, WhatsApp |
| `operations_manager` | ops_dashboard | All operations: projects, tasks, team, scheduling |
| `client` | client_portal | Own projects, invoices, approvals, reports only |
| `worker` | worker_dashboard | Assigned tasks, time tracking |

### Permission Logic
Located in `main.py` lines ~70-88:
```python
def require_auth(request) → dict     # Returns user or redirects to /login
def require_role(request, roles) → dict  # Returns user or raises 403
```

---

## 10. API Integrations (9 Integrations)

All integrations work in **demo mode** without API keys. Real API keys are configured in Settings page.

| # | Integration | Demo Behavior | Production Library | Cost |
|---|-------------|--------------|-------------------|------|
| 1 | Claude AI | Returns mock SEO audit data | `anthropic` | ~$3-15/MTok |
| 2 | ChatGPT | Returns mock content | `openai` | ~$2.50-10/MTok |
| 3 | Gemini | Returns mock analysis | `google-generativeai` | Free tier + $1.25/MTok |
| 4 | SMTP Email | Logs email action | `smtplib` (built-in) | Free (Gmail) |
| 5 | Twilio | Returns TwiML XML | `twilio` | $1/mo + per-call |
| 6 | WhatsApp | Logs message action | Meta Graph API | Free 1000/mo |
| 7 | Slack | Logs notification | `requests` | Free |
| 8 | Stripe | Creates demo subscription + invoice | `stripe` | 2.9% + $0.30 |
| 9 | Google Search Console | Returns mock keyword data | `google-api-python-client` | Free |

**To switch to production:** Search `# PRODUCTION:` in `main.py` — each integration has commented-out real API code ready to uncomment.

**Full setup guide:** See `API_GUIDE.md`

---

## 11. Security Features

| Feature | Location | Details |
|---------|----------|---------|
| JWT Authentication | `main.py` line 39 | 256-bit secret key, 24hr expiry, HttpOnly cookie |
| bcrypt Password Hashing | `database.py` | passlib bcrypt backend, hash stored in DB |
| Rate Limiting | `main.py` | In-memory rate limit store, per-IP tracking |
| Security Headers | `main.py` lines 26-34 | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy |
| RBAC | `main.py` require_role() | Role-based access on every endpoint |
| SQL Injection Prevention | All queries | Parameterized queries (`?` placeholders) |
| File Upload Validation | `main.py` line 1123 | 10MB max, MIME type whitelist |
| CSRF Protection | JWT cookie | SameSite=lax cookie attribute |
| Password Change | `/api/change-password` | Requires old password verification |
| Activity Logging | `log_activity()` | Every action logged with user ID, IP, timestamp |

---

## 12. Demo Credentials

| Username | Password | Role | Dashboard |
|----------|----------|------|-----------|
| admin | admin123 | super_admin | Full admin dashboard |
| client_chen | password123 | client | Client portal |
| ops_manager | password123 | operations_manager | Operations dashboard |
| rachel_g | password123 | finance | Finance dashboard |
| sarah_k | password123 | tech_seo | Worker dashboard |
| mike_j | password123 | content_writer | Worker dashboard |
| alex_r | password123 | link_builder | Worker dashboard |
| jessica_m | password123 | social_media | Social dashboard |
| david_s | password123 | sales | Sales dashboard |
| emily_w | password123 | account_manager | Worker dashboard |
| tom_b | password123 | worker | Worker dashboard |

---

## 13. Key Functions Explained

### `main.py` — Core Functions

| Function | Line | What It Does |
|----------|------|-------------|
| `security_headers()` | 27 | Middleware: adds security headers to all responses |
| `require_auth(request)` | ~70 | Decodes JWT from cookie, returns user dict or redirects to /login |
| `require_role(request, roles)` | ~80 | Calls require_auth + checks role in allowed list |
| `log_activity(db, user_id, action, details, entity_type, entity_id)` | ~85 | Inserts into activity_log table |
| `dashboard()` | 150 | Routes to correct dashboard template based on user role |
| `login_submit()` | 94 | Validates credentials, creates JWT, sets cookie |

### `database.py` — Core Functions

| Function | Line | What It Does |
|----------|------|-------------|
| `get_db()` | ~5 | Returns SQLite connection with Row factory |
| `init_db()` | ~15 | Creates all 27 tables + populates demo data |

### Dashboard Routing Logic (`main.py` line ~150)
```python
role → template mapping:
  super_admin      → admin_dashboard.html
  client           → client_portal.html
  finance          → finance_dashboard.html
  operations_manager → ops_dashboard.html
  sales            → sales_dashboard.html
  social_media     → social_dashboard.html
  *                → worker_dashboard.html (default for all workers)
```

### Performance Score Calculation (`main.py` line ~1627)
```python
score = (
    task_completion_rate * 0.4 +     # % of completed tasks
    hours_factor * 0.3 +              # hours logged (40+ = 100%)
    project_factor * 0.3              # active projects (3+ = 100%)
)
# Result: 0-100 score displayed on leaderboard
```

### Revenue Forecasting (`main.py` line ~1785)
```python
# Takes: all invoices, active contracts
# Calculates: monthly revenue from paid invoices
# Forecasts: next 6 months based on active contract values
# Returns: { monthly_data, forecast, total_revenue, mrr }
```

---

## 14. How to Modify

### Adding a New Service Page
1. Copy any existing page from `pages/` (e.g., `pages/local-seo.html`)
2. Change: `<title>`, `<h1>`, meta tags, pricing, features
3. Add nav link in `index.html` under Services dropdown
4. Add nav link in the new page's own `<header>` section

### Adding a New API Endpoint
1. Open `dashboard/main.py`
2. Add endpoint before `if __name__ == "__main__":`
```python
@app.post("/api/your-endpoint")
async def your_function(request: Request):
    user = require_role(request, ["super_admin"])  # Set allowed roles
    data = await request.json()
    db = get_db()
    # ... your logic ...
    log_activity(db, user["id"], "action_name", "description", "entity_type", entity_id)
    db.commit()
    db.close()
    return {"message": "Done"}
```

### Adding a New Database Table
1. Open `dashboard/database.py`
2. Add `CREATE TABLE IF NOT EXISTS` in `init_db()` function
3. Add demo data INSERT at the bottom of `init_db()`
4. Delete `agency.db` and restart to regenerate

### Adding a New Dashboard Template
1. Create file in `dashboard/templates/your_template.html`
2. Follow existing template structure (sidebar, main, header-bar)
3. Add route in `main.py`:
```python
@app.get("/your-page", response_class=HTMLResponse)
async def your_page(request: Request):
    user = require_auth(request)
    return templates.TemplateResponse("your_template.html", {"request": request, "user": user})
```

### Adding a New User Role
1. Update `users` table CHECK constraint in `database.py`
2. Add role → template mapping in `dashboard()` function in `main.py`
3. Create dashboard template if needed
4. Add role to `require_role()` calls for relevant endpoints

### Switching from Demo to Live API
1. Go to Settings page (login as admin)
2. Paste real API key for desired integration
3. Click "Save & Activate"
4. OR: In `main.py`, search for `# PRODUCTION:` comments and uncomment the real API code
5. Install required pip packages (see `API_GUIDE.md`)

### Deploying to Production
1. See `DEPLOYMENT_GUIDE.md` for cPanel/VPS setup
2. Change `SECRET_KEY` to a fixed value (not random)
3. Switch from SQLite to PostgreSQL for production load
4. Set up HTTPS with SSL certificate
5. Configure API keys in Settings
6. Set up Twilio/WhatsApp webhook URLs to point to your domain

---

## File Modification Quick Reference

| Want to change... | Edit this file | Location |
|-------------------|---------------|----------|
| Homepage content | `index.html` | Full file |
| Color theme | `css/style.css` | Lines 1-50 (CSS variables) |
| Dashboard styles | `dashboard/static/css/dashboard.css` | Full file |
| API endpoints | `dashboard/main.py` | See endpoint table above |
| Database schema | `dashboard/database.py` | `init_db()` function |
| Dashboard UI | `dashboard/templates/*.html` | Respective template |
| Service page | `pages/[service].html` | Full file |
| Navigation links | `index.html` (homepage) or `pages/*.html` (inner pages) | `<nav>` section |
| API keys | Dashboard → Settings UI | OR `dashboard/main.py` PRODUCTION comments |
| Demo data | `dashboard/database.py` | Bottom of `init_db()` |
| User roles | `dashboard/database.py` + `dashboard/main.py` | CHECK constraint + require_role() |

---

*Generated: May 2026 | Total: ~9,700 lines of code | 99 endpoints | 27 tables | 9 integrations | 25 pages | 16 templates*
