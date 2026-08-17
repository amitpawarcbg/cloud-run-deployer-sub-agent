from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from agents.slack_notifier import slack_notifier_agent

app = FastAPI(
    title="image-creator-slack-notifier-sub-agent Microservice",
    description="Sub-agent container service for rendering status cards, GCS upload, and Slack notifications.",
    version="1.0.0"
)

class NotifyRequest(BaseModel):
    repo: str
    pr_id: int
    commit: str
    image: str
    service_url: str

@app.get("/health")
def health_check():
    return {"status": "healthy", "agent": "image-creator-slack-notifier-sub-agent"}

@app.post("/notify", status_code=status.HTTP_200_OK)
def notify_slack(req: NotifyRequest):
    result = slack_notifier_agent.create_image_and_post_to_slack(
        repo=req.repo,
        pr_id=req.pr_id,
        commit=req.commit,
        image=req.image,
        service_url=req.service_url
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
