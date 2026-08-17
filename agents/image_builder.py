import os
import time
import shutil
import logging
import subprocess
from typing import Dict, Any
from agents.base import BaseADKAgent, settings

logger = logging.getLogger("image-builder-agent")

class ImageBuilderSubAgent(BaseADKAgent):
    """
    Sub-Agent 1: image-builder-sub-agent
    Responsibility: Accepts repo, branch, and tag specifications, clones latest merged commit from GitHub,
    builds application container image via Cloud Build, pushes to Google Artifact Registry (GAR),
    and returns final image_name:tag.
    """
    def __init__(self):
        super().__init__(
            name="image-builder-sub-agent",
            role="Container Build & Registry Specialist",
            instructions="Target container build for Google Artifact Registry (GAR). Fetch source from GitHub repository."
        )

    def build_and_push_image(self, repo: str, branch: str, tag: str) -> Dict[str, Any]:
        """
        Executes build and push of application container image to GAR via non-blocking Cloud Build async submission.
        Returns payload containing image_name:tag.
        """
        logger.info(f"[{self.name}] Initiating build for repo={repo}, branch={branch}, tag={tag}")
        
        reasoning = self.generate_agent_reasoning(f"Prepare GAR build for {repo} on branch {branch} with tag {tag}")
        logger.info(f"[{self.name}] Agent Reasoning: {reasoning}")

        repo_basename = repo.split("/")[-1].lower()
        project_id = settings.gcp_project_id
        region = settings.gcp_region
        image_repo_path = f"{region}-docker.pkg.dev/{project_id}/{settings.gar_repository}/{repo_basename}"
        unique_image_tag = f"{image_repo_path}:{tag}"
        latest_image_tag = f"{image_repo_path}:latest"

        # Clone merged commit source from GitHub into temp folder
        clone_dir = f"/tmp/repo_{tag}"
        if os.path.exists(clone_dir):
            shutil.rmtree(clone_dir, ignore_errors=True)

        github_url = f"https://github.com/{repo}.git"
        clone_cmd = f"git clone --depth 1 {github_url} {clone_dir}"
        logger.info(f"[{self.name}] Cloning GitHub repository: {clone_cmd}")
        
        try:
            clone_res = subprocess.run(clone_cmd, shell=True, capture_output=True, text=True, timeout=60)
            logger.info(f"[{self.name}] Git clone stdout: {clone_res.stdout.strip()}")
            if not os.path.exists(os.path.join(clone_dir, "Dockerfile")):
                raise FileNotFoundError(f"Dockerfile not found in cloned directory {clone_dir}")
            build_dir = clone_dir
        except Exception as e:
            logger.error(f"[{self.name}] Git clone error: {e}")
            raise RuntimeError(f"Git clone failed for {github_url}: {e}")

        # Submit Cloud Build asynchronously to avoid stdout pipe buffer deadlock inside Cloud Run container
        submit_command = f"gcloud builds submit {build_dir} --tag {unique_image_tag} --project {project_id} --async --format=\"value(id)\""
        logger.info(f"[{self.name}] Executing async build submission: {submit_command}")

        try:
            submit_res = subprocess.run(
                submit_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            if submit_res.returncode != 0:
                raise RuntimeError(f"gcloud builds submit --async failed: {submit_res.stderr.strip()}")

            build_id = submit_res.stdout.strip()
            logger.info(f"[{self.name}] Cloud Build submitted successfully with Build ID: {build_id}")

            # Poll Cloud Build status until completion (max 600s)
            start_time = time.time()
            build_status = "WORKING"

            while build_status in ["WORKING", "QUEUED", "PENDING"]:
                if time.time() - start_time > 600:
                    raise TimeoutError(f"Cloud Build {build_id} timed out after 600 seconds")

                time.sleep(10)
                status_cmd = f"gcloud builds describe {build_id} --project {project_id} --format=\"value(status)\""
                status_res = subprocess.run(status_cmd, shell=True, capture_output=True, text=True, timeout=30)
                build_status = status_res.stdout.strip()
                logger.info(f"[{self.name}] Cloud Build {build_id} status: {build_status}")

            if build_status != "SUCCESS":
                raise RuntimeError(f"Cloud Build {build_id} failed with status: {build_status}")

            logger.info(f"[{self.name}] Cloud Build {build_id} completed successfully!")

        except Exception as e:
            logger.error(f"[{self.name}] Build error: {e}")
            raise RuntimeError(f"Build failed for {unique_image_tag}: {e}")
        finally:
            if os.path.exists(clone_dir):
                shutil.rmtree(clone_dir, ignore_errors=True)

        return {
            "status": "SUCCESS",
            "agent": self.name,
            "repo": repo,
            "branch": branch,
            "image_name_tag": unique_image_tag,
            "gar_repository": settings.gar_repository,
            "build_command": submit_command,
            "reasoning": reasoning
        }

image_builder_agent = ImageBuilderSubAgent()
