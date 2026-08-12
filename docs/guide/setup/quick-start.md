---
title: "Quick Start"
description: "Khởi tạo project trong 5 phút"
weight: 1
---

## Quick Start Guide

### Bước 1: Clone Template

```bash
git clone https://github.com/AI20K-Build-Cohort-2/starter-code-template.git C2-App-XXX
cd C2-App-XXX
```

### Bước 2: Environment Setup

```bash
# Tạo virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Cài dependencies
pip install -r requirements.txt

# Tạo .env từ template
cp .env.example .env
# → Mở .env và điền API keys
```

### Bước 3: Chạy Backend và Frontend

```bash
# Backend — từ thư mục gốc repo
# Windows PowerShell:
python scripts/run_dev.py

# macOS/Linux có thể dùng:
# uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Mở browser: http://localhost:8000/docs
# → Phải thấy Swagger UI
```

Mở hai terminal khác để chạy frontend:

```powershell
# User frontend
cd Frontend\user
npm.cmd install
npm.cmd run dev
```

```powershell
# Admin frontend
cd Frontend\admin
npm.cmd install
npm.cmd run dev
```

Mở User tại `http://localhost:5173` và Admin tại `http://localhost:5174`.

Project dùng PostgreSQL bắt buộc. Trước khi chạy backend, kiểm tra `.env` có `DATABASE_URL`, ví dụ:

```env
DATABASE_URL=postgresql://postgres:123456@localhost:5432/orbit_1
```

### Bước 4: Git Setup

```bash
# Đổi remote origin sang repo của team
git remote set-url origin https://github.com/AI20K-Build-Cohort-2/C2-App-XXX.git

# Tạo branch develop
git checkout -b develop

# Push lần đầu
git push -u origin develop
```

## Folder Structure

```
C2-App-XXX/
├── src/                    ← Source code chính
│   ├── agents/             ← LangGraph agents
│   │   ├── graph.py        ← Graph definition
│   │   ├── state.py        ← State schema
│   │   ├── nodes/          ← Processing nodes
│   │   └── tools/          ← Agent tools
│   ├── api/                ← FastAPI routes
│   ├── models/             ← Pydantic schemas
│   ├── services/           ← Business logic
│   ├── config.py           ← Settings
│   └── main.py             ← App entry point
├── tests/                  ← Test suite
├── docs/                   ← Documentation
├── eval/                   ← Evaluation results
├── presentation/           ← Demo materials
├── Dockerfile              ← Multi-stage build
├── docker-compose.yml      ← Full stack
└── .github/workflows/      ← CI/CD
```

## Nguyên tắc tổ chức code

1. **Một file một trách nhiệm** — `graph.py` chỉ build graph, `state.py` chỉ định nghĩa state
2. **Nodes vào folder `nodes/`** — Mỗi node là một file riêng
3. **Tools vào folder `tools/`** — Mỗi tool là một file riêng
4. **API routes tách riêng** — Không trộn logic vào main.py
5. **Config centralized** — Tất cả settings trong `config.py`
