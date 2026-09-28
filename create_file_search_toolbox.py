import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchToolboxTool
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


load_dotenv()

PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
VECTOR_STORE_ID = os.environ["VECTOR_STORE_ID"]

TOOLBOX_NAME = os.getenv(
    "FILE_SEARCH_TOOLBOX_NAME",
    "risk-advisor-file-search",
)


def main() -> None:
    credential = DefaultAzureCredential()

    with AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    ) as project:
        toolbox = project.toolboxes.create_version(
            name=TOOLBOX_NAME,
            description=(
                "Risk Advisor company-profile File Search toolbox."
            ),
            tools=[
                FileSearchToolboxTool(
                    vector_store_ids=[VECTOR_STORE_ID]
                )
            ],
        )

    version_endpoint = (
        f"{PROJECT_ENDPOINT}/toolboxes/{toolbox.name}"
        f"/versions/{toolbox.version}/mcp?api-version=v1"
    )

    default_endpoint = (
        f"{PROJECT_ENDPOINT}/toolboxes/{toolbox.name}"
        f"/mcp?api-version=v1"
    )

    print(f"Created toolbox: {toolbox.name}")
    print(f"Created version: {toolbox.version}")
    print()
    print("Version-specific MCP endpoint:")
    print(version_endpoint)
    print()
    print("Default-version MCP endpoint:")
    print(default_endpoint)
    print()
    print(
        "If this is the first version of a new toolbox, it becomes the "
        "default automatically. If you created a later version, either "
        "set FILE_SEARCH_TOOLBOX_VERSION to this version while testing "
        "or promote the version to default in Foundry."
    )


if __name__ == "__main__":
    main()
