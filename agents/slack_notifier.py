import os
import logging
import httpx
import subprocess
from typing import Dict, Any
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from agents.base import BaseADKAgent, settings

logger = logging.getLogger("slack-notifier-agent")

class ImageCreatorSlackNotifierSubAgent(BaseADKAgent):
    """
    Sub-Agent 3: image-creator-slack-notifier-sub-agent
    Responsibility: Accepts repo, pr_id, commit, image, and service_url.
    Dynamically renders a status image (PNG) displaying deployment details, uploads PNG to GCS,
    and posts notification to Slack via Webhook.
    """
    def __init__(self):
        super().__init__(
            name="image-creator-slack-notifier-sub-agent",
            role="Status Image Renderer & Slack Notification Specialist",
            instructions="Render deployment status image PNG, save artifact to GCS, and dispatch notification payload to Slack."
        )

    def render_status_image(self, repo: str, pr_id: int, commit: str, service_url: str, output_path: str) -> str:
        """
        Dynamically renders a stylish PNG deployment badge using Pillow.
        """
        width, height = 800, 400
        # Dark tech theme background
        img = Image.new("RGB", (width, height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Draw header banner
        draw.rectangle([0, 0, width, 80], fill=(37, 99, 235))
        
        # Text annotations
        draw.text((30, 25), "CLOUD RUN DEPLOYMENT SUCCESSFUL", fill=(255, 255, 255))
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Details section
        labels_values = [
            ("Repository:", repo),
            ("PR ID:", f"#{pr_id}"),
            ("Commit Hash:", commit[:8]),
            ("Deployed At:", now_str),
            ("Service URL:", service_url),
            ("Orchestrator:", "Google ADK (gemini-2.5-flash)"),
        ]

        y_offset = 120
        for label, val in labels_values:
            draw.text((40, y_offset), label, fill=(148, 163, 184))
            draw.text((200, y_offset), val, fill=(56, 189, 248) if "https" in val else (248, 250, 252))
            y_offset += 40

        # Draw success pill badge
        draw.rounded_rectangle([620, 20, 760, 60], radius=15, fill=(34, 197, 94))
        draw.text((645, 32), "LIVE 🚀", fill=(255, 255, 255))

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        logger.info(f"[{self.name}] Generated status image PNG at {output_path}")
        return output_path

    def upload_to_gcs(self, local_file_path: str, filename: str) -> str:
        """
        Uploads generated PNG artifact card to Google Cloud Storage.
        """
        try:
            from google.cloud import storage
            client = storage.Client(project=settings.gcp_project_id)
            bucket = client.bucket(settings.gcs_bucket_name)
            blob = bucket.blob(filename)
            blob.upload_from_filename(local_file_path, content_type="image/png")
            logger.info(f"[{self.name}] Successfully uploaded {filename} via SDK to GCS bucket {settings.gcs_bucket_name}")
            return f"https://storage.googleapis.com/{settings.gcs_bucket_name}/{filename}"
        except Exception as e:
            logger.warning(f"[{self.name}] GCS SDK upload error: {e}. Attempting gcloud storage cp fallback...")
            cmd = f"gcloud storage cp {local_file_path} gs://{settings.gcs_bucket_name}/{filename} --project {settings.gcp_project_id}"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info(f"[{self.name}] gcloud storage cp succeeded: {res.stdout.strip()}")
                return f"https://storage.googleapis.com/{settings.gcs_bucket_name}/{filename}"
            else:
                logger.error(f"[{self.name}] GCS upload failed via both SDK and CLI: {res.stderr.strip()}")
                raise RuntimeError(f"GCS upload failed: {e} | CLI error: {res.stderr.strip()}")

    def post_to_slack(self, repo: str, pr_id: int, commit: str, service_url: str, gcs_png_url: str) -> bool:
        """
        Dispatches Slack webhook message with deployment details and status image attachment.
        """
        payload = {
            "text": f"🚀 *Cloud Run Deployment Complete!*",
            "attachments": [
                {
                    "color": "#22c55e",
                    "title": f"Repository: {repo} (PR #{pr_id})",
                    "title_link": service_url,
                    "text": (
                        f"*Commit:* `{commit[:8]}`\n"
                        f"*Live App URL:* <{service_url}|{service_url}>\n"
                        f"*Artifact Card:* <{gcs_png_url}|View Artifact PNG Card>"
                    ),
                    "image_url": gcs_png_url,
                    "footer": "Google ADK Multi-Agent Pipeline • Vertex AI gemini-2.5-flash",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        try:
            logger.info(f"[{self.name}] Dispatching Slack notification to {settings.slack_webhook_url}")
            if not settings.slack_webhook_url.startswith("https://hooks.slack.com/services/mock"):
                response = httpx.post(settings.slack_webhook_url, json=payload, timeout=5.0)
                return response.status_code == 200
            else:
                logger.info(f"[{self.name}] Mock Slack notification delivered successfully.")
                return True
        except Exception as e:
            logger.error(f"[{self.name}] Error posting to Slack: {e}")
            return False

    def create_image_and_post_to_slack(self, repo: str, pr_id: int, commit: str, image: str, service_url: str) -> Dict[str, Any]:
        """
        Main sub-agent method: renders PNG image, uploads to GCS, and sends Slack notification.
        """
        logger.info(f"[{self.name}] Creating status image and sending Slack notification for PR #{pr_id}")

        reasoning = self.generate_agent_reasoning(
            f"Generate status image PNG card and send Slack notification for repo {repo}, PR #{pr_id}, live URL {service_url}"
        )
        logger.info(f"[{self.name}] Agent Reasoning: {reasoning}")

        date_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"pr-{pr_id}-{commit[:8]}-{date_str}.png"
        local_png_path = os.path.join("scratch", filename)

        self.render_status_image(repo, pr_id, commit, service_url, local_png_path)
        gcs_png_url = self.upload_to_gcs(local_png_path, filename)
        slack_status = self.post_to_slack(repo, pr_id, commit, service_url, gcs_png_url)

        return {
            "status": "SUCCESS",
            "agent": self.name,
            "png_file": local_png_path,
            "gcs_png_url": gcs_png_url,
            "slack_posted": slack_status,
            "reasoning": reasoning
        }

slack_notifier_agent = ImageCreatorSlackNotifierSubAgent()
