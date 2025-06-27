"""
Streamlit Frontend for Document Chat Application

This module provides a Streamlit-based user interface for uploading PDF documents,
triggering backend processing, and chatting with an assistant about the uploaded content.

TODOs:
    - TODO: Refactor synchronous file I/O to asynchronous patterns for scalability.
    - TODO: Improve error handling and user feedback for backend failures.
"""

import streamlit as st
import requests
import pandas as pd
import json
from typing import Dict, Any, List
import os
# --- Configuration ---
def get_api_url() -> str:
    """
    Returns the API URL based on environment.
    Uses Docker host if available, otherwise falls back to localhost.
    """
    return os.getenv("API_URL", "http://api:8000/api/v1" if os.getenv("DOCKER", "1") == "1" else "http://localhost:8000/api/v1")

API_URL = get_api_url()

st.set_page_config(page_title="Chat with Documents", layout="wide")

# --- Authentication ---
def login_user(username: str, password: str) -> None:
    """
    Authenticates the user and stores token in session state.
    """
    try:
        response = requests.post(f"{API_URL}/auth/token", data={"username": username, "password": password})
        if response.status_code == 200:
            st.session_state.token = response.json()["access_token"]
            st.session_state.username = username
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Login failed. Please check your username and password.")
    except requests.RequestException as e:
        st.error(f"Connection to API failed: {e}")

def signup_user(username: str, password: str) -> None:
    """
    Registers a new user.
    """
    try:
        response = requests.post(f"{API_URL}/auth/signup", json={"username": username, "password": password})
        if response.status_code == 200:
            st.success("Signup successful! Please log in.")
        else:
            detail = response.json().get('detail', 'Unknown error')
            st.error(f"Signup failed: {detail}")
    except requests.RequestException as e:
        st.error(f"Connection to API failed: {e}")

def auth_page() -> None:
    """
    Renders the authentication page for login and signup.
    """
    st.title("Welcome to Chat with Documents")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                login_user(username, password)

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username")
            new_password = st.text_input("Choose a Password", type="password")
            submitted = st.form_submit_button("Sign Up")
            if submitted:
                signup_user(new_username, new_password)

# --- API Helpers ---
def get_auth_headers() -> Dict[str, str]:
    """
    Returns the authorization headers for API requests.
    """
    return {"Authorization": f"Bearer {st.session_state.token}"}

def get_projects() -> List[Dict[str, Any]]:
    """
    Fetches the list of projects for the authenticated user.
    """
    try:
        res = requests.get(f"{API_URL}/projects/", headers=get_auth_headers())
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []

def create_project(name: str) -> Dict[str, Any]:
    """
    Creates a new project.
    """
    res = requests.post(f"{API_URL}/projects/", json={"name": name}, headers=get_auth_headers())
    return res.json()

# --- Main App ---
def main_app() -> None:
    """
    Main application logic for authenticated users.
    """
    st.sidebar.title(f"Welcome, {st.session_state.username}!")

    # Project Selection
    projects = get_projects()
    project_names = [p['name'] for p in projects]
    st.sidebar.header("Projects")
    if 'current_project_name' not in st.session_state:
        st.session_state.current_project_name = project_names[0] if project_names else None

    selected_project_name = st.sidebar.selectbox(
        "Select a Project", project_names,
        index=project_names.index(st.session_state.current_project_name) if st.session_state.current_project_name in project_names and project_names else 0
    )

    if selected_project_name != st.session_state.current_project_name:
        st.session_state.current_project_name = selected_project_name
        # Reset chat when project changes
        st.session_state.messages = {}
        st.session_state.current_chat_id = None

    project_id = next((p['id'] for p in projects if p['name'] == selected_project_name), None)
    st.session_state.current_project_id = project_id

    with st.sidebar.expander("Create New Project"):
        with st.form("new_project_form", clear_on_submit=True):
            new_project_name = st.text_input("Project Name")
            if st.form_submit_button("Create") and new_project_name:
                create_project(new_project_name)
                st.rerun()

    if not project_id:
        st.header("Create your first project to get started!")
        return

    # Page selection
    page = st.sidebar.radio("Navigate", ["Chat", "Manage Documents"])

    if page == "Chat":
        chat_page(project_id)
    elif page == "Manage Documents":
        documents_page(project_id)

    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def documents_page(project_id: str) -> None:
    """
    Renders the document management page for a project.
    """
    st.header(f"Manage Documents for '{st.session_state.current_project_name}'")

    # Uploader
    with st.expander("Upload New Documents", expanded=True):
        st.subheader("Upload Files")
        uploaded_files = st.file_uploader(
            "Upload PDF, DOCX, TXT, or MD files",
            type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True
        )
        if st.button("Upload and Process Files"):
            if uploaded_files:
                with st.spinner("Uploading..."):
                    for file in uploaded_files:
                        files = {'file': (file.name, file.getvalue(), file.type)}
                        try:
                            requests.post(f"{API_URL}/documents/upload/{project_id}", files=files, headers=get_auth_headers())
                        except Exception as e:
                            st.error(f"Failed to upload {file.name}: {e}")
                    st.success("Files uploaded! Processing has started in the background.")
                    st.rerun()
            else:
                st.warning("Please select at least one file to upload.")

        st.subheader("Add from URL")
        url = st.text_input("Enter a URL to scrape and add")
        if st.button("Add URL"):
            if url:
                with st.spinner("Scraping and processing URL..."):
                    payload = {"url": url}
                    try:
                        requests.post(f"{API_URL}/documents/upload_url/{project_id}", json=payload, headers=get_auth_headers())
                        st.success("URL added! Processing has started.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add URL: {e}")
            else:
                st.warning("Please enter a URL.")

    # Document List
    st.subheader("Uploaded Documents")
    try:
        docs_res = requests.get(f"{API_URL}/documents/{project_id}", headers=get_auth_headers())
        if docs_res.status_code == 200:
            docs = docs_res.json()
            if docs:
                df = pd.DataFrame(docs)
                st.dataframe(df[['file_name', 'status', 'created_at']], use_container_width=True)
            else:
                st.info("No documents found in this project yet.")
        else:
            st.error("Failed to fetch documents.")
    except Exception as e:
        st.error(f"Error fetching documents: {e}")

def chat_page(project_id: str) -> None:
    """
    Renders the chat interface for a project.
    """
    st.header(f"Chat with '{st.session_state.current_project_name}'")

    if 'messages' not in st.session_state:
        st.session_state.messages = {}  # Dict of {chat_id: [messages]}

    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None

    # Load chat history for the project
    try:
        history_res = requests.get(f"{API_URL}/chat/sessions/{project_id}", headers=get_auth_headers())
        if history_res.status_code == 200:
            sessions = history_res.json()
            with st.sidebar:
                st.subheader("Chat History")
                if st.button("➕ New Chat"):
                    st.session_state.current_chat_id = None
                    st.rerun()

                for session in sessions:
                    if st.button(session['title'], key=session['id'], use_container_width=True):
                        st.session_state.current_chat_id = session['id']
                        # Load messages for this chat
                        try:
                            msgs_res = requests.get(f"{API_URL}/chat/sessions/{project_id}/{session['id']}", headers=get_auth_headers())
                            if msgs_res.status_code == 200:
                                st.session_state.messages[session['id']] = msgs_res.json()['messages']
                        except Exception:
                            pass
                        st.rerun()
    except Exception:
        st.sidebar.error("Failed to load chat history.")

    # Display current chat messages
    chat_key = st.session_state.current_chat_id
    if chat_key and chat_key in st.session_state.messages:
        for msg in st.session_state.messages[chat_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander("Sources"):
                        try:
                            sources = json.loads(msg["sources"]) if isinstance(msg["sources"], str) else msg["sources"]
                            for source in sources:
                                st.info(f"Source: {source.get('source', 'N/A')}")
                                st.text(source.get('content', ''))
                        except Exception:
                            st.warning("Could not parse sources.")

    # Chat input
    prompt = st.chat_input("Ask a question about your documents...")
    if prompt:
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare payload
        payload = {"query": prompt}
        if st.session_state.current_chat_id:
            payload["chat_id"] = st.session_state.current_chat_id

        # Call API
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(f"{API_URL}/chat/{project_id}", json=payload, headers=get_auth_headers())
                except Exception as e:
                    message_placeholder.markdown(f"Error: {e}")
                    return

            if response.status_code == 200:
                data = response.json()
                full_response = data.get("answer", "No answer found.")
                message_placeholder.markdown(full_response)

                # Update session state with new chat ID if it's a new chat
                if not st.session_state.current_chat_id:
                    st.session_state.current_chat_id = data['chat_id']
                    st.session_state.messages[data['chat_id']] = []
                    st.rerun()  # Rerun to show history list

                # Display sources
                if data.get("sources"):
                    with st.expander("Sources"):
                        for source in data["sources"]:
                            st.info(f"Source: {source.get('source', 'N/A')}")
                            st.text(source.get('content', ''))
            else:
                full_response = f"Error: {response.text}"
                message_placeholder.markdown(full_response)

# --- Page Routing ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    main_app()
else:
    auth_page()