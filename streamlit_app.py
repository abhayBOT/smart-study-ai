import streamlit as st
import sys
import os
import json
import hashlib
from werkzeug.utils import secure_filename

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your existing functions
from assistant import load_db, search_chunks, generate_answer
from replit_storage import safe_load_json, safe_save_json

# Streamlit configuration
st.set_page_config(
    page_title="Smart Study AI", 
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'role' not in st.session_state:
    st.session_state.role = "Student"

# Load database (cached for performance)
@st.cache_resource
def load_database():
    return load_db()

# Load syllabus
@st.cache_data
def load_syllabus():
    try:
        with open("data/syllabus.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback syllabus
        return {
            "classes": {
                "Class 8": {"subjects": {"Science": ["Chapter 1", "Chapter 2", "Chapter 3"], "Mathematics": ["Chapter 1", "Chapter 2", "Chapter 3"]}},
                "Class 9": {"subjects": {"Science": ["Chapter 1", "Chapter 2", "Chapter 3"], "Mathematics": ["Chapter 1", "Chapter 2", "Chapter 3"]}},
                "Class 10": {"subjects": {"Science": ["Chapter 1", "Chapter 2", "Chapter 3"], "Mathematics": ["Chapter 1", "Chapter 2", "Chapter 3"]}}
            }
        }

# User authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    users = safe_load_json("users.json", {"users": []})
    return users

def save_users(data):
    return safe_save_json("users.json", data)

def load_notes():
    data = safe_load_json("notes.json", {"notes": []})
    return data if "notes" in data else {"notes": data}

def save_notes(data):
    success = safe_save_json("notes.json", data)
    return success

def load_assignments():
    data = safe_load_json("assignments.json", {"assignments": []})
    return data if "assignments" in data else {"assignments": data}

def save_assignments(data):
    success = safe_save_json("assignments.json", data)
    return success

# Login/Signup Page
def login_page():
    st.title("🎓 Smart Study AI")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary"):
            if username and password:
                users = load_users()
                for user in users["users"]:
                    if user.get("login_type", "manual") != "manual":
                        continue
                    if user.get("username") == username and user.get("password") == hash_password(password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = user.get("role", "Student")
                        st.success("Login successful!")
                        st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Please enter both username and password")
    
    with tab2:
        st.subheader("Sign Up")
        new_username = st.text_input("Username", key="signup_username")
        new_password = st.text_input("Password", type="password", key="signup_password")
        role = st.selectbox("Role", ["Student", "Teacher"], key="signup_role")
        
        if st.button("Sign Up", type="secondary"):
            if new_username and new_password:
                users = load_users()
                if "users" not in users:
                    users["users"] = []
                
                for user in users["users"]:
                    if user.get("username") == new_username:
                        st.error("Username already exists")
                        break
                else:
                    users["users"].append({
                        "username": new_username,
                        "password": hash_password(new_password),
                        "role": role,
                        "login_type": "manual"
                    })
                    save_users(users)
                    st.success("Sign up successful! Please login.")
            else:
                st.error("Please enter both username and password")

# Dashboard Page
def dashboard():
    st.title(f"🎓 Smart Study AI - Welcome {st.session_state.username}!")
    st.markdown(f"**Role:** {st.session_state.role}")
    
    # Load data
    syllabus = load_syllabus()
    notes = load_notes()["notes"]
    assignments = load_assignments()["assignments"]
    
    # Sidebar navigation
    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio("Choose Page", ["Dashboard", "AI Assistant", "Notes", "Assignments"])
    
    if page == "Dashboard":
        dashboard_page(syllabus, notes, assignments)
    elif page == "AI Assistant":
        ai_assistant_page(syllabus)
    elif page == "Notes":
        notes_page(notes)
    elif page == "Assignments":
        assignments_page(assignments)
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = "Student"
        st.rerun()

def dashboard_page(syllabus, notes, assignments):
    st.markdown("---")
    st.subheader("📚 Your Learning Dashboard")
    
    # Syllabus Overview
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📖 Available Courses")
        selected_class = st.selectbox("Select Class", list(syllabus.get("classes", {}).keys()))
        
        if selected_class and selected_class in syllabus.get("classes", {}):
            subjects = syllabus["classes"][selected_class].get("subjects", {})
            for subject, chapters in subjects.items():
                with st.expander(f"📚 {subject}"):
                    for chapter in chapters:
                        st.write(f"- {chapter}")
    
    with col2:
        st.markdown("### 📝 Recent Activity")
        st.write(f"📄 Notes Available: {len(notes)}")
        st.write(f"📋 Assignments: {len(assignments)}")
        
        # Quick AI Query
        st.markdown("### 🤖 Quick Question")
        quick_query = st.text_input("Ask anything:", key="quick_query")
        if st.button("Ask Quick", key="quick_ask"):
            if quick_query:
                with st.spinner("Getting answer..."):
                    index, metadata = load_database()
                    results = search_chunks(quick_query, index, metadata)
                    answer = generate_answer(quick_query, results, "", "", "")
                    st.success(answer[:300] + "..." if len(answer) > 300 else answer)

def ai_assistant_page(syllabus):
    st.markdown("---")
    st.subheader("🤖 AI Study Assistant")
    
    # Load database
    index, metadata = load_database()
    
    # Query interface
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_class = st.selectbox("Class", [""] + list(syllabus.get("classes", {}).keys()), key="ai_class")
    
    with col2:
        subjects = []
        if selected_class and selected_class in syllabus.get("classes", {}):
            subjects = list(syllabus["classes"][selected_class].get("subjects", {}).keys())
        subject = st.selectbox("Subject", [""] + subjects, key="ai_subject")
    
    with col3:
        chapter = st.text_input("Chapter (optional)", key="ai_chapter")
    
    query = st.text_area("Enter your question:", height=120, key="ai_query")
    
    if st.button("🔍 Search & Ask AI", type="primary", key="ai_ask"):
        if query:
            with st.spinner("🔍 Searching database and generating answer..."):
                # Search vector database
                results = search_chunks(query, index, metadata)
                
                # Filter results based on selection
                filtered = []
                for r in results:
                    if selected_class and selected_class not in r.get("class", ""):
                        continue
                    if subject and subject not in r.get("subject", ""):
                        continue
                    if chapter and chapter.lower() not in r.get("text", "").lower():
                        continue
                    filtered.append(r)
                
                if filtered:
                    results = filtered
                
                # Generate AI answer
                answer = generate_answer(query, results, selected_class, subject, chapter)
                
                # Display results
                st.markdown("### 🤖 AI Answer")
                st.write(answer)
                
                # Display source materials
                if results:
                    st.markdown("### 📚 Source Materials")
                    for i, result in enumerate(results[:3]):
                        with st.expander(f"📄 Source {i+1}"):
                            st.write(f"**Class:** {result.get('class', 'N/A')}")
                            st.write(f"**Subject:** {result.get('subject', 'N/A')}")
                            st.write(f"**Text:** {result.get('text', '')}")
                
                # Educational Resources (placeholder for YouTube videos)
                st.info("📺 Educational video recommendations will be available in the next update")
        else:
            st.error("Please enter a question")

def notes_page(notes):
    st.markdown("---")
    st.subheader("📝 Study Notes")
    
    if st.session_state.role == "Teacher":
        st.markdown("### 📤 Upload New Note")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        
        if uploaded_file:
            selected_class = st.selectbox("Class", ["Class 8", "Class 9", "Class 10"])
            subject = st.text_input("Subject")
            chapter = st.text_input("Chapter")
            
            if st.button("Upload Note", type="primary"):
                if uploaded_file and selected_class and subject and chapter:
                    filename = secure_filename(uploaded_file.name)
                    save_path = f"teacher_uploads/notes/{filename}"
                    
                    # Create directory if it doesn't exist
                    os.makedirs("teacher_uploads/notes", exist_ok=True)
                    
                    # Save file
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Save to notes.json
                    notes_data = load_notes()
                    notes_data["notes"].append({
                        "filename": filename,
                        "class": selected_class,
                        "subject": subject,
                        "chapter": chapter,
                        "path": save_path
                    })
                    save_notes(notes_data)
                    
                    st.success("Note uploaded successfully!")
                    st.rerun()
    
    # Display existing notes
    st.markdown("### 📚 Available Notes")
    
    if notes:
        for note in notes:
            with st.expander(f"📄 {note.get('filename', 'Unknown')}"):
                st.write(f"**Class:** {note.get('class', 'N/A')}")
                st.write(f"**Subject:** {note.get('subject', 'N/A')}")
                st.write(f"**Chapter:** {note.get('chapter', 'N/A')}")
                
                if st.session_state.role == "Teacher":
                    if st.button(f"Delete {note.get('filename', '')}", key=f"del_note_{note.get('filename', '')}"):
                        # Delete file
                        if os.path.exists(note.get('path', '')):
                            os.remove(note.get('path', ''))
                        
                        # Remove from notes
                        notes_data = load_notes()
                        notes_data["notes"] = [n for n in notes_data["notes"] if n.get('filename') != note.get('filename')]
                        save_notes(notes_data)
                        
                        st.success("Note deleted!")
                        st.rerun()
    else:
        st.info("No notes available yet.")

def assignments_page(assignments):
    st.markdown("---")
    st.subheader("📋 Assignments")
    
    if st.session_state.role == "Teacher":
        st.markdown("### 📤 Upload New Assignment")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="assignment_file")
        
        if uploaded_file:
            selected_class = st.selectbox("Class", ["Class 8", "Class 9", "Class 10"], key="assignment_class")
            subject = st.text_input("Subject", key="assignment_subject")
            chapter = st.text_input("Chapter", key="assignment_chapter")
            
            if st.button("Upload Assignment", type="primary"):
                if uploaded_file and selected_class and subject and chapter:
                    filename = secure_filename(uploaded_file.name)
                    save_path = f"teacher_uploads/assignments/{filename}"
                    
                    # Create directory if it doesn't exist
                    os.makedirs("teacher_uploads/assignments", exist_ok=True)
                    
                    # Save file
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Save to assignments.json
                    assignments_data = load_assignments()
                    assignments_data["assignments"].append({
                        "filename": filename,
                        "class": selected_class,
                        "subject": subject,
                        "chapter": chapter,
                        "path": save_path
                    })
                    save_assignments(assignments_data)
                    
                    st.success("Assignment uploaded successfully!")
                    st.rerun()
    
    # Display existing assignments
    st.markdown("### 📚 Available Assignments")
    
    if assignments:
        for assignment in assignments:
            with st.expander(f"📋 {assignment.get('filename', 'Unknown')}"):
                st.write(f"**Class:** {assignment.get('class', 'N/A')}")
                st.write(f"**Subject:** {assignment.get('subject', 'N/A')}")
                st.write(f"**Chapter:** {assignment.get('chapter', 'N/A')}")
                
                if st.session_state.role == "Teacher":
                    if st.button(f"Delete {assignment.get('filename', '')}", key=f"del_assignment_{assignment.get('filename', '')}"):
                        # Delete file
                        if os.path.exists(assignment.get('path', '')):
                            os.remove(assignment.get('path', ''))
                        
                        # Remove from assignments
                        assignments_data = load_assignments()
                        assignments_data["assignments"] = [a for a in assignments_data["assignments"] if a.get('filename') != assignment.get('filename')]
                        save_assignments(assignments_data)
                        
                        st.success("Assignment deleted!")
                        st.rerun()
    else:
        st.info("No assignments available yet.")

# Main app logic
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()
