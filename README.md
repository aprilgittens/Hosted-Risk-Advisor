# Hosted Risk Advisor

Hosted Risk Advisor is a Python agent for Microsoft Foundry that answers
questions about a client's risk profile. It combines:

- File Search for general company information, such as operations, markets,
  products, revenue, and strategic initiatives.
- Python function tools for structured claims, insurance program, facility,
  and supply-chain exposure data.
- Microsoft Agent Framework hosting through the Responses protocol.
- Agent optimization configuration for evaluating alternative prompts, tool
  descriptions, and model choices.

The agent is configured as a hosted Microsoft Foundry service in `azure.yaml`.

## Project structure

| Path | Purpose |
| --- | --- |
| `main.py` | Loads the data and agent configuration, registers the tools, and starts the hosted agent server. |
| `create_file_search_toolbox.py` | Creates a Foundry File Search toolbox backed by an existing vector store. |
| `optimize_hosted_agent.py` | Starts and monitors a Foundry agent optimization job. |
| `.agent_configs/baseline/` | Contains the baseline model, instructions, and tool descriptions. |
| `data/` | Contains the structured client risk data used by the Python tools. |
| `azure.yaml` | Defines the hosted agent for Azure Developer CLI (`azd`). |

## Prerequisites

- Python 3.13 (the version configured for the hosted runtime)
- An Azure subscription and access to a Microsoft Foundry project
- A deployed model in that Foundry project
- Azure CLI, authenticated with `az login`
- Azure Developer CLI (`azd`) if you plan to deploy the hosted agent
- A Foundry vector store containing the company-profile documents used by
  File Search

Your Azure identity must be authorized to access the Foundry project, model,
vector store, and toolbox resources. The scripts use
`DefaultAzureCredential`, so local development normally uses the identity from
Azure CLI.

## Setup

### 1. Create and activate a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the repository root. It is ignored by Git and should
never be committed.

```dotenv
# Required to run the agent
FOUNDRY_PROJECT_ENDPOINT=https://<foundry-resource>.services.ai.azure.com/api/projects/<project-name>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<model-deployment-name>

# File Search toolbox
FILE_SEARCH_TOOLBOX_NAME=risk-advisor-file-search
# Optional: pin a specific toolbox version instead of using its default
FILE_SEARCH_TOOLBOX_VERSION=<toolbox-version>

# Required only when creating the File Search toolbox
VECTOR_STORE_ID=<vector-store-id>

# Required only when running agent optimization
FOUNDRY_AGENT_NAME=hosted-risk-advisor
DATASET_NAME=<optimization-dataset-name>
DATASET_VERSION=1

# Optional optimization settings
EVAL_MODEL=gpt-4o
OPTIMIZATION_MODEL=gpt-5
POLL_INTERVAL_SECONDS=10
```

`FOUNDRY_PROJECT_ENDPOINT` is required. The agent has a default model and
toolbox name, but explicitly setting them helps keep local and deployed
configuration consistent.

### 4. Create the File Search toolbox

Before the first run, create a vector store in Foundry, upload the relevant
company-profile documents, and set `VECTOR_STORE_ID` in `.env`. Then run:

```bash
python create_file_search_toolbox.py
```

The command prints the toolbox version and MCP endpoints. For a newly created
toolbox, the first version becomes the default. For later versions, either
promote the new version in Foundry or set `FILE_SEARCH_TOOLBOX_VERSION` in
`.env`.

### 5. Run locally

Make sure your Azure CLI session is active:

```bash
az login
python main.py
```

The server uses the Responses host supplied by
`agent-framework-foundry-hosting`. Stop it with `Ctrl+C`.

## Deploy to Microsoft Foundry

Authenticate Azure Developer CLI:

```bash
azd auth login
```

Set the values referenced by `azure.yaml` in the selected `azd` environment:

```bash
azd env set FOUNDRY_PROJECT_ENDPOINT "<project-endpoint>"
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME "<model-deployment-name>"
azd env set FILE_SEARCH_TOOLBOX_NAME "risk-advisor-file-search"
```

If the agent should use a non-default toolbox version, also set
`FILE_SEARCH_TOOLBOX_VERSION` in the hosted environment through your Foundry
configuration.

Deploy the hosted agent:

```bash
azd up
```

The deployment uses `main.py` as its entry point, resolves Python dependencies
with a remote build, and exposes the Responses protocol.

## Run agent optimization

Agent optimization is optional. Create or identify a Foundry dataset, configure
the optimization variables in `.env`, and run:

```bash
python optimize_hosted_agent.py
```

The script submits an optimization job, polls until it finishes, and prints
the baseline, best candidate, and candidate scores. Its evaluator and model
search space are currently defined in `optimize_hosted_agent.py`.

## Data and tool behavior

The agent routes general company-profile questions to File Search. It uses the
JSON files in `data/` only for questions specifically involving:

- Claim history and prior losses
- Insurance limits, deductibles, and program structure
- Facility and operational exposure
- Supply-chain dependencies and resilience

The baseline prompt and tool descriptions in `.agent_configs/baseline/`
control this routing behavior.
