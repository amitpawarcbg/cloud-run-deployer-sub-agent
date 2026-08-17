from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.cloud_run_deployer import cloud_run_deployer_agent

app = FastAPI(title="Cloud Run Deployer Sub-Agent API")

class DeployPayload(BaseModel):
    image: str
    agent_md_content: str = ""
    commit: str = "main"

@app.get("/health")
def health():
    return {"status": "healthy", "agent": "cloud-run-deployer-sub-agent"}

@app.post("/deploy")
def deploy_service(payload: DeployPayload):
    try:
        res = cloud_run_deployer_agent.deploy_cloud_run_service(
            image=payload.image,
            agent_md_content=payload.agent_md_content,
            commit=payload.commit
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
