import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import hashlib
from pathlib import Path
import secrets
import string

# Page configuration
st.set_page_config(
    page_title="Project Allocation System",
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

# Create data directories if they don't exist
Path(DATA_DIR).mkdir(exist_ok=True)
Path(ARCHIVE_DIR).mkdir(exist_ok=True)
Path(os.path.join(DATA_DIR, "submitted_files")).mkdir(exist_ok=True)

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
        "max_members": 4,
        "next_group_number": 1,
        "form_published": True,
        "base_url": "http://localhost:8501",
        "enable_file_submission": False
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
            "title": "🎓 Final Year Project Allocation",
            "content": """
# Welcome to Project Allocation System

This form is for final year students to select their project topics and form groups.

## Important Instructions:
1. Form groups of 1-4 members (as specified by your department)
2. The first member will be the group leader
3. Select only ONE project from the available list
4. Ensure all information is accurate before submission

## Submission Guidelines:
- Deadline: December 31, 2024
- Contact: projects@university.edu
- Queries: Contact project coordinator
            """,
            "background_color": "#ffffff",
            "text_color": "#000000"
        },
        "form_header": {
            "title": "Final Year Project Selection Form",
            "description": "Please fill in all required fields to submit your project group allocation. All fields marked with * are mandatory.",
            "show_deadline": True,
            "deadline": "2024-12-31",
            "show_contact": True,
            "contact_email": "projects@university.edu"
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
        (FILE_SUBMISSIONS_FILE, {})
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
    
    st.markdown(f'<div style="font-size: 2.5rem; font-weight: bold; margin-bottom: 1rem;">{cover.get("title", "🎓 Project Allocation")}</div>', unsafe_allow_html=True)
    st.markdown(cover.get("content", ""))
    st.markdown("---")

def display_form_header(form_content):
    """Display the form header/title section"""
    header = form_content.get("form_header", {})
    
    st.title(header.get("title", "Final Year Project Selection Form"))
    
    # Description
    st.markdown(f"**Description:** {header.get('description', '')}")
    
    # Additional info if enabled
    if header.get("show_deadline", True):
        deadline = header.get("deadline", "2024-12-31")
        st.info(f"⏰ **Submission Deadline:** {deadline}")
    
    if header.get("show_contact", True):
        contact_email = header.get("contact_email", "projects@university.edu")
        st.info(f"📧 **Contact for Queries:** {contact_email}")
    
    st.markdown("---")

def student_form_standalone():
    """Student form without Admin Dashboard option in sidebar"""
    # Load form content
    form_content = load_data(FORM_CONTENT_FILE) or {}
    config = load_data(CONFIG_FILE) or {}
    
    # Check if form is published
    if not config.get("form_published", True):
        st.warning("⏸️ The form is currently under maintenance. Please check back later.")
        return
    
    # Check if file submission is enabled
    file_submission_enabled = config.get("enable_file_submission", False)
    
    if file_submission_enabled:
        # File submission tabs
        tab1, tab2, tab3 = st.tabs(["📄 File Submission", "📊 View Allocations", "ℹ️ Instructions"])
        with tab1:
            display_file_submission_form(form_content, config)
        with tab2:
            display_allocations_table_for_students()
        with tab3:
            display_instructions(form_content)
    else:
        # Regular form tabs
        tab1, tab2, tab3 = st.tabs(["📋 Submit Form", "📊 View Allocations", "ℹ️ Instructions"])
        with tab1:
            display_submission_form(form_content, config)
        with tab2:
            display_allocations_table_for_students()
        with tab3:
            display_instructions(form_content)

def display_file_submission_form(form_content, config):
    """Display file submission form (simplified version)"""
    # Display cover page if enabled
    display_cover_page(form_content)
    
    # Display form header
    display_form_header(form_content)
    
    # Load file submission settings
    file_settings = load_data(FILE_SUBMISSION_FILE) or {}
    
    st.header("📁 File Submission")
    st.info("⚠️ You can only submit files if you have already submitted your project allocation.")
    
    with st.form("file_submission_form"):
        # Group number input
        group_number = st.number_input(
            "Enter Your Group Number*",
            min_value=1,
            step=1,
            help="Enter the group number you received after submission"
        )
        
        # Verify group exists
        groups = load_data(GROUPS_FILE) or []
        group_exists = any(g['group_number'] == group_number and not g.get('deleted', False) for g in groups)
        
        if group_exists:
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
                
                # File upload
                st.subheader("📎 Upload Files")
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
                    "Upload your project files",
                    type=file_types,
                    accept_multiple_files=True,
                    help=f"Allowed formats: {', '.join(allowed_formats)} | Max size: {file_settings.get('max_size_mb', 10)}MB per file"
                )
                
                # Instructions
                st.info(file_settings.get("instructions", "Please upload your project files."))
                
                # Submit button
                submitted = st.form_submit_button("📤 Submit Files", use_container_width=True)
                
                if submitted:
                    if uploaded_files:
                        # Save file information
                        file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
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
                    else:
                        st.error("❌ Please select at least one file to upload")
        else:
            st.error("❌ Group number not found. Please check your group number.")
            st.info("You must first submit your project allocation before uploading files.")

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

def display_instructions(form_content):
    """Display instructions tab"""
    st.header("ℹ️ Instructions & Guidelines")
    
    cover = form_content.get("cover_page", {})
    if cover.get("enabled", True):
        st.markdown(cover.get("content", ""))
    
    st.markdown("---")
    
    st.subheader("📋 Submission Process")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Step-by-Step Guide
        
        1. **Form Your Group**
           - Minimum 1 member required (Group Leader)
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
        """)
    
    with col2:
        st.markdown("""
        ### Important Rules
        
        ⚠️ **Project Selection Rules:**
        - Each project can be selected by only ONE group
        - Once selected, project disappears from available list
        - No duplicate roll numbers across groups
        
        ⚠️ **Group Formation Rules:**
        - Group Leader is mandatory
        - Roll numbers must be unique within group
        - Cannot edit after submission
        
        ⚠️ **After Submission:**
        - Save your Group Number
        - Check allocation table for updates
        - Contact admin for any changes
        """)

def display_submission_form(form_content, config):
    """Display the submission form"""
    # Display cover page if enabled
    display_cover_page(form_content)
    
    # Display form header
    display_form_header(form_content)
    
    # Load configuration
    max_members = config.get("max_members", 4)
    
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
        
        # Additional members
        if max_members > 1:
            st.markdown("### 👥 Additional Members")
            st.caption(f"Fill details for members 2 to {max_members} (optional)")
            
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
                st.header("🎉 Thank You! 🙏")
                
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

def manage_form_content():
    """Admin interface to manage form content"""
    st.header("📝 Form Content Management")
    
    # Load current form content
    form_content = load_data(FORM_CONTENT_FILE) or {}
    config = load_data(CONFIG_FILE) or {}
    
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
    
    # File submission toggle
    st.markdown("---")
    st.subheader("📁 File Submission Settings")
    
    file_submission_enabled = st.toggle(
        "Enable File Submission for Students",
        value=config.get("enable_file_submission", False),
        help="When enabled, students can upload project files"
    )
    
    if st.button("💾 Save File Submission Settings"):
        config['enable_file_submission'] = file_submission_enabled
        if save_data(config, CONFIG_FILE):
            status = "enabled" if file_submission_enabled else "disabled"
            st.success(f"File submission {status} successfully!")
    
    if file_submission_enabled:
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
    
    st.markdown("---")
    
    # Tab for cover page and form header
    tab1, tab2 = st.tabs(["📄 Cover Page Settings", "🏷️ Form Header Settings"])
    
    with tab1:
        st.subheader("Cover Page Configuration")
        
        cover = form_content.get("cover_page", {})
        
        # Enable/disable cover page
        cover_enabled = st.checkbox(
            "Enable Cover Page",
            value=cover.get("enabled", True),
            help="Show cover page to students"
        )
        
        # Cover page title
        cover_title = st.text_input(
            "Cover Page Title",
            value=cover.get("title", "🎓 Final Year Project Allocation"),
            help="Main title displayed on cover page"
        )
        
        # Cover page content (Markdown editor)
        st.markdown("**Cover Page Content (Markdown Supported)**")
        cover_content = st.text_area(
            "Content",
            value=cover.get("content", ""),
            height=200,
            help="Use Markdown formatting for better presentation"
        )
        
        # Save button for cover page
        if st.button("💾 Save Cover Page Settings", key="save_cover"):
            form_content["cover_page"] = {
                "enabled": cover_enabled,
                "title": cover_title,
                "content": cover_content,
                "last_updated": datetime.now().isoformat()
            }
            if save_data(form_content, FORM_CONTENT_FILE):
                st.success("Cover page settings saved!")
    
    with tab2:
        st.subheader("Form Header Configuration")
        
        header = form_content.get("form_header", {})
        
        # Form title
        form_title = st.text_input(
            "Form Title",
            value=header.get("title", "Final Year Project Selection Form"),
            help="Main title of the form"
        )
        
        # Form description
        form_description = st.text_area(
            "Form Description",
            value=header.get("description", ""),
            height=100,
            help="Short description explaining the form's purpose"
        )
        
        # Deadline settings
        st.subheader("⏰ Deadline Settings")
        show_deadline = st.checkbox(
            "Show Deadline",
            value=header.get("show_deadline", True),
            help="Display submission deadline to students"
        )
        
        if show_deadline:
            try:
                deadline_date = datetime.strptime(header.get("deadline", "2024-12-31"), "%Y-%m-%d").date()
            except:
                deadline_date = datetime.now().date()
            deadline = st.date_input(
                "Submission Deadline",
                value=deadline_date
            )
            deadline_str = deadline.strftime("%Y-%m-%d")
        else:
            deadline_str = header.get("deadline", "2024-12-31")
        
        # Contact settings
        st.subheader("📧 Contact Information")
        show_contact = st.checkbox(
            "Show Contact Information",
            value=header.get("show_contact", True),
            help="Display contact email to students"
        )
        
        if show_contact:
            contact_email = st.text_input(
                "Contact Email",
                value=header.get("contact_email", "projects@university.edu")
            )
        else:
            contact_email = header.get("contact_email", "projects@university.edu")
        
        # Save button for form header
        if st.button("💾 Save Form Header Settings", key="save_header"):
            form_content["form_header"] = {
                "title": form_title,
                "description": form_description,
                "show_deadline": show_deadline,
                "deadline": deadline_str,
                "show_contact": show_contact,
                "contact_email": contact_email,
                "last_updated": datetime.now().isoformat()
            }
            if save_data(form_content, FORM_CONTENT_FILE):
                st.success("Form header settings saved!")
    
    # Reset to defaults button
    st.markdown("---")
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
    """View archived/deleted items"""
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
    
    # Display archive files
    for filename in archive_files:
        filepath = os.path.join(ARCHIVE_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                archive_data = json.load(f)
        except Exception as e:
            st.error(f"Error loading {filename}: {e}")
            continue
        
        with st.expander(f"📄 {filename}"):
            st.json(archive_data, expanded=False)
            
            # Download button
            try:
                with open(filepath, 'r') as f:
                    file_content = f.read()
                
                st.download_button(
                    label=f"Download {filename}",
                    data=file_content,
                    file_name=filename,
                    mime="application/json"
                )
            except Exception as e:
                st.error(f"Error reading {filename}: {e}")

def export_data_section():
    """Export data section - CSV format (no openpyxl required)"""
    st.header("📊 Export Data")
    
    groups = load_data(GROUPS_FILE) or []
    active_groups = [g for g in groups if not g.get('deleted', False)]
    config = load_data(CONFIG_FILE) or {}
    max_members = config.get("max_members", 4)
    
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
                ["CSV File", "Excel File"]
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
            
            if export_format == "Excel File":
                try:
                    # Try to use Excel if openpyxl is available
                    import openpyxl
                    filename = f"project_allocations_{timestamp}.xlsx"
                    
                    # Save to Excel in memory
                    from io import BytesIO
                    excel_bytes = BytesIO()
                    with pd.ExcelWriter(excel_bytes, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Project Allocations')
                    excel_bytes.seek(0)
                    
                    # Create download button
                    st.download_button(
                        label="⬇️ Click to Download Excel File",
                        data=excel_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success(f"✅ Excel file '{filename}' is ready for download!")
                    
                except ImportError:
                    st.warning("⚠️ openpyxl module not installed. Falling back to CSV format...")
                    export_format = "CSV File"
            
            if export_format == "CSV File":
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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "🔗 Short URLs", 
        "📝 Form Content", 
        "📋 Project Management", 
        "👥 Manage Groups", 
        "🗂️ View Deleted",
        "👥 Group Submissions", 
        "⚙️ System Configuration",
        "📊 Export Data",
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
        
        # Display and manage projects
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
            
            # Project management controls
            st.subheader("Manage Projects")
            col1, col2, col3 = st.columns([2,1,1])
            
            with col1:
                project_to_update = st.selectbox(
                    "Select Project to Update",
                    options=[""] + [p['name'] for p in active_projects],
                    key="update_project_select"
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
                    if project_to_update:
                        for project in projects:
                            if project['name'] == project_to_update:
                                old_status = project['status']
                                project['status'] = new_status
                                if save_data(projects, PROJECTS_FILE):
                                    st.success(f"Status updated from '{old_status}' to '{new_status}' for '{project_to_update}'!")
                                    st.rerun()
                                break
                    else:
                        st.error("Please select a project")
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
            # Maximum members configuration - START FROM 1
            st.subheader("Group Size Configuration")
            max_members = st.slider(
                "Maximum Number of Members per Group",
                min_value=1,  # CHANGED FROM 4 TO 1
                max_value=10,
                value=config.get('max_members', 4),
                help="Maximum number of members allowed in a group"
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
    
    # Tab 9: Change Password
    with tab9:
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
        st.sidebar.title("🎓 Admin Dashboard")
        if st.sidebar.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
        admin_dashboard()
    else:
        # Show main page with navigation
        st.sidebar.title("🎓 Project Allocation System")
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