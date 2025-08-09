from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import json
import os
from datetime import datetime

app = FastAPI(title="Agent Manager with Versioning")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

DATA_FILE = "data.json"

# ---------- Helpers ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"agents": {}}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_agent_or_404(agent_key):
    data = load_data()
    if agent_key not in data["agents"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    return data

def get_next_version_id(agent):
    if not agent["versions"]:
        return 1
    return max(v["version_id"] for v in agent["versions"]) + 1

# ---------- API ----------
@app.post("/create_agent")
def create_agent(
    name: str = Form(...),
    init_message: str = Form(""),
    prompt: str = Form(""),
    commit_message: str = Form(...)
):
    data = load_data()
    agent_key = str(uuid.uuid4())
    data["agents"][agent_key] = {
        "name": name,
        "versions": [{
            "version_id": 1,
            "init_message": init_message,
            "prompt": prompt,
            "commit_message": commit_message,
            "timestamp": datetime.utcnow().isoformat(),
            "is_head": True
        }]
    }
    save_data(data)
    return {"status": "success", "agent_key": agent_key}

@app.get("/agents")
def list_agents():
    data = load_data()
    return [{"key": k, "name": v["name"]} for k, v in data["agents"].items()]

@app.get("/agent/{agent_key}")
def get_agent(agent_key: str):
    data = load_data()
    if agent_key not in data["agents"]:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = data["agents"][agent_key]
    head_version = next(v for v in agent["versions"] if v["is_head"])
    return {"agent_key": agent_key, "name": agent["name"], **head_version}

@app.get("/agent/{agent_key}/versions")
def get_agent_versions(agent_key: str):
    data = get_agent_or_404(agent_key)
    return data["agents"][agent_key]["versions"]

@app.post("/agent/{agent_key}/update")
def update_agent(
    agent_key: str,
    init_message: str = Form(...),
    prompt: str = Form(...),
    commit_message: str = Form(...)
):
    data = get_agent_or_404(agent_key)
    agent = data["agents"][agent_key]

    # Mark all old versions as non-head
    for v in agent["versions"]:
        v["is_head"] = False

    # Create new version
    version_id = get_next_version_id(agent)
    agent["versions"].append({
        "version_id": version_id,
        "init_message": init_message,
        "prompt": prompt,
        "commit_message": commit_message,
        "timestamp": datetime.utcnow().isoformat(),
        "is_head": True
    })

    save_data(data)
    return {"status": "success", "version_id": version_id}

@app.post("/agent/{agent_key}/set_head/{version_id}")
def set_head_version(agent_key: str, version_id: int):
    data = get_agent_or_404(agent_key)
    agent = data["agents"][agent_key]
    found = False
    for v in agent["versions"]:
        v["is_head"] = (v["version_id"] == version_id)
        if v["version_id"] == version_id:
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="Version not found")
    save_data(data)
    return {"status": "success", "head_version": version_id}

# ---------- Serve UI ----------
@app.get("/")
def index():
    return FileResponse("static/index.html")
