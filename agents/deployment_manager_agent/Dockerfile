FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY ../agents /app/agents
COPY ../scratch /app/scratch
COPY ../app/Agent.md /app/app/Agent.md

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "agents.deployment_manager_agent.main:app", "--host", "0.0.0.0", "--port", "8080"]
