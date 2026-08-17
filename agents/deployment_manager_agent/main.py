from fastapi import FastAPI, HTTPException, status
from typing import Dict, Any
from agents.deployment_manager import deployment_manager_agent

app = FastAPI(
    title="deployment-manager-agent Microservice",
    description="Main Orchestrator Agent service invoking sub-agents for end-to-end CI/CD deployments.",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "agent": "deployment-manager-agent"}

@app.post("/prepare_deploy_context", status_code=status.HTTP_200_OK)
def prepare_deploy_context(payload: Dict[str, Any]):
    result = deployment_manager_agent.prepare_deploy_context(payload)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
