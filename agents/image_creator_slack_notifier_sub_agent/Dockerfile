FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "agents.image_creator_slack_notifier_sub_agent.main:app", "--host", "0.0.0.0", "--port", "8080"]
