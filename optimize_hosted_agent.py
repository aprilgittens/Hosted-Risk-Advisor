import os
import time

from azure.ai.agentserver.optimization import load_config
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    OptimizedAgentIdentifier,
    AgentOptimizationEvaluatorRef,
    AgentOptimizationJob,
    AgentOptimizationJobInputs,
    AgentOptimizationOptions,
    AgentOptimizationReferenceDatasetInput,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
agent_name = os.environ["FOUNDRY_AGENT_NAME"]
dataset_name = os.environ["DATASET_NAME"]

dataset_version = os.environ.get("DATASET_VERSION", "1")
eval_model = os.environ.get("EVAL_MODEL", "gpt-4o")
optimization_model = os.environ.get("OPTIMIZATION_MODEL", "gpt-5")

poll_interval_seconds = int(
    os.environ.get("POLL_INTERVAL_SECONDS", "10")
)

optimization_config = load_config()

# Reads agent optimization config from:
# .agent_configs/baseline/metadata.yaml

evaluators = [
    AgentOptimizationEvaluatorRef(name="risk_advisor_quality"),
]

model_search_space = [
    "gpt-5.6-terra-1",
    "gpt-5.6-luna-1",
]

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(
        endpoint=endpoint,
        credential=credential,
    ) as project_client,
):
    job = AgentOptimizationJob(
        inputs=AgentOptimizationJobInputs(
            agent=OptimizedAgentIdentifier(
                agent_name=agent_name
            ),
            train_dataset=AgentOptimizationReferenceDatasetInput(
                name=dataset_name,
                version=dataset_version,
            ),
            evaluators=evaluators,
            options=AgentOptimizationOptions(
                max_candidates=3,
                eval_model=eval_model,
                optimization_model=optimization_model,
                optimization_config={
                    "model": optimization_config.model,
                    "system_prompt": optimization_config.instructions,
                    **(
                        {
                            "tools": optimization_config.tool_definitions
                        }
                        if optimization_config.tool_definitions
                        else {}
                    ),
                    **(
                        {
                            "skills": optimization_config.skills
                        }
                        if optimization_config.has_skills
                        else {}
                    ),
                    "model_search_space": model_search_space,
                },
            ),
        )
    )

    poller = project_client.beta.agents.begin_create_optimization_job(
        job=job,
        polling=False,
    )

    poller_details = poller.details
    if isinstance(poller_details, dict):
        job_id = (
            poller_details.get("job_id")
            or poller_details.get("jobId")
            or poller_details.get("id")
        )
    else:
        job_id = getattr(poller_details, "job_id", None)

    if not job_id:
        raise RuntimeError(
            "Optimization poller did not return a job ID in its details: "
            f"{poller_details!r}"
        )

    print(f"Optimization job ID: {job_id}")
    print("Optimization job started, waiting for completion...")

    while True:
        optimization_job = (
            project_client.beta.agents.get_optimization_job(job_id)
        )
        status = getattr(
            optimization_job.status,
            "value",
            optimization_job.status,
        ).lower()
        print(f"\tstatus=`{status}`")

        if status == "succeeded":
            result = optimization_job.result
            break

        if status in {"failed", "cancelled", "canceled"}:
            raise RuntimeError(
                f"Optimization job {job_id} {status}: "
                f"{optimization_job.error!r}"
            )

        time.sleep(poll_interval_seconds)

    if result:
        print(f"Baseline candidate: {result.baseline}")
        print(f"Best candidate: {result.best}")

        for candidate in result.candidates or []:
            print(
                f"{candidate.name}: "
                f"candidate_id={candidate.candidate_id}, "
                f"avg_score={candidate.avg_score:.4f}, "
                f"avg_tokens={candidate.avg_tokens:.0f}"
            )