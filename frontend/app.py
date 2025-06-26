"""
Streamlit Frontend for Document Chat Application

This module provides a Streamlit-based user interface for uploading PDF documents,
triggering backend processing, and chatting with an assistant about the uploaded content.

TODOs:
    - TODO: Implement per-user document storage and isolation.
    - TODO: Refactor synchronous file I/O to asynchronous patterns for scalability.
    - TODO: Add authentication and user session management.
    - TODO: Improve error handling and user feedback for backend failures.
"""

import streamlit as st
import requests
import os
import time
from typing import List, Dict, Any, Optional

# Configuration
API_BASE_URL: str = os.getenv("API_URL", "http://api:8000/api/v1")
st.set_page_config(page_title="Chat with Documents", page_icon="📚", layout="wide")


def check_api_health() -> bool:
    """
    Check if the backend API is reachable, with up to 3 retries.

    Uses a simple cache in Streamlit session state to avoid redundant checks.

    Returns:
        bool: True if the API is healthy and reachable, False otherwise.
    """
    if "api_healthy" in st.session_state and st.session_state.api_healthy:
        return True

    for attempt in range(3):
        try:
            health_url: str = os.getenv("API_URL", "http://api:8000").replace("/api/v1", "") + "/health"
            response: requests.Response = requests.get(health_url, timeout=3)
            if response.status_code == 200:
                st.session_state.api_healthy = True
                return True
        except requests.exceptions.RequestException:
            print(f"API health check attempt {attempt + 1} failed.")
            time.sleep(2)
    st.session_state.api_healthy = False
    return False


def save_uploaded_files(uploaded_files: List[Any], data_path: str) -> None:
    """
    Save uploaded files to the specified directory.

    Args:
        uploaded_files (List[Any]): List of uploaded file-like objects from Streamlit.
        data_path (str): Destination directory path.

    Returns:
        None

    Technical Debt:
        - Synchronous file I/O is used; consider refactoring to async for scalability.
    """
    os.makedirs(data_path, exist_ok=True)
    for file in uploaded_files:
        with open(os.path.join(data_path, file.name), "wb") as f:
            f.write(file.getbuffer())


def trigger_document_processing(api_base_url: str) -> requests.Response:
    """
    Trigger the backend API to process documents in the shared folder.

    Args:
        api_base_url (str): Base URL of the backend API.

    Returns:
        requests.Response: Response object from the backend API.
    """
    process_url: str = f"{api_base_url}/documents/process"
    return requests.post(process_url)


def display_chat_history(messages: List[Dict[str, str]]) -> None:
    """
    Render the chat history in the Streamlit UI.

    Args:
        messages (List[Dict[str, str]]): List of chat messages with 'role' and 'content'.

    Returns:
        None
    """
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def handle_user_prompt(prompt: str, api_base_url: str) -> str:
    """
    Send the user's prompt to the backend API and display the assistant's response.

    Args:
        prompt (str): User's input question.
        api_base_url (str): Base URL of the backend API.

    Returns:
        str: The assistant's full response (including sources if available).
    """
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response: str = ""
        try:
            chat_url: str = f"{api_base_url}/chat/"
            payload: Dict[str, str] = {"query": prompt}
            response: requests.Response = requests.post(chat_url, json=payload)

            if response.status_code == 200:
                data: Dict[str, Any] = response.json()
                answer: str = data.get("answer", "Sorry, I couldn't find an answer.")
                sources: List[str] = data.get("sources", [])

                for chunk in answer.split():
                    full_response += chunk + " "
                    message_placeholder.markdown(full_response + "▌")

                if sources:
                    full_response += "\n\n**Sources:**\n"
                    for source in sources:
                        full_response += f"- `{source}`\n"

                message_placeholder.markdown(full_response)
            elif response.status_code == 404:
                full_response = "I couldn't find a relevant answer in the provided documents."
                message_placeholder.markdown(full_response)
            else:
                full_response = f"Error: Received status code {response.status_code}\n\n{response.text}"
                message_placeholder.markdown(full_response)

        except requests.exceptions.RequestException as e:
            full_response = f"Error: Could not connect to the API. {e}"
            message_placeholder.markdown(full_response)

    return full_response


# --- UI Layout ---
st.title("📚 Chat with Your Documents")

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! Upload your documents and ask me anything about them."}
    ]

# --- Sidebar for Document Management ---
with st.sidebar:
    st.header("Document Management")

    uploaded_files: Optional[List[Any]] = st.file_uploader(
        "Upload your PDF documents",
        type="pdf",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if st.button("Process Documents", use_container_width=True):
        if uploaded_files:
            with st.spinner("Processing documents... This may take a moment."):
                try:
                    # TODO: Implement per-user document storage and isolation.
                    data_path: str = "/data/books"  # Path inside the container (shared volume)
                    save_uploaded_files(uploaded_files, data_path)
                    response: requests.Response = trigger_document_processing(API_BASE_URL)
                    if response.status_code == 202:
                        st.success("✅ Documents are being processed in the background! You can start chatting soon.")
                    else:
                        st.error(f"Error processing: {response.text}")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("⚠️ Please upload at least one PDF file.")

    if not check_api_health():
        st.error("🔴 Backend API is not reachable. Please ensure the backend service is running.")
    else:
        st.success("✅ Backend API is connected.")

# --- Main Chat Interface ---
display_chat_history(st.session_state.messages)

if prompt := st.chat_input("What is this document about?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    assistant_response: str = handle_user_prompt(prompt, API_BASE_URL)
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})