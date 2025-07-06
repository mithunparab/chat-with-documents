# frontend/app.py

import streamlit as st
import requests
import pandas as pd
import json
from typing import Dict, Any, List, Optional
import os

# --- Configuration and API Setup ---

st.set_page_config(
    page_title="Chat with Documents",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_api_url() -> str:
    """Returns the API URL from environment variable or defaults to localhost."""
    return os.getenv("API_URL", "http://localhost:8000/api/v1")

API_URL = get_api_url()
GOOGLE_LOGIN_URL = f"{API_URL}/auth/login/google"

# --- Session State Initialization ---

def init_session_state():
    """Initializes all required keys in the session state."""
    defaults = {
        "logged_in": False,
        "token": None,
        "username": None,
        "current_project_id": None,
        "current_project_name": None,
        "current_chat_id": None,
        "messages": {},  # Stores messages per chat_id: {'chat_id': [messages]}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- API Client Functions ---

class ApiClient:
    """A client to interact with the backend API."""
    def _get_headers(self) -> Dict[str, str]:
        if st.session_state.token:
            return {"Authorization": f"Bearer {st.session_state.token}"}
        return {}

    def _handle_request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        url = f"{API_URL}/{endpoint}"
        try:
            response = requests.request(method, url, headers=self._get_headers(), **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            try:
                detail = e.response.json().get("detail", e.response.text)
            except json.JSONDecodeError:
                detail = e.response.text
            
            if status_code == 401:
                st.error("Authentication failed. Please log in again.")
                logout()
            else:
                st.error(f"API Error ({status_code}): {detail}")
        except requests.exceptions.RequestException as e:
            st.error(f"Connection Error: Could not connect to the API. {e}")
        return None

    def login(self, username, password) -> bool:
        try:
            response = requests.post(f"{API_URL}/auth/token", data={"username": username, "password": password})
            if response.status_code == 200:
                token_data = response.json()
                st.session_state.token = token_data["access_token"]
                st.session_state.username = username
                st.session_state.logged_in = True
                return True
            else:
                st.error(f"Login failed: {response.json().get('detail', 'Invalid credentials')}")
        except requests.exceptions.RequestException as e:
            st.error(f"Connection to API failed: {e}")
        return False
        
    def signup(self, username, password) -> bool:
        try:
            response = requests.post(f"{API_URL}/auth/signup", json={"username": username, "password": password})
            if response.status_code == 200:
                st.success("Signup successful! Please log in.")
                return True
            else:
                st.error(f"Signup failed: {response.json().get('detail', 'Unknown error')}")
        except requests.exceptions.RequestException as e:
            st.error(f"Connection to API failed: {e}")
        return False

    def get_projects(self) -> List[Dict[str, Any]]:
        response = self._handle_request("get", "projects/")
        return response.json() if response else []

    def create_project(self, name: str) -> Optional[Dict[str, Any]]:
        response = self._handle_request("post", "projects/", json={"name": name})
        return response.json() if response else None

    def get_documents(self, project_id: str) -> List[Dict[str, Any]]:
        response = self._handle_request("get", f"documents/{project_id}")
        return response.json() if response else []

    def upload_document_file(self, project_id: str, file) -> bool:
        files = {'file': (file.name, file.getvalue(), file.type)}
        response = self._handle_request("post", f"documents/upload/{project_id}", files=files)
        return response is not None

    def upload_document_from_url(self, project_id: str, url: str) -> bool:
        response = self._handle_request("post", f"documents/upload_url/{project_id}", json={"url": url})
        return response is not None

    def delete_document(self, project_id: str, document_id: str) -> bool:
        response = self._handle_request("delete", f"documents/{project_id}/{document_id}")
        return response is not None

    def get_chat_sessions(self, project_id: str) -> List[Dict[str, Any]]:
        response = self._handle_request("get", f"chat/sessions/{project_id}")
        return response.json() if response else []

    def delete_chat_session(self, project_id: str, session_id: str) -> bool:
        response = self._handle_request("delete", f"chat/sessions/{project_id}/{session_id}")
        return response is not None

    def send_chat_query(self, project_id: str, query: str, chat_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        payload = {"query": query, "chat_id": chat_id}
        response = self._handle_request("post", f"chat/{project_id}", json=payload)
        return response.json() if response else None

client = ApiClient()

# --- Authentication Logic ---

def logout():
    """Clears session state and reruns to show login page."""
    keys_to_clear = list(st.session_state.keys())
    for key in keys_to_clear:
        del st.session_state[key]
    st.rerun()

def handle_google_auth_callback():
    """Checks for token in URL params from Google OAuth redirect."""
    token = st.query_params.get("token")
    if token:
        st.session_state.token = token
        # For simplicity, we can't easily get the username here without another API call.
        # We'll set a generic name or leave it to be fetched later.
        st.session_state.username = "User" # Or make a /users/me endpoint
        st.session_state.logged_in = True
        st.query_params.clear() # Clean the URL
        st.rerun()

def auth_page():
    """Renders the authentication page for login and signup."""
    st.title("Welcome to Chat with Documents")
    st.markdown("Log in to chat with your documents using advanced AI.")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username (Email)")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted and client.login(username, password):
                st.rerun()

        st.markdown("---")
        st.link_button("Sign in with Google", GOOGLE_LOGIN_URL, use_container_width=True)

    with col2:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username (Email)")
            new_password = st.text_input("Choose a Password", type="password")
            submitted = st.form_submit_button("Sign Up")
            if submitted:
                client.signup(new_username, new_password)


# --- Main App UI Components ---

def project_sidebar():
    """Renders project selection and management in the sidebar."""
    st.sidebar.title(f"Welcome!") # Welcome, {st.session_state.username}!")
    st.sidebar.header("Projects")

    projects = client.get_projects()
    if not projects:
        st.sidebar.info("No projects yet. Create one below.")
    else:
        project_names = [p['name'] for p in projects]
        # Set a default project if none is selected or the selected one is gone
        if not st.session_state.current_project_name or st.session_state.current_project_name not in project_names:
            st.session_state.current_project_name = project_names[0]

        selected_name = st.sidebar.selectbox(
            "Select Project",
            options=project_names,
            index=project_names.index(st.session_state.current_project_name)
        )
        if selected_name != st.session_state.current_project_name:
            st.session_state.current_project_name = selected_name
            st.session_state.current_chat_id = None # Reset chat on project switch
            st.rerun()

        # Update project ID based on selected name
        project_map = {p['name']: p['id'] for p in projects}
        st.session_state.current_project_id = project_map.get(st.session_state.current_project_name)

    with st.sidebar.expander("Create New Project"):
        with st.form("new_project_form", clear_on_submit=True):
            new_project_name = st.text_input("Project Name")
            if st.form_submit_button("Create"):
                if new_project_name:
                    if client.create_project(new_project_name):
                        st.rerun()
                else:
                    st.warning("Project name cannot be empty.")

def chat_history_sidebar():
    st.sidebar.header("Chat History")
    project_id = st.session_state.current_project_id
    if not project_id:
        st.sidebar.info("Select a project to see chat history.")
        return

    if st.sidebar.button("➕ New Chat", use_container_width=True):
        st.session_state.current_chat_id = None
        st.rerun()

    sessions = client.get_chat_sessions(project_id)
    for session in sessions:
        is_selected = session['id'] == st.session_state.current_chat_id
        button_type = "primary" if is_selected else "secondary"
        
        col_title, col_del = st.sidebar.columns([4, 1])
        if col_title.button(session['title'], key=f"session_{session['id']}", use_container_width=True, type=button_type):
            st.session_state.current_chat_id = session['id']
            st.session_state.messages[session['id']] = session['messages']
            st.rerun()
        
        if col_del.button("🗑️", key=f"del_{session['id']}", use_container_width=True):
            if client.delete_chat_session(project_id, session['id']):
                if st.session_state.current_chat_id == session['id']:
                    st.session_state.current_chat_id = None
                st.rerun()

def chat_pane():
    """Renders the main chat interface."""
    project_id = st.session_state.current_project_id
    chat_id = st.session_state.current_chat_id

    st.subheader(f"Chat")
    
    # Display existing messages
    if chat_id and chat_id in st.session_state.messages:
        for msg in st.session_state.messages[chat_id]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("sources"):
                    sources = json.loads(msg["sources"]) if isinstance(msg["sources"], str) else msg["sources"]
                    with st.expander("View Sources"):
                        for i, source in enumerate(sources):
                            st.info(f"Source {i+1}: {source.get('source', 'N/A')}")
                            st.code(source.get('content', ''), language=None)
    elif not chat_id:
         st.info("Start a new chat or select a previous one from the sidebar.")

    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Display user message
        if not chat_id:
            st.session_state.messages['new_chat'] = []
        
        # Add user message to state
        current_messages = st.session_state.messages.get(chat_id or 'new_chat', [])
        current_messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = client.send_chat_query(project_id, prompt, chat_id)
            
            if response:
                answer = response.get("answer", "Sorry, something went wrong.")
                sources = response.get("sources", [])
                st.markdown(answer)

                if sources:
                    with st.expander("View Sources"):
                        for i, source in enumerate(sources):
                            st.info(f"Source {i+1}: {source.get('source', 'N/A')}")
                            st.code(source.get('content', ''), language=None)
                
                # Update state and rerun to finalize the new chat session
                new_chat_id = response.get('chat_id')
                if not chat_id and new_chat_id: # This was a new chat
                    st.session_state.current_chat_id = new_chat_id
                    st.session_state.messages[new_chat_id] = [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": answer, "sources": json.dumps(sources)}
                    ]
                    if 'new_chat' in st.session_state.messages:
                        del st.session_state.messages['new_chat']
                    st.rerun()
                elif chat_id: # Existing chat
                    current_messages.append({"role": "assistant", "content": answer, "sources": json.dumps(sources)})

def document_manager_pane():
    """Renders the document management UI."""
    project_id = st.session_state.current_project_id
    st.subheader("Document Management")
    
    # Upload controls
    with st.expander("Add New Documents", expanded=True):
        tab_file, tab_url = st.tabs(["Upload File", "Add from URL"])
        with tab_file:
            uploaded_files = st.file_uploader(
                "Upload PDF, DOCX, TXT, MD files",
                type=["pdf", "docx", "txt", "md"],
                accept_multiple_files=True
            )
            if st.button("Upload Files"):
                if uploaded_files:
                    with st.spinner("Uploading..."):
                        for file in uploaded_files:
                            client.upload_document_file(project_id, file)
                    st.success("Upload tasks started. Refresh list to see status.")
                    st.rerun()

        with tab_url:
            url = st.text_input("Enter a public URL")
            if st.button("Add URL"):
                if url:
                    with st.spinner("Processing URL..."):
                        if client.upload_document_from_url(project_id, url):
                            st.success("URL processing started. Refresh list to see status.")
                            st.rerun()

    # Document list
    st.markdown("---")
    st.subheader("Project Documents")
    if st.button("Refresh List"):
        st.rerun()

    docs = client.get_documents(project_id)
    if not docs:
        st.info("No documents uploaded yet.")
    else:
        doc_data = []
        for doc in docs:
            status_map = {
                "COMPLETED": "✅ Completed", "PROCESSING": "⏳ Processing",
                "PENDING": "⚪ Pending", "FAILED": "❌ Failed"
            }
            doc_data.append({
                "File Name": doc.get('file_name'),
                "Status": status_map.get(doc.get('status', 'FAILED')),
                "id": doc.get('id')
            })
        
        for item in doc_data:
            col1, col2, col3 = st.columns([4, 2, 1])
            col1.write(item["File Name"])
            col2.write(item["Status"])
            if col3.button("🗑️", key=f"del_doc_{item['id']}"):
                with st.spinner("Deleting..."):
                    if client.delete_document(project_id, item['id']):
                        st.rerun()

def main_app():
    """Renders the main application interface after authentication."""
    project_sidebar()
    chat_history_sidebar()
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        logout()

    st.header(f"Project: {st.session_state.current_project_name or 'N/A'}")
    
    if st.session_state.current_project_id:
        tab1, tab2 = st.tabs(["Chat", "Document Management"])
        with tab1:
            chat_pane()
        with tab2:
            document_manager_pane()
    else:
        st.info("Create or select a project from the sidebar to begin.")

# --- App Entry Point ---

if __name__ == "__main__":
    init_session_state()
    handle_google_auth_callback()

    if st.session_state.logged_in:
        main_app()
    else:
        auth_page()