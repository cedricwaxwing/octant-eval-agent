import streamlit as st
import pandas as pd
import time

from agent import load_dataset, build_context_for_question, call_claude, build_project_index

# --- Page config ---
st.set_page_config(page_title="Octant Eval Agent", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stSidebar hr {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    h2:first-of-type {
        padding-top: 0 !important;
    }
    .block-container {
        max-width: 900px;
        margin: auto;
        padding-top: 2rem;
    }
    [data-testid="stSidebarHeader"] {
        height: 3rem;
        margin-bottom: 0;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
    }
    [data-testid="stChatInput"] {
        max-width: 740px;
        margin: auto;
    }
    button p {
        font-size: 0.8rem !important;
        overflow-wrap: anywhere;
        text-wrap: pretty;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Load data ---
@st.cache_resource
def get_dataset():
    return load_dataset()


def wei_to_eth(wei_val) -> str:
    """Convert wei to ETH, formatted with commas."""
    try:
        eth = int(wei_val) / 1e18
        return f"{eth:,.2f}"
    except (ValueError, TypeError):
        return "N/A"


def compute_dataset_stats(data):
    """Precompute summary stats for the sidebar."""
    epochs = data.get("epochs", {})
    project_index = build_project_index(data)

    total_staking = 0
    total_donated = 0
    total_donors = set()
    total_patrons = set()
    epoch_count = len(epochs)

    for epoch_str, epoch_data in epochs.items():
        stats = epoch_data.get("stats", {})
        try:
            total_staking += int(stats.get("stakingProceeds", 0))
        except (ValueError, TypeError):
            pass
        try:
            total_donated += int(stats.get("donatedToProjects", 0))
        except (ValueError, TypeError):
            pass
        for d in epoch_data.get("donors", []):
            total_donors.add(d)
        for p in epoch_data.get("patrons", []):
            total_patrons.add(p)

    return {
        "epoch_count": epoch_count,
        "project_count": len(project_index),
        "total_staking_eth": wei_to_eth(total_staking),
        "total_donated_eth": wei_to_eth(total_donated),
        "unique_donors": len(total_donors),
        "unique_patrons": len(total_patrons),
    }


def wei_to_eth_float(wei_val) -> float:
    """Convert wei to ETH as a float for charting."""
    try:
        return int(wei_val) / 1e18
    except (ValueError, TypeError):
        return 0.0


def build_epoch_chart_data(data):
    """Build a DataFrame of per-epoch donated vs matched rewards in ETH."""
    epochs = data.get("epochs", {})
    rows = []
    for epoch_str in sorted(epochs.keys(), key=int):
        epoch_data = epochs[epoch_str]
        stats = epoch_data.get("stats", {})
        donated = wei_to_eth_float(stats.get("donatedToProjects", 0))
        if donated <= 1:
            continue
        rows.append({
            "Epoch": int(epoch_str),
            "Donated to projects (ETH)": donated,
            "Matched rewards (ETH)": wei_to_eth_float(stats.get("matchedRewards", 0)),
        })
    return pd.DataFrame(rows)


dataset = get_dataset()
stats = compute_dataset_stats(dataset)
chart_df = build_epoch_chart_data(dataset)



# --- Sidebar ---
with st.sidebar:
    st.title("🔮 Octant Eval Agent")
    st.caption("Grounded in real protocol data from the Octant mainnet API.")

    st.divider()

    st.subheader("Dataset overview")
    col_a, col_b = st.columns(2)
    col_a.metric("Epochs", stats["epoch_count"])
    col_b.metric("Projects", stats["project_count"])

    col_c, col_d = st.columns(2)
    col_c.metric("Unique donors", f"{stats['unique_donors']:,}")
    col_d.metric("Unique patrons", f"{stats['unique_patrons']:,}")

    st.metric("Total donated to projects", f"{stats['total_donated_eth']} ETH")

    st.divider()

    st.subheader("How it works")
    st.markdown(
        "The agent builds a compact context slice for each question using epoch "
        "summaries, project rewards, and allocation stats. It retrieves only the "
        "relevant data, then calls an LLM to produce a grounded answer with "
        "explicit citations. No hallucination -- if it's not in the data, it says so."
    )

    st.divider()

    st.caption(
        "Built for the [Synthesis hackathon](https://synthesis.md/) (March 2026). "
        "Octant partner track."
    )


# --- Main content area ---

# Title
st.title("🔮 Octant Eval Agent")

# Accordion
with st.expander("Built with Octant data for the Synthesis Hackathon 2026"):
    st.markdown(
        "**Octant Eval Agent** is an AI-powered tool for analyzing the "
        "[Octant](https://octant.build) public goods funding protocol. "
        "It pulls complete historical data from the live Octant mainnet API "
        "and lets you ask natural-language questions about epochs, projects, "
        "donors, and rewards."
    )
    st.markdown(
        "Answers are grounded strictly in protocol data. The agent uses "
        "structured retrieval (not RAG) to build targeted context slices, "
        "then calls an LLM that cites specific epochs and projects in every response. "
        "If the data doesn't contain the answer, it says so."
    )
    st.markdown(
        "Built for the [Synthesis hackathon](https://synthesis.md/) Octant partner track. "
        "Targeting the **Data Collection** and **Data Analysis** bounties."
    )

st.bar_chart(
    chart_df.set_index("Epoch"),
    color=["#22c55e", "#3b82f6"],
    height=240,
)

st.divider()

# --- Chat ---

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.greeted = False

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Greet user
if not st.session_state.greeted:
    with st.chat_message("assistant"):
        intro = (
            "Hey! I'm the Octant Eval Agent. Ask me anything about Octant's "
            "epochs, projects, donors, and rewards. I'll answer using real "
            "protocol data and cite my sources."
        )
        st.markdown(intro)
        st.session_state.messages.append({"role": "assistant", "content": intro})
        st.session_state.greeted = True


# --- Example prompts (6 buttons, 3x2 grid, short labels, detail on hover) ---
example_prompts = [
    "Staking proceeds donated overall",
    "Top matched projects last epoch",
    "Donor participation over time",
    "Leverage ratios across epochs",
    "Largest single-epoch reward spike",
    "Projects in the most epochs",
]

example_full_questions = [
    "What percentage of total staking proceeds have been donated to projects across all epochs?",
    "Which projects received the highest matched rewards in the most recent finalized epoch?",
    "How has the number of unique donors changed across all epochs?",
    "Compare the leverage ratios across all finalized epochs. Which had the highest and lowest?",
    "Which epoch saw the biggest increase in total matched rewards compared to the previous epoch?",
    "Which projects appeared in the most epochs, and how consistent was their funding?",
]

example_help = [
    "What share of staking yield actually reached projects? Measures protocol efficiency.",
    "See which projects led in matched funding in the latest completed round.",
    "Track whether community engagement is growing or shrinking epoch to epoch.",
    "Leverage = how much the matching pool amplifies donor allocations. Higher is better.",
    "Find the epoch where matched rewards jumped the most vs. the prior round.",
    "Identify projects with the longest track record across Octant's history.",
]

row1 = st.columns(3)
row2 = st.columns(3)
button_cols = row1 + row2

clicked_prompt = ""
for i, col in enumerate(button_cols):
    if col.button(example_prompts[i], help=example_help[i], use_container_width=True):
        clicked_prompt = example_full_questions[i]


# --- Handle input ---
user_input = st.chat_input("Ask a question about Octant...")
prompt = clicked_prompt or user_input

if prompt:
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generate and show response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing Octant data..."):
            ctx = build_context_for_question(prompt, dataset)
            answer = call_claude(prompt, ctx)

        # Simulate streaming for readability
        message_placeholder = st.empty()
        full_response = ""
        for chunk in answer.split(" "):
            full_response += chunk + " "
            time.sleep(0.015)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response.strip())

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()