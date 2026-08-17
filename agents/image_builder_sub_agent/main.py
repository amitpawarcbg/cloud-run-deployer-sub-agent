from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from agents.image_builder import image_builder_agent

app = FastAPI(
    title="image-builder-sub-agent Microservice",
    description="Sub-agent container service for building and pushing images to Google Artifact Registry.",
    version="1.0.0"
)

class BuildRequest(BaseModel):
    repo: str
    branch: str
    tag: str

@app.get("/health")
def health_check():
    return {"status": "healthy", "agent": "image-builder-sub-agent"}

@app.post("/build_and_push", status_code=status.HTTP_200_OK)
def build_and_push(req: BuildRequest):
    result = image_builder_agent.build_and_push_image(
        repo=req.repo,
        branch=req.branch,
        tag=req.tag
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
