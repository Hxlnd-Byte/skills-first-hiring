"""Skills-First Hiring: local web app. Run with Docker (see README.md)."""
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import extract, llm, rules

HERE = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
CV_DIR = DATA_DIR / "cvs"
DB_PATH = DATA_DIR / "app.db"
MAX_CV_BYTES = 10 * 1024 * 1024
_lock = threading.Lock()

@asynccontextmanager
async def lifespan(_app):
    load_state()
    llm.start_background_pull()
    yield


app = FastAPI(title="Skills-First Hiring", docs_url=None, redoc_url=None, lifespan=lifespan)


# ---------- storage: one JSON document in SQLite, plus CV files on disk ----------

def _db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CV_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return con


def sample_state():
    return json.loads((HERE / "sample_data.json").read_text(encoding="utf-8"))


def load_state():
    with _lock, _db() as con:
        row = con.execute("SELECT value FROM kv WHERE key='state'").fetchone()
    if row:
        return json.loads(row[0])
    s = sample_state()
    save_state(s)
    return s


def save_state(s):
    with _lock, _db() as con:
        con.execute("INSERT OR REPLACE INTO kv (key, value) VALUES ('state', ?)", (json.dumps(s, ensure_ascii=False),))


def find_cand(s, cid):
    c = next((c for c in s["candidates"] if c["id"] == cid), None)
    if not c:
        raise HTTPException(404, "Candidate not found.")
    return c


# ---------- API ----------

@app.get("/api/health")
def health():
    return {"ai": llm.STATUS}


@app.get("/api/state")
def get_state():
    return load_state()


@app.put("/api/state")
def put_state(body: dict):
    for key in ("role", "team", "candidates", "clients"):
        if key not in body:
            raise HTTPException(400, f"Missing '{key}'.")
    save_state(body)
    return {"ok": True}


@app.post("/api/reset")
def reset():
    for f in CV_DIR.glob("*"):
        f.unlink(missing_ok=True)
    s = sample_state()
    save_state(s)
    return s


@app.post("/api/cvs")
def upload_cvs(files: list[UploadFile] = File(...)):
    results = []
    for up in files[:20]:
        name = os.path.basename(up.filename or "cv")
        ext = Path(name).suffix.lower()
        if ext not in extract.ALLOWED:
            results.append({"file": name, "error": "Only PDF, Word (.docx) and text files are supported."})
            continue
        data = up.file.read(MAX_CV_BYTES + 1)
        if len(data) > MAX_CV_BYTES:
            results.append({"file": name, "error": "The file is larger than 10 MB."})
            continue
        cid = "cv" + uuid.uuid4().hex[:10]
        stored = CV_DIR / f"{cid}{ext}"
        CV_DIR.mkdir(parents=True, exist_ok=True)
        stored.write_bytes(data)
        try:
            text = extract.text_from_file(stored)
            s = load_state()
            scored = llm.score_cv(text, s)
        except (extract.ExtractError, llm.AIError) as exc:
            stored.unlink(missing_ok=True)
            results.append({"file": name, "error": str(exc)})
            continue
        cand = {
            "id": cid,
            "name": scored["name"] or Path(name).stem.replace("_", " ").replace("-", " ").title(),
            "headline": scored["headline"] or "Candidate",
            "applied": f"{date.today().day} {date.today().strftime('%b')}",
            "status": "review",
            "location": scored["location"],
            "ev": scored["ev"], "cv": scored["cv"], "jobs": scored["jobs"],
            "extras": scored["extras"], "strength": scored["strength"],
            "file": {"name": name, "stored": stored.name},
        }
        s = load_state()
        s["candidates"].append(cand)
        save_state(s)
        results.append({"file": name, "candidate": cid, "name": cand["name"]})
    return {"results": results}


@app.get("/api/cvs/{cid}/file")
def cv_file(cid: str):
    if not re.fullmatch(r"cv[0-9a-f]{10}", cid):
        raise HTTPException(404, "Not found.")
    c = find_cand(load_state(), cid)
    f = c.get("file")
    if not f:
        raise HTTPException(404, "This candidate has no uploaded CV.")
    path = CV_DIR / f["stored"]
    if not path.exists():
        raise HTTPException(404, "The CV file is missing.")
    return FileResponse(path, filename=f["name"], content_disposition_type="inline")


@app.post("/api/candidates/{cid}/rescore")
def rescore(cid: str):
    s = load_state()
    c = find_cand(s, cid)
    if not c.get("file"):
        raise HTTPException(400, "Only uploaded CVs can be re-read.")
    try:
        scored = llm.score_cv(extract.text_from_file(CV_DIR / c["file"]["stored"]), s)
    except (extract.ExtractError, llm.AIError) as exc:
        raise HTTPException(503, str(exc))
    s = load_state()
    c = find_cand(s, cid)
    for key in ("ev", "cv", "jobs", "extras", "strength"):
        c[key] = scored[key]
    save_state(s)
    return c


class RejectionReq(BaseModel):
    cand_id: str
    kind: str = "level"


@app.post("/api/draft/rejection")
def draft_rejection(req: RejectionReq):
    s = load_state()
    c = find_cand(s, req.cand_id)
    kind = "more" if req.kind == "more" else "level"
    note = ""
    for _ in range(2):
        try:
            text = llm.draft_rejection(s, c, kind)
        except llm.AIError as exc:
            note = str(exc)
            break
        if rules.rejection_ok(s, c, text):
            return {"text": text, "source": "ai"}
        note = "The AI draft broke the wording rules, so the house template was used."
    return {"text": rules.template_rejection(s, c, kind), "source": "template", "note": note}


class PlanReq(BaseModel):
    cand_id: str


@app.post("/api/draft/plan")
def draft_plan(req: PlanReq):
    s = load_state()
    c = find_cand(s, req.cand_id)
    try:
        return {"plan": llm.draft_plan(s, c), "source": "ai"}
    except llm.AIError as exc:
        return {"plan": rules.plan_for(s, c), "source": "rules", "note": str(exc)}


app.mount("/", StaticFiles(directory=HERE / "static", html=True), name="static")
