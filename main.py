import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import hashlib
from pathlib import Path
import secrets
import string
import zipfile
import io
import shutil

# Page configuration
st.set_page_config(
    page_title="Academic Projects, Labs & Assignments Portal",
    page_icon="🎓",
    layout="wide"
)

# Constants
DATA_DIR = "data"
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
ADMIN_CREDENTIALS_FILE = os.path.join(DATA_DIR, "admin_credentials.json")
FORM_CONTENT_FILE = os.path.join(DATA_DIR, "form_content.json")
SHORT_URLS_FILE = os.path.join(DATA_DIR, "short_urls.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
FILE_SUBMISSION_FILE = os.path.join(DATA_DIR, "file_submission.json")
FILE_SUBMISSIONS_FILE = os.path.join(DATA_DIR, "file_submissions.json")
HIDDEN_FIELDS_FILE = os.path.join(DATA_DIR, "hidden_fields.json")
LAB_MANUAL_FILE = os.path.join(DATA_DIR, "lab_manual.json")
CLASS_ASSIGNMENTS_FILE = os.path.join(DATA_DIR, "class_assignments.json")

# Create data directories if they don't exist
Path(DATA_DIR).mkdir(exist_ok=True)
Path(ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)
Path(os.path.join(DATA_DIR, "submitted_files")).mkdir(parents=True, exist_ok=True)
Path(os.path.join(DATA_DIR, "lab_manual")).mkdir(parents=True, exist_ok=True)
Path(os.path.join(DATA_DIR, "class_assignments")).mkdir(parents=True, exist_ok=True)

def generate_short_code(length=8):
    """Generate a random short code for URLs"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def archive_data(data_type, data, reason=""):
    """Archive deleted data for record keeping"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{data_type}_deleted_{timestamp}.json"
    filepath = os.path.join(ARCHIVE_DIR, filename)
    
    archive_record = {
        "data_type": data_type,
        "deleted_data": data,
        "deleted_at": datetime.now().isoformat(),
        "deleted_by": "admin",
        "reason": reason
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(archive_record, f, indent=4)
        return filepath
    except Exception as e:
        st.error(f"Error archiving data: {e}")
        return None

# Initialize data files
def init_files():
    """Initialize data files if they don't exist"""
    default_config = {
        "max_members": 3,
        "next_group_number": 1,
        "form_published": True,
        "base_url": "http://localhost:8501",
        "enable_file_submission": False,
        "form_mode": "project_allocation",
        "allow_allocation_edit": False,
        "project_file_submission_open": False,
        "lab_manual_open": False,
        "lab_file_upload_required": False,
        "class_assignment_open": False,
        "course_name": "",
        "lab_subject_name": ""
    }
    
    # Admin credentials (default: admin/password123)
    default_admin = {
        "username": "admin",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest()
    }
    
    # Default form content
    default_form_content = {
        "cover_page": {
            "enabled": True,
            "title": "🎓 COAL Project Allocation",
            "content": "",
            "background_color": "#ffffff",
            "text_color": "#000000" 
         },
        "form_header": {
            "title": "COAL Project Selection Form",
            "description": "Please fill in all required fields to submit your project group allocation. All fields marked with * are mandatory.",
            "show_deadline": True,
            "deadline": "2024-12-31",
            "show_contact": True,
            "contact_email": "coal@university.edu"
        },
        "instructions": {
            "enabled": True,
            "title": "ℹ️ Instructions & Guidelines",
            "content": """# Instructions & Guidelines

## Submission Process

### Step-by-Step Guide

1. **Form Your Group**
   - Minimum 1 member required (Group Leader)
   - Maximum members as set by admin
   - First member is Group Leader
   - All members should have unique roll numbers

2. **Select a Project**
   - Only unselected projects are shown
   - Each project can be selected only once
   - Choose carefully - selection is final

3. **Submit Application**
   - Fill all required fields
   - Confirm accuracy of information
   - Submit before deadline

## Important Rules

⚠️ **Project Selection Rules:**
- Each project can be selected by only ONE group
- Once selected, project disappears from available list
- No duplicate roll numbers across groups

⚠️ **Group Formation Rules:**
- Group Leader is mandatory
- Minimum 1 member required
- Roll numbers must be unique within group
- Cannot edit after submission

⚠️ **After Submission:**
- Save your Group Number
- Check allocation table for updates
- Contact admin for any changes""",
             "additional_notes": "For any queries or issues, please contact the Class Representative.",
            "visibility": {
                "project_allocation": True,
                "project_file_submission": True,
                "lab_manual": False,
                "class_assignment": False
            }
        }
    }
    
    # Default file submission settings
    default_file_submission = {
        "enabled": False,
        "allowed_formats": [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".zip", ".rar"],
        "max_size_mb": 10,
        "instructions": "Please upload your project files in the specified formats."
    }
    
    files_to_init = [
        (PROJECTS_FILE, []),
        (GROUPS_FILE, []),
        (CONFIG_FILE, default_config),
        (ADMIN_CREDENTIALS_FILE, default_admin),
        (FORM_CONTENT_FILE, default_form_content),
        (SHORT_URLS_FILE, {}),
        (FILE_SUBMISSION_FILE, default_file_submission),
        (FILE_SUBMISSIONS_FILE, {}),
        (HIDDEN_FIELDS_FILE, []),
        (LAB_MANUAL_FILE, []),
        (CLASS_ASSIGNMENTS_FILE, [])
    ]
    
    for file_path, default_data in files_to_init:
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w') as f:
                    json.dump(default_data, f, indent=4)
            except Exception as e:
                st.error(f"Error creating {file_path}: {e}")

# Load and save functions
def load_data(file_path):
    """Load data from JSON file"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Error loading {file_path}: {e}")
        return None

def save_data(data, file_path):
    """Save data to JSON file"""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving to {file_path}: {e}")
        return False

def hash_password(password):
    """Hash password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication
def authenticate(username, password):
    """Authenticate admin user"""
    admin_data = load_data(ADMIN_CREDENTIALS_FILE)
    if not admin_data:
        return False
    
    password_hash = hash_password(password)
    return admin_data.get("username") == username and admin_data.get("password_hash") == password_hash

def get_base_url():
    """Get base URL from config"""
    config = load_data(CONFIG_FILE) or {}
    return config.get('base_url', 'http://localhost:8501')

# Initialize files
init_files()

def display_cover_page(form_content):
    """Display the cover page"""
    cover = form_content.get("cover_page", {})
    if not cover.get("enabled", True):
        return
    
    # Apply custom styles
    st.markdown(f"""
    <div style="
        background-color: {cover.get('background_color', '#ffffff')};
        color: {cover.get('text_color', '#000000')};
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    ">
        <div style="font-size: 2.5rem; font-weight: bold; margin-bottom: 1rem;">
            {cover.get('title', '🎓 COAL Project Allocation')}
        </div>
        {cover.get('content', '')}
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

def display_form_header(form_content):
    """Display the form header/title section"""
    header = form_content.get("form_header", {})
    
    st.title(header.get("title", "COAL Project Selection Form"))
    
    # Description
    st.markdown(f"**Description:** {header.get('description', 'Please fill in all required fields to submit your project group allocation. All fields marked with * are mandatory.')}")
    
    # Additional info if enabled
    if header.get("show_deadline", True):
        deadline = header.get("deadline", "2024-12-31")
        st.info(f"⏰ **Submission Deadline:** {deadline}")
    
    if header.get("show_contact", True):
        contact_email = header.get("contact_email", "coal@university.edu")
        st.info(f"📧 **Contact for Queries:** {contact_email}")
    
    st.markdown("---")

def class_assignment_submission_form():
    """Form for class assignment submission"""
    st.header("📘 Class Assignment Submission")
    
    # Load course name from config
    config = load_data(CONFIG_FILE) or {}
    course_name = config.get("course_name", "")
    
    if course_name:
        st.info(f"**Course:** {course_name}")
    
    with st.form("class_assignment_form", clear_on_submit=True):
        # Student information
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name*", placeholder="Enter your full name")
        with col2:
            roll_no = st.text_input("Roll Number*", placeholder="Enter your roll number")
        
        # File upload
        st.subheader("📎 Upload Assignment File")
        
        allowed_formats = [".pdf", ".doc", ".docx", ".txt", ".zip", ".rar", ".py", ".java", ".cpp", ".c"]
        file_types = [fmt[1:] if fmt.startswith('.') else fmt for fmt in allowed_formats]
        
        uploaded_file = st.file_uploader(
            "Upload your assignment file*",
            type=file_types,
            help=f"Allowed formats: {', '.join(allowed_formats)}"
        )
        
        # Assignment details
        assignment_no = st.number_input("Assignment Number", min_value=1, value=1)
        remarks = st.text_area("Remarks (optional)", placeholder="Any additional remarks about your submission...")
        
        # Terms agreement
        agree = st.checkbox("I confirm that this is my own work*")
        
        submitted = st.form_submit_button("📤 Submit Assignment", use_container_width=True)
        
        if submitted:
            errors = []
            if not name.strip():
                errors.append("❌ Name is required")
            if not roll_no.strip():
                errors.append("❌ Roll number is required")
            if not uploaded_file:
                errors.append("❌ File upload is required")
            if not agree:
                errors.append("❌ Please confirm this is your own work")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Load existing submissions
                class_submissions = load_data(CLASS_ASSIGNMENTS_FILE) or []
                
                # Check if this roll number already submitted this assignment
                existing = next((s for s in class_submissions if s.get('roll_no') == roll_no.strip() and s.get('assignment_no') == assignment_no), None)
                if existing:
                    st.error("❌ This roll number has already submitted this assignment")
                else:
                    # Create submission record
                    submission_record = {
                        "name": name.strip(),
                        "roll_no": roll_no.strip(),
                        "course_name": course_name,
                        "assignment_no": assignment_no,
                        "remarks": remarks.strip() if remarks.strip() else "",
                        "submission_date": datetime.now().isoformat(),
                        "status": "Submitted"
                    }
                    
                    # Save uploaded file
                    if uploaded_file:
                        # Create directory for class assignments
                        class_dir = os.path.join(DATA_DIR, "class_assignments")
                        Path(class_dir).mkdir(parents=True, exist_ok=True)
                        
                        # Generate unique filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{timestamp}_{roll_no.strip()}_{assignment_no}_{uploaded_file.name}"
                        file_path = os.path.join(class_dir, filename)
                        
                        # Save file
                        with open(file_path, 'wb') as f:
                            f.write(uploaded_file.getbuffer())
                        
                        submission_record["filename"] = filename
                        submission_record["original_filename"] = uploaded_file.name
                        submission_record["file_size"] = uploaded_file.size
                        submission_record["file_type"] = uploaded_file.type
                    
                    # Save to database
                    class_submissions.append(submission_record)
                    save_data(class_submissions, CLASS_ASSIGNMENTS_FILE)
                    
                    st.success("✅ Assignment submitted successfully!")
                    st.balloons()
                    
                    # Show confirmation
                    st.markdown("---")
                    st.markdown(f"""
                    ## ✅ Submission Complete!
                    
                    **Name:** {name}
                    **Roll Number:** {roll_no}
                    **Course:** {course_name}
                    **Assignment No:** {assignment_no}
                    **Submission Time:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
                    
                    Your assignment has been submitted successfully.
                    """)

def lab_manual_submission_form():
    """Form for lab manual submission"""
    st.header("📚 Lab Manual Submission")
    
    # Load subject name from config
    config = load_data(CONFIG_FILE) or {}
    lab_subject_name = config.get("lab_subject_name", "")
    
    if lab_subject_name:
        st.info(f"**Subject:** {lab_subject_name}")
    
    with st.form("lab_manual_form", clear_on_submit=True):
        # Simple fields only
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name*", placeholder="Enter your full name")
        with col2:
            roll_no = st.text_input("Roll Number*", placeholder="Enter your roll number")
        
        # File upload
        st.subheader("📎 Upload File")
        
        # Load lab settings from config
        lab_file_required = config.get("lab_file_upload_required", False)
        
        allowed_formats = [".pdf", ".doc", ".docx", ".txt", ".zip", ".rar"]
        file_types = [fmt[1:] if fmt.startswith('.') else fmt for fmt in allowed_formats]
        
        uploaded_file = st.file_uploader(
            f"Upload your file{'*' if lab_file_required else ''}",
            type=file_types,
            help=f"Allowed formats: {', '.join(allowed_formats)}"
        )
        
        # Terms agreement
        agree = st.checkbox("I confirm that this is my own work*")
        
        submitted = st.form_submit_button("📤 Submit Lab Manual", use_container_width=True)
        
        if submitted:
            errors = []
            if not name.strip():
                errors.append("❌ Name is required")
            if not roll_no.strip():
                errors.append("❌ Roll number is required")
            if lab_file_required and not uploaded_file:
                errors.append("❌ File upload is required")
            if not agree:
                errors.append("❌ Please confirm this is your own work")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Load existing submissions
                lab_manual = load_data(LAB_MANUAL_FILE) or []
                
                # Check if roll number already submitted
                existing = next((s for s in lab_manual if s.get('roll_no') == roll_no.strip()), None)
                if existing:
                    st.error("❌ This roll number has already submitted a lab manual")
                else:
                    # Create submission record
                    submission_record = {
                        "name": name.strip(),
                        "roll_no": roll_no.strip(),
                        "subject_name": lab_subject_name,
                        "submission_date": datetime.now().isoformat(),
                        "status": "Submitted"
                    }
                    
                    # Save uploaded file
                    if uploaded_file:
                        # Create directory for lab manual
                        lab_dir = os.path.join(DATA_DIR, "lab_manual")
                        Path(lab_dir).mkdir(parents=True, exist_ok=True)
                        
                        # Generate unique filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{timestamp}_{roll_no.strip()}_{uploaded_file.name}"
                        file_path = os.path.join(lab_dir, filename)
                        
                        # Save file
                        with open(file_path, 'wb') as f:
                            f.write(uploaded_file.getbuffer())
                        
                        submission_record["filename"] = filename
                        submission_record["original_filename"] = uploaded_file.name
                        submission_record["file_size"] = uploaded_file.size
                    
                    # Save to database
                    lab_manual.append(submission_record)
                    save_data(lab_manual, LAB_MANUAL_FILE)
                    
                    st.success("✅ Lab manual submitted successfully!")
                    st.balloons()
                    
                    # Show confirmation
                    st.markdown("---")
                    st.markdown(f"""
                    ## ✅ Submission Complete!
                    
                    **Name:** {name}
                    **Roll Number:** {roll_no}
                    **Subject:** {lab_subject_name}
                    **Submission Time:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
                    
                    Your lab manual has been submitted successfully.
                    """)

def display_instructions(form_content):
    """Display instructions tab based on current mode"""
    config = load_data(CONFIG_FILE) or {}
    current_mode = config.get("form_mode", "project_allocation")
    
    instructions = form_content.get("instructions", {})
    
    # Check if instructions are enabled for current mode
    visibility = instructions.get("visibility", {})
    if not visibility.get(current_mode, True):
        return
    
    if not instructions.get("enabled", True):
        return
    
    st.header(instructions.get("title", "ℹ️ Instructions & Guidelines"))
    
    # Display main instructions content
    st.markdown(instructions.get("content", ""))
    
    # Display additional notes if any
    if instructions.get("additional_notes"):
        st.markdown("---")
        st.markdown("### Additional Information")
        st.markdown(instructions.get("additional_notes"))
    
    # Display contact information
    st.markdown("---")
    st.subheader("Need Help?")
    st.info("For any queries or issues, please contact the Class Representative.")

def student_form_standalone():
    """Student form without Admin Dashboard option in sidebar"""
    # Load config
    config = load_data(CONFIG_FILE) or {}
    
    # Check if form is published
    if not config.get("form_published", True):
        st.warning("⏸️ The form is currently under maintenance. Please check back later.")
        return
    
    # Determine which mode is active
    form_mode = config.get("form_mode", "project_allocation")
    
    if form_mode == "project_allocation":
        # MODE A: Project Allocation Mode
        form_content = load_data(FORM_CONTENT_FILE) or {}
        
        # Check if allocation editing is allowed
        allow_edit = config.get("allow_allocation_edit", False)
        
        if allow_edit:
            # Show tabs with edit option
            tab1, tab2, tab3 = st.tabs(["📋 Project Selection Form", "📊 View Allocations", "ℹ️ Instructions"])
            with tab1:
                display_submission_form(form_content, config)
            with tab2:
                display_allocations_table_for_students()
            with tab3:
                display_instructions(form_content)
        else:
            # View only mode
            tab1, tab2 = st.tabs(["📊 View Allocations", "ℹ️ Instructions"])
            with tab1:
                display_allocations_table_for_students()
            with tab2:
                display_instructions(form_content)
    
    elif form_mode == "project_file_submission":
        # MODE B: Project File Submission Mode
        form_content = load_data(FORM_CONTENT_FILE) or {}
        
        # Check if submission is open
        submission_open = config.get("project_file_submission_open", False)
        
        if submission_open:
            # Show file submission form
            tab1, tab2, tab3 = st.tabs(["📁 Submit Files", "📊 View Allocations", "ℹ️ Instructions"])
            with tab1:
                display_project_file_submission_form(form_content, config)
            with tab2:
                display_allocations_table_for_students()
            with tab3:
                display_instructions(form_content)
        else:
            # Show message that submission is closed
            st.info("📁 Project file submission is currently closed.")
            tab1, tab2 = st.tabs(["📊 View Allocations", "ℹ️ Instructions"])
            with tab1:
                display_allocations_table_for_students()
            with tab2:
                display_instructions(form_content)
    
    elif form_mode == "lab_manual":
        # MODE C: Lab Manual Submission Mode
        lab_manual_submission_form()
    
    elif form_mode == "class_assignment":
        # MODE D: Class Assignment Submission Mode
        class_assignment_submission_form()

def display_project_file_submission_form(form_content, config):
    """Display project file submission form with submission status"""
    st.header("📁 Project File Submission")
    
    with st.form("project_file_submission_form", clear_on_submit=False):
        # Group number input - use a clean numeric input without session state conflicts
        group_number = st.number_input(
            "Enter Your Group Number*",
            min_value=1,
            step=1,
            value=1,
            help="Enter the group number you received after project allocation",
            key="project_file_group_number"
        )
        
        # Submit button for group number verification
        group_number_submitted = st.form_submit_button("🔍 Verify Group Number", use_container_width=True)
        
        if group_number_submitted:
            # Verify group exists
            groups = load_data(GROUPS_FILE) or []
            group_exists = any(g['group_number'] == group_number and not g.get('deleted', False) for g in groups)
            
            if not group_exists:
                st.error("❌ Group number not found. Please check your group number.")
                st.info("You must have submitted a project allocation first.")
                st.session_state.group_verified = False
            else:
                st.session_state.group_verified = True
                st.session_state.verified_group_number = group_number
                
                # Get group details
                group = next((g for g in groups if g['group_number'] == group_number), None)
                if group:
                    project_name = group.get('project_name', 'N/A')
                    leader_name = ""
                    for member in group.get('members', []):
                        if member.get('is_leader'):
                            leader_name = member.get('name', '')
                            break
                    
                    # Show group details
                    st.success(f"✅ Group {group_number} verified!")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Group Leader:** {leader_name}")
                    with col2:
                        st.info(f"**Project:** {project_name}")
                    
                    # Check submission status (only status, not file names)
                    file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
                    group_files = file_submissions.get(str(group_number), [])
                    
                    # Display submission status only (no file names)
                    st.markdown("---")
                    st.subheader("📋 Submission Status")
                    
                    if group_files:
                        status_icon = "✅"
                        status_text = "Submitted"
                        st.success(f"{status_icon} **Status:** {status_text}")
                        st.info(f"✅ You have submitted {len(group_files)} file(s) for your project.")
                    else:
                        status_icon = "❌"
                        status_text = "Not Submitted"
                        st.error(f"{status_icon} **Status:** {status_text}")
                        st.info("Please submit your project files below.")
                    
                    # File upload section (only shown after verification)
                    st.markdown("---")
                    st.subheader("📎 Upload Files")
                    
                    # Load file submission settings
                    file_settings = load_data(FILE_SUBMISSION_FILE) or {}
                    allowed_formats = file_settings.get("allowed_formats", [".pdf", ".doc", ".docx"])
                    max_size = file_settings.get("max_size_mb", 10) * 1024 * 1024
                    
                    # Convert formats for file_uploader
                    file_types = []
                    for fmt in allowed_formats:
                        if fmt.startswith('.'):
                            file_types.append(fmt[1:])  # Remove dot
                        else:
                            file_types.append(fmt)
                    
                    uploaded_files = st.file_uploader(
                        "Upload your project files*",
                        type=file_types,
                        accept_multiple_files=True,
                        help=f"Allowed formats: {', '.join(allowed_formats)} | Max size: {file_settings.get('max_size_mb', 10)}MB per file",
                        key="project_file_uploader"
                    )
                    
                    # Instructions
                    st.info(file_settings.get("instructions", "Please upload your project files in the specified formats."))
                    
                    # Submit files button
                    files_submitted = st.form_submit_button("📤 Submit Files", use_container_width=True, key="submit_project_files")
                    
                    if files_submitted and uploaded_files:
                        if str(group_number) not in file_submissions:
                            file_submissions[str(group_number)] = []
                        
                        for uploaded_file in uploaded_files:
                            file_info = {
                                "filename": uploaded_file.name,
                                "size": uploaded_file.size,
                                "uploaded_at": datetime.now().isoformat(),
                                "project_name": project_name,
                                "group_leader": leader_name
                            }
                            file_submissions[str(group_number)].append(file_info)
                            
                            # Save file to disk
                            file_dir = os.path.join(DATA_DIR, "submitted_files", str(group_number))
                            Path(file_dir).mkdir(parents=True, exist_ok=True)
                            file_path = os.path.join(file_dir, uploaded_file.name)
                            try:
                                with open(file_path, 'wb') as f:
                                    f.write(uploaded_file.getbuffer())
                            except Exception as e:
                                st.error(f"Error saving file {uploaded_file.name}: {e}")
                                continue
                        
                        save_data(file_submissions, FILE_SUBMISSIONS_FILE)
                        st.success("✅ Files submitted successfully!")
                        st.balloons()
                        st.rerun()
                    elif files_submitted and not uploaded_files:
                        st.error("❌ Please select at least one file to upload")
        
        # Handle case where group was already verified
        elif st.session_state.get('group_verified', False) and st.session_state.get('verified_group_number'):
            group_number = st.session_state.verified_group_number
            groups = load_data(GROUPS_FILE) or []
            group = next((g for g in groups if g['group_number'] == group_number), None)
            
            if group:
                project_name = group.get('project_name', 'N/A')
                leader_name = ""
                for member in group.get('members', []):
                    if member.get('is_leader'):
                        leader_name = member.get('name', '')
                        break
                
                # Show group details
                st.success(f"✅ Group {group_number} verified!")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Group Leader:** {leader_name}")
                with col2:
                    st.info(f"**Project:** {project_name}")
                
                # Check submission status
                file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
                group_files = file_submissions.get(str(group_number), [])
                
                # Display submission status
                st.markdown("---")
                st.subheader("📋 Submission Status")
                
                if group_files:
                    status_icon = "✅"
                    status_text = "Submitted"
                    st.success(f"{status_icon} **Status:** {status_text}")
                    st.info(f"✅ You have submitted {len(group_files)} file(s) for your project.")
                else:
                    status_icon = "❌"
                    status_text = "Not Submitted"
                    st.error(f"{status_icon} **Status:** {status_text}")
                    st.info("Please submit your project files below.")
                
                # File upload section
                st.markdown("---")
                st.subheader("📎 Upload Files")
                
                # Load file submission settings
                file_settings = load_data(FILE_SUBMISSION_FILE) or {}
                allowed_formats = file_settings.get("allowed_formats", [".pdf", ".doc", ".docx"])
                max_size = file_settings.get("max_size_mb", 10) * 1024 * 1024
                
                # Convert formats for file_uploader
                file_types = []
                for fmt in allowed_formats:
                    if fmt.startswith('.'):
                        file_types.append(fmt[1:])
                    else:
                        file_types.append(fmt)
                
                uploaded_files = st.file_uploader(
                    "Upload your project files*",
                    type=file_types,
                    accept_multiple_files=True,
                    help=f"Allowed formats: {', '.join(allowed_formats)} | Max size: {file_settings.get('max_size_mb', 10)}MB per file",
                    key="project_file_uploader_verified"
                )
                
                # Instructions
                st.info(file_settings.get("instructions", "Please upload your project files in the specified formats."))
                
                # Submit files button
                files_submitted = st.form_submit_button("📤 Submit Files", use_container_width=True, key="submit_project_files_verified")
                
                if files_submitted and uploaded_files:
                    if str(group_number) not in file_submissions:
                        file_submissions[str(group_number)] = []
                    
                    for uploaded_file in uploaded_files:
                        file_info = {
                            "filename": uploaded_file.name,
                            "size": uploaded_file.size,
                            "uploaded_at": datetime.now().isoformat(),
                            "project_name": project_name,
                            "group_leader": leader_name
                        }
                        file_submissions[str(group_number)].append(file_info)
                        
                        # Save file to disk
                        file_dir = os.path.join(DATA_DIR, "submitted_files", str(group_number))
                        Path(file_dir).mkdir(parents=True, exist_ok=True)
                        file_path = os.path.join(file_dir, uploaded_file.name)
                        try:
                            with open(file_path, 'wb') as f:
                                f.write(uploaded_file.getbuffer())
                        except Exception as e:
                            st.error(f"Error saving file {uploaded_file.name}: {e}")
                            continue
                    
                    save_data(file_submissions, FILE_SUBMISSIONS_FILE)
                    st.success("✅ Files submitted successfully!")
                    st.balloons()
                    st.rerun()
                elif files_submitted and not uploaded_files:
                    st.error("❌ Please select at least one file to upload")

def display_allocations_table_for_students():
    """Display allocations table for students with project count"""
    st.header("📊 Current Project Allocations")
    
    # Load data
    groups = load_data(GROUPS_FILE) or []
    projects = load_data(PROJECTS_FILE) or []
    
    # Filter out deleted groups
    active_groups = [g for g in groups if not g.get('deleted', False)]
    
    # Filter active projects (not deleted)
    active_projects = [p for p in projects if not p.get('deleted', False)]
    
    if not active_groups:
        st.info("No project allocations yet. Be the first to submit!")
    else:
        # Create SIMPLIFIED DataFrame - Only Group #, Project Name, and Group Leader
        summary_data = []
        for group in sorted(active_groups, key=lambda x: x.get('group_number', 0)):
            # Find group leader
            group_leader = ""
            for member in group.get('members', []):
                if member.get('is_leader'):
                    group_leader = member.get('name', '')
                    break
            
            summary_data.append({
                "Group #": group.get('group_number', ''),
                "Project Name": group.get('project_name', ''),
                "Group Leader": group_leader
            })
        
        df_summary = pd.DataFrame(summary_data)
        
        # Display table
        st.dataframe(
            df_summary,
            use_container_width=True,
            column_config={
                "Group #": st.column_config.NumberColumn(width="small"),
                "Project Name": st.column_config.TextColumn(width="large"),
                "Group Leader": st.column_config.TextColumn(width="medium")
            }
        )
    
    # Show project statistics
    st.markdown("---")
    st.subheader("📈 Project Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Groups", len(active_groups))
    
    with col2:
        selected_groups = len([g for g in active_groups if g.get('status') == 'Selected'])
        st.metric("Selected Groups", selected_groups)
    
    with col3:
        st.metric("Total Projects", len(active_projects))
    
    with col4:
        # Calculate available projects (not selected by any group)
        selected_projects = set()
        for group in active_groups:
            if group.get('project_name'):
                selected_projects.add(group['project_name'])
        
        # Get available projects (Not Selected status and not already selected)
        available_projects = []
        for project in active_projects:
            if project.get('status') == 'Not Selected' and project['name'] not in selected_projects:
                available_projects.append(project)
        
        st.metric("Available Projects", len(available_projects))
    
    # Show available projects list
    if available_projects:
        st.subheader("✅ Available Projects for Selection")
        available_list = [p['name'] for p in available_projects]
        for project in available_list:
            st.markdown(f"• {project}")
    else:
        st.info("⚠️ No projects available for selection at the moment.")

def display_submission_form(form_content, config):
    """Display the submission form"""
    # Display cover page if enabled
    display_cover_page(form_content)
    
    # Display form header
    display_form_header(form_content)
    
    # Load configuration
    max_members = config.get("max_members", 3)
    
    # Load projects
    projects = load_data(PROJECTS_FILE) or []
    
    if not projects:
        st.warning("No projects available yet. Please contact administrator.")
        return
    
    # Show available projects count BEFORE form
    available_projects = [p for p in projects if p.get('status') == 'Not Selected' and not p.get('deleted', False)]
    st.info(f"📊 **Currently Available Projects:** {len(available_projects)}")
    
    # Create form
    with st.form("project_allocation_form", clear_on_submit=True):
        st.subheader("👥 Group Members Information")
        st.markdown("*Note: Member 1 will be the Group Leader*")
        
        # Dynamic member fields based on max_members
        members_data = []
        
        # Member 1 (Group Leader) - Always required
        st.markdown("### 👑 Group Leader (Member 1)")
        col1, col2 = st.columns(2)
        with col1:
            member1_name = st.text_input("Full Name*", placeholder="Enter full name", key="member1_name")
        with col2:
            member1_roll = st.text_input("Roll Number*", placeholder="Enter roll number", key="member1_roll")
        
        members_data.append({
            "name": member1_name,
            "roll_no": member1_roll,
            "is_leader": True
        })
        
        # Additional members (up to max_members-1 more)
        if max_members > 1:
            st.markdown("### 👥 Additional Members (Optional)")
            st.caption(f"You can add up to {max_members - 1} additional members (maximum {max_members} total)")
            
            for i in range(2, max_members + 1):
                st.markdown(f"**Member {i}**")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input(f"Full Name", placeholder="Enter full name", key=f"member_{i}_name")
                with col2:
                    roll = st.text_input(f"Roll Number", placeholder="Enter roll number", key=f"member_{i}_roll")
                
                members_data.append({
                    "name": name,
                    "roll_no": roll,
                    "is_leader": False
                })
        
        # Project selection
        st.markdown("---")
        st.subheader("📋 Project Selection")
        st.markdown("*Select ONE project from the available options below*")
        
        # Get only unselected projects that are not deleted
        available_projects = [p for p in projects if p.get('status') == 'Not Selected' and not p.get('deleted', False)]
        project_options = [f"{p['name']}" for p in available_projects]
        
        if not project_options:
            st.error("❌ All projects have been selected. No available projects at the moment.")
            st.info("Please contact the administrator for more options.")
            project_choice = None
        else:
            # Check for duplicate roll numbers in submissions
            groups = load_data(GROUPS_FILE) or []
            
            # Filter out projects already selected
            selected_projects = set()
            for group in groups:
                if group.get('project_name'):
                    selected_projects.add(group['project_name'])
            
            # Only show projects not already selected and not deleted
            final_available_projects = [
                p for p in available_projects 
                if p['name'] not in selected_projects 
                and not p.get('deleted', False)
            ]
            
            if not final_available_projects:
                st.error("❌ All available projects have already been selected by other groups.")
                project_choice = None
            else:
                project_options_final = [f"{p['name']}" for p in final_available_projects]
                project_choice = st.selectbox(
                    "Select Your Project*",
                    options=[""] + project_options_final,
                    help="Choose only one project from the available options",
                    format_func=lambda x: "Click to choose..." if x == "" else x
                )
                
                # Show project count
                st.caption(f"📊 {len(project_options_final)} project(s) available for selection")
                
                # Show available projects list
                if project_options_final:
                    with st.expander("📋 View Available Projects"):
                        for project in project_options_final:
                            st.write(f"• {project}")
        
        # Terms and conditions
        st.markdown("---")
        st.subheader("✅ Confirmation")
        
        col1, col2 = st.columns(2)
        with col1:
            agree_terms = st.checkbox("I confirm that all information provided is accurate*", value=False)
        with col2:
            agree_final = st.checkbox("I understand this selection is final*", value=False)
        
        # Form submission
        submitted = st.form_submit_button("🚀 Submit Application", use_container_width=True)
        
        if submitted:
            # Validation
            errors = []
            
            # Check Member 1 (required)
            if not member1_name.strip() or not member1_roll.strip():
                errors.append("❌ Member 1 (Group Leader) name and roll number are required")
            
            if not project_choice:
                errors.append("❌ Please select a project")
            
            # Check terms agreement
            if not agree_terms:
                errors.append("❌ Please confirm that information is accurate")
            if not agree_final:
                errors.append("❌ Please confirm that selection is final")
            
            # Check for duplicate roll numbers within this submission
            roll_numbers = [m['roll_no'] for m in members_data if m['roll_no'].strip()]
            unique_rolls = [r for r in roll_numbers if r.strip()]
            if len(unique_rolls) != len(set(unique_rolls)):
                errors.append("❌ Duplicate roll numbers detected within your group")
            
            # Check if roll numbers already used in other submissions
            groups = load_data(GROUPS_FILE) or []
            existing_rolls = set()
            for group in groups:
                if not group.get('deleted', False):
                    for member in group['members']:
                        if member['roll_no'].strip():
                            existing_rolls.add(member['roll_no'].strip())
            
            duplicate_existing = False
            for roll in unique_rolls:
                if roll.strip() in existing_rolls:
                    duplicate_existing = True
                    errors.append(f"❌ Roll number {roll} is already registered in another group")
                    break
            
            # Check if project is still available
            if project_choice:
                projects_data = load_data(PROJECTS_FILE) or []
                project_still_available = any(
                    p['name'] == project_choice and 
                    p.get('status') == 'Not Selected' and
                    not p.get('deleted', False)
                    for p in projects_data
                )
                
                # Check if project already selected by another group
                groups_data = load_data(GROUPS_FILE) or []
                project_already_selected = any(
                    g['project_name'] == project_choice and not g.get('deleted', False)
                    for g in groups_data
                )
                
                if not project_still_available or project_already_selected:
                    errors.append("❌ This project is no longer available. Please select another project.")
            
            # Check minimum members (at least member 1)
            active_members = len([m for m in members_data if m['name'].strip() and m['roll_no'].strip()])
            if active_members < 1:
                errors.append("❌ At least one member (Group Leader) is required")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Load existing groups and config
                groups = load_data(GROUPS_FILE) or []
                config = load_data(CONFIG_FILE)
                
                # Create new group
                new_group = {
                    "group_number": config.get("next_group_number", 1),
                    "project_name": project_choice,
                    "status": "Not Selected",
                    "members": members_data,
                    "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "submission_timestamp": datetime.now().isoformat(),
                    "deleted": False
                }
                
                # Add to groups
                groups.append(new_group)
                save_data(groups, GROUPS_FILE)
                
                # Update project selection count
                projects_data = load_data(PROJECTS_FILE) or []
                for project in projects_data:
                    if project['name'] == project_choice:
                        project['selected_by'] = project.get('selected_by', 0) + 1
                        # Update project status if selected by a group
                        if project['selected_by'] >= 1:
                            project['status'] = 'Selected'
                        break
                save_data(projects_data, PROJECTS_FILE)
                
                # Update config for next group number
                config['next_group_number'] = config.get('next_group_number', 1) + 1
                save_data(config, CONFIG_FILE)
                
                # Show success message
                st.success("✅ Application submitted successfully!")
                st.balloons()
                
                # Thank you page
                st.markdown("---")
                st.header("🎉 Thank You!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    ### Submission Details
                    
                    **Group Number:** `{new_group['group_number']}`
                    
                    **Selected Project:** {project_choice}
                    
                    **Group Leader:** {member1_name}
                    
                    **Submission Time:** {datetime.now().strftime("%Y-%m-%d %I:%M %p")}
                    """)
                
                with col2:
                    st.markdown("""
                    ### Next Steps
                    
                    1. Save your **Group Number** for future reference
                    2. The administrator will review your application
                    3. Project status will be updated soon
                    4. Contact administrator if you need to make changes
                    """)
                
                st.markdown("---")
                st.info("📱 You may close this window now. Your submission has been recorded.")

def manage_file_submissions():
    """Admin panel to manage and download submitted files"""
    st.header("📁 Project File Submissions")
    
    # Load file submissions data
    file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
    
    if not file_submissions:
        st.info("No project files have been submitted yet.")
        return
    
    # Display all groups with submitted files
    st.subheader("📋 Submission Status Report")
    
    # Get all groups
    groups = load_data(GROUPS_FILE) or []
    active_groups = [g for g in groups if not g.get('deleted', False)]
    
    # Create submission status report
    status_data = []
    for group in active_groups:
        group_num = group['group_number']
        group_files = file_submissions.get(str(group_num), [])
        
        # Get group leader
        leader_name = ""
        for member in group['members']:
            if member.get('is_leader'):
                leader_name = member['name']
                break
        
        status_data.append({
            "Group #": group_num,
            "Project": group['project_name'],
            "Group Leader": leader_name,
            "Files Submitted": len(group_files),
            "Status": "✅ Submitted" if len(group_files) > 0 else "❌ Not Submitted",
            "Last Submission": max([f['uploaded_at'] for f in group_files], default="Not submitted")
        })
    
    # Sort by group number
    status_data.sort(key=lambda x: x['Group #'])
    
    # Create DataFrame
    df_status = pd.DataFrame(status_data)
    
    # Display status table
    st.dataframe(
        df_status,
        use_container_width=True,
        column_config={
            "Group #": st.column_config.NumberColumn(width="small"),
            "Project": st.column_config.TextColumn(width="medium"),
            "Group Leader": st.column_config.TextColumn(width="medium"),
            "Files Submitted": st.column_config.NumberColumn(width="small"),
            "Status": st.column_config.TextColumn(width="medium"),
            "Last Submission": st.column_config.DatetimeColumn(width="medium")
        }
    )
    
    # Show statistics
    st.subheader("📊 Submission Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_groups = len(active_groups)
        st.metric("Total Groups", total_groups)
    
    with col2:
        submitted_groups = len([g for g in status_data if g['Files Submitted'] > 0])
        st.metric("Submitted Groups", submitted_groups)
    
    with col3:
        not_submitted = total_groups - submitted_groups
        st.metric("Not Submitted", not_submitted)
    
    with col4:
        submission_rate = (submitted_groups / total_groups * 100) if total_groups > 0 else 0
        st.metric("Submission Rate", f"{submission_rate:.1f}%")
    
    # Show groups without submission
    not_submitted_groups = [g for g in status_data if g['Files Submitted'] == 0]
    if not_submitted_groups:
        st.subheader("📝 Groups Without Submission")
        for group in not_submitted_groups:
            st.write(f"• **Group {group['Group #']}**: {group['Project']} (Leader: {group['Group Leader']})")
    
    # Download functionality
    st.markdown("---")
    st.subheader("📥 Download Submitted Files")
    
    # Display groups with files
    st.write("**Groups with submitted files:**")
    groups_with_files = [g for g in status_data if g['Files Submitted'] > 0]
    
    if not groups_with_files:
        st.info("No files available for download.")
    else:
        # Create tabs for download options
        tab1, tab2 = st.tabs(["📦 Download All Files", "📁 Download by Group"])
        
        with tab1:
            # Download all files button
            if st.button("⬇️ Download All Project Files as ZIP", use_container_width=True):
                # Check if there are any files
                has_files = False
                for group_num in file_submissions.keys():
                    group_dir = os.path.join(DATA_DIR, "submitted_files", group_num)
                    if os.path.exists(group_dir) and os.listdir(group_dir):
                        has_files = True
                        break
                
                if not has_files:
                    st.warning("No files available for download.")
                else:
                    # Create zip of all files
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for group_num in file_submissions.keys():
                            group_dir = os.path.join(DATA_DIR, "submitted_files", group_num)
                            if os.path.exists(group_dir):
                                for root, dirs, filenames in os.walk(group_dir):
                                    for filename in filenames:
                                        file_path = os.path.join(root, filename)
                                        arcname = os.path.join(f"Group_{group_num}", filename)
                                        zip_file.write(file_path, arcname)
                    
                    zip_buffer.seek(0)
                    
                    # Provide download
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="📥 Download All Project Files",
                        data=zip_buffer,
                        file_name=f"all_project_files_{timestamp}.zip",
                        mime="application/zip"
                    )
        
        with tab2:
            # Download by group
            group_options = [f"Group {g['Group #']}" for g in groups_with_files]
            selected_group = st.selectbox("Select Group", options=[""] + group_options)
            
            if selected_group:
                group_num = selected_group.replace("Group ", "")
                group_dir = os.path.join(DATA_DIR, "submitted_files", group_num)
                
                if os.path.exists(group_dir) and os.listdir(group_dir):
                    # Create zip file for the group
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for root, dirs, filenames in os.walk(group_dir):
                            for filename in filenames:
                                file_path = os.path.join(root, filename)
                                arcname = filename
                                zip_file.write(file_path, arcname)
                    
                    zip_buffer.seek(0)
                    
                    # Provide download
                    st.download_button(
                        label=f"📥 Download {selected_group} Files",
                        data=zip_buffer,
                        file_name=f"{selected_group}_files.zip",
                        mime="application/zip"
                    )
                else:
                    st.info("No files found for this group.")
    
    # Delete functionality
    st.markdown("---")
    st.subheader("🗑️ Delete Files")
    
    col1, col2 = st.columns(2)
    with col1:
        group_to_delete = st.selectbox(
            "Select group to delete files",
            options=[""] + [str(g['Group #']) for g in groups_with_files]
        )
    
    with col2:
        if group_to_delete and st.button("🗑️ Delete Group Files", type="secondary"):
            # Archive file submission data
            if group_to_delete in file_submissions:
                archive_data("file_submissions", {group_to_delete: file_submissions[group_to_delete]}, "Admin deleted group files")
                
                # Remove from file submissions data
                del file_submissions[group_to_delete]
                save_data(file_submissions, FILE_SUBMISSIONS_FILE)
                
                # Delete files from disk
                group_dir = os.path.join(DATA_DIR, "submitted_files", group_to_delete)
                if os.path.exists(group_dir):
                    try:
                        shutil.rmtree(group_dir)
                    except Exception as e:
                        st.error(f"Error deleting files: {e}")
                
                st.success(f"✅ Files for Group {group_to_delete} deleted successfully!")
                st.rerun()

def manage_lab_manual():
    """Admin panel to manage lab manual submissions"""
    st.header("📚 Lab Manual Submissions")
    
    # Load config for subject name
    config = load_data(CONFIG_FILE) or {}
    
    # Subject name configuration
    st.subheader("Subject Configuration")
    lab_subject_name = st.text_input("Lab Subject Name", value=config.get('lab_subject_name', ''))
    
    if st.button("💾 Save Subject Name"):
        config['lab_subject_name'] = lab_subject_name
        if save_data(config, CONFIG_FILE):
            st.success("Subject name saved!")
    
    if lab_subject_name:
        st.info(f"**Current Subject:** {lab_subject_name}")
    
    # Load lab manual submissions
    lab_manual = load_data(LAB_MANUAL_FILE) or []
    
    if not lab_manual:
        st.info("No lab manuals submitted yet.")
        return
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 View Submissions", "📥 Download Files", "🗑️ Delete Submissions"])
    
    with tab1:
        # Display all submissions
        if lab_manual:
            # Convert to DataFrame for better display
            df_data = []
            for submission in lab_manual:
                df_data.append({
                    "Name": submission.get('name', ''),
                    "Roll No": submission.get('roll_no', ''),
                    "Subject": submission.get('subject_name', ''),
                    "Status": submission.get('status', 'Submitted'),
                    "File": submission.get('original_filename', 'No file'),
                    "File Size": f"{submission.get('file_size', 0) / 1024:.1f} KB" if submission.get('file_size') else "N/A",
                    "Submitted": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M')
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Statistics
            st.subheader("📊 Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Submissions", len(lab_manual))
            with col2:
                with_files = len([s for s in lab_manual if s.get('filename')])
                st.metric("With Files", with_files)
            with col3:
                without_files = len([s for s in lab_manual if not s.get('filename')])
                st.metric("Without Files", without_files)
    
    with tab2:
        # Download functionality
        st.subheader("Download All Lab Manuals")
        
        # Check if there are files to download
        submissions_with_files = [s for s in lab_manual if s.get('filename')]
        
        if not submissions_with_files:
            st.warning("No files to download.")
        else:
            if st.button("📦 Download All Lab Manuals as ZIP", use_container_width=True):
                # Create zip of all files
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    lab_dir = os.path.join(DATA_DIR, "lab_manual")
                    if os.path.exists(lab_dir):
                        for submission in submissions_with_files:
                            filename = submission.get('filename')
                            if filename:
                                file_path = os.path.join(lab_dir, filename)
                                if os.path.exists(file_path):
                                    # Create a descriptive name for the file
                                    new_filename = f"{submission['roll_no']}_{submission['name']}_{submission.get('original_filename', filename)}"
                                    zip_file.write(file_path, new_filename)
                
                zip_buffer.seek(0)
                
                # Provide download
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ Download All Lab Manuals",
                    data=zip_buffer,
                    file_name=f"lab_manuals_{timestamp}.zip",
                    mime="application/zip"
                )
    
    with tab3:
        # Delete functionality
        st.subheader("🗑️ Delete Submissions")
        
        roll_numbers = [s['roll_no'] for s in lab_manual]
        selected_roll = st.selectbox(
            "Select submission to delete",
            options=[""] + roll_numbers
        )
        
        if selected_roll:
            submission = next((s for s in lab_manual if s['roll_no'] == selected_roll), None)
            if submission:
                st.warning(f"Delete submission for {submission['name']} ({selected_roll})?")
                
                if st.button("🗑️ Delete Submission", type="secondary"):
                    # Archive before deletion
                    archive_data("lab_manual", submission, "Admin deleted lab manual submission")
                    
                    # Remove from data
                    lab_manual = [s for s in lab_manual if s['roll_no'] != selected_roll]
                    save_data(lab_manual, LAB_MANUAL_FILE)
                    
                    # Delete file if exists
                    if submission.get('filename'):
                        file_path = os.path.join(DATA_DIR, "lab_manual", submission['filename'])
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                st.error(f"Error deleting file: {e}")
                    
                    st.success("✅ Submission deleted successfully!")
                    st.rerun()

def manage_class_assignments():
    """Admin panel to manage class assignment submissions"""
    st.header("📘 Class Assignment Management")
    
    # Load config for course name
    config = load_data(CONFIG_FILE) or {}
    
    # Course name configuration
    st.subheader("Course Configuration")
    course_name = st.text_input("Course/Subject Name", value=config.get('course_name', ''))
    
    if st.button("💾 Save Course Name"):
        config['course_name'] = course_name
        if save_data(config, CONFIG_FILE):
            st.success("Course name saved!")
    
    if course_name:
        st.info(f"**Current Course:** {course_name}")
    
    # Load class assignments
    class_assignments = load_data(CLASS_ASSIGNMENTS_FILE) or []
    
    if not class_assignments:
        st.info("No class assignments submitted yet.")
        return
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 View Submissions", "📥 Download Files", "🗑️ Delete Submissions"])
    
    with tab1:
        # Display all submissions
        if class_assignments:
            # Convert to DataFrame for better display
            df_data = []
            for submission in class_assignments:
                df_data.append({
                    "Name": submission.get('name', ''),
                    "Roll No": submission.get('roll_no', ''),
                    "Course": submission.get('course_name', ''),
                    "Assignment No": submission.get('assignment_no', 1),
                    "File": submission.get('original_filename', 'No file'),
                    "File Size": f"{submission.get('file_size', 0) / 1024:.1f} KB" if submission.get('file_size') else "N/A",
                    "Remarks": submission.get('remarks', ''),
                    "Submitted": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M')
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Statistics
            st.subheader("📊 Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Submissions", len(class_assignments))
            with col2:
                unique_students = len(set([s['roll_no'] for s in class_assignments]))
                st.metric("Unique Students", unique_students)
            with col3:
                assignments_count = len(set([s['assignment_no'] for s in class_assignments]))
                st.metric("Assignments", assignments_count)
    
    with tab2:
        # Download functionality
        st.subheader("Download All Class Assignments")
        
        # Check if there are files to download
        submissions_with_files = [s for s in class_assignments if s.get('filename')]
        
        if not submissions_with_files:
            st.warning("No files to download.")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📦 Download All as ZIP", use_container_width=True):
                    # Create zip of all files
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        class_dir = os.path.join(DATA_DIR, "class_assignments")
                        if os.path.exists(class_dir):
                            for submission in submissions_with_files:
                                filename = submission.get('filename')
                                if filename:
                                    file_path = os.path.join(class_dir, filename)
                                    if os.path.exists(file_path):
                                        # Create a descriptive name for the file
                                        new_filename = f"Assignment_{submission['assignment_no']}_{submission['roll_no']}_{submission['name']}_{submission.get('original_filename', filename)}"
                                        zip_file.write(file_path, new_filename)
                    
                    zip_buffer.seek(0)
                    
                    # Provide download
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="⬇️ Download ZIP File",
                        data=zip_buffer,
                        file_name=f"class_assignments_{timestamp}.zip",
                        mime="application/zip"
                    )
            
            with col2:
                if st.button("📊 Export to CSV", use_container_width=True):
                    if class_assignments:
                        # Convert to DataFrame
                        export_data = []
                        for submission in class_assignments:
                            export_data.append({
                                "Name": submission.get('name', ''),
                                "Roll Number": submission.get('roll_no', ''),
                                "Course": submission.get('course_name', ''),
                                "Assignment No": submission.get('assignment_no', ''),
                                "Filename": submission.get('original_filename', ''),
                                "File Size": submission.get('file_size', 0),
                                "Submission Date": submission.get('submission_date', '')
                            })
                        
                        df_export = pd.DataFrame(export_data)
                        
                        # Create CSV file in memory
                        csv_buffer = io.StringIO()
                        df_export.to_csv(csv_buffer, index=False)
                        csv_buffer.seek(0)
                        
                        # Provide download
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.download_button(
                            label="⬇️ Download CSV File",
                            data=csv_buffer.getvalue(),
                            file_name=f"class_assignments_{timestamp}.csv",
                            mime="text/csv"
                        )
    
    with tab3:
        # Delete functionality
        st.subheader("🗑️ Delete Submissions")
        
        # Options for deletion
        delete_option = st.radio(
            "Delete Options:",
            ["Delete by Roll Number", "Delete by Assignment Number", "Delete All"]
        )
        
        if delete_option == "Delete by Roll Number":
            roll_numbers = list(set([s['roll_no'] for s in class_assignments]))
            selected_roll = st.selectbox("Select Roll Number", options=[""] + roll_numbers)
            
            if selected_roll:
                submissions_to_delete = [s for s in class_assignments if s['roll_no'] == selected_roll]
                st.warning(f"Found {len(submissions_to_delete)} submission(s) for roll number {selected_roll}")
                
                if submissions_to_delete and st.button("🗑️ Delete Submissions", type="secondary"):
                    # Archive before deletion
                    for submission in submissions_to_delete:
                        archive_data("class_assignment", submission, f"Admin deleted class assignment for {selected_roll}")
                    
                    # Remove from data
                    class_assignments = [s for s in class_assignments if s['roll_no'] != selected_roll]
                    save_data(class_assignments, CLASS_ASSIGNMENTS_FILE)
                    
                    # Delete files
                    for submission in submissions_to_delete:
                        if submission.get('filename'):
                            file_path = os.path.join(DATA_DIR, "class_assignments", submission['filename'])
                            if os.path.exists(file_path):
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    st.error(f"Error deleting file {submission['filename']}: {e}")
                    
                    st.success(f"✅ All submissions for {selected_roll} deleted successfully!")
                    st.rerun()
        
        elif delete_option == "Delete by Assignment Number":
            assignment_nos = list(set([s['assignment_no'] for s in class_assignments]))
            selected_assignment = st.selectbox("Select Assignment Number", options=[""] + [str(n) for n in assignment_nos])
            
            if selected_assignment:
                selected_assignment = int(selected_assignment)
                submissions_to_delete = [s for s in class_assignments if s['assignment_no'] == selected_assignment]
                st.warning(f"Found {len(submissions_to_delete)} submission(s) for assignment {selected_assignment}")
                
                if submissions_to_delete and st.button("🗑️ Delete Submissions", type="secondary"):
                    # Archive before deletion
                    for submission in submissions_to_delete:
                        archive_data("class_assignment", submission, f"Admin deleted assignment {selected_assignment}")
                    
                    # Remove from data
                    class_assignments = [s for s in class_assignments if s['assignment_no'] != selected_assignment]
                    save_data(class_assignments, CLASS_ASSIGNMENTS_FILE)
                    
                    # Delete files
                    for submission in submissions_to_delete:
                        if submission.get('filename'):
                            file_path = os.path.join(DATA_DIR, "class_assignments", submission['filename'])
                            if os.path.exists(file_path):
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    st.error(f"Error deleting file {submission['filename']}: {e}")
                    
                    st.success(f"✅ All submissions for assignment {selected_assignment} deleted successfully!")
                    st.rerun()
        
        elif delete_option == "Delete All":
            st.warning("⚠️ This will delete ALL class assignment submissions!")
            confirm = st.checkbox("I understand this action cannot be undone")
            
            if confirm and st.button("🗑️ Delete All Submissions", type="secondary"):
                # Archive all data
                archive_data("class_assignments_all", class_assignments, "Admin deleted all class assignments")
                
                # Delete all files
                class_dir = os.path.join(DATA_DIR, "class_assignments")
                if os.path.exists(class_dir):
                    try:
                        shutil.rmtree(class_dir)
                        Path(class_dir).mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        st.error(f"Error deleting files: {e}")
                
                # Clear data
                save_data([], CLASS_ASSIGNMENTS_FILE)
                st.success("✅ All class assignments deleted successfully!")
                st.rerun()

def manage_form_content():
    """Admin interface to manage form content"""
    st.header("📝 Form Content & Mode Management")
    
    # Load current form content
    form_content = load_data(FORM_CONTENT_FILE) or {}
    config = load_data(CONFIG_FILE) or {}
    
    # Mode selection
    st.subheader("🔄 Submission Mode Configuration")
    
    form_mode = st.selectbox(
        "Select Active Mode",
        options=["project_allocation", "project_file_submission", "lab_manual", "class_assignment"],
        index=["project_allocation", "project_file_submission", "lab_manual", "class_assignment"].index(
            config.get("form_mode", "project_allocation")
        ) if config.get("form_mode", "project_allocation") in ["project_allocation", "project_file_submission", "lab_manual", "class_assignment"] else 0,
        help="""Choose the active mode:
        - Project Allocation: Students view/edit allocations
        - Project File Submission: Students submit project files
        - Lab Manual: Simple file submission for lab manuals
        - Class Assignment: Course assignment submission"""
    )
    
    # Mode-specific settings
    if form_mode == "project_allocation":
        st.info("🔧 **Project Allocation Mode Settings**")
        allow_edit = st.checkbox(
            "Allow students to edit allocation details",
            value=config.get("allow_allocation_edit", False),
            help="When enabled, students can modify their group/project details"
        )
        config["allow_allocation_edit"] = allow_edit
    
    elif form_mode == "project_file_submission":
        st.info("🔧 **Project File Submission Mode Settings**")
        submission_open = st.checkbox(
            "Open file submission",
            value=config.get("project_file_submission_open", False),
            help="When enabled, students can submit project files"
        )
        config["project_file_submission_open"] = submission_open
        
        if submission_open:
            # File submission settings
            file_settings = load_data(FILE_SUBMISSION_FILE) or {}
            
            st.markdown("---")
            st.subheader("File Upload Settings")
            
            # Allowed formats
            default_formats = [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".zip", ".rar"]
            allowed_formats = st.multiselect(
                "Allowed File Formats",
                options=default_formats,
                default=file_settings.get("allowed_formats", default_formats)
            )
            
            # Max file size
            max_size = st.slider(
                "Maximum File Size (MB)",
                min_value=1,
                max_value=100,
                value=file_settings.get("max_size_mb", 10)
            )
            
            # Instructions
            instructions = st.text_area(
                "Upload Instructions",
                value=file_settings.get("instructions", "Please upload your project files in the specified formats."),
                height=100
            )
            
            if st.button("💾 Save File Settings", key="save_file_settings"):
                file_settings = {
                    "allowed_formats": allowed_formats,
                    "max_size_mb": max_size,
                    "instructions": instructions
                }
                if save_data(file_settings, FILE_SUBMISSION_FILE):
                    st.success("File settings saved!")
    
    elif form_mode == "lab_manual":
        st.info("🔧 **Lab Manual Mode Settings**")
        lab_open = st.checkbox(
            "Open lab manual submission",
            value=config.get("lab_manual_open", False),
            help="When enabled, students can submit lab manuals"
        )
        config["lab_manual_open"] = lab_open
        
        file_required = st.checkbox(
            "File upload required",
            value=config.get("lab_file_upload_required", False),
            help="When enabled, students must upload a file"
        )
        config["lab_file_upload_required"] = file_required
    
    elif form_mode == "class_assignment":
        st.info("🔧 **Class Assignment Mode Settings**")
        assignment_open = st.checkbox(
            "Open class assignment submission",
            value=config.get("class_assignment_open", False),
            help="When enabled, students can submit class assignments"
        )
        config["class_assignment_open"] = assignment_open
    
    # Save mode configuration
    if st.button("💾 Save Mode Configuration", key="save_mode"):
        config["form_mode"] = form_mode
        if save_data(config, CONFIG_FILE):
            st.success(f"Mode set to: {form_mode.replace('_', ' ').title()}")
    
    st.markdown("---")
    
    # Publish/Unpublish toggle
    col1, col2 = st.columns(2)
    with col1:
        form_published = st.toggle(
            "Publish Form for Students",
            value=config.get("form_published", True),
            help="When off, students will see a maintenance message"
        )
    
    with col2:
        if st.button("💾 Save Publication Status"):
            config['form_published'] = form_published
            if save_data(config, CONFIG_FILE):
                status = "published" if form_published else "unpublished"
                st.success(f"Form {status} successfully!")
    
    st.markdown("---")
    
    # COVER PAGE CONFIGURATION SECTION
    st.subheader("📋 Cover Page Configuration")
    
    # Load current cover page settings
    cover = form_content.get("cover_page", {})
    
    # Enable/disable cover page
    cover_enabled = st.checkbox(
        "Enable Cover Page",
        value=cover.get("enabled", True),
        help="Show/hide cover page in student form"
    )
    
    # Cover page title
    cover_title = st.text_input(
        "Cover Page Title",
        value=cover.get("title", "🎓 COAL Project Allocation"),
        help="Title displayed on cover page"
    )
    
    # Background and text colors
    col1, col2 = st.columns(2)
    with col1:
        bg_color = st.color_picker(
            "Background Color",
            value=cover.get("background_color", "#ffffff"),
            help="Background color for cover page"
        )
    with col2:
        text_color = st.color_picker(
            "Text Color",
            value=cover.get("text_color", "#000000"),
            help="Text color for cover page"
        )
    
    # Save cover page button
    if st.button("💾 Save Cover Page Settings", key="save_cover_page"):
        form_content["cover_page"] = {
            "enabled": cover_enabled,
            "title": cover_title,
            "background_color": bg_color,
            "text_color": text_color,
            "last_updated": datetime.now().isoformat()
        }
        
        if save_data(form_content, FORM_CONTENT_FILE):
            st.success("Cover page settings saved successfully!")
    
    st.markdown("---")
    
    # FORM HEADER CONFIGURATION SECTION
    st.subheader("📋 Form Header Configuration")
    
    # Load current form header
    form_header = form_content.get("form_header", {})
    
    # Form title
    form_title = st.text_input(
        "Form Title",
        value=form_header.get("title", "COAL Project Selection Form"),
        help="Title displayed at the top of the form"
    )
    
    # Form description
    form_description = st.text_area(
        "Form Description",
        value=form_header.get("description", "Please fill in all required fields to submit your project group allocation. All fields marked with * are mandatory."),
        height=100,
        help="Description displayed below the form title"
    )
    
    # Deadline settings
    col1, col2 = st.columns(2)
    with col1:
        show_deadline = st.checkbox(
            "Show Deadline",
            value=form_header.get("show_deadline", True),
            help="Show submission deadline to students"
        )
    with col2:
        deadline_date = st.text_input(
            "Deadline Date",
            value=form_header.get("deadline", "2024-12-31"),
            help="Format: YYYY-MM-DD"
        )
    
    # Contact settings
    col3, col4 = st.columns(2)
    with col3:
        show_contact = st.checkbox(
            "Show Contact Email",
            value=form_header.get("show_contact", True),
            help="Show contact email to students"
        )
    with col4:
        contact_email = st.text_input(
            "Contact Email",
            value=form_header.get("contact_email", "coal@university.edu"),
            help="Email address for student queries"
        )
    
    # Save form header button
    if st.button("💾 Save Form Header", key="save_form_header"):
        form_content["form_header"] = {
            "title": form_title,
            "description": form_description,
            "show_deadline": show_deadline,
            "deadline": deadline_date,
            "show_contact": show_contact,
            "contact_email": contact_email,
            "last_updated": datetime.now().isoformat()
        }
        
        if save_data(form_content, FORM_CONTENT_FILE):
            st.success("Form header saved successfully!")
    
    st.markdown("---")
    
    # Instructions editing
    st.subheader("📋 Instructions Configuration")
    
    # Load current instructions
    instructions = form_content.get("instructions", {})
    
    # Instructions visibility settings
    st.write("**Visibility Settings:**")
    col1, col2 = st.columns(2)
    with col1:
        show_in_allocation = st.checkbox(
            "Show in Project Allocation Mode",
            value=instructions.get("visibility", {}).get("project_allocation", True),
            help="Show instructions when in project allocation mode"
        )
        show_in_file_submission = st.checkbox(
            "Show in File Submission Mode",
            value=instructions.get("visibility", {}).get("project_file_submission", True),
            help="Show instructions when in project file submission mode"
        )
    with col2:
        show_in_class = st.checkbox(
            "Show in Class Assignment Mode",
            value=instructions.get("visibility", {}).get("class_assignment", False),
            help="Show instructions when in class assignment mode"
        )
    
    # Enable/disable instructions
    instructions_enabled = st.checkbox(
        "Enable Instructions",
        value=instructions.get("enabled", True),
        help="Enable/disable instructions system"
    )
    
    # Instructions title
    instructions_title = st.text_input(
        "Instructions Tab Title",
        value=instructions.get("title", "ℹ️ Instructions & Guidelines"),
        help="Title displayed on instructions tab"
    )
    
    # Instructions content (Markdown editor)
    st.markdown("**Instructions Content (Markdown Supported)**")
    instructions_content = st.text_area(
        "Instructions",
        value=instructions.get("content", """# Instructions & Guidelines

## Submission Process

### Step-by-Step Guide

1. **Form Your Group**
   - Minimum 1 member required (Group Leader)
   - Maximum members as set by admin
   - First member is Group Leader
   - All members should have unique roll numbers

2. **Select a Project**
   - Only unselected projects are shown
   - Each project can be selected only once
   - Choose carefully - selection is final

3. **Submit Application**
   - Fill all required fields
   - Confirm accuracy of information
   - Submit before deadline

## Important Rules

⚠️ **Project Selection Rules:**
- Each project can be selected by only ONE group
- Once selected, project disappears from available list
- No duplicate roll numbers across groups

⚠️ **Group Formation Rules:**
- Group Leader is mandatory
- Minimum 1 member required
- Roll numbers must be unique within group
- Cannot edit after submission

⚠️ **After Submission:**
- Save your Group Number
- Check allocation table for updates
- Contact admin for any changes"""),
        height=400,
        help="Use Markdown formatting for better presentation"
    )
    
    # Additional notes
    additional_notes = st.text_area(
        "Additional Notes (Optional)",
        value=instructions.get("additional_notes", ""),
        height=100,
        help="Additional information shown below instructions"
    )
    
    # Save button for instructions
    if st.button("💾 Save Instructions", key="save_instructions"):
        form_content["instructions"] = {
            "enabled": instructions_enabled,
            "title": instructions_title,
            "content": instructions_content,
            "additional_notes": additional_notes,
            "visibility": {
                "project_allocation": show_in_allocation,
                "project_file_submission": show_in_file_submission,
                "lab_manual": False,
                "class_assignment": show_in_class
            },
            "last_updated": datetime.now().isoformat()
        }
        if save_data(form_content, FORM_CONTENT_FILE):
            st.success("Instructions saved!")
    
    st.markdown("---")
    
    # Reset to defaults button
    if st.button("🔄 Reset to Default Content", type="secondary"):
        # Reload default form content
        init_files()
        st.success("Form content reset to defaults!")
        st.rerun()

def manage_short_urls():
    """Manage short URLs for the form"""
    st.header("🔗 Short URL Management")
    
    # Load short URLs
    short_urls = load_data(SHORT_URLS_FILE) or {}
    
    # Get base URL
    base_url = get_base_url()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info(f"**Base URL:** {base_url}")
    
    with col2:
        if st.button("🔄 Generate New Short URL", use_container_width=True):
            short_code = generate_short_code()
            full_url = f"{base_url}/?short={short_code}"
            short_urls[short_code] = {
                "url": full_url,
                "created_at": datetime.now().isoformat(),
                "clicks": 0,
                "last_accessed": None
            }
            if save_data(short_urls, SHORT_URLS_FILE):
                st.success(f"New short URL created!")
                st.rerun()
    
    st.markdown("---")
    
    # Display existing short URLs
    if short_urls:
        st.subheader("📋 Existing Short URLs")
        
        url_data = []
        for code, data in short_urls.items():
            short_url = f"{base_url}/?short={code}"
            created_time = datetime.fromisoformat(data['created_at']).strftime("%Y-%m-%d %H:%M") if data.get('created_at') else "Unknown"
            last_accessed = datetime.fromisoformat(data['last_accessed']).strftime("%Y-%m-%d %H:%M") if data.get('last_accessed') else "Never"
            
            url_data.append({
                "Short Code": code,
                "Short URL": short_url,
                "Target URL": data.get('url', ''),
                "Clicks": data.get('clicks', 0),
                "Created": created_time,
                "Last Accessed": last_accessed
            })
        
        df_urls = pd.DataFrame(url_data)
        st.dataframe(df_urls, use_container_width=True)
        
        # URL actions
        st.subheader("🔧 URL Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_code = st.selectbox(
                "Select URL to manage",
                options=[""] + list(short_urls.keys())
            )
        
        with col2:
            if selected_code:
                short_url = f"{base_url}/?short={selected_code}"
                st.code(short_url, language="text")
                
                # Delete URL
                if st.button("🗑️ Delete URL", type="secondary"):
                    # Archive before deletion
                    archive_data("short_url", short_urls[selected_code], "Admin deleted short URL")
                    
                    del short_urls[selected_code]
                    if save_data(short_urls, SHORT_URLS_FILE):
                        st.success(f"Short URL {selected_code} deleted!")
                        st.rerun()
        
        # Copy all URLs
        if st.button("📋 Copy All URLs to Clipboard"):
            all_urls = "\n".join([f"{base_url}/?short={code}" for code in short_urls.keys()])
            st.code(all_urls, language="text")
    
    else:
        st.info("No short URLs created yet. Click 'Generate New Short URL' to create one.")

def manage_projects_and_groups():
    """Manage projects and groups with delete functionality"""
    st.header("🗑️ Manage Projects & Groups")
    
    # Create tabs for projects and groups
    tab1, tab2 = st.tabs(["🗂️ Manage Projects", "👥 Manage Groups"])
    
    with tab1:
        manage_project_deletion()
    
    with tab2:
        manage_group_editing()

def manage_group_editing():
    """Manage group editing and member deletion"""
    st.subheader("Edit Groups & Delete Members")
    
    # Load groups
    groups = load_data(GROUPS_FILE) or []
    
    if not groups:
        st.info("No groups available to edit.")
        return
    
    # Filter active groups (not deleted)
    active_groups = [g for g in groups if not g.get('deleted', False)]
    
    if not active_groups:
        st.info("All groups have been deleted.")
        return
    
    # Group selection for editing
    st.write("### Select Group to Edit")
    
    # Display groups in a table
    group_data = []
    for group in active_groups:
        # Find group leader
        leader_name = ""
        for member in group['members']:
            if member.get('is_leader'):
                leader_name = member['name']
                break
        
        group_data.append({
            "Group #": group['group_number'],
            "Project": group['project_name'],
            "Group Leader": leader_name,
            "Status": group['status'],
            "Members": len([m for m in group['members'] if m['name'].strip()]),
            "Submitted": group.get('submission_date', '')
        })
    
    df_groups = pd.DataFrame(group_data)
    st.dataframe(df_groups, use_container_width=True)
    
    # Selection for editing
    group_numbers = [g['group_number'] for g in active_groups]
    selected_group_num = st.selectbox(
        "Choose a group to edit",
        options=[""] + group_numbers,
        key="edit_group_select"
    )
    
    if selected_group_num:
        # Get group details
        group_to_edit = next((g for g in groups if g['group_number'] == selected_group_num and not g.get('deleted', False)), None)
        
        if group_to_edit:
            # Show group details
            st.write("### Group Details")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"**Group Number:** {group_to_edit['group_number']}")
                st.info(f"**Project:** {group_to_edit['project_name']}")
                st.info(f"**Status:** {group_to_edit['status']}")
            
            with col2:
                st.info(f"**Submitted:** {group_to_edit.get('submission_date', '')}")
                st.info(f"**Total Members:** {len([m for m in group_to_edit['members'] if m['name'].strip()])}")
            
            # Show members with delete option
            st.write("### Group Members")
            
            for i, member in enumerate(group_to_edit['members'], 1):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    leader_badge = "👑 " if member.get('is_leader') else ""
                    st.write(f"{leader_badge}**Member {i}:** {member['name']}")
                with col2:
                    st.write(f"Roll: {member['roll_no']}")
                with col3:
                    # Don't allow deleting group leader
                    if not member.get('is_leader'):
                        if st.button(f"🗑️", key=f"delete_member_{selected_group_num}_{i}"):
                            # Remove member from group
                            group_to_edit['members'].pop(i-1)
                            if save_data(groups, GROUPS_FILE):
                                st.success(f"Member {i} deleted from group {selected_group_num}!")
                                st.rerun()
                    else:
                        st.write("👑 Leader")
            
            # Add new member option
            st.write("### Add New Member")
            with st.form(f"add_member_form_{selected_group_num}"):
                new_member_name = st.text_input("Full Name", key=f"new_name_{selected_group_num}")
                new_member_roll = st.text_input("Roll Number", key=f"new_roll_{selected_group_num}")
                
                if st.form_submit_button("➕ Add Member"):
                    if new_member_name.strip() and new_member_roll.strip():
                        # Check for duplicate roll number
                        existing_rolls = [m['roll_no'] for m in group_to_edit['members']]
                        if new_member_roll.strip() in existing_rolls:
                            st.error("❌ This roll number already exists in the group!")
                        else:
                            group_to_edit['members'].append({
                                "name": new_member_name.strip(),
                                "roll_no": new_member_roll.strip(),
                                "is_leader": False
                            })
                            if save_data(groups, GROUPS_FILE):
                                st.success("✅ New member added!")
                                st.rerun()
                    else:
                        st.error("❌ Please enter both name and roll number")
            
            # Delete entire group option
            st.write("---")
            st.write("### Delete Entire Group")
            reason = st.text_area(
                "Reason for deletion (optional)",
                placeholder="Enter reason for deleting this group...",
                key="group_delete_reason"
            )
            
            confirm_delete = st.checkbox(
                f"I confirm I want to delete Group {selected_group_num}",
                value=False,
                key="confirm_group_delete"
            )
            
            if confirm_delete:
                st.warning(f"⚠️ **Warning:** This will permanently delete Group {selected_group_num}")
                
                if st.button("🗑️ Delete Entire Group", type="secondary"):
                    # Archive group data
                    archive_data("group", group_to_edit, reason)
                    
                    # Mark group as deleted
                    for i, group in enumerate(groups):
                        if group['group_number'] == selected_group_num:
                            groups[i]['deleted'] = True
                            groups[i]['deleted_at'] = datetime.now().isoformat()
                            groups[i]['deleted_reason'] = reason
                            break
                    
                    # Update project count
                    projects = load_data(PROJECTS_FILE) or []
                    project_name = group_to_edit['project_name']
                    for project in projects:
                        if project['name'] == project_name:
                            if project.get('selected_by', 0) > 0:
                                project['selected_by'] -= 1
                                if project['selected_by'] == 0:
                                    project['status'] = 'Not Selected'
                            break
                    
                    if save_data(groups, GROUPS_FILE) and save_data(projects, PROJECTS_FILE):
                        st.success(f"✅ Group {selected_group_num} deleted successfully!")
                        st.rerun()

def manage_project_deletion():
    """Manage project deletion"""
    st.subheader("Delete Projects")
    
    # Load projects
    projects = load_data(PROJECTS_FILE) or []
    
    if not projects:
        st.info("No projects available to delete.")
        return
    
    # Filter active projects (not deleted)
    active_projects = [p for p in projects if not p.get('deleted', False)]
    
    if not active_projects:
        st.info("All projects have been deleted.")
        return
    
    # Project selection for deletion
    st.write("### Select Project to Delete")
    
    # Display projects in a table
    project_data = []
    for project in active_projects:
        project_data.append({
            "Project Name": project['name'],
            "Status": project['status'],
            "Selected By Groups": project.get('selected_by', 0),
            "Created": project.get('created_at', '')
        })
    
    df_projects = pd.DataFrame(project_data)
    st.dataframe(df_projects, use_container_width=True)
    
    # Selection for deletion
    project_names = [p['name'] for p in active_projects]
    selected_project = st.selectbox(
        "Choose a project to delete",
        options=[""] + project_names,
        key="delete_project_select"
    )
    
    if selected_project:
        # Get project details
        project_to_delete = next((p for p in projects if p['name'] == selected_project), None)
        
        if project_to_delete:
            # Show project details
            st.write("### Project Details")
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"**Name:** {project_to_delete['name']}")
                st.info(f"**Status:** {project_to_delete['status']}")
            
            with col2:
                st.info(f"**Selected By:** {project_to_delete.get('selected_by', 0)} groups")
                st.info(f"**Created:** {project_to_delete.get('created_at', '')}")
            
            # Check if project is selected by any group
            groups = load_data(GROUPS_FILE) or []
            groups_with_project = [g for g in groups if g['project_name'] == selected_project and not g.get('deleted', False)]
            
            if groups_with_project:
                st.warning(f"⚠️ **Warning:** This project is selected by {len(groups_with_project)} group(s).")
                st.write("**Groups with this project:**")
                for group in groups_with_project:
                    st.write(f"- Group {group['group_number']} (Status: {group['status']})")
                
                # Options for handling groups
                st.write("### Options for Groups")
                option = st.radio(
                    "What should happen to groups with this project?",
                    options=[
                        "Keep groups but mark project as deleted",
                        "Delete groups along with project"
                    ],
                    key="project_delete_option"
                )
            
            # Reason for deletion
            reason = st.text_area(
                "Reason for deletion (optional)",
                placeholder="Enter reason for deleting this project...",
                key="project_delete_reason"
            )
            
            # Confirmation
            st.write("### Confirmation")
            confirm_delete = st.checkbox(
                f"I confirm I want to delete project '{selected_project}'",
                value=False,
                key="confirm_project_delete"
            )
            
            # Delete button
            if st.button("🗑️ Delete Project", type="secondary", disabled=not confirm_delete):
                if confirm_delete:
                    # Archive project data
                    archive_data("project", project_to_delete, reason)
                    
                    # Mark project as deleted
                    for i, project in enumerate(projects):
                        if project['name'] == selected_project:
                            projects[i]['deleted'] = True
                            projects[i]['deleted_at'] = datetime.now().isoformat()
                            projects[i]['deleted_reason'] = reason
                            break
                    
                    # Handle groups based on option
                    if groups_with_project and option == "Delete groups along with project":
                        for group in groups_with_project:
                            # Archive group
                            archive_data("group", group, f"Deleted along with project: {selected_project}")
                            
                            # Mark group as deleted
                            for i, g in enumerate(groups):
                                if g['group_number'] == group['group_number']:
                                    groups[i]['deleted'] = True
                                    groups[i]['deleted_at'] = datetime.now().isoformat()
                                    groups[i]['deleted_reason'] = f"Project '{selected_project}' was deleted"
                                    break
                    
                    if save_data(projects, PROJECTS_FILE) and save_data(groups, GROUPS_FILE):
                        st.success(f"✅ Project '{selected_project}' deleted successfully!")
                        st.rerun()

def view_deleted_items():
    """View archived/deleted items with option to delete permanently"""
    st.header("🗂️ View Deleted Items")
    
    # Get all archive files
    try:
        archive_files = [f for f in os.listdir(ARCHIVE_DIR) if f.endswith('.json')]
    except FileNotFoundError:
        st.info("No deleted items found in archive.")
        return
    
    if not archive_files:
        st.info("No deleted items found in archive.")
        return
    
    # Sort by modification time (newest first)
    archive_files.sort(key=lambda x: os.path.getmtime(os.path.join(ARCHIVE_DIR, x)), reverse=True)
    
    # Delete all button
    st.subheader("Delete Options")
    if st.button("🗑️ Delete All Archived Items", type="secondary"):
        for filename in archive_files:
            filepath = os.path.join(ARCHIVE_DIR, filename)
            try:
                os.remove(filepath)
            except Exception as e:
                st.error(f"Error deleting {filename}: {e}")
        
        st.success("✅ All archived items deleted permanently!")
        st.rerun()
    
    # Display archive files
    st.subheader("Archived Items")
    for filename in archive_files:
        filepath = os.path.join(ARCHIVE_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                archive_data_content = json.load(f)
        except Exception as e:
            st.error(f"Error loading {filename}: {e}")
            continue
        
        with st.expander(f"📄 {filename}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Display basic info
                data_type = archive_data_content.get("data_type", "Unknown")
                deleted_at = archive_data_content.get("deleted_at", "")
                reason = archive_data_content.get("reason", "")
                
                st.write(f"**Type:** {data_type}")
                st.write(f"**Deleted At:** {deleted_at[:19] if deleted_at else 'Unknown'}")
                if reason:
                    st.write(f"**Reason:** {reason}")
                
                # Show preview of data
                if st.checkbox(f"Show data for {filename}", key=f"show_{filename}"):
                    st.json(archive_data_content, expanded=False)
            
            with col2:
                # Delete button for individual file
                if st.button(f"🗑️ Delete", key=f"delete_{filename}"):
                    try:
                        os.remove(filepath)
                        st.success(f"✅ {filename} deleted permanently!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting file: {e}")
                
                # Download button
                try:
                    with open(filepath, 'r') as f:
                        file_content = f.read()
                    
                    st.download_button(
                        label=f"Download",
                        data=file_content,
                        file_name=filename,
                        mime="application/json",
                        key=f"download_{filename}"
                    )
                except Exception as e:
                    st.error(f"Error reading {filename}: {e}")

def export_data_section():
    """Export data section - CSV format (no openpyxl required)"""
    st.header("📊 Export Data")
    
    groups = load_data(GROUPS_FILE) or []
    active_groups = [g for g in groups if not g.get('deleted', False)]
    config = load_data(CONFIG_FILE) or {}
    max_members = config.get("max_members", 3)
    
    if active_groups:
        # Prepare data for CSV
        csv_data = []
        
        for group in active_groups:
            row = {
                "Group Number": group['group_number'],
                "Project Name": group['project_name'],
                "Status": group['status'],
                "Submission Date": group.get('submission_date', '')
            }
            
            # Add member information
            for i in range(1, max_members + 1):
                if i <= len(group['members']):
                    member = group['members'][i-1]
                    member_name = member['name']
                    if member.get('is_leader'):
                        member_name += " (Group Leader)"
                    row[f"Member {i} Name"] = member_name
                    row[f"Member {i} Roll No"] = member['roll_no']
                else:
                    row[f"Member {i} Name"] = ""
                    row[f"Member {i} Roll No"] = ""
            
            csv_data.append(row)
        
        # Create DataFrame
        df_export = pd.DataFrame(csv_data)
        
        # Show preview
        st.subheader("Data Preview")
        st.dataframe(df_export, use_container_width=True)
        
        # Export options
        st.subheader("Export Options")
        col1, col2 = st.columns(2)
        
        with col1:
            include_deleted = st.checkbox("Include deleted items", value=False)
        
        with col2:
            export_format = st.selectbox(
                "Export Format",
                ["CSV File"]
            )
        
        # Generate file
        if st.button("📥 Generate Export File"):
            if include_deleted:
                # Include deleted groups
                deleted_groups = [g for g in groups if g.get('deleted', False)]
                for group in deleted_groups:
                    row = {
                        "Group Number": f"{group['group_number']} (DELETED)",
                        "Project Name": group['project_name'],
                        "Status": f"{group['status']} (DELETED)",
                        "Submission Date": group.get('submission_date', ''),
                        "Deleted Reason": group.get('deleted_reason', ''),
                        "Deleted At": group.get('deleted_at', '')
                    }
                    
                    # Add member information
                    for i in range(1, max_members + 1):
                        if i <= len(group['members']):
                            member = group['members'][i-1]
                            member_name = member['name']
                            if member.get('is_leader'):
                                member_name += " (Group Leader)"
                            row[f"Member {i} Name"] = member_name
                            row[f"Member {i} Roll No"] = member['roll_no']
                        else:
                            row[f"Member {i} Name"] = ""
                            row[f"Member {i} Roll No"] = ""
                    
                    csv_data.append(row)
                
                # Update DataFrame
                df_export = pd.DataFrame(csv_data)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Always use CSV format
            filename = f"project_allocations_{timestamp}.csv"
            
            # Convert to CSV
            csv_string = df_export.to_csv(index=False)
            
            # Create download button
            st.download_button(
                label="⬇️ Click to Download CSV File",
                data=csv_string,
                file_name=filename,
                mime="text/csv"
            )
            
            st.success(f"✅ CSV file '{filename}' is ready for download!")
    else:
        st.info("No data to export yet.")

def admin_dashboard():
    """Admin dashboard with authentication - NO SIDEBAR HERE"""
    # Check if already logged in
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        # Login form
        st.title("🔐 Admin Login")
        
        with st.form("login_form"):
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit:
                    if authenticate(username, password):
                        st.session_state.logged_in = True
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
        return
    
    # Main admin dashboard
    st.title("🛠️ Admin Dashboard")
    
    # Tabs for different admin functions
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
        "🔗 Short URLs", 
        "📝 Form Content", 
        "📋 Project Management", 
        "👥 Manage Groups", 
        "🗂️ View Deleted",
        "👥 Group Submissions", 
        "⚙️ System Configuration",
        "📊 Export Data",
        "📁 File Submissions",
        "📚 Lab Manual",
        "📘 Class Assignments",
        "🔐 Change Password"
    ])
    
    # Tab 1: Short URL Management
    with tab1:
        manage_short_urls()
    
    # Tab 2: Form Content Management
    with tab2:
        manage_form_content()
    
    # Tab 3: Project Management
    with tab3:
        st.header("📋 Project Management")
        
        # Add new project
        with st.expander("➕ Add New Project", expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_project_name = st.text_input("Project Name")
            with col2:
                new_project_status = st.selectbox("Status", ["Not Selected", "Selected"])
            
            if st.button("Add Project", key="add_project"):
                if new_project_name.strip():
                    projects = load_data(PROJECTS_FILE) or []
                    
                    # Check if project already exists (including deleted ones)
                    existing_project = next((p for p in projects if p['name'] == new_project_name), None)
                    
                    if existing_project:
                        if existing_project.get('deleted', False):
                            # Reactivate deleted project
                            existing_project['deleted'] = False
                            existing_project['status'] = new_project_status
                            existing_project['reactivated_at'] = datetime.now().isoformat()
                            if save_data(projects, PROJECTS_FILE):
                                st.success(f"Project '{new_project_name}' reactivated successfully!")
                        else:
                            st.error("Project with this name already exists!")
                    else:
                        projects.append({
                            "name": new_project_name,
                            "status": new_project_status,
                            "selected_by": 0,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "deleted": False
                        })
                        if save_data(projects, PROJECTS_FILE):
                            st.success(f"Project '{new_project_name}' added successfully!")
                            st.rerun()
                else:
                    st.error("Please enter a project name")
        
        # Display and manage projects with DELETE option
        st.subheader("Project List")
        projects = load_data(PROJECTS_FILE) or []
        active_projects = [p for p in projects if not p.get('deleted', False)]
        
        if active_projects:
            # Create DataFrame for display
            project_data = []
            for project in active_projects:
                # Check if project is selected by any group
                groups = load_data(GROUPS_FILE) or []
                selected_by_groups = [g for g in groups if g['project_name'] == project['name'] and not g.get('deleted', False)]
                
                project_data.append({
                    "Project Name": project['name'],
                    "Status": project['status'],
                    "Selected By Groups": len(selected_by_groups),
                    "Group Numbers": ", ".join([str(g['group_number']) for g in selected_by_groups]) if selected_by_groups else "None",
                    "Created": project.get('created_at', '')
                })
            
            df_projects = pd.DataFrame(project_data)
            st.dataframe(df_projects, use_container_width=True)
            
            # Project management controls with DELETE option
            st.subheader("Manage Projects")
            
            col1, col2, col3, col4 = st.columns([2,1,1,1])
            
            with col1:
                project_to_manage = st.selectbox(
                    "Select Project to Manage",
                    options=[""] + [p['name'] for p in active_projects],
                    key="manage_project_select"
                )
            
            with col2:
                new_status = st.selectbox(
                    "New Status",
                    options=["Not Selected", "Selected"],
                    key="new_status_select"
                )
            
            with col3:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("Update Status", key="update_status_btn"):
                    if project_to_manage:
                        for project in projects:
                            if project['name'] == project_to_manage:
                                old_status = project['status']
                                project['status'] = new_status
                                if save_data(projects, PROJECTS_FILE):
                                    st.success(f"Status updated from '{old_status}' to '{new_status}' for '{project_to_manage}'!")
                                    st.rerun()
                                break
                    else:
                        st.error("Please select a project")
            
            with col4:
                if project_to_manage and st.button("🗑️ Delete Project", type="secondary", key="delete_project_btn"):
                    # Show delete confirmation
                    st.warning(f"⚠️ Are you sure you want to delete project '{project_to_manage}'?")
                    
                    # Get project details
                    project_to_delete = next((p for p in projects if p['name'] == project_to_manage), None)
                    
                    if project_to_delete:
                        # Check if project is selected by any group
                        groups = load_data(GROUPS_FILE) or []
                        groups_with_project = [g for g in groups if g['project_name'] == project_to_manage and not g.get('deleted', False)]
                        
                        if groups_with_project:
                            st.error(f"Cannot delete! Project is selected by {len(groups_with_project)} group(s).")
                        else:
                            # Archive project data
                            archive_data("project", project_to_delete, "Admin deleted project from management")
                            
                            # Mark project as deleted
                            for i, project in enumerate(projects):
                                if project['name'] == project_to_manage:
                                    projects[i]['deleted'] = True
                                    projects[i]['deleted_at'] = datetime.now().isoformat()
                                    projects[i]['deleted_reason'] = "Admin deleted from project management"
                                    break
                            
                            if save_data(projects, PROJECTS_FILE):
                                st.success(f"✅ Project '{project_to_manage}' deleted successfully!")
                                st.rerun()
        else:
            st.info("No projects added yet. Add your first project above.")
    
    # Tab 4: Manage Groups (with member deletion)
    with tab4:
        manage_group_editing()
    
    # Tab 5: View Deleted Items
    with tab5:
        view_deleted_items()
    
    # Tab 6: Group Submissions
    with tab6:
        st.header("👥 Group Submissions")
        
        groups = load_data(GROUPS_FILE) or []
        active_groups = [g for g in groups if not g.get('deleted', False)]
        
        if active_groups:
            # Create a simplified table for quick overview
            st.subheader("Groups Overview")
            overview_data = []
            for group in active_groups:
                overview_data.append({
                    "Group Number": group['group_number'],
                    "Project Name": group['project_name'],
                    "Status": group['status'],
                    "Members Count": len([m for m in group['members'] if m['name'].strip()]),
                    "Submission Date": group.get('submission_date', '')
                })
            
            df_overview = pd.DataFrame(overview_data)
            st.dataframe(df_overview, use_container_width=True)
            
            # Group details and management
            st.subheader("Group Details & Management")
            
            # Select group to view/edit
            selected_group_num = st.selectbox(
                "Select Group to View/Edit",
                options=[""] + [g['group_number'] for g in active_groups],
                key="group_select"
            )
            
            if selected_group_num:
                selected_group = next((g for g in active_groups if g['group_number'] == selected_group_num), None)
                
                if selected_group:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Group Number", selected_group['group_number'])
                        st.metric("Project", selected_group['project_name'])
                    
                    with col2:
                        # Update status
                        new_group_status = st.selectbox(
                            "Update Group Status",
                            options=["Not Selected", "Selected"],
                            index=0 if selected_group['status'] == "Not Selected" else 1,
                            key=f"group_status_{selected_group_num}"
                        )
                        
                        if st.button("Update Group Status", key=f"update_group_{selected_group_num}"):
                            selected_group['status'] = new_group_status
                            if save_data(groups, GROUPS_FILE):
                                st.success("Group status updated!")
                                st.rerun()
                    
                    # Display members
                    st.subheader("Group Members")
                    for i, member in enumerate(selected_group['members'], 1):
                        if member['name'].strip():
                            leader_badge = "👑 " if member.get('is_leader') else ""
                            st.write(f"**{leader_badge}Member {i}:** {member['name']} (Roll: {member['roll_no']})")
        else:
            st.info("No group submissions yet.")
    
    # Tab 7: System Configuration
    with tab7:
        st.header("⚙️ System Configuration")
        
        config = load_data(CONFIG_FILE) or {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Maximum members configuration - Admin can set 1 to 10
            st.subheader("Group Size Configuration")
            max_members = st.slider(
                "Maximum Number of Members per Group",
                min_value=1,
                max_value=10,
                value=config.get('max_members', 3),
                help="Set the maximum number of members allowed per group (1-10)"
            )
            
            # Next group number configuration
            st.subheader("Group Numbering")
            next_group_num = st.number_input(
                "Next Group Number",
                min_value=1,
                value=config.get('next_group_number', 1),
                help="This number will be assigned to the next submitted group"
            )
        
        with col2:
            # Base URL configuration
            st.subheader("URL Configuration")
            base_url = st.text_input(
                "Base URL",
                value=config.get('base_url', 'http://localhost:8501'),
                help="Base URL for short URL generation"
            )
            
            st.info("""
            **URL Format Examples:**
            - Local: http://localhost:8501
            - Cloud: https://your-app.streamlit.app
            - Custom: https://projects.yourdomain.com
            """)
        
        if st.button("💾 Save Configuration", key="save_config"):
            config['max_members'] = max_members
            config['next_group_number'] = int(next_group_num)
            config['base_url'] = base_url.strip()
            if save_data(config, CONFIG_FILE):
                st.success("Configuration saved successfully!")
    
    # Tab 8: Export Data
    with tab8:
        export_data_section()
    
    # Tab 9: File Submissions (Project Files)
    with tab9:
        manage_file_submissions()
    
    # Tab 10: Lab Manual
    with tab10:
        manage_lab_manual()
    
    # Tab 11: Class Assignments
    with tab11:
        manage_class_assignments()
    
    # Tab 12: Change Password
    with tab12:
        st.header("🔐 Change Admin Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submit = st.form_submit_button("Change Password")
            
            if submit:
                admin_data = load_data(ADMIN_CREDENTIALS_FILE)
                current_hash = hash_password(current_password)
                
                if admin_data.get("password_hash") != current_hash:
                    st.error("Current password is incorrect!")
                elif new_password != confirm_password:
                    st.error("New passwords do not match!")
                elif len(new_password) < 6:
                    st.error("New password must be at least 6 characters long!")
                else:
                    admin_data["password_hash"] = hash_password(new_password)
                    if save_data(admin_data, ADMIN_CREDENTIALS_FILE):
                        st.success("Password changed successfully!")

def main():
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'group_verified' not in st.session_state:
        st.session_state.group_verified = False
    if 'verified_group_number' not in st.session_state:
        st.session_state.verified_group_number = None
    
    # Get query parameters
    query_params = st.query_params
    
    # Check if this is a short URL access
    if 'short' in query_params:
        short_code = query_params['short']
        short_urls = load_data(SHORT_URLS_FILE) or {}
        
        if short_code in short_urls:
            # Track click
            short_urls[short_code]['clicks'] = short_urls[short_code].get('clicks', 0) + 1
            short_urls[short_code]['last_accessed'] = datetime.now().isoformat()
            save_data(short_urls, SHORT_URLS_FILE)
            
            # Show student form WITHOUT Admin Dashboard option
            student_form_standalone()
            return
        else:
            # Invalid short code, show normal page
            st.warning("Invalid short URL code. Please use a valid link.")
    
    # Check if admin is already logged in
    if st.session_state.logged_in:
        # Show admin dashboard with logout in sidebar
        st.sidebar.title("🎓 M. Moiz Admin")
        if st.sidebar.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.group_verified = False
            st.session_state.verified_group_number = None
            st.rerun()
        admin_dashboard()
    else:
        # Show main page with navigation
        st.sidebar.title("🎓 COAL Project Allocation")
        page = st.sidebar.radio("Navigate to:", ["Student Form", "Admin Login"])
        
        if page == "Student Form":
            student_form_standalone()
        else:
            # Show admin login
            st.title("🔐 Admin Login")
            
            with st.form("login_form"):
                col1, col2, col3 = st.columns([1,2,1])
                with col2:
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Login", use_container_width=True)
                    
                    if submit:
                        if authenticate(username, password):
                            st.session_state.logged_in = True
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")

if __name__ == "__main__":
    main()