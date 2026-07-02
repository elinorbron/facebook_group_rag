import streamlit as st

from src.query_engine import ask

st.set_page_config(page_title="Facebook Group RAG", page_icon="💬", layout="wide")

st.title("Facebook Group RAG")
st.caption("Ask questions about your Facebook group posts — fully local on your Mac.")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("About")
    st.markdown(
        "This app searches your Facebook group export locally using Ollama. "
        "Your data never leaves this machine."
    )
    st.markdown("**Example questions**")
    st.markdown(
        "- What did I post on March 15, 2024?\n"
        "- Summarize my posts from April\n"
        "- What topics come up most often?"
    )
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for src in message["sources"]:
                    st.markdown(
                        f"**{src['date']}** · {src['group']} · {src['type']}\n\n"
                        f"{src['preview']}..."
                    )

prompt = st.chat_input("Ask about your group posts...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching your posts..."):
            try:
                result = ask(prompt)
                st.markdown(result["answer"])
                if result["sources"]:
                    with st.expander("Sources"):
                        for src in result["sources"]:
                            st.markdown(
                                f"**{src['date']}** · {src['group']} · {src['type']}\n\n"
                                f"{src['preview']}..."
                            )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result["sources"],
                    }
                )
            except Exception as exc:
                st.error(str(exc))
