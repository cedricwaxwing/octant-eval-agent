import streamlit as st

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

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("Context summary")
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

st.markdown("### Chat")

for turn in st.session_state.history:
    st.markdown(f"**You:** {turn['question']}")
    st.markdown(f"**Agent:** {turn['answer']}")
    st.markdown("---")

question = st.chat_input("Ask a question about Octant...")  # type: ignore[attr-defined]

if question:
    with st.spinner("Thinking with Claude..."):
        answer = answer_question(question, dataset)
    st.session_state.history.append({"question": question, "answer": answer})
    st.experimental_rerun()

