import os
import logging
from typing import Dict, Any
from agents.base import BaseADKAgent
from agents.image_builder import image_builder_agent
from agents.cloud_run_deployer import cloud_run_deployer_agent
from agents.slack_notifier import slack_notifier_agent

logger = logging.getLogger("deployment-manager-agent")

class DeploymentManagerAgent(BaseADKAgent):
    """
    Main Orchestrator Agent: deployment-manager-agent
    Powered by Google ADK SDK & Vertex AI gemini-2.5-flash.
    Coordinates sub-agents via Agent-to-Agent (A2A) protocol:
    1. image-builder-sub-agent (Build & GAR Push)
    2. cloud-run-deployer-sub-agent (Agent.md parse & Cloud Run deployment)
    3. image-creator-slack-notifier-sub-agent (PNG render, GCS upload & Slack alert)
    """
    def __init__(self):
        super().__init__(
            name="deployment-manager-agent",
            role="Main CI/CD Pipeline Orchestrator",
            instructions=(
                "Orchestrate PR deployment pipeline step by step: "
                "1. Build container image via image-builder-sub-agent. "
                "2. Provision Cloud Run service via cloud-run-deployer-sub-agent. "
                "3. Notify team via image-creator-slack-notifier-sub-agent."
            )
        )

    def read_agent_md_file(self) -> str:
        """
        Reads app/Agent.md file content from workspace.
        """
        possible_paths = ["app/Agent.md", "Agent.md"]
        for p in possible_paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
        
        # Default spec if file not found
        return """---
service_name: student-registration-app
cpu: "1000m"
memory: "512Mi"
concurrency: 80
env_vars:
  ENV: "production"
---"""

    def prepare_deploy_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes complete multi-agent CI/CD orchestration workflow.
        """
        repo = payload.get("repo", "cybage-devops/student-app")
        pr_id = payload.get("pr_id", 1)
        branch = payload.get("branch", "main")
        commit = payload.get("commit", "head123")
        date_str = payload.get("date", "2026-08-03")
        time_str = payload.get("time", "13:20:00").replace(":", "")

        tag = f"pr{pr_id}-{commit[:7]}-{date_str}-{time_str}"
        logger.info(f"[{self.name}] Starting deployment pipeline for PR #{pr_id} on {repo} (tag: {tag})")

        # Initial Orchestrator reasoning call via Vertex AI gemini-2.5-flash
        orchestrator_plan = self.generate_agent_reasoning(
            f"Analyze deployment request for PR #{pr_id} on repo {repo}, commit {commit}. Formulate A2A execution graph."
        )
        logger.info(f"[{self.name}] Orchestrator Plan: {orchestrator_plan}")

        # Step 1: A2A Call to image-builder-sub-agent
        logger.info(f"[{self.name}] ---> Dispatching Step 1 (Build) to image-builder-sub-agent")
        step1_result = image_builder_agent.build_and_push_image(
            repo=repo,
            branch=branch,
            tag=tag
        )
        image_name_tag = step1_result["image_name_tag"]

        # Step 2: A2A Call to cloud-run-deployer-sub-agent
        logger.info(f"[{self.name}] ---> Dispatching Step 2 (Deploy) to cloud-run-deployer-sub-agent")
        agent_md_content = self.read_agent_md_file()
        step2_result = cloud_run_deployer_agent.deploy_cloud_run_service(
            image=image_name_tag,
            agent_md_content=agent_md_content,
            commit=commit
        )
        service_url = step2_result["service_url"]

        # Step 3: A2A Call to image-creator-slack-notifier-sub-agent
        logger.info(f"[{self.name}] ---> Dispatching Step 3 (Notify) to image-creator-slack-notifier-sub-agent")
        step3_result = slack_notifier_agent.create_image_and_post_to_slack(
            repo=repo,
            pr_id=pr_id,
            commit=commit,
            image=image_name_tag,
            service_url=service_url
        )

        pipeline_summary = {
            "status": "SUCCESS",
            "orchestrator": self.name,
            "llm_model": self.model_name,
            "pipeline_plan": orchestrator_plan,
            "context": {
                "repo": repo,
                "pr_id": pr_id,
                "branch": branch,
                "commit": commit,
                "tag": tag
            },
            "step1_builder": step1_result,
            "step2_deployer": step2_result,
            "step3_notifier": step3_result,
            "final_service_url": service_url
        }

        logger.info(f"[{self.name}] Pipeline execution completed successfully! Service URL: {service_url}")
        return pipeline_summary

deployment_manager_agent = DeploymentManagerAgent()
