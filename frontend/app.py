"""
Main Streamlit UI logic for Chat with Documents.

This module handles authentication, project and document management, chat interactions,
and the overall user interface for the document chat application.
"""
import streamlit as st
import requests
import pandas as pd
import json
from typing import Dict, Any, List, Optional
import os

def get_api_url() -> str:
    """Returns the API URL from the environment variable or defaults to localhost."""
    return os.getenv("API_URL", "http://localhost:8000/api/v1")

API_URL = get_api_url()

st.set_page_config(
    page_title="Chat with Documents",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Authentication and Session Management ---

def initialize_session():
    """Initializes all required keys in the session state."""
    defaults = {
        "logged_in": False,
        "username": None,
        "token": None,
        "current_project_name": None,
        "current_project_id": None,
        "current_chat_id": None,
        "messages": {}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def validate_token_and_login(token: str):
    """Validates a token with the backend and logs the user in."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_URL}/auth/users/me", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            st.session_state.token = token
            st.session_state.username = user_data["username"]
            st.session_state.logged_in = True
            # Use st.query_params.clear() in Streamlit > 1.33.0
            st.query_params.clear()
            return True
        else:
            st.error("Login failed: Invalid token.")
            return False
    except requests.RequestException as e:
        st.error(f"Login failed: Could not connect to API. {e}")
        return False

def login_user(username: str, password: str) -> bool:
    """Authenticates with password and stores token in session state."""
    try:
        response = requests.post(f"{API_URL}/auth/token", data={"username": username, "password": password})
        if response.status_code == 200:
            token = response.json()["access_token"]
            return validate_token_and_login(token)
        else:
            error_detail = response.json().get('detail', 'Invalid credentials')
            st.error(f"Login failed: {error_detail}")
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
            error_detail = response.json().get('detail', 'Unknown error')
            st.error(f"Signup failed: {error_detail}")
            return False
    except requests.RequestException as e:
        st.error(f"Connection to API failed: {e}")
        return False

def logout_user():
    """Clears session state for logout."""
    # Re-initialize to clear all state
    initialize_session()
    st.success("Logged out successfully. Please log in again.")
    st.rerun()

def auth_page():
    """Renders the authentication page for login and signup."""
    st.title("Welcome to Chat with Documents")
    st.markdown("Chat with your documents using advanced AI. Log in or create an account to get started.")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted and login_user(username, password):
                st.rerun()
        
        st.divider()
        
        st.markdown("Or sign in with:")
        # These will open the link in a new tab by default which is fine.
        # The user returns to the app and the token in URL is detected.
        st.link_button("Sign in with Google", f"{API_URL}/auth/login/google", use_container_width=True)
        st.link_button("Sign in with Apple", f"{API_URL}/auth/login/apple", use_container_width=True)

    with col2:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username", key="signup_user")
            new_email = st.text_input("Your Email Address", key="signup_email")
            new_password = st.text_input("Choose a Password", type="password", key="signup_pass")
            submitted = st.form_submit_button("Sign Up")
            if submitted:
                signup_user(new_username, new_email, new_password)

# --- API Helper Functions (unchanged from here, just adding comments) ---

def get_auth_headers() -> Dict[str, str]:
    """Returns the authorization headers for API requests."""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def get_projects() -> List[Dict[str, Any]]:
    # ... (rest of the function is identical)
    try:
        res = requests.get(f"{API_URL}/projects/", headers=get_auth_headers())
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching projects: {e}")
        return []

def create_project(name: str) -> Optional[Dict[str, Any]]:
    # ... (rest of the function is identical)
    try:
        res = requests.post(f"{API_URL}/projects/", json={"name": name}, headers=get_auth_headers())
        res.raise_for_status()
        st.success(f"Project '{name}' created successfully!")
        return res.json()
    except requests.exceptions.RequestException as e:
        error_detail = e.response.json().get('detail', 'An unexpected error occurred') if e.response else 'Connection Error'
        st.error(f"Failed to create project '{name}': {error_detail}")
        return None

def get_documents(project_id: str) -> List[Dict[str, Any]]:
    # ... (rest of the function is identical)
    try:
        res = requests.get(f"{API_URL}/documents/{project_id}", headers=get_auth_headers())
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching documents: {e}")
        return []

def upload_document_file(project_id: str, file: st.file_uploader) -> bool:
    # ... (rest of the function is identical)
    try:
        files = {'file': (file.name, file.getvalue(), file.type)}
        res = requests.post(f"{API_URL}/documents/upload/{project_id}", files=files, headers=get_auth_headers())
        res.raise_for_status()
        st.success(f"'{file.name}' uploaded. Processing started.")
        return True
    except requests.exceptions.RequestException as e:
        error_detail = e.response.json().get('detail', 'An unexpected error occurred') if e.response else 'Connection Error'
        st.error(f"Failed to upload '{file.name}': {error_detail}")
        return False

def upload_document_from_url(project_id: str, url: str) -> bool:
    # ... (rest of the function is identical)
    try:
        payload = {"url": url}
        res = requests.post(f"{API_URL}/documents/upload_url/{project_id}", json=payload, headers=get_auth_headers())
        res.raise_for_status()
        st.success(f"URL '{url}' added. Processing started.")
        return True
    except requests.exceptions.RequestException as e:
        error_detail = e.response.json().get('detail', 'An unexpected error occurred') if e.response else 'Connection Error'
        st.error(f"Failed to add URL '{url}': {error_detail}")
        return False

def delete_document(project_id: str, document_id: str) -> bool:
    # ... (rest of the function is identical)
    try:
        res = requests.delete(f"{API_URL}/documents/{project_id}/{document_id}", headers=get_auth_headers())
        if res.status_code == 204:
            st.success("Document deleted successfully.")
            return True
        else:
            error_detail = res.json().get('detail', 'An unexpected error occurred') if res.response else 'Unknown Error'
            st.error(f"Failed to delete document: {error_detail}")
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection to API failed: {e}")
        return False

def get_chat_sessions(project_id: str) -> List[Dict[str, Any]]:
    # ... (rest of the function is identical)
    try:
        res = requests.get(f"{API_URL}/chat/sessions/{project_id}", headers=get_auth_headers())
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching chat history: {e}")
        return []

def get_chat_session_messages(project_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    # ... (rest of the function is identical)
    try:
        res = requests.get(f"{API_URL}/chat/sessions/{project_id}/{session_id}", headers=get_auth_headers())
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching chat session messages: {e}")
        return None

def delete_chat_session(project_id: str, session_id: str) -> bool:
    # ... (rest of the function is identical)
    try:
        res = requests.delete(f"{API_URL}/chat/sessions/{project_id}/{session_id}", headers=get_auth_headers())
        if res.status_code == 204:
            st.success("Chat session deleted.")
            return True
        else:
            try:
                error_detail = res.json().get('detail', 'An unexpected error occurred.')
            except json.JSONDecodeError:
                error_detail = res.text
            st.error(f"Failed to delete chat session (Status {res.status_code}): {error_detail}")
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection to API failed during delete: {e}")
        return False

def send_chat_query(project_id: str, query: str, chat_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    # ... (rest of the function is identical)
    payload = {"query": query}
    if chat_id:
        payload["chat_id"] = chat_id
    try:
        res = requests.post(f"{API_URL}/chat/{project_id}", json=payload, headers=get_auth_headers())
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        error_detail = e.response.json().get('detail', 'An unexpected error occurred') if e.response else 'Connection Error'
        st.error(f"Chat query failed: {error_detail}")
        return None

# --- Main Application UI ---
def project_sidebar():
    """Renders the project selection and creation UI in the sidebar."""
    st.sidebar.title(f"Welcome, {st.session_state.username}!")
    projects = get_projects()
    project_names = [p['name'] for p in projects]
    st.sidebar.header("Projects")
    if 'current_project_name' not in st.session_state or st.session_state.current_project_name not in project_names:
        st.session_state.current_project_name = project_names[0] if project_names else None
        st.session_state.current_chat_id = None
        st.session_state.messages = {}
    selected_project_name = st.sidebar.selectbox(
        "Select a Project",
        options=project_names,
        index=project_names.index(st.session_state.current_project_name) if st.session_state.current_project_name in project_names else 0,
        key="project_select"
    )
    if selected_project_name != st.session_state.current_project_name:
        st.session_state.current_project_name = selected_project_name
        st.session_state.current_chat_id = None
        st.session_state.messages = {}
        st.rerun()
    project_id = next((p['id'] for p in projects if p['name'] == selected_project_name), None)
    st.session_state.current_project_id = project_id
    with st.sidebar.expander("Create New Project", expanded=False):
        with st.form("new_project_form", clear_on_submit=True):
            new_project_name = st.text_input("Project Name")
            if st.form_submit_button("Create"):
                if new_project_name:
                    created_project = create_project(new_project_name)
                    if created_project:
                        st.session_state.current_project_name = created_project['name']
                        st.rerun()
                else:
                    st.warning("Project name cannot be empty.")
    st.sidebar.header("Chat History")
    if project_id:
        chat_sessions = get_chat_sessions(project_id)
        if st.sidebar.button("➕ New Chat", key="new_chat_btn", use_container_width=True):
            st.session_state.current_chat_id = None
            st.session_state.messages = {}
            st.rerun()
        for session in chat_sessions:
            col_title, col_del = st.sidebar.columns([3, 1])
            col_title.button(session['title'], key=f"session_{session['id']}", use_container_width=True, on_click=select_chat_session, args=(project_id, session['id'], session['messages']))
            if col_del.button("🗑️", key=f"del_session_{session['id']}", type="primary", use_container_width=True):
                if delete_chat_session(project_id, session['id']):
                    if st.session_state.current_chat_id == session['id']:
                        st.session_state.current_chat_id = None
                        st.session_state.messages = {}
                    st.rerun()
    else:
        st.sidebar.info("Create a project to start chatting.")
    st.sidebar.header("Account")
    if st.sidebar.button("Logout", use_container_width=True):
        logout_user()
    with st.sidebar.expander("Delete Account", expanded=False):
        st.warning("This action is irreversible and will delete all your projects and data.")
        # Note: Deleting users is not implemented in the provided backend code, but this is where the button would go.
        if st.button("Confirm Account Deletion", type="secondary", disabled=True):
            pass

def select_chat_session(project_id: str, session_id: str, messages_data: List[Dict[str, Any]]):
    # ... (rest of the function is identical)
    st.session_state.current_chat_id = session_id
    st.session_state.messages[session_id] = messages_data
    st.rerun()

def chat_pane(project_id: str):
    # ... (rest of the function is identical)
    st.subheader(f"Chat with '{st.session_state.current_project_name}'")
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
    elif not chat_key:
        st.info("Start a 'New Chat' or select a previous session from the sidebar to begin.")
    prompt = st.chat_input("Ask a question about your documents...")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        if not chat_key:
             st.session_state.messages['new_chat'] = [{"role": "user", "content": prompt}]
        else:
             st.session_state.messages[chat_key].append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")
            response_data = send_chat_query(project_id, prompt, chat_key)
            if response_data:
                answer = response_data.get("answer", "Sorry, I couldn't generate an answer.")
                message_placeholder.markdown(answer)
                new_chat_id = response_data.get('chat_id')
                if not chat_key and new_chat_id: # This was a new chat
                    st.session_state.current_chat_id = new_chat_id
                    st.session_state.messages[new_chat_id] = st.session_state.messages.pop('new_chat', [])
                    st.session_state.messages[new_chat_id].append({"role": "assistant", "content": answer, "sources": response_data.get("sources")})
                    st.rerun()
                elif chat_key:
                    st.session_state.messages[chat_key].append({"role": "assistant", "content": answer, "sources": response_data.get("sources")})
                if response_data.get("sources"):
                    with st.expander("Sources"):
                        for source in response_data["sources"]:
                            st.info(f"Source: {source.get('source', 'N/A')}")
                            st.text(source.get('content', ''))
            else:
                message_placeholder.markdown("An error occurred while trying to get an answer.")

def document_manager_pane(project_id: str):
    # ... (rest of the function is identical, removed for brevity)
    st.subheader(f"Documents for '{st.session_state.current_project_name}'")
    col_upload_file, col_upload_url = st.columns([1, 1])
    with col_upload_file:
        with st.expander("Upload New Documents", expanded=True):
            uploaded_files = st.file_uploader(
                "Upload PDF, DOCX, TXT, MD files",
                type=["pdf", "docx", "txt", "md"],
                accept_multiple_files=True
            )
            if st.button("Upload Files", key="upload_btn"):
                if uploaded_files:
                    with st.spinner("Uploading files..."):
                        success_count = 0
                        for file in uploaded_files:
                            if upload_document_file(project_id, file):
                                success_count += 1
                        if success_count == len(uploaded_files):
                            st.success(f"All {success_count} files uploaded. Check status below.")
                        elif success_count > 0:
                            st.warning(f"{success_count} out of {len(uploaded_files)} files uploaded successfully.")
                        st.rerun()
                else:
                    st.warning("Please select at least one file to upload.")
    with col_upload_url:
        with st.expander("Add Document from URL", expanded=True):
            url_input = st.text_input("Enter a URL", key="url_input")
            if st.button("Add URL", key="add_url_btn"):
                if url_input:
                    with st.spinner("Processing URL..."):
                        if upload_document_from_url(project_id, url_input):
                            st.rerun()
                else:
                    st.warning("Please enter a URL.")
    st.markdown("---")
    st.subheader("Project Documents")
    if st.button("Refresh Document Status"):
        st.rerun()
    docs = get_documents(project_id)
    if not docs:
        st.info("No documents have been uploaded to this project yet. Use the upload sections above.")
    else:
        doc_data = []
        for doc in docs:
            status = doc.get('status', 'UNKNOWN')
            status_display = ""
            if status == "COMPLETED":
                status_display = "✅ Completed"
            elif status == "PROCESSING":
                status_display = "⏳ Processing..."
            elif status == "PENDING":
                status_display = "⚪ Pending"
            else:
                status_display = "❌ Failed"
            created_at_str = "N/A"
            try:
                created_at_str = pd.to_datetime(doc.get('created_at', '')).strftime('%Y-%m-%d %H:%M')
            except Exception:
                pass
            doc_data.append({
                "File Name": doc.get('file_name', 'N/A'),
                "Status": status_display,
                "Uploaded On": created_at_str,
                "Actions": {
                    "id": doc.get('id'),
                    "file_name": doc.get('file_name', 'N/A')
                }
            })
        df = pd.DataFrame(doc_data)
        if not df.empty:
            cols = st.columns([3, 2, 2, 1])
            cols[0].markdown("**File Name**")
            cols[1].markdown("**Status**")
            cols[2].markdown("**Uploaded On**")
            cols[3].markdown("**Action**")
            for index, row in df.iterrows():
                cols[0].write(row["File Name"])
                status_text = row["Status"]
                if "Completed" in status_text:
                    cols[1].success(status_text)
                elif "Processing" in status_text:
                    cols[1].warning(status_text)
                elif "Pending" in status_text:
                    cols[1].info(status_text)
                else:
                    cols[1].error(status_text)
                cols[2].write(row["Uploaded On"])
                if cols[3].button("🗑️", key=f"delete_doc_{row['Actions']['id']}", type="secondary", use_container_width=True):
                    if st.session_state.current_project_id and row["Actions"]["id"]:
                        if delete_document(st.session_state.current_project_id, row["Actions"]["id"]):
                            st.rerun()
                    else:
                        st.error("Cannot delete document. Project or Document ID missing.")
        else:
            st.info("No documents found for this project.")

def main_app():
    """Renders the main application interface after authentication."""
    project_sidebar()
    
    main_area = st.container()
    with main_area:
        st.header(f"Project: {st.session_state.current_project_name}")
        
        chat_tab, docs_tab = st.tabs(["Chat", "Manage Documents"])

        with chat_tab:
            if st.session_state.current_project_id:
                chat_pane(st.session_state.current_project_id)
            else:
                st.warning("Please select or create a project from the sidebar to start chatting.")

        with docs_tab:
            if st.session_state.current_project_id:
                document_manager_pane(st.session_state.current_project_id)
            else:
                st.warning("Please select or create a project from the sidebar to manage documents.")


if __name__ == "__main__":
    initialize_session()
    
    # Check for token in URL from OAuth redirect
    query_params = st.query_params
    if "token" in query_params:
        token = query_params["token"]
        if validate_token_and_login(token):
            st.rerun()
    
    # Display appropriate page
    if st.session_state.logged_in:
        main_app()
    else:
        auth_page()