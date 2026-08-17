from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from agents.cloud_run_deployer import cloud_run_deployer_agent

app = FastAPI(
    title="cloud-run-deployer-sub-agent Microservice",
    description="Sub-agent container service for provisioning and updating Cloud Run services.",
    version="1.0.0"
)

class DeployRequest(BaseModel):
    image: str
    agent_md_content: str
    commit: str

@app.get("/health")
def health_check():
    return {"status": "healthy", "agent": "cloud-run-deployer-sub-agent"}

@app.post("/deploy", status_code=status.HTTP_200_OK)
def deploy_service(req: DeployRequest):
    result = cloud_run_deployer_agent.deploy_cloud_run_service(
        image=req.image,
        agent_md_content=req.agent_md_content,
        commit=req.commit
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
