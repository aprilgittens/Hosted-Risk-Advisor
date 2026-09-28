import json
import logging
import os
from pathlib import Path

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient, FoundryToolbox
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.ai.agentserver.optimization import load_config
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hosted-risk-advisor")


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]

FILE_SEARCH_TOOLBOX_NAME = os.environ.get(
    "FILE_SEARCH_TOOLBOX_NAME",
    "risk-advisor-file-search",
)

FILE_SEARCH_TOOLBOX_VERSION = os.environ.get(
    "FILE_SEARCH_TOOLBOX_VERSION"
)


BASE_DIR = Path(__file__).resolve().parent

CLAIMS_PATH = BASE_DIR / "data" / "claims.json"
INSURANCE_PATH = BASE_DIR / "data" / "insurance-programs.json"
FACILITY_PATH = BASE_DIR / "data" / "facility-exposures.json"
SUPPLY_CHAIN_PATH = BASE_DIR / "data" / "supply-chain-exposures.json"


# ---------------------------------------------------------------------
# Load structured client data
# ---------------------------------------------------------------------

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


CLAIMS_DATA = load_json(CLAIMS_PATH)
INSURANCE_DATA = load_json(INSURANCE_PATH)
FACILITY_DATA = load_json(FACILITY_PATH)
SUPPLY_CHAIN_DATA = load_json(SUPPLY_CHAIN_PATH)


# ---------------------------------------------------------------------
# Function tools
# ---------------------------------------------------------------------

def get_claim_history(client_name: str) -> dict:
    """
    Retrieve structured historical claims and loss events for a client.

    Use this tool only when the request involves claims history, prior losses,
    incidents, loss frequency, loss severity, or historical events.

    Do not use this tool for general company-profile facts such as headquarters,
    employee count, industry, revenue, markets, products, or company overview.
    """
    return {
        "client_name": client_name,
        "data": CLAIMS_DATA.get(client_name),
    }


def get_insurance_program(client_name: str) -> dict:
    """
    Retrieve structured insurance program information for a client.

    Use this tool only when the request involves insurance coverage, limits,
    deductibles, retentions, policy structure, or insurance adequacy.

    Do not use this tool for general company-profile facts such as headquarters,
    employee count, industry, revenue, markets, products, or company overview.
    """
    return {
        "client_name": client_name,
        "data": INSURANCE_DATA.get(client_name),
    }


def get_facility_exposure(client_name: str) -> dict:
    """
    Retrieve structured facility and operational exposure data for a client.

    Use this tool only when the request involves facilities, property exposure,
    site concentration, business interruption, operational dependencies,
    catastrophe exposure, or physical operations.

    Do not use this tool merely to answer general company-profile questions
    such as headquarters, employee count, industry, revenue, or markets.
    Use File Search for those general profile facts.
    """
    return {
        "client_name": client_name,
        "data": FACILITY_DATA.get(client_name),
    }


def get_supply_chain_exposure(client_name: str) -> dict:
    """
    Retrieve structured supply-chain exposure data for a client.

    Use this tool only when the request involves suppliers, sourcing,
    logistics, inventory, third-party manufacturing, supplier concentration,
    or supply-chain resilience.

    Do not use this tool for general company-profile facts such as headquarters,
    employee count, industry, revenue, markets, products, or company overview.
    """
    return {
        "client_name": client_name,
        "data": SUPPLY_CHAIN_DATA.get(client_name),
    }


# ---------------------------------------------------------------------
# File Search toolbox
# ---------------------------------------------------------------------

def build_file_search_toolbox_url() -> str:
    if FILE_SEARCH_TOOLBOX_VERSION:
        return (
            f"{PROJECT_ENDPOINT}"
            f"/toolboxes/{FILE_SEARCH_TOOLBOX_NAME}"
            f"/versions/{FILE_SEARCH_TOOLBOX_VERSION}"
            f"/mcp?api-version=v1"
        )

    return (
        f"{PROJECT_ENDPOINT}"
        f"/toolboxes/{FILE_SEARCH_TOOLBOX_NAME}"
        f"/mcp?api-version=v1"
    )


# ---------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------

def main():
    credential = DefaultAzureCredential()

    # Load baseline or optimizer candidate configuration.
    config = load_config()

    if config is None:
        raise RuntimeError(
            "No optimization configuration found. "
            "Expected .agent_configs/baseline/metadata.yaml."
        )

    model = config.model or os.environ.get(
        "AZURE_AI_MODEL_DEPLOYMENT_NAME",
        "gpt-5.6-sol-1",
    )

    instructions = config.compose_instructions()

    function_tools = [
        get_claim_history,
        get_insurance_program,
        get_facility_exposure,
        get_supply_chain_exposure,
    ]

    # Applies baseline or optimizer-generated tool and parameter descriptions
    # from tools.json to the Python function tools.
    config.apply_tool_descriptions(function_tools)

    file_search_tool = FoundryToolbox(
        credential,
        url=build_file_search_toolbox_url(),
    )

    model_client = FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=model,
        credential=credential,
    )

    logger.info(
        "Config source=%s | model=%s | prompt_len=%d | function_tools=%d",
        config.source,
        model,
        len(instructions),
        len(function_tools),
    )

    agent = Agent(
        client=model_client,
        instructions=instructions,
        tools=[
            file_search_tool,
            *function_tools,
        ],
        default_options={
            "store": False,
        },
    )

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()