"""
Unified Streamlit UI for Chat with Documents

This module handles the complete user experience, including:
- User authentication via password, Google, and Apple (OAuth2).
- Project management with a choice of LLM providers (Cloud vs. Local).
- Document management (upload, URL, status tracking).
- Real-time chat interaction with source citations.
"""
import streamlit as st
import requests
import pandas as pd
import json
from typing import Dict, Any, List, Optional
import os

# --- Configuration ---
st.set_page_config(
    page_title="Chat with Your Docs",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🤖"
)

# --- API URL Helpers ---
def get_api_url() -> str:
    """Returns the INTERNAL API URL for server-to-server calls."""
    return os.getenv("API_URL", "http://localhost:8000/api/v1")

def get_public_api_url() -> str:
    """Returns the PUBLIC API URL for browser-facing links (like OAuth)."""
    return os.getenv("PUBLIC_API_URL", "http://localhost:8000/api/v1")

API_URL = get_api_url()
PUBLIC_API_URL = get_public_api_url()


# --- Authentication & Session Management ---

def initialize_session_state():
    """Initializes all required keys in the session state to prevent errors."""
    defaults = {
        "logged_in": False,
        "username": None,
        "token": None,
        "projects": [],
        "current_project_id": None,
        "current_project_name": None,
        "current_chat_id": None,
        "messages": {}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def handle_oauth_token():
    """Checks for an OAuth token in the URL params and attempts to log in."""
    if token := st.query_params.get("token"):
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(f"{API_URL}/auth/users/me", headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                st.session_state.token = token
                st.session_state.username = user_data["username"]
                st.session_state.logged_in = True
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Login failed: Invalid token received from provider.")
        except requests.RequestException as e:
            st.error(f"Login failed: Could not connect to API to validate token. {e}")

def login_user(username: str, password: str) -> bool:
    """Authenticates with password and stores token."""
    try:
        response = requests.post(f"{API_URL}/auth/token", data={"username": username, "password": password})
        if response.status_code == 200:
            st.session_state.token = response.json()["access_token"]
            st.session_state.username = username
            st.session_state.logged_in = True
            return True
        else:
            st.error(f"Login failed: {response.json().get('detail', 'Invalid credentials')}")
            return False
    except requests.RequestException as e:
        st.error(f"Connection to API failed: {e}")
        return False

def signup_user(username: str, email: str, password: str) -> bool:
    """Registers a new user."""
    try:
        response = requests.post(f"{API_URL}/auth/signup", json={"username": username, "email": email, "password": password})
        if response.status_code == 201:
            st.success("Signup successful! Please log in.")
            return True
        else:
            st.error(f"Signup failed: {response.json().get('detail', 'Unknown error')}")
            return False
    except requests.RequestException as e:
        st.error(f"Connection to API failed: {e}")
        return False

def logout_user():
    """Clears session state for logout."""
    initialize_session_state()
    st.success("Logged out successfully.")
    st.rerun()

def auth_page():
    """Renders the two-column authentication page."""
    st.title("🤖 Chat with Your Docs")
    st.markdown("Unlock insights from your documents using the power of local or cloud-based AI. **Log in or create an account to get started.**")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.form_submit_button("Login", use_container_width=True):
                if login_user(username, password):
                    st.rerun()
        
        st.divider()
        st.markdown("Or sign in with a single click:")
        
        google_login_url = f"{PUBLIC_API_URL}/auth/login/google"
        st.markdown(f"""<a href="{google_login_url}" target="_top" style="display: flex; align-items: center; justify-content: center; font-family: 'Roboto', sans-serif; font-weight: 500; font-size: 14px; color: #333; background-color: #ffffff; border: 1px solid #ddd; border-radius: 4px; padding: 10px 24px; text-decoration: none; width: 100%; margin-top: 10px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.1);"><img src="https://accounts.google.com/favicon.ico" alt="Google logo" style="margin-right: 10px; width: 18px; height: 18px;">Sign in with Google</a>""", unsafe_allow_html=True)
        
        st.markdown(f"""<div style="display: flex; align-items: center; justify-content: center; font-family: -apple-system, 'Helvetica Neue', sans-serif; font-weight: 500; font-size: 14px; color: #888; background-color: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; padding: 10px 24px; text-decoration: none; width: 100%; margin-top: 10px; cursor: not-allowed;"><svg viewBox="0 0 16 16" style="margin-right: 10px; width: 18px; height: 18px; fill: #888;" xmlns="http://www.w3.org/2000/svg"><path d="M8.614 11.535c-.422.188-.87.31-1.344.31-.598 0-1.156-.16-1.676-.478-.05-.03-.132-.075-.15-.088l-.06-.045c-1.21-.806-2.115-2.223-2.115-3.843 0-1.226.582-2.313 1.488-3.053.453-.37.97-.582 1.54-.596.536 0 1.05.203 1.5.555.03.022.09.06.11.075l.064.045c.42.315.686.825.686 1.41 0 .42-.142.795-.424 1.11-.274.308-.63.533-1.046.615.93.525 1.533 1.485 1.533 2.595 0 .57-.195 1.103-.525 1.53zM12.43 9.4c.038-1.245-.6-2.25-1.71-2.25-.9 0-1.545.69-1.92 1.17.615 1.545.42 3.195 1.845 3.195.405 0 .81-.195 1.2-.495-.12-.015-.645-.255-.495-1.62z"></path></svg>Sign in with Apple (Coming Soon)</div>""", unsafe_allow_html=True)

    with col2:
        st.subheader("Create an Account")
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username", key="signup_user")
            new_email = st.text_input("Your Email Address", key="signup_email")
            new_password = st.text_input("Choose a Password", type="password", key="signup_pass")
            if st.form_submit_button("Sign Up", use_container_width=True):
                signup_user(new_username, new_email, new_password)


# --- API Helper Functions ---

def get_auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

def api_request(method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
    """A centralized function for making API requests."""
    try:
        url = f"{API_URL}/{endpoint}"
        res = requests.request(method, url, headers=get_auth_headers(), **kwargs)
        res.raise_for_status()
        return res
    except requests.exceptions.RequestException as e:
        status = e.response.status_code if e.response is not None else "N/A"
        try:
            detail = e.response.json().get('detail', e.response.text)
        except (AttributeError, json.JSONDecodeError):
            detail = str(e)
        st.error(f"API Error ({status}): {detail}")
        return None

# --- Main Application UI ---

def project_sidebar():
    """Renders the project selection and creation UI in the sidebar."""
    st.sidebar.title(f"Welcome, {st.session_state.username}!")
    
    projects_res = api_request("GET", "projects/")
    st.session_state.projects = projects_res.json() if projects_res else []
    project_names = [p['name'] for p in st.session_state.projects]
    
    st.sidebar.header("Projects")
    
    if project_names:
        if st.session_state.current_project_name not in project_names:
            st.session_state.current_project_name = project_names[0]
            st.session_state.current_chat_id = None
        
        selected_project_index = project_names.index(st.session_state.current_project_name)
        selected_project_name = st.sidebar.selectbox("Select Project", options=project_names, index=selected_project_index)
        
        if selected_project_name != st.session_state.current_project_name:
            st.session_state.current_project_name = selected_project_name
            st.session_state.current_chat_id = None
            st.rerun()
            
        current_project = next((p for p in st.session_state.projects if p['name'] == selected_project_name), {})
        st.session_state.current_project_id = current_project.get('id')
        provider = current_project.get('llm_provider', 'groq').upper()
        st.sidebar.caption(f"Provider: {provider}")
    else:
        st.sidebar.info("Create a project to get started.")

    with st.sidebar.expander("Create New Project"):
        with st.form("new_project_form", clear_on_submit=True):
            new_project_name = st.text_input("Project Name")
            llm_provider = st.selectbox("LLM Provider", options=["groq", "ollama"], format_func=lambda x: "Groq (Cloud)" if x == "groq" else "Ollama (Local)")
            default_model = "llama3-8b-8192" if llm_provider == "groq" else "llama3"
            llm_model_name = st.text_input("Model Name", value=default_model)

            if st.form_submit_button("Create Project"):
                if new_project_name:
                    payload = {"name": new_project_name, "llm_provider": llm_provider, "llm_model_name": llm_model_name}
                    if res := api_request("POST", "projects/", json=payload):
                        st.session_state.current_project_name = res.json()['name']
                        st.rerun()
                else:
                    st.warning("Project name cannot be empty.")
    
    st.sidebar.header("Account")
    if st.sidebar.button("Logout", use_container_width=True):
        logout_user()

def chat_history_sidebar():
    """Renders the chat history for the current project."""
    st.sidebar.header("Chat History")
    if st.session_state.current_project_id:
        if st.sidebar.button("➕ New Chat", use_container_width=True):
            st.session_state.current_chat_id = None
            st.rerun()
        
        if sessions_res := api_request("GET", f"chat/sessions/{st.session_state.current_project_id}"):
            for session in sessions_res.json():
                if st.sidebar.button(session['title'], key=f"session_{session['id']}", use_container_width=True):
                    st.session_state.current_chat_id = session['id']
                    st.rerun()
    
def chat_pane():
    """Renders the main chat interface."""
    st.header(f"Project: {st.session_state.current_project_name}")
    
    # Load and display chat messages
    if st.session_state.current_chat_id:
        if 'messages' not in st.session_state or st.session_state.messages.get('chat_id') != st.session_state.current_chat_id:
            if res := api_request("GET", f"chat/sessions/{st.session_state.current_project_id}/{st.session_state.current_chat_id}"):
                st.session_state.messages = {'chat_id': st.session_state.current_chat_id, 'history': res.json()['messages']}
        
        for msg in st.session_state.messages.get('history', []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Handle new user input
    if prompt := st.chat_input("Ask a question about your documents..."):
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")
            
            payload = {"query": prompt, "chat_id": st.session_state.current_chat_id}
            if res := api_request("POST", f"chat/{st.session_state.current_project_id}", json=payload):
                response_data = res.json()
                message_placeholder.markdown(response_data["answer"])
                with st.expander("Sources"):
                    for source in response_data["sources"]:
                        st.info(f"Source: {source.get('source', 'N/A')}")
                        st.text(source.get('content', ''))
                
                # If it was a new chat, update session state and rerun
                if not st.session_state.current_chat_id:
                    st.session_state.current_chat_id = response_data['chat_id']
                    st.rerun()
            else:
                message_placeholder.markdown("An error occurred while getting an answer.")

def document_manager_pane():
    """Renders the document management UI."""
    st.header(f"Manage Documents for '{st.session_state.current_project_name}'")

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("Upload New Documents", expanded=True):
            uploaded_files = st.file_uploader("Upload files", type=["pdf", "docx", "txt", "md"], accept_multiple_files=True)
            if st.button("Upload Files", use_container_width=True):
                if uploaded_files:
                    success_count = 0
                    for file in uploaded_files:
                        files = {'file': (file.name, file.getvalue(), file.type)}
                        if api_request("POST", f"documents/upload/{st.session_state.current_project_id}", files=files):
                            success_count += 1
                    st.success(f"{success_count}/{len(uploaded_files)} files uploaded successfully. Processing has started.")
                    st.rerun()
                else:
                    st.warning("Please select at least one file to upload.")

    with col2:
        with st.expander("Add Document from URL", expanded=True):
            url = st.text_input("Enter a URL")
            if st.button("Add URL", use_container_width=True):
                if url:
                    if api_request("POST", f"documents/upload_url/{st.session_state.current_project_id}", json={"url": url}):
                        st.success(f"URL added. Processing has started.")
                        st.rerun()
                else:
                    st.warning("Please enter a URL.")
    
    st.markdown("---")
    st.subheader("Project Documents")
    if st.button("Refresh Status"):
        st.rerun()

    if docs_res := api_request("GET", f"documents/{st.session_state.current_project_id}"):
        docs = docs_res.json()
        if not docs:
            st.info("No documents have been added to this project yet.")
        else:
            doc_data = []
            for doc in docs:
                status = doc.get('status', 'UNKNOWN').capitalize()
                status_icon = {"Pending": "⚪", "Processing": "⏳", "Completed": "✅", "Failed": "❌"}.get(status, "❓")
                doc_data.append({"Status": f"{status_icon} {status}", "File Name": doc.get('file_name', 'N/A'), "ID": doc.get('id')})
            
            df = pd.DataFrame(doc_data)
            st.dataframe(df[['Status', 'File Name']], use_container_width=True, hide_index=True)

def main_app():
    """Renders the main application interface after authentication."""
    st.sidebar.image("https://www.onepointltd.com/wp-content/uploads/2020/03/inno2.png") # Placeholder logo
    project_sidebar()
    chat_history_sidebar()
    
    if not st.session_state.current_project_id:
        st.info("Please create or select a project from the sidebar to begin.")
        return

    main_area, docs_area = st.columns([2, 1])
    with main_area:
        chat_pane()
    with docs_area:
        document_manager_pane()


# --- Main Execution Logic ---

if __name__ == "__main__":
    initialize_session_state()
    handle_oauth_token()

    if st.session_state.logged_in:
        main_app()
    else:
        auth_page()