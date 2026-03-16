import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

import requests


def load_env_from_dotenv(path: str = ".env") -> None:
    """
    Lightweight .env loader so we don't require python-dotenv.
    Only parses simple KEY=VALUE lines.
    """
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_dataset(path: str = "octant_data.json") -> Dict[str, Any]:
    if not os.path.exists(path):
        print(f"Missing {path}. Run collect_data.py first.", file=sys.stderr)
        sys.exit(1)
    with open(path, "r") as f:
        return json.load(f)


def build_project_index(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Index projects by address and name.
    Returns dict keyed by address with:
      { "name": str, "epochs": [int, ...] }
    """
    index: Dict[str, Dict[str, Any]] = {}
    for proj in data.get("all_projects", []):
        addr = proj.get("address")
        name = proj.get("name")
        try:
            epoch = int(proj.get("epoch"))
        except (TypeError, ValueError):
            continue
        if not addr:
            continue
        entry = index.setdefault(
            addr,
            {"name": name or addr, "epochs": []},
        )
        if epoch not in entry["epochs"]:
            entry["epochs"].append(epoch)
    return index


def detect_epochs_in_question(question: str, max_epoch: int) -> List[int]:
    """
    Heuristic: look for phrases like 'epoch 3', 'epochs 2-5', or bare numbers <= max_epoch.
    """
    epochs: List[int] = []

    # Ranges like "epochs 2-5"
    for m in re.finditer(r"epoch[s]?\s+(\d+)\s*[-–]\s*(\d+)", question, flags=re.IGNORECASE):
        start = int(m.group(1))
        end = int(m.group(2))
        for e in range(min(start, end), max(start, end) + 1):
            if 1 <= e <= max_epoch and e not in epochs:
                epochs.append(e)

    # Explicit "epoch 3"
    for m in re.finditer(r"epoch\s+(\d+)", question, flags=re.IGNORECASE):
        e = int(m.group(1))
        if 1 <= e <= max_epoch and e not in epochs:
            epochs.append(e)

    # Bare numbers that look like epochs (fallback)
    for m in re.finditer(r"\b(\d{1,2})\b", question):
        e = int(m.group(1))
        if 1 <= e <= max_epoch and e not in epochs:
            epochs.append(e)

    return sorted(epochs)


PROJECT_ALIASES: Dict[str, List[str]] = {
    # Simple alias examples; extend as needed
    "gitcoin": ["gitcoin", "gitcoin grants"],
    "giveth": ["giveth"],
    "glo dollar": ["glo", "glo dollar"],
}


def tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def find_projects_matching_question(
    question: str,
    project_index: Dict[str, Dict[str, Any]],
    limit: int = 5,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Fuzzy match: look for project-name tokens and aliases inside the question.
    Returns list of (address, project_info).
    """
    q_lower = question.lower()
    q_tokens = set(tokenize(question))

    matches: List[Tuple[str, Dict[str, Any]]] = []
    for addr, info in project_index.items():
        name = (info.get("name") or "").lower()
        if not name:
            continue

        name_tokens = set(tokenize(name))

        # Direct substring match: project name appears in question
        name_in_question = name in q_lower

        # Token overlap: any project token appears in question tokens
        token_overlap = bool(name_tokens & q_tokens)

        # Alias-based matching
        alias_hit = False
        for canonical, aliases in PROJECT_ALIASES.items():
            if canonical in name:
                if any(alias in q_lower for alias in aliases):
                    alias_hit = True
                    break

        if name_in_question or token_overlap or alias_hit:
            matches.append((addr, info))

    return matches[:limit]


def summarize_epoch(epoch_num: int, epoch_data: Dict[str, Any]) -> str:
    stats = (epoch_data or {}).get("stats", {})
    donors = (epoch_data or {}).get("donor_count")
    patrons = (epoch_data or {}).get("patron_count")
    unused = (epoch_data or {}).get("unused_rewards")
    leverage = (epoch_data or {}).get("leverage")
    threshold = (epoch_data or {}).get("threshold")

    parts = [f"Epoch {epoch_num}:"]
    if stats:
        parts.append(
            "  Stats: "
            f"stakingProceeds={stats.get('stakingProceeds')}, "
            f"totalRewards={stats.get('totalRewards')}, "
            f"matchedRewards={stats.get('matchedRewards')}, "
            f"donatedToProjects={stats.get('donatedToProjects')}"
        )
    if donors is not None:
        parts.append(f"  Donors: {donors}")
    if patrons is not None:
        parts.append(f"  Patrons: {patrons}")
    if unused is not None:
        parts.append(f"  Unused rewards: {unused}")
    if leverage is not None:
        parts.append(f"  Leverage: {leverage}")
    if threshold is not None:
        parts.append(f"  Threshold: {threshold}")
    return "\n".join(parts)


def project_rewards_across_epochs(
    address: str,
    data: Dict[str, Any],
) -> List[Tuple[int, Dict[str, Any]]]:
    """
    For a given project address, collect its reward entries across all epochs.
    Returns list of (epoch_num, reward_entry).
    """
    results: List[Tuple[int, Dict[str, Any]]] = []
    for epoch_str, epoch_data in data.get("epochs", {}).items():
        try:
            e = int(epoch_str)
        except ValueError:
            continue
        for entry in epoch_data.get("project_rewards", []):
            if entry.get("address") == address:
                results.append((e, entry))
    return sorted(results, key=lambda x: x[0])


def build_context_for_question(question: str, data: Dict[str, Any]) -> str:
    meta = data.get("meta", {})
    epochs = data.get("epochs", {})
    current_epoch = int(meta.get("current_epoch", len(epochs)))

    project_index = build_project_index(data)
    mentioned_epochs = detect_epochs_in_question(question, current_epoch)
    matched_projects = find_projects_matching_question(question, project_index)

    lines: List[str] = []
    lines.append("You are an expert Octant analyst.")
    lines.append("You are given a structured snapshot of Octant epochs and projects.")
    lines.append(
        "Use only the provided data to answer the user's question as precisely as possible. "
        "When you cite numbers, mention which epochs or projects they come from."
    )
    lines.append("")
    lines.append("=== META ===")
    lines.append(json.dumps(meta, indent=2))
    lines.append("")

    # Epoch summaries (only those mentioned, or all if none explicitly mentioned)
    if mentioned_epochs:
        target_epochs = mentioned_epochs
    else:
        # Default: all finalized epochs, but summarized
        target_epochs = sorted(int(e) for e in epochs.keys())

    lines.append("=== EPOCH SUMMARIES ===")
    for e in target_epochs:
        epoch_data = epochs.get(str(e), {})
        lines.append(summarize_epoch(e, epoch_data))
    lines.append("")

    # Project details for matches
    if matched_projects:
        lines.append("=== PROJECTS RELATED TO THE QUESTION ===")
        for addr, info in matched_projects:
            lines.append(f"Project: {info.get('name')} (address={addr})")
            lines.append(f"Epochs listed: {sorted(info.get('epochs', []))}")
            rewards = project_rewards_across_epochs(addr, data)
            if rewards:
                lines.append("Rewards by epoch (allocated, matched):")
                for e, r in rewards:
                    lines.append(
                        f"  Epoch {e}: allocated={r.get('allocated')}, matched={r.get('matched')}"
                    )
            lines.append("")

    return "\n".join(lines)


def call_claude(question: str, context: str) -> str:
    load_env_from_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "ANTHROPIC_API_KEY is not set. "
            "Please add it to your .env file or environment and try again."
        )

    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    system_prompt = (
        "You are OctantEvalAgent, an assistant that answers questions about the "
        "Octant funding mechanism, epochs, projects, donors, and rewards. "
        "Use ONLY the structured data provided in the context. "
        "When you give numeric answers, explicitly mention which epochs or projects "
        "they come from, e.g. 'In epoch 3, ...'. If the answer is not in the data, "
        "say so clearly rather than guessing."
    )

    payload = {
        "model": model,
        "max_tokens": 800,
        "temperature": 0.2,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "User question:\n"
                            f"{question}\n\n"
                            "Relevant Octant data:\n"
                            f"{context}"
                        ),
                    }
                ],
            }
        ],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        return f"Error from Anthropic API ({resp.status_code}): {resp.text}"

    data = resp.json()
    # messages API returns a top-level 'content' list with text blocks
    content = data.get("content", [])
    if content and isinstance(content, list):
        # Take the first text block
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "").strip()
    return json.dumps(data, indent=2)


def answer_question(question: str, dataset: Dict[str, Any]) -> str:
    """
    Shared helper used by both the CLI and the HTTP API.
    """
    ctx = build_context_for_question(question, dataset)
    return call_claude(question, ctx)


def interactive_loop(dataset: Dict[str, Any]) -> None:
    print("=== OctantEvalAgent ===")
    print("Ask questions about Octant epochs, projects, donors, and rewards.")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not question:
            continue
        if question.lower() in {"quit", "exit"}:
            print("Goodbye.")
            break

        print("\nThinking with Claude...\n")
        answer = answer_question(question, dataset)
        print(f"Agent: {answer}\n")


def main() -> None:
    dataset = load_dataset()
    interactive_loop(dataset)


if __name__ == "__main__":
    main()

