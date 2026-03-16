# Octant Eval Agent

An AI agent that ingests the full history of Octant's public goods funding protocol and answers natural-language questions grounded strictly in real data. Built for the [Synthesis hackathon](https://synthesis.md/) (March 2026).

## What it does

Octant has distributed over $12M in grants across multiple epochs. The data is public but scattered across API endpoints: epoch stats, project rewards, donor allocations, patron counts, leverage ratios, thresholds, and more.

This agent pulls all of that into a single structured dataset, then uses an LLM to answer questions about it. You ask a question in plain language, it retrieves only the relevant slices of data, and returns a grounded answer with explicit epoch and project citations.

No hallucination. No guessing. If the data doesn't contain the answer, it says so.

## Octant track alignment

This project targets two of the three Octant partner bounties at the Synthesis hackathon:

### Agents for Public Goods Data Collection for Project Evaluation ($1,000)

> "How can agents surface richer, more reliable signals about a project's impact or legitimacy?"

`collect_data.py` programmatically fetches every finalized epoch from the Octant mainnet API and assembles a complete local dataset: staking proceeds, total/matched rewards, donor lists, patron lists, allocation pairs, leverage ratios, thresholds, unused rewards, and full project metadata across all epochs. This is the data collection layer. It turns a scattered set of API endpoints into a single structured source of truth that any agent (or human) can query.

### Agents for Public Goods Data Analysis for Project Evaluation ($1,000)

> "What patterns or insights can agents extract from existing datasets that humans can't scale?"

`agent.py` takes that collected dataset and makes it queryable through natural language. It uses structured retrieval (not RAG) to build targeted context slices per question, then calls an LLM to produce grounded answers with explicit epoch and project citations. The agent can surface cross-epoch trends, compare project performance over time, and identify participation patterns across donors and patrons, all at a speed and depth that manual analysis can't match.

### Design principles

- **Auditable reasoning**: Every answer cites specific epochs and projects. The human can verify exactly where the numbers came from.
- **Scoped data access**: The agent doesn't get the full dataset dumped into its context. It builds a targeted retrieval slice per question, pulling only the relevant epoch summaries and project reward traces.
- **Strict grounding**: The system prompt enforces that the model only uses provided data and explicitly flags when information is missing rather than fabricating an answer.
- **Transparent data pipeline**: The dataset is generated from Octant's public API with a single script. Anyone can reproduce it.

## Services and dependencies

This project is built on top of two external services:

- **Octant Mainnet API** (`backend.mainnet.octant.app`): The public production API for Octant v1. Used exclusively by `collect_data.py` to fetch epoch stats, project rewards, donor/patron lists, allocations, and project metadata. All data is pulled once and stored locally; the agent never calls this API at query time.
- **Anthropic Messages API** (`api.anthropic.com`): Used by `agent.py` to generate grounded natural-language answers. The model receives a structured context slice (not raw JSON) and a system prompt that enforces strict citation and no-hallucination behavior.

All other code (data parsing, question detection, context building, project indexing) is written from scratch for this hackathon with zero external dependencies beyond Python stdlib and `requests`.

## How it works

```
collect_data.py          agent.py
     |                       |
     v                       v
 Octant API  ------>  octant_data.json  ------>  Question Parser
(all epochs)          (local dataset)            |
                                                 v
                                          Context Builder
                                          (epoch summaries +
                                           project rewards)
                                                 |
                                                 v
                                          Anthropic API
                                          (grounded answer)
```

1. `collect_data.py` hits the live Octant mainnet API and fetches every finalized epoch: stats, rewards, donors, patrons, allocations, leverage, thresholds, and project metadata. Writes everything to `octant_data.json`.

2. `agent.py` loads that dataset and runs a CLI loop. For each question it:
   - Detects which epochs are mentioned (or defaults to all)
   - Finds projects matching the question via name lookup
   - Builds a compact context with only the relevant data slices
   - Sends the context + question to the Anthropic Messages API
   - Returns an answer that explicitly cites its sources

## Quick start

```bash
git clone https://github.com/cedricwaxwing/octant-eval-agent.git
cd octant-eval-agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.sample .env
# Add your ANTHROPIC_API_KEY to .env
```

### Step 1: Collect the data

```bash
python collect_data.py
```

This fetches all finalized epochs from Octant's production API and writes `octant_data.json`. Takes about 30 seconds.

### Step 2: Collect the data

```bash
python collect_data.py
```

This fetches all finalized epochs from Octant's production API and writes `octant_data.json`. Takes about 30 seconds.

### Step 3: Run the CLI agent

```bash
python agent.py
```

### Example questions

```
You: Which projects received the highest matched rewards in epoch 4?
You: How many donors and patrons participated in epoch 7?
You: How did rewards for Giveth change over time?
You: What was the total staking proceeds across all epochs?
You: Compare donor participation between epochs 3 and 6.
```

Type `quit` or `exit` to stop.

### Step 4: Run the HTTP API (optional)

Start the FastAPI server:

```bash
uvicorn api:app --reload
```

Endpoints:

- `GET /health` – basic health/status.
- `GET /epochs` – list of epochs in the dataset.
- `POST /ask` – JSON body `{ "question": "..." }`, returns `{ "answer": "...", "model": "...", "epochs": [...] }`.

### Step 5: Run the Streamlit chat UI (optional)

```bash
streamlit run app.py
```

This opens a browser UI where you can:

- Enter questions in a chat-style interface
- See a running history of Q&A
- View basic dataset metadata (current epoch, available epochs) in the sidebar

### Step 6: Run the evaluation harness (optional)

```bash
python eval.py
```

This sends a small set of curated questions through the agent and checks that key phrases appear in the answers, printing per-test PASS/FAIL plus an aggregate score.

## Project structure

```
octant-eval-agent/
  agent.py           # CLI/logic: question parsing, context building, LLM call
  api.py             # FastAPI app: /health, /epochs, /ask
  app.py             # Streamlit chat UI on top of the agent
  collect_data.py    # Data collector: fetches all Octant epochs from production API
  eval.py            # Simple evaluation harness with test questions
  octant_data.json   # Generated dataset (gitignored)
  .env               # API keys (gitignored)
  .env.sample        # Template for .env
  requirements.txt   # Python deps
  README.md
```

## Technical decisions

**Structured retrieval over RAG.** Instead of embedding the dataset and doing vector similarity search, the agent uses deterministic retrieval: it parses the question for epoch references and project names, then pulls exactly those data slices into the prompt. This keeps answers precise and traceable.

**Pre-computed local dataset.** All data is fetched once and stored locally. The agent never calls the Octant API at query time. This means fast responses and no risk of hammering a production endpoint during a demo.

**Minimal dependencies.** The data collector uses only stdlib (`urllib`, `json`). The agent stack adds `requests` for the Anthropic API call, `fastapi`+`uvicorn` for an optional HTTP API, and `streamlit` for a lightweight chat UI. No vector DBs, no complex infra.

## Requirements

- Python 3.9+
- Anthropic API key (model: `claude-sonnet-4-6` or compatible)

## Future directions

- **HTTP API** (FastAPI) so a web frontend or other agents can call `/ask`
- **Chat UI** (Streamlit or Next.js) for interactive exploration
- **Evaluation harness** with ground-truth Q&A pairs to measure answer accuracy
- **Allocation-level analysis** (donor-to-project pairs, average allocation size, unique donor counts per project)
- **OSO integration** to blend on-chain funding data with open-source health signals
- **Autonomous allocation recommendations** where the eval agent's grounding layer feeds into an allocation agent that can suggest or execute funding decisions on-chain

## Built by

[Colin Spence](https://colinspencedesign.com) | [@cedricwaxwing](https://github.com/cedricwaxwing)

Built for the Synthesis hackathon, March 2026. Octant partner track.
