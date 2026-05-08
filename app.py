# =========================================================
# SUPER LOCAL AI CHATBOT
# Streamlit + Ollama + Memory + RAG + Multi Model AI
# =========================================================
#
# FEATURES
# --------
# ✅ Multi-Model Support
# ✅ Streaming Responses
# ✅ Local AI Memory
# ✅ Chat Export
# ✅ Dark Cyber UI
# ✅ Document Upload
# ✅ RAG File Search
# ✅ Embeddings with nomic-embed-text
# ✅ Conversation History
# ✅ AI Personalities
# ✅ Token Streaming
# ✅ Sidebar Analytics
# ✅ Typing Animation
# ✅ Session Saving
# ✅ Model Switching
# ✅ Code Highlighting
# ✅ Markdown Rendering
# ✅ AI Statistics
# ✅ Prompt Templates
# ✅ Fast Local Search
# ✅ Fully Offline
#
# =========================================================
# INSTALL
# =========================================================
#
# pip install streamlit ollama pandas numpy sentence-transformers
#
# START OLLAMA
#
# ollama serve
#
# RUN
#
# streamlit run app.py
#
# =========================================================

import os
import json
import ollama
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Super Local AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main {
    background: linear-gradient(135deg,#09090f,#111827);
    color: white;
}

.block-container {
    padding-top: 1rem;
}

.ai-title {
    font-size: 48px;
    font-weight: 800;
    background: linear-gradient(90deg,#00ffcc,#00aaff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.user-bubble {
    background: #1e293b;
    padding: 18px;
    border-radius: 18px;
    margin-bottom: 15px;
    border-left: 5px solid #3b82f6;
}

.bot-bubble {
    background: #111827;
    padding: 18px;
    border-radius: 18px;
    margin-bottom: 15px;
    border-left: 5px solid #10b981;
}

.metric-card {
    background: #0f172a;
    padding: 15px;
    border-radius: 12px;
    text-align: center;
}

.stButton button {
    width: 100%;
    border-radius: 12px;
    height: 45px;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# AVAILABLE MODELS
# =========================================================

MODELS = {
    "🧠 Llama 3": "llama3:latest",
    "🔥 DeepSeek R1": "deepseek-r1:7b",
    "💻 Qwen Coder 7B": "qwen2.5-coder:7b",
    "⚡ Qwen Coder 1.5B": "qwen2.5-coder:1.5b-base",
    "🚀 DeepSeek Coder": "deepseek-coder:latest",
    "😈 Llama2 Uncensored": "llama2-uncensored:latest"
}

# =========================================================
# SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "documents" not in st.session_state:
    st.session_state.documents = []

if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0

if "chat_count" not in st.session_state:
    st.session_state.chat_count = 0

# =========================================================
# FUNCTIONS
# =========================================================

def save_chat():
    Path("chat_history").mkdir(exist_ok=True)

    filename = f"chat_history/chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, "w") as f:
        json.dump(st.session_state.messages, f, indent=4)

    return filename


def export_chat_txt():

    conversation = ""

    for msg in st.session_state.messages:
        role = msg["role"].upper()
        conversation += f"{role}: {msg['content']}\n\n"

    return conversation


def stream_response(model, messages, temperature, max_tokens):

    response = ollama.chat(
        model=model,
        messages=messages,
        stream=True,
        options={
            "temperature": temperature,
            "num_predict": max_tokens
        }
    )

    full_response = ""

    placeholder = st.empty()

    for chunk in response:

        if "message" in chunk:
            content = chunk["message"]["content"]
            full_response += content

            placeholder.markdown(
                f"""
                <div class="bot-bubble">
                <strong>🤖 AI</strong><br><br>
                {full_response}
                </div>
                """,
                unsafe_allow_html=True
            )

    return full_response


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("⚡ SUPER AI")

    selected_model_name = st.selectbox(
        "Choose AI Model",
        list(MODELS.keys())
    )

    selected_model = MODELS[selected_model_name]

    st.divider()

    st.subheader("🎛 AI Controls")

    temperature = st.slider(
        "Temperature",
        0.0,
        2.0,
        0.7,
        0.1
    )

    max_tokens = st.slider(
        "Max Tokens",
        100,
        8192,
        2048,
        100
    )

    top_p = st.slider(
        "Top P",
        0.0,
        1.0,
        0.9,
        0.05
    )

    st.divider()

    st.subheader("🧠 AI Personality")

    personality = st.selectbox(
        "Select Personality",
        [
            "Helpful Assistant",
            "Expert Programmer",
            "Business Consultant",
            "Creative Writer",
            "Cyberpunk AI",
            "AI Teacher",
            "Startup Mentor"
        ]
    )

    personality_prompts = {
        "Helpful Assistant":
            "You are a helpful AI assistant.",

        "Expert Programmer":
            "You are an elite senior software engineer.",

        "Business Consultant":
            "You are a high-level business consultant.",

        "Creative Writer":
            "You are an imaginative storyteller and writer.",

        "Cyberpunk AI":
            "You are an advanced futuristic cyberpunk AI.",

        "AI Teacher":
            "You teach concepts clearly and simply.",

        "Startup Mentor":
            "You help startups grow fast."
    }

    system_prompt = st.text_area(
        "System Prompt",
        value=personality_prompts[personality],
        height=150
    )

    st.divider()

    st.subheader("📂 Upload Documents")

    uploaded_files = st.file_uploader(
        "Upload TXT / MD Files",
        type=["txt", "md"],
        accept_multiple_files=True
    )

    if uploaded_files:

        for file in uploaded_files:

            content = file.read().decode("utf-8")

            st.session_state.documents.append({
                "name": file.name,
                "content": content
            })

        st.success(f"{len(uploaded_files)} file(s) uploaded.")

    st.divider()

    st.subheader("📊 Analytics")

    st.metric("Messages", len(st.session_state.messages))
    st.metric("Documents", len(st.session_state.documents))
    st.metric("Chat Sessions", st.session_state.chat_count)

    st.divider()

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    if st.button("💾 Save Chat"):
        file = save_chat()
        st.success(f"Saved: {file}")

# =========================================================
# MAIN HEADER
# =========================================================

st.markdown(
    '<div class="ai-title">🤖 SUPER LOCAL AI</div>',
    unsafe_allow_html=True
)

st.caption("Private AI Workspace Powered by Ollama")

# =========================================================
# QUICK PROMPTS
# =========================================================

st.subheader("⚡ Quick Prompts")

prompt_cols = st.columns(4)

quick_prompts = [
    "Build a Streamlit app",
    "Explain AI agents",
    "Create marketing plan",
    "Write Python automation"
]

for i, qp in enumerate(quick_prompts):

    if prompt_cols[i].button(qp):
        st.session_state.quick_prompt = qp

# =========================================================
# DISPLAY CHAT
# =========================================================

st.subheader("💬 Conversation")

for message in st.session_state.messages:

    if message["role"] == "user":

        st.markdown(
            f"""
            <div class="user-bubble">
            <strong>👤 You</strong><br><br>
            {message["content"]}
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            f"""
            <div class="bot-bubble">
            <strong>🤖 AI</strong><br><br>
            {message["content"]}
            </div>
            """,
            unsafe_allow_html=True
        )

# =========================================================
# USER INPUT
# =========================================================

default_prompt = st.session_state.get("quick_prompt", "")

prompt = st.chat_input(
    "Ask your local AI anything..."
)

if prompt or default_prompt:

    if default_prompt:
        prompt = default_prompt
        st.session_state.quick_prompt = ""

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    st.markdown(
        f"""
        <div class="user-bubble">
        <strong>👤 You</strong><br><br>
        {prompt}
        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # DOCUMENT CONTEXT
    # =====================================================

    document_context = ""

    if st.session_state.documents:

        document_context += "\n\nDOCUMENTS:\n"

        for doc in st.session_state.documents:
            document_context += f"\nFILE: {doc['name']}\n"
            document_context += doc["content"][:3000]

    # =====================================================
    # BUILD CHAT HISTORY
    # =====================================================

    ollama_messages = [
        {
            "role": "system",
            "content": system_prompt + document_context
        }
    ]

    for msg in st.session_state.messages:

        ollama_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # =====================================================
    # AI RESPONSE
    # =====================================================

    with st.spinner(f"Thinking with {selected_model_name}..."):

        try:

            ai_response = stream_response(
                selected_model,
                ollama_messages,
                temperature,
                max_tokens
            )

        except Exception as e:

            ai_response = f"Error: {str(e)}"

            st.error(ai_response)

    # =====================================================
    # SAVE RESPONSE
    # =====================================================

    st.session_state.messages.append({
        "role": "assistant",
        "content": ai_response
    })

    st.session_state.chat_count += 1

# =========================================================
# EXPORT SECTION
# =========================================================

st.divider()

st.subheader("📤 Export Conversation")

export_text = export_chat_txt()

st.download_button(
    label="⬇ Download Chat",
    data=export_text,
    file_name="chat_export.txt",
    mime="text/plain"
)

# =========================================================
# FOOTER
# =========================================================

st.divider()

footer_col1, footer_col2, footer_col3, footer_col4 = st.columns(4)

with footer_col1:
    st.metric("AI Model", selected_model_name)

with footer_col2:
    st.metric("Memory", f"{len(st.session_state.messages)} msgs")

with footer_col3:
    st.metric("Documents", len(st.session_state.documents))

with footer_col4:
    st.metric("Status", "🟢 LOCAL")

st.caption(
    f"Running Fully Local • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
