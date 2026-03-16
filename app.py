import streamlit as st
import pandas as pd

from agent import answer_question, load_dataset


@st.cache_resource
def get_dataset():
    return load_dataset()


st.set_page_config(page_title="Octant Eval Agent", layout="wide")

st.title("Octant Eval Agent")
st.write(
    "Ask questions about Octant epochs, projects, donors, and rewards. "
    "Answers are grounded strictly in the pre-collected `octant_data.json` dataset."
)

dataset = get_dataset()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! Ask me anything about Octant epochs, projects, donors, and rewards.",
        }
    ]

with st.sidebar:
    st.header("Dataset summary")
    meta = dataset.get("meta", {})
    epochs = sorted(int(e) for e in dataset.get("epochs", {}).keys())
    st.markdown("**Current epoch**")
    st.write(meta.get("current_epoch"))
    st.markdown("**Finalized epochs in dataset**")
    st.write(epochs)
    st.markdown("**Notes**")
    st.write(
        "The agent builds a compact context slice for each question using "
        "epoch summaries, project rewards, and (when relevant) allocation stats."
    )

    st.markdown("---")
    st.markdown("**Quick epoch chart**")
    metric = st.selectbox(
        "Metric", ["totalRewards", "matchedRewards", "donatedToProjects"], index=0
    )

    data_rows = []
    for e in epochs:
        stats = (dataset.get("epochs", {}).get(str(e), {}) or {}).get("stats", {}) or {}
        value = stats.get(metric)
        if value is not None:
            try:
                data_rows.append({"epoch": e, metric: float(value)})
            except (TypeError, ValueError):
                continue

    if data_rows:
        df = pd.DataFrame(data_rows).set_index("epoch")
        st.line_chart(df, height=200)

st.markdown("### Chat")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Ask a question about Octant...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking with Claude..."):
            answer = answer_question(prompt, dataset)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
