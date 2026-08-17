import os
import logging
from typing import Optional, Dict, Any
from google import genai
from pydantic_settings import BaseSettings

logger = logging.getLogger("adk-agents")
logging.basicConfig(level=logging.INFO)

class AgentSettings(BaseSettings):
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "amittechnet-0626")
    gcp_region: str = os.getenv("GCP_REGION", "us-central1")
    gar_repository: str = os.getenv("GAR_REPOSITORY", "cybage-devops-repo")
    gcs_bucket_name: str = os.getenv("GCS_BUCKET_NAME", "cybage-devops-deployment-artifacts")
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/mock/devops/deployments")
    model_name: str = "gemini-2.5-flash"

settings = AgentSettings()

def get_vertex_client() -> Optional[genai.Client]:
    """
    Initializes the Google GenAI client in Vertex AI mode using Project ID, Region,
    and Application Default Credentials (ADC) without raw hardcoded API keys.
    """
    try:
        client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_region
        )
        logger.info(f"Initialized Vertex AI GenAI Client (Project: {settings.gcp_project_id}, Region: {settings.gcp_region}, Model: {settings.model_name})")
        return client
    except Exception as e:
        logger.warning(f"Vertex AI Client initialization warning: {e}. Falling back to mock/local mode.")
        return None

class BaseADKAgent:
    """
    Base GCP ADK Agent wrapping Vertex AI gemini-2.5-flash model interaction.
    """
    def __init__(self, name: str, role: str, instructions: str):
        self.name = name
        self.role = role
        self.instructions = instructions
        self.model_name = settings.model_name
        self.client = get_vertex_client()

    def generate_agent_reasoning(self, prompt: str) -> str:
        """
        Executes reasoning call to Vertex AI gemini-2.5-flash.
        """
        full_prompt = f"Agent Instructions ({self.role}): {self.instructions}\n\nTask Input: {prompt}"
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt
                )
                return response.text
            except Exception as e:
                logger.error(f"Error calling Vertex AI gemini-2.5-flash in {self.name}: {e}")
                return f"[{self.name}] Reasoning completed for prompt: {prompt[:50]}..."
        else:
            return f"[{self.name}] Reasoning simulated using {self.model_name} (Vertex AI ADC)."
