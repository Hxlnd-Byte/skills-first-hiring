"""Tests run without Docker or a real model: the AI is replaced by a stand-in."""
import os
import tempfile
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["SKIP_MODEL_PULL"] = "1"

import pytest
from fastapi.testclient import TestClient

from app import llm, main, rules

SAMPLE_CV = (Path(__file__).parent.parent / "sample-cvs" / "marco-bianchi.txt").read_text(encoding="utf-8")


@pytest.fixture()
def client(monkeypatch):
    llm.STATUS["ready"] = True
    c = TestClient(main.app)
    c.post("/api/reset")
    yield c


def fake_cv_answer(*_args, **_kw):
    return {
        "name": "Marco Bianchi", "headline": "Solutions architect, supply chain software", "location": "Dubai",
        "jobs": [{"title": "Solutions Architect", "company": "Freightly", "dates": "2021 - present"}],
        "skills": [
            {"id": "disc", "score": 82, "evidence": "Led discovery workshops with operations directors at 12 logistics companies"},
            {"id": "demo", "score": 75, "evidence": "Built tailored demos of warehouse dashboards"},
            {"id": "cloud", "score": 88, "evidence": "Designed cloud architectures on Azure for multi-site warehouse customers"},
            {"id": "exec", "score": 90, "evidence": "This sentence is not in the CV at all"},
            {"id": "prop", "score": 60, "evidence": "Not listed"},
            {"id": "data", "score": 72, "evidence": "Built a demand forecasting proof of concept with machine learning"},
            {"id": "arabic", "score": 10, "evidence": "Not listed"},
        ],
        "extras": ["Ran a cross-industry user group for 40 customers"],
        "strength": "Your cross-industry user group stood out.",
    }


def test_state_loads_sample(client):
    s = client.get("/api/state").json()
    assert s["role"]["title"] == "Presales Solutions Consultant"
    assert len(s["candidates"]) == 5


def test_upload_cv_scores_and_guards(client, monkeypatch):
    monkeypatch.setattr(llm, "chat", fake_cv_answer)
    r = client.post("/api/cvs", files=[("files", ("marco-bianchi.txt", SAMPLE_CV.encode(), "text/plain"))])
    res = r.json()["results"][0]
    assert "candidate" in res, res
    s = client.get("/api/state").json()
    c = next(x for x in s["candidates"] if x["id"] == res["candidate"])
    assert c["name"] == "Marco Bianchi"
    assert c["ev"]["cloud"] == 88                       # quoted evidence kept
    assert c["ev"]["exec"] <= 69                        # quote not in CV: capped and marked
    assert c["cv"]["exec"].startswith("(summary)")
    assert c["ev"]["prop"] <= 30                        # no evidence: capped
    assert c["ev"]["logi"] == 0 and c["cv"]["logi"] == "Not listed"   # skill missing from answer
    f = client.get(f"/api/cvs/{c['id']}/file")
    assert f.status_code == 200 and b"MARCO BIANCHI" in f.content


def test_upload_rejects_bad_files(client):
    r = client.post("/api/cvs", files=[("files", ("cv.exe", b"x" * 500, "application/octet-stream")),
                                       ("files", ("short.txt", b"too short", "text/plain"))]).json()["results"]
    assert "supported" in r[0]["error"]
    assert "Hardly any text" in r[1]["error"]


def test_upload_when_ai_not_ready(client):
    llm.STATUS["ready"] = False
    r = client.post("/api/cvs", files=[("files", ("m.txt", SAMPLE_CV.encode(), "text/plain"))]).json()["results"][0]
    assert "getting ready" in r["error"]


def test_rejection_ai_ok(client, monkeypatch):
    s = client.get("/api/state").json()
    sara = next(c for c in s["candidates"] if c["id"] == "sara")
    good = ("Thank you for applying for the Presales Solutions Consultant role. Based on the CV you shared, your experience in "
            "cloud architecture wasn't yet at the level this role needs to be successful.")
    monkeypatch.setattr(llm, "chat", lambda *a, **k: {"text": good})
    r = client.post("/api/draft/rejection", json={"cand_id": "sara", "kind": "level"}).json()
    assert r["source"] == "ai" and r["text"] == good
    assert rules.reason_skill(s, sara)["id"] == "cloud"


def test_rejection_falls_back_when_rules_broken(client, monkeypatch):
    bad = "Thank you for applying. You need 10 years of experience in cloud architecture and solution demos."
    monkeypatch.setattr(llm, "chat", lambda *a, **k: {"text": bad})
    r = client.post("/api/draft/rejection", json={"cand_id": "sara", "kind": "level"}).json()
    assert r["source"] == "template"
    assert "cloud architecture" in r["text"] and "years" not in r["text"]


def test_plan_ai_and_fallback(client, monkeypatch):
    plan = {"d30": ["Meet Harbourline Freight's account team."], "d60": ["Lead discovery with Omar Saleh observing."], "d90": ["Own the Harbourline workstream."]}
    monkeypatch.setattr(llm, "chat", lambda *a, **k: plan)
    r = client.post("/api/draft/plan", json={"cand_id": "priya"}).json()
    assert r["source"] == "ai" and r["plan"]["d60"] == plan["d60"]

    def broken(*a, **k):
        raise llm.AIError("model offline")
    monkeypatch.setattr(llm, "chat", broken)
    r = client.post("/api/draft/plan", json={"cand_id": "priya"}).json()
    assert r["source"] == "rules" and len(r["plan"]["d30"]) >= 2


def test_state_roundtrip_and_validation(client):
    s = client.get("/api/state").json()
    s["role"]["coreTarget"] = 3
    assert client.put("/api/state", json=s).status_code == 200
    assert client.get("/api/state").json()["role"]["coreTarget"] == 3
    assert client.put("/api/state", json={"role": {}}).status_code == 400


def test_page_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "Skills-First Hiring" in r.text
