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

# --- Model Selection Options ---
MODEL_OPTIONS = {
    "groq": {
        "Llama 3 8B": "llama3-8b-8192",
        "Llama 3 70B": "llama3-70b-8192",
        "Mixtral 8x7B": "mixtral-8x7b-32768",
        "Gemma 7B": "gemma-7b-it",
    },
    "ollama": {
        "Llama 3": "llama3",
        "Gemma": "gemma",
        "Phi-3": "phi3",
        "Mistral": "mistral",
    }
}

# --- Authentication & Session Management ---

def initialize_session_state():
    """Initializes all required keys in the session state to prevent errors."""
    defaults = {
        "logged_in": False,
        "username": "Guest",
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
    if "token" in st.query_params:
        token = st.query_params["token"]
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(f"{API_URL}/auth/users/me", headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                st.session_state.token = token
                # **FIX**: Use full name if available, otherwise fallback to username
                st.session_state.username = user_data.get("full_name") or user_data.get("username", "User")
                st.session_state.logged_in = True
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Login failed: Invalid token received from provider.")
                st.query_params.clear()
        except requests.RequestException as e:
            st.error(f"Login failed: Could not connect to API to validate token. {e}")
            st.query_params.clear()

def login_user(username: str, password: str) -> bool:
    """Authenticates with password and stores token."""
    try:
        response = requests.post(f"{API_URL}/auth/token", data={"username": username, "password": password})
        if response.status_code == 200:
            st.session_state.token = response.json()["access_token"]
            st.session_state.username = username # For local login, username is the display name
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
        # **FIX**: Ensure the payload matches the backend schema (UserCreate requires email)
        payload = {"username": username, "email": email, "password": password}
        response = requests.post(f"{API_URL}/auth/signup", json=payload)
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
    """Clears session state for logout and flags a message to be shown."""
    # **FIX**: Reset the entire session state to its initial default values
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()
    st.query_params.clear()
    st.query_params["logout"] = "true" # Flag to show logout message on next run
    st.rerun()

def auth_page():
    """Renders the two-column authentication page."""
    if "logout" in st.query_params:
        st.success("You have been logged out successfully.")
        st.query_params.clear()

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
        st.link_button("Sign in with Google", google_login_url, use_container_width=True)
        st.button("Sign in with Apple (Coming Soon)", use_container_width=True, disabled=True)


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
        if e.response is not None:
            status = e.response.status_code
            try:
                detail = e.response.json().get('detail', e.response.text)
            except (AttributeError, json.JSONDecodeError):
                detail = str(e)
            st.error(f"API Error ({status}): {detail}")
        else:
            st.error(f"API Connection Error: {e}")
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
        model_name = current_project.get('llm_model_name', 'default')
        st.sidebar.caption(f"Provider: {provider} | Model: {model_name}")
    else:
        st.sidebar.info("Create a project to get started.")

    with st.sidebar.expander("Create New Project"):
        with st.form("new_project_form", clear_on_submit=True):
            new_project_name = st.text_input("Project Name")
            
            # **FIX**: Dynamic model selection
            llm_provider = st.selectbox(
                "LLM Provider", 
                options=list(MODEL_OPTIONS.keys()), 
                format_func=lambda x: "Groq (Cloud)" if x == "groq" else "Ollama (Local)"
            )
            
            provider_models = MODEL_OPTIONS.get(llm_provider, {})
            model_display_names = list(provider_models.keys())
            
            selected_model_display_name = st.selectbox("Select Model", options=model_display_names)
            llm_model_name = provider_models.get(selected_model_display_name)

            if st.form_submit_button("Create Project"):
                if new_project_name and llm_model_name:
                    payload = {"name": new_project_name, "llm_provider": llm_provider, "llm_model_name": llm_model_name}
                    if res := api_request("POST", "projects/", json=payload):
                        st.session_state.current_project_name = res.json()['name']
                        st.rerun()
                else:
                    st.warning("Project name cannot be empty.")
    
    st.sidebar.header("Profile")
    if st.sidebar.button("Logout", use_container_width=True):
        logout_user()

def chat_history_sidebar():
    """Renders the chat history for the current project."""
    st.sidebar.header("Chat History")
    if st.session_state.current_project_id:
        if st.sidebar.button("➕ New Chat", use_container_width=True):
            st.session_state.current_chat_id = None
            if 'messages' in st.session_state:
                st.session_state.messages = {}
            st.rerun()
        
        if sessions_res := api_request("GET", f"chat/sessions/{st.session_state.current_project_id}"):
            for session in sessions_res.json():
                if st.sidebar.button(session['title'], key=f"session_{session['id']}", use_container_width=True):
                    st.session_state.current_chat_id = session['id']
                    st.rerun()
    
def chat_pane():
    """Renders the main chat interface."""
    st.header(f"Project: {st.session_state.current_project_name}")
    
    if st.session_state.current_chat_id:
        if 'messages' not in st.session_state or st.session_state.messages.get('chat_id') != st.session_state.current_chat_id:
            if res := api_request("GET", f"chat/sessions/{st.session_state.current_project_id}/{st.session_state.current_chat_id}"):
                st.session_state.messages = {'chat_id': st.session_state.current_chat_id, 'history': res.json()['messages']}
        
        for msg in st.session_state.messages.get('history', []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    else:
        if 'history' in st.session_state.get('messages', {}):
            st.session_state.messages['history'] = []

    if prompt := st.chat_input("Ask a question about your documents..."):
        if 'history' not in st.session_state.get('messages', {}):
            st.session_state.messages['history'] = []
        st.session_state.messages['history'].append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # **FIX**: Better user feedback during wait time
            with st.spinner("🔍 Searching documents and formulating a response... This may take a moment."):
                payload = {"query": prompt, "chat_id": st.session_state.current_chat_id}
                res = api_request("POST", f"chat/{st.session_state.current_project_id}", json=payload)

            if res:
                response_data = res.json()
                st.markdown(response_data["answer"])
                st.session_state.messages['history'].append({"role": "assistant", "content": response_data["answer"]})
                
                with st.expander("Sources"):
                    for source in response_data["sources"]:
                        st.info(f"Source: {source.get('source', 'N/A')}")
                        st.text(source.get('content', ''))
                
                if not st.session_state.current_chat_id:
                    st.session_state.current_chat_id = response_data['chat_id']
                    st.rerun()
            else:
                st.error("An error occurred while getting an answer.")
                st.session_state.messages['history'].pop()

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
                    st.success(f"{success_count}/{len(uploaded_files)} files uploaded. Processing has started in the background.")
                    st.rerun()
                else:
                    st.warning("Please select at least one file to upload.")

    with col2:
        with st.expander("Add Document from URL", expanded=True):
            url = st.text_input("Enter a URL")
            if st.button("Add URL", use_container_width=True):
                if url:
                    if api_request("POST", f"documents/upload_url/{st.session_state.current_project_id}", json={"url": url}):
                        st.success(f"URL added. Processing has started in the background.")
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
                status = doc.get('status', 'UNKNOWN')
                status_icon = {"PENDING": "⚪️", "PROCESSING": "⏳", "COMPLETED": "✅", "FAILED": "❌"}.get(status, "❓")
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