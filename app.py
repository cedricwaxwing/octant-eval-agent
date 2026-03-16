import streamlit as st

from agent import answer_question, load_dataset


@st.cache_resource
def get_dataset():
    return load_dataset()


st.set_page_config(page_title="Octant Eval Agent", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        max-width: 800px;
        margin: auto;
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Octant Eval Agent")
st.caption(
    "Ask questions about Octant epochs, projects, donors, and rewards. "
    "Answers are grounded in protocol data collected from the Octant mainnet API."
)

dataset = get_dataset()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! Ask me anything about Octant epochs, projects, donors, and rewards.",
        }
    ]

st.write("")
col1, col2, col3, col4 = st.columns(4)

examples = [
    "What percentage of staking proceeds have been donated to projects across all epochs?",
    "Which projects received the most matched rewards in the latest epoch?",
    "How has donor participation changed over time?",
    "Compare leverage ratios across all epochs.",
]

clicked_prompt = None
for col, question in zip((col1, col2, col3, col4), examples):
    with col:
        if st.button(question, use_container_width=True):
            clicked_prompt = question

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_input = st.chat_input("Ask a question about Octant...")
prompt = clicked_prompt or user_input

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing Octant data..."):
            answer = answer_question(prompt, dataset)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
