import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import secrets
import string
import zipfile
import io
import shutil

# Page configuration
st.set_page_config(
    page_title="Academic Projects Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# HELPER FUNCTIONS
# ============================================

def sanitize_filename(name):
    """Remove invalid characters from filenames/directory names"""
    if not name:
        return "unknown"
    
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    
    # Also replace spaces with underscores
    name = name.replace(' ', '_')
    
    # Remove any other non-ASCII characters
    name = ''.join(c for c in name if c.isalnum() or c in ['_', '-', '.'])
    
    # If name becomes empty after sanitization, use a default
    if not name:
        name = 'unknown'
    
    # Limit length to avoid path too long errors
    if len(name) > 100:
        name = name[:100]
    
    return name

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

def add_to_deleted_items(item_type, item_data, reason=""):
    """Add item to deleted items list for easy viewing"""
    deleted_items = load_data(DELETED_ITEMS_FILE) or []
    
    deleted_record = {
        "id": str(len(deleted_items) + 1).zfill(3),
        "type": item_type,
        "data": item_data,
        "deleted_at": datetime.now().isoformat(),
        "reason": reason
    }
    
    deleted_items.append(deleted_record)
    save_data(deleted_items, DELETED_ITEMS_FILE)

def check_form_deadline(form_type):
    """Check if form submission deadline has passed"""
    deadlines = load_data(DEADLINES_FILE) or {}
    form_deadline = deadlines.get(form_type, {})
    
    if not form_deadline or not form_deadline.get("enabled", False):
        return True  # No deadline set or disabled
    
    deadline_str = form_deadline.get("datetime", "")
    if not deadline_str:
        return True
    
    try:
        deadline = datetime.fromisoformat(deadline_str)
        now = datetime.now()
        return now <= deadline
    except:
        return True  # If there's an error with the date, allow submission

def get_form_status(form_type):
    """Get form status with deadline information"""
    deadlines = load_data(DEADLINES_FILE) or {}
    form_deadline = deadlines.get(form_type, {})
    
    if not form_deadline or not form_deadline.get("enabled", False):
        return {"open": True, "deadline": None, "message": None}
    
    deadline_str = form_deadline.get("datetime", "")
    if not deadline_str:
        return {"open": True, "deadline": None, "message": None}
    
    try:
        deadline = datetime.fromisoformat(deadline_str)
        now = datetime.now()
        
        if now <= deadline:
            time_left = deadline - now
            hours_left = time_left.total_seconds() / 3600
            
            if hours_left < 24:
                time_text = f"{int(hours_left)} hours"
            else:
                days_left = int(hours_left / 24)
                time_text = f"{days_left} days"
            
            return {
                "open": True,
                "deadline": deadline,
                "message": f"⏰ Submission closes in {time_text}"
            }
        else:
            return {
                "open": False,
                "deadline": deadline,
                "message": f" Submission deadline has passed on {deadline.strftime('%Y-%m-%d %H:%M')}"
            }
    except:
        return {"open": True, "deadline": None, "message": None}

# ============================================
# CONSTANTS AND INITIALIZATION
# ============================================

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
DELETED_ITEMS_FILE = os.path.join(DATA_DIR, "deleted_items.json")
DEADLINES_FILE = os.path.join(DATA_DIR, "deadlines.json")

# Create data directories if they don't exist
Path(DATA_DIR).mkdir(exist_ok=True)
Path(ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)
Path(os.path.join(DATA_DIR, "submitted_files")).mkdir(parents=True, exist_ok=True)
Path(os.path.join(DATA_DIR, "lab_manual")).mkdir(parents=True, exist_ok=True)
Path(os.path.join(DATA_DIR, "class_assignments")).mkdir(parents=True, exist_ok=True)

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
        "lab_subject_name": "",
        "current_assignment_no": 1,
        "project_allocation_project_optional": False,
        # NEW: tab visibility settings
        "tab_visibility": {
            "project_allocation": {
                "form": True,
                "allocations": True,
                "instructions": True
            },
            "project_file_submission": {
                "form": True,
                "allocations": True,
                "instructions": True
            },
            "lab_manual": {
                "form": True,
                "instructions": True
            },
            "class_assignment": {
                "form": True,
                "instructions": True
            }
        }
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
            "title": "🎓Project Allocation",
            "content": "",
            "background_color": "#1f2937",
            "text_color": "#e5e7eb" 
         },
        "form_header": {
            "title": "Project Selection Form",
            "description": "Please fill in all required fields to submit your project group allocation. All fields marked with * are mandatory.",
            "show_deadline": False,
            "deadline": "",
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

2. **Select a Project** (if required)
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
                "lab_manual": True,
                "class_assignment": True
            }
        }
    }
    
    # Default file submission settings with file limits
    default_file_submission = {
        "enabled": False,
        "allowed_formats": [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".zip", ".rar"],
        "max_size_mb": 10,
        "max_files": 5,
        "allow_multiple_submissions": False,
        "instructions": "Please upload your project files in the specified formats."
    }
    
    # Default lab manual settings with file limits
    default_lab_settings = {
        "allowed_formats": [".pdf", ".doc", ".docx", ".txt"],
        "max_size_mb": 5,
        "max_files": 1
    }
    
    # Default class assignment settings with file limits
    default_class_settings = {
        "allowed_formats": [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".zip", ".rar"],
        "max_size_mb": 10,
        "max_files": 3
    }
    
    # Default deadlines
    default_deadlines = {
        "project_allocation": {
            "enabled": False,
            "datetime": "",
            "message": ""
        },
        "project_file_submission": {
            "enabled": False,
            "datetime": "",
            "message": ""
        },
        "lab_manual": {
            "enabled": False,
            "datetime": "",
            "message": ""
        },
        "class_assignment": {
            "enabled": False,
            "datetime": "",
            "message": ""
        }
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
        (CLASS_ASSIGNMENTS_FILE, []),
        (DELETED_ITEMS_FILE, []),
        (DEADLINES_FILE, default_deadlines),
        (os.path.join(DATA_DIR, "lab_settings.json"), default_lab_settings),
        (os.path.join(DATA_DIR, "class_settings.json"), default_class_settings)
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

# ============================================
# CUSTOM CSS WITH ALL FIXES
# ============================================

st.markdown("""
<style>
    /* Main styles */
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4f46e5, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    
    .sub-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #e5e7eb !important;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        background-color: #1f2937;
        border-left: 4px solid #dc2626;
    }
    
    .card {
        background-color: #1f2937;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        margin-bottom: 1.5rem;
        border: 1px solid #374151;
        color: #e5e7eb;
    }
    
    .success-card {
        border-left: 5px solid #10b981;
        background-color: #064e3b;
        color: #d1fae5;
    }
    
    .warning-card {
        border-left: 5px solid #f59e0b;
        background-color: #78350f;
        color: #fef3c7;
    }
    
    .info-card {
        border-left: 5px solid #3b82f6;
        background-color: #1e3a8a;
        color: #dbeafe;
        border-radius: 8px;
    }
    
    .error-card {
        border-left: 5px solid #ef4444;
        background-color: #7f1d1d;
        color: #fee2e2;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        display: inline-block;
    }
    
    .inline-error {
        display: inline-block;
        margin: 0;
        white-space: nowrap;
        padding: 0.5rem 1rem;
    }
    
    /* Button styles - RED THEME */
    .stButton > button {
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
        border: 1px solid #dc2626;
        background-color: #dc2626;
        color: white;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        background-color: #b91c1c;
        border-color: #b91c1c;
    }
    
    .primary-button {
        background: linear-gradient(90deg, #dc2626, #b91c1c) !important;
        color: white !important;
        border: none !important;
    }
    
    .secondary-button {
        background-color: #ef4444 !important;
        color: white !important;
        border: none !important;
    }
    
    .danger-button {
        background-color: #7f1d1d !important;
        color: white !important;
        border: none !important;
    }
    
    /* Keep sidebar buttons with original colors */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #374151 !important;
        border: 1px solid #4b5563 !important;
        color: white !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #4b5563 !important;
        transform: translateX(5px);
    }
    
    section[data-testid="stSidebar"] .stButton > button:active {
        background-color: #6b7280 !important;
    }
    
    /* Form styles */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #4b5563;
        padding: 0.75rem;
        background-color: #111827;
        color: #e5e7eb;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #dc2626;
        box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.3);
    }
    
    .stSelectbox > div > div > div {
        border-radius: 8px;
        border: 2px solid #4b5563;
        background-color: #111827;
        color: #e5e7eb;
    }
    
    /* Sidebar styles */
    section[data-testid="stSidebar"] {
        background-color: #1f2937;
    }
    
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] .stMarkdown p {
        color: white !important;
    }
    
    section[data-testid="stSidebar"] hr {
        border-color: #4b5563;
    }
    
    /* Tab styles */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #111827;
        padding: 8px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        background-color: #1f2937;
        border: 2px solid transparent;
        color: #e5e7eb;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #dc2626 !important;
        color: white !important;
        border-color: #dc2626 !important;
    }
    
    /* Dataframe styles */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Metric cards */
    .stMetric {
        background-color: #1f2937;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        border: 1px solid #374151;
        color: #e5e7eb;
    }
    
    /* Progress bars */
    .stProgress > div > div > div > div {
        background-color: #dc2626;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
    }
    
    .status-submitted { background-color: #065f46; color: #d1fae5; }
    .status-approved { background-color: #1e40af; color: #dbeafe; }
    .status-pending { background-color: #92400e; color: #fef3c7; }
    .status-rejected { background-color: #991b1b; color: #fee2e2; }
    
    /* Login form specific */
    .login-form {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        background-color: #1f2937;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        color: #e5e7eb;
    }
    
    /* Alert boxes */
    .stAlert {
        border-radius: 10px;
        padding: 1rem 1.5rem;
    }
    
    /* Expander styles */
    .streamlit-expanderHeader {
        background-color: #111827;
        border-radius: 8px;
        font-weight: 600;
        color: #e5e7eb !important;
    }
    
    .streamlit-expanderContent {
        background-color: #1f2937;
        color: #e5e7eb;
    }
    
    /* File uploader */
    .stFileUploader > div {
        border: 2px dashed #4b5563;
        border-radius: 8px;
        padding: 2rem;
        background-color: #111827;
    }
    
    .stFileUploader > div:hover {
        border-color: #dc2626;
        background-color: #1e1b4b;
    }
    
    /* Checkbox styles */
    .stCheckbox > label {
        color: #e5e7eb !important;
    }
    
    /* Radio button styles */
    .stRadio > label {
        color: #e5e7eb !important;
    }
    
    /* Slider styles */
    .stSlider > div > div > div {
        color: #e5e7eb;
    }
    
    /* Text area styles */
    .stTextArea > div > div > textarea {
        background-color: #111827;
        color: #e5e7eb;
        border: 2px solid #4b5563;
    }
    
    /* Selectbox styles */
    .stSelectbox > label {
        color: #e5e7eb !important;
    }
    
    /* Number input styles */
    .stNumberInput > label {
        color: #e5e7eb !important;
    }
    
    .stNumberInput > div > div > input {
        background-color: #111827;
        color: #e5e7eb;
        border: 2px solid #4b5563;
    }
    
    /* Date input styles */
    .stDateInput > label {
        color: #e5e7eb !important;
    }
    
    .stDateInput > div > div > input {
        background-color: #111827;
        color: #e5e7eb;
        border: 2px solid #4b5563;
    }
    
    /* Time input styles */
    .stTimeInput > label {
        color: #e5e7eb !important;
    }
    
    .stTimeInput > div > div > input {
        background-color: #111827;
        color: #e5e7eb;
        border: 2px solid #4b5563;
    }
    
    /* Color picker styles */
    .stColorPicker > label {
        color: #e5e7eb !important;
    }
    
    /* Multi-select styles */
    .stMultiSelect > label {
        color: #e5e7eb !important;
    }
    
    .stMultiSelect > div > div > div {
        background-color: #111827;
        color: #e5e7eb;
        border: 2px solid #4b5563;
    }
    
    /* Toggle styles */
    .stToggle > label {
        color: #e5e7eb !important;
    }
    
    /* Markdown text */
    .stMarkdown {
        color: #e5e7eb;
    }
    
    /* Caption text */
    .stCaption {
        color: #9ca3af !important;
    }
    
    /* Code block */
    .stCodeBlock {
        background-color: #111827;
        color: #e5e7eb;
    }
    
    /* Divider */
    hr {
        border-color: #4b5563;
    }
    
    /* Data editor */
    [data-testid="stDataFrame"] {
        background-color: #1f2937;
        color: #e5e7eb;
    }
    
    /* Success/Error/Warning/Info message colors */
    div[data-testid="stSuccess"] > div {
        background-color: #065f46;
        color: #d1fae5;
        border: 1px solid #10b981;
    }
    
    div[data-testid="stError"] > div {
        background-color: #7f1d1d;
        color: #fee2e2;
        border: 1px solid #ef4444;
    }
    
    div[data-testid="stWarning"] > div {
        background-color: #78350f;
        color: #fef3c7;
        border: 1px solid #f59e0b;
    }
    
    div[data-testid="stInfo"] > div {
        background-color: #1e3a8a;
        color: #dbeafe;
        border: 1px solid #3b82f6;
    }
    
    /* Form background */
    .stForm {
        background-color: transparent;
    }
    
    /* Remove unnecessary white sections */
    div[style*="background-color: white"],
    div[style*="background: white"],
    div[style*="background-color: #ffffff"],
    div[style*="background: #ffffff"] {
        background-color: #1f2937 !important;
        color: #e5e7eb !important;
    }
    
    /* Fix for specific white sections in cards */
    .card div[style*="background-color: white"] {
        background-color: #111827 !important;
        color: #e5e7eb !important;
    }
    
    /* Fix for gradient backgrounds */
    div[style*="background: linear-gradient"] {
        color: #e5e7eb !important;
    }
    
    /* Fix table styles */
    table {
        color: #e5e7eb !important;
    }
    
    th {
        background-color: #374151 !important;
        color: #e5e7eb !important;
    }
    
    td {
        background-color: #1f2937 !important;
        color: #e5e7eb !important;
    }
    
    /* Fix for Streamlit's default styles */
    .main .block-container {
        background-color: #111827;
        color: #e5e7eb;
    }
    
    /* Card heading styles */
    .card h3, .card h4 {
        color: #e5e7eb;
        margin-top: 0;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #374151;
    }
    
    .card .stMarkdown h3 {
        color: #e5e7eb !important;
        margin: 0 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #374151;
    }
    
    /* Fix for form section headings */
    .form-section {
        background-color: #1f2937;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        margin-bottom: 1.5rem;
        border: 1px solid #374151;
        color: #e5e7eb;
    }
    
    .form-section h3 {
        color: #e5e7eb;
        margin-top: 0;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #374151;
    }
    
    /* Extra spacing for project file submit button */
    .extra-spacing {
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# STUDENT FORM FUNCTIONS - MAIN CONTENT AREA
# ============================================

def display_cover_page(form_content):
    """Display the cover page"""
    cover = form_content.get("cover_page", {})
    if not cover.get("enabled", True):
        return
    
    # Apply custom styles with enhanced UI
    st.markdown(f"""
    <div class="card" style="
        background: linear-gradient(135deg, {cover.get('background_color', '#1f2937')} 0%, #111827 100%);
        color: {cover.get('text_color', '#e5e7eb')};
        padding: 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        border: none;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
    ">
        <div style="font-size: 2.8rem; font-weight: 800; margin-bottom: 1.5rem; background: linear-gradient(90deg, #4f46e5, #7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            {cover.get('title', '🎓 Project Allocation')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)

def display_form_header(form_content):
    """Display the form header/title section"""
    header = form_content.get("form_header", {})
    
    st.markdown(f'<h1 class="main-header">{header.get("title", "Project Selection Form")}</h1>', unsafe_allow_html=True)
    
    # Description in a card
    st.markdown(f"""
    <div class="info-card">
        <div style="font-size: 1.1rem; line-height: 1.6;">
            {header.get('description', 'Please fill in all required fields to submit your project group allocation. All fields marked with * are mandatory.')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Contact info only if enabled
    if header.get("show_contact", True):
        contact_email = header.get("contact_email", "coal@university.edu")
        st.markdown(f"""
        <div style="background-color: #1e3a8a; padding: 1rem 1.5rem; border-radius: 10px; border-left: 4px solid #3b82f6; margin: 1rem 0;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">📧</span>
                <div>
                    <strong style="color: #93c5fd;">Contact for Queries:</strong>
                    <div style="color: #dbeafe;">{contact_email}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)

def class_assignment_submission_form():
    """Form for class assignment submission - MAIN CONTENT AREA - REMARKS REMOVED"""
    st.markdown('<h2 class="sub-header">📘 Class Assignment Submission</h2>', unsafe_allow_html=True)
    
    # Check deadline
    status = get_form_status("class_assignment")
    if not status["open"]:
        st.markdown(f"""
        <div class="error-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">⛔</span>
                <div style="font-size: 1.1rem; font-weight: 600;">{status['message']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if status["message"]:
        st.markdown(f"""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">⏰</span>
                <div>{status['message']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Load course name from config
    config = load_data(CONFIG_FILE) or {}
    course_name = config.get("course_name", "")
    current_assignment_no = config.get("current_assignment_no", 1)
    
    # Course name display
    if course_name:
        st.markdown(f"""
        <div class="card" style="background-color: #0c4a6e; border-left: 4px solid #0ea5e9;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">📚</span>
                <div>
                    <strong>Course:</strong> {course_name}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Load class settings
    class_settings = load_data(os.path.join(DATA_DIR, "class_settings.json")) or {}
    allowed_formats = class_settings.get("allowed_formats", [".pdf", ".doc", ".docx", ".txt"])
    max_size_mb = class_settings.get("max_size_mb", 10)
    max_files = class_settings.get("max_files", 3)
    
    with st.form("class_assignment_form", clear_on_submit=False):
        # Student information in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">👤 Student Information</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("**Full Name***", placeholder="Enter your full name", help="Your full name as per university records")
        with col2:
            roll_no = st.text_input("**Roll Number***", placeholder="Enter your roll number", help="Your official university roll number")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Assignment details in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📝 Assignment Details</h3>', unsafe_allow_html=True)
        assignment_no = st.number_input("**Assignment Number**", min_value=1, value=current_assignment_no, disabled=True)
        st.caption(f"Assignment number is set by administrator")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # File upload in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📎 Upload Assignment File</h3>', unsafe_allow_html=True)
        
        # Convert formats for file_uploader
        file_types = []
        for fmt in allowed_formats:
            if fmt.startswith('.'):
                file_types.append(fmt[1:])
            else:
                file_types.append(fmt)
        
        uploaded_files = st.file_uploader(
            f"**Upload your assignment file(s)***",
            type=file_types,
            accept_multiple_files=True,
            help=f"📁 Allowed formats: {', '.join(allowed_formats)} | 📦 Maximum files: {max_files} | 💾 Maximum file size: {max_size_mb}MB"
        )
        
        # Check file count and size
        if uploaded_files:
            max_size_bytes = max_size_mb * 1024 * 1024
            
            # Check file count
            if len(uploaded_files) > max_files:
                st.error(f"❌ Maximum {max_files} files allowed. You have uploaded {len(uploaded_files)} files.")
            
            # Check file sizes
            for uploaded_file in uploaded_files:
                if uploaded_file.size > max_size_bytes:
                    st.error(f"❌ File '{uploaded_file.name}' exceeds {max_size_mb}MB limit")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Terms agreement in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">✅ Confirmation</h3>', unsafe_allow_html=True)
        agree = st.checkbox("**I confirm that this is my own work***")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit button with custom styling
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "📤 **Submit Assignment**",
                use_container_width=True,
                type="primary"
            )
        
        if submitted:
            errors = []
            if not name.strip():
                errors.append("❌ Name is required")
            if not roll_no.strip():
                errors.append("❌ Roll number is required")
            if not uploaded_files:
                errors.append("❌ File upload is required")
            if not agree:
                errors.append("❌ Please confirm this is your own work")
            
            # File validation
            if uploaded_files:
                # Check file count
                if len(uploaded_files) > max_files:
                    errors.append(f"❌ Maximum {max_files} files allowed")
                
                # Check file sizes
                max_size_bytes = max_size_mb * 1024 * 1024
                for uploaded_file in uploaded_files:
                    if uploaded_file.size > max_size_bytes:
                        errors.append(f"❌ File '{uploaded_file.name}' exceeds {max_size_mb}MB limit")
            
            if errors:
                for error in errors:
                    st.markdown(f'<div class="error-card">{error}</div>', unsafe_allow_html=True)
            else:
                # Load existing submissions
                class_submissions = load_data(CLASS_ASSIGNMENTS_FILE) or []
                
                # Sanitize roll number for directory name
                sanitized_roll_no = sanitize_filename(roll_no.strip())
                
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
                        "submission_date": datetime.now().isoformat(),
                        "status": "Submitted",
                        "files": []
                    }
                    
                    # Save uploaded files
                    if uploaded_files:
                        # Create directory for class assignments
                        class_dir = os.path.join(DATA_DIR, "class_assignments")
                        Path(class_dir).mkdir(parents=True, exist_ok=True)
                        
                        # Create directory for this submission using sanitized roll number
                        submission_dir = os.path.join(class_dir, f"{sanitized_roll_no}_assignment_{assignment_no}")
                        Path(submission_dir).mkdir(parents=True, exist_ok=True)
                        
                        for uploaded_file in uploaded_files:
                            # Generate unique filename with sanitized names
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            sanitized_filename = sanitize_filename(uploaded_file.name)
                            filename = f"{timestamp}_{sanitized_roll_no}_{assignment_no}_{sanitized_filename}"
                            file_path = os.path.join(submission_dir, filename)
                            
                            # Save file
                            with open(file_path, 'wb') as f:
                                f.write(uploaded_file.getbuffer())
                            
                            submission_record["files"].append({
                                "filename": filename,
                                "original_filename": uploaded_file.name,
                                "file_size": uploaded_file.size,
                                "file_type": uploaded_file.type
                            })
                    
                    # Save to database
                    class_submissions.append(submission_record)
                    save_data(class_submissions, CLASS_ASSIGNMENTS_FILE)
                    
                    # Success message with animation
                    st.markdown("""
                    <div style="text-align: center; margin: 2rem 0;">
                        <div style="font-size: 4rem; margin-bottom: 1rem;">🎉</div>
                        <h2 style="color: #10b981; margin-bottom: 1rem;">✅ Assignment Submitted Successfully!</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                    
                    # Show confirmation in a card
                    st.markdown("""
                    <div class="success-card">
                        <h3 style="color: #a7f3d0; margin-bottom: 1rem;">📋 Submission Details</h3>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Name</div>
                            <div style="font-weight: 600;">{name}</div>
                        </div>
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Roll Number</div>
                            <div style="font-weight: 600;">{roll_no}</div>
                        </div>
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Course</div>
                            <div style="font-weight: 600;">{course_name}</div>
                        </div>
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Assignment No</div>
                            <div style="font-weight: 600;">{assignment_no}</div>
                        </div>
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Files Submitted</div>
                            <div style="font-weight: 600;">{len(uploaded_files) if uploaded_files else 0}</div>
                        </div>
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Submission Time</div>
                            <div style="font-weight: 600;">{datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 1.5rem; padding: 1rem; background-color: #065f46; border-radius: 8px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.2rem;">✅</span>
                            <div>Your assignment has been submitted successfully.</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

def lab_manual_submission_form():
    """Form for lab manual submission - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">📚 Lab Manual Submission</h2>', unsafe_allow_html=True)
    
    # Check deadline
    status = get_form_status("lab_manual")
    if not status["open"]:
        st.markdown(f"""
        <div class="error-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">⛔</span>
                <div style="font-size: 1.1rem; font-weight: 600;">{status['message']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if status["message"]:
        st.markdown(f"""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">⏰</span>
                <div>{status['message']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Load subject name from config
    config = load_data(CONFIG_FILE) or {}
    lab_subject_name = config.get("lab_subject_name", "")
    
    # Subject name display
    if lab_subject_name:
        st.markdown(f"""
        <div class="card" style="background-color: #0c4a6e; border-left: 4px solid #0ea5e9;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">🧪</span>
                <div>
                    <strong>Subject:</strong> {lab_subject_name}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Load lab settings
    lab_settings = load_data(os.path.join(DATA_DIR, "lab_settings.json")) or {}
    allowed_formats = lab_settings.get("allowed_formats", [".pdf", ".doc", ".docx", ".txt"])
    max_size_mb = lab_settings.get("max_size_mb", 5)
    max_files = lab_settings.get("max_files", 1)
    file_required = config.get("lab_file_upload_required", False)
    
    with st.form("lab_manual_form", clear_on_submit=False):
        # Student information in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">👤 Student Information</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("**Full Name***", placeholder="Enter your full name", help="Your full name as per university records")
        with col2:
            roll_no = st.text_input("**Roll Number***", placeholder="Enter your roll number", help="Your official university roll number")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # File upload in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📎 Upload File</h3>', unsafe_allow_html=True)
        
        # Convert formats for file_uploader
        file_types = []
        for fmt in allowed_formats:
            if fmt.startswith('.'):
                file_types.append(fmt[1:])
            else:
                file_types.append(fmt)
        
        uploaded_files = st.file_uploader(
            f"**Upload your file(s)**{'*' if file_required else ''}",
            type=file_types,
            accept_multiple_files=True,
            help=f"📁 Allowed formats: {', '.join(allowed_formats)} | 📦 Maximum files: {max_files} | 💾 Maximum file size: {max_size_mb}MB"
        )
        
        # Check file count and size
        if uploaded_files:
            max_size_bytes = max_size_mb * 1024 * 1024
            
            # Check file count
            if len(uploaded_files) > max_files:
                st.error(f"❌ Maximum {max_files} file(s) allowed. You have uploaded {len(uploaded_files)} files.")
            
            # Check file sizes
            for uploaded_file in uploaded_files:
                if uploaded_file.size > max_size_bytes:
                    st.error(f"❌ File '{uploaded_file.name}' exceeds {max_size_mb}MB limit")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Terms agreement in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">✅ Confirmation</h3>', unsafe_allow_html=True)
        agree = st.checkbox("**I confirm that this is my own work***")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit button with custom styling
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "📤 **Submit Lab Manual**",
                use_container_width=True,
                type="primary"
            )
        
        if submitted:
            errors = []
            if not name.strip():
                errors.append("❌ Name is required")
            if not roll_no.strip():
                errors.append("❌ Roll number is required")
            if file_required and not uploaded_files:
                errors.append("❌ File upload is required")
            if not agree:
                errors.append("❌ Please confirm this is your own work")
            
            # File validation
            if uploaded_files:
                # Check file count
                if len(uploaded_files) > max_files:
                    errors.append(f"❌ Maximum {max_files} file(s) allowed")
                
                # Check file sizes
                max_size_bytes = max_size_mb * 1024 * 1024
                for uploaded_file in uploaded_files:
                    if uploaded_file.size > max_size_bytes:
                        errors.append(f"❌ File '{uploaded_file.name}' exceeds {max_size_mb}MB limit")
            
            if errors:
                for error in errors:
                    st.markdown(f'<div class="error-card">{error}</div>', unsafe_allow_html=True)
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
                        "status": "Submitted",
                        "files": []
                    }
                    
                    # Save uploaded files
                    if uploaded_files:
                        # Create directory for lab manual
                        lab_dir = os.path.join(DATA_DIR, "lab_manual")
                        Path(lab_dir).mkdir(parents=True, exist_ok=True)
                        
                        # Sanitize roll number for directory name
                        sanitized_roll_no = sanitize_filename(roll_no.strip())
                        
                        # Create directory for this submission
                        submission_dir = os.path.join(lab_dir, sanitized_roll_no)
                        Path(submission_dir).mkdir(parents=True, exist_ok=True)
                        
                        for uploaded_file in uploaded_files:
                            # Generate unique filename with sanitized names
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            sanitized_filename = sanitize_filename(uploaded_file.name)
                            filename = f"{timestamp}_{sanitized_roll_no}_{sanitized_filename}"
                            file_path = os.path.join(submission_dir, filename)
                            
                            # Save file
                            with open(file_path, 'wb') as f:
                                f.write(uploaded_file.getbuffer())
                            
                            submission_record["files"].append({
                                "filename": filename,
                                "original_filename": uploaded_file.name,
                                "file_size": uploaded_file.size
                            })
                    
                    # Save to database
                    lab_manual.append(submission_record)
                    save_data(lab_manual, LAB_MANUAL_FILE)
                    
                    # Success message
                    st.markdown("""
                    <div style="text-align: center; margin: 2rem 0;">
                        <div style="font-size: 4rem; margin-bottom: 1rem;">🎉</div>
                        <h2 style="color: #10b981; margin-bottom: 1rem;">✅ Lab Manual Submitted Successfully!</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                    
                    # Show confirmation in a card
                    st.markdown("""
                    <div class="success-card">
                        <h3 style="color: #a7f3d0; margin-bottom: 1rem;">📋 Submission Details</h3>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Name</div>
                            <div style="font-weight: 600;">{name}</div>
                        </div>
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Roll Number</div>
                            <div style="font-weight: 600;">{roll_no}</div>
                        </div>
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Subject</div>
                            <div style="font-weight: 600;">{lab_subject_name}</div>
                        </div>
                        <div style="background-color: #065f46; padding: 1rem; border-radius: 8px;">
                            <div style="font-size: 0.9rem; color: #a7f3d0;">Files Submitted</div>
                            <div style="font-weight: 600;">{len(uploaded_files) if uploaded_files else 0}</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 1.5rem; padding: 1rem; background-color: #065f46; border-radius: 8px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.2rem;">✅</span>
                            <div>Your lab manual has been submitted successfully.</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

def display_instructions(form_content):
    """Display instructions tab based on current mode - MAIN CONTENT AREA"""
    config = load_data(CONFIG_FILE) or {}
    current_mode = config.get("form_mode", "project_allocation")
    
    instructions = form_content.get("instructions", {})
    
    # Check if instructions are enabled for current mode
    visibility = instructions.get("visibility", {})
    if not visibility.get(current_mode, True):
        return
    
    if not instructions.get("enabled", True):
        return
    
    st.markdown(f'<h2 class="sub-header">{instructions.get("title", "ℹ️ Instructions & Guidelines")}</h2>', unsafe_allow_html=True)
    
    # Display main instructions content in a card
    st.markdown(instructions.get("content", ""))
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Display additional notes if any
    if instructions.get("additional_notes"):
        st.markdown("""
        <div class="info-card">
            <h3 style="color: #93c5fd; margin-bottom: 1rem;">📌 Additional Information</h3>
        """, unsafe_allow_html=True)
        st.markdown(instructions.get("additional_notes"))
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display contact information
    st.markdown("""
    <div class="card" style="background-color: #78350f; border-left: 4px solid #f59e0b;">
        <h3 style="color: #fef3c7; margin-bottom: 1rem;">❓ Need Help?</h3>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.2rem;">📞</span>
            <div>For any queries or issues, please contact the Class Representative.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def student_form_standalone():
    """Student form without Admin Dashboard option in sidebar"""
    # Load config
    config = load_data(CONFIG_FILE) or {}
    
    # Check if form is published
    if not config.get("form_published", True):
        st.markdown("""
        <div class="warning-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">⏸️</span>
                <div>
                    <h3 style="color: #fef3c7; margin: 0;">Form Closed</h3>
                    <p style="margin: 0.5rem 0 0 0;">This form is closed. Please contact your Class CR for submission issues.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Determine which mode is active
    form_mode = config.get("form_mode", "project_allocation")
    form_content = load_data(FORM_CONTENT_FILE) or {}
    
    # Get tab visibility settings
    tab_visibility = config.get("tab_visibility", {}).get(form_mode, {})
    
    if form_mode == "project_allocation":
        # MODE A: Project Allocation Mode
        allow_edit = config.get("allow_allocation_edit", False)
        status = get_form_status("project_allocation")
        
        # Build tabs list based on visibility and allow_edit
        tabs = []
        if allow_edit and tab_visibility.get("form", True):
            tabs.append(("📋 **Project Selection Form**", lambda: display_submission_form(form_content, config)))
        if tab_visibility.get("allocations", True):
            tabs.append(("📊 **View Allocations**", display_allocations_table_for_students))
        if tab_visibility.get("instructions", True):
            tabs.append(("ℹ️ **Instructions**", lambda: display_instructions(form_content)))
        
        # If no tabs enabled, show a message
        if not tabs:
            st.warning("⚠️ No tabs are enabled for this mode. Please contact administrator.")
            return
        
        # Show deadline status before tabs
        if not status["open"]:
            st.markdown(f"""
            <div class="error-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">⛔</span>
                    <div style="font-size: 1.1rem; font-weight: 600;">{status['message']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            return
        
        if status["message"]:
            st.markdown(f"""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">⏰</span>
                    <div>{status['message']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Create tabs
        tab_objects = st.tabs([label for label, _ in tabs])
        for i, (_, func) in enumerate(tabs):
            with tab_objects[i]:
                func()
    
    elif form_mode == "project_file_submission":
        # MODE B: Project File Submission Mode
        submission_open = config.get("project_file_submission_open", False)
        status = get_form_status("project_file_submission")
        
        # Build tabs
        tabs = []
        if submission_open and tab_visibility.get("form", True):
            tabs.append(("📁 **Submit Files**", lambda: display_project_file_submission_form(form_content, config)))
        if tab_visibility.get("allocations", True):
            tabs.append(("📊 **View Allocations**", display_allocations_table_for_students))
        if tab_visibility.get("instructions", True):
            tabs.append(("ℹ️ **Instructions**", lambda: display_instructions(form_content)))
        
        if not tabs:
            st.warning("⚠️ No tabs are enabled for this mode. Please contact administrator.")
            return
        
        # Show deadline status
        if not status["open"]:
            st.markdown(f"""
            <div class="error-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">⛔</span>
                    <div style="font-size: 1.1rem; font-weight: 600;">{status['message']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            return
        
        if status["message"]:
            st.markdown(f"""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">⏰</span>
                    <div>{status['message']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        tab_objects = st.tabs([label for label, _ in tabs])
        for i, (_, func) in enumerate(tabs):
            with tab_objects[i]:
                func()
    
    elif form_mode == "lab_manual":
        # MODE C: Lab Manual Submission Mode
        status = get_form_status("lab_manual")
        
        tabs = []
        if tab_visibility.get("form", True):
            tabs.append(("📚 **Lab Manual Submission**", lab_manual_submission_form))
        if tab_visibility.get("instructions", True):
            tabs.append(("ℹ️ **Instructions**", lambda: display_instructions(form_content)))
        
        if not tabs:
            st.warning("⚠️ No tabs are enabled for this mode. Please contact administrator.")
            return
        
        if not status["open"]:
            st.markdown(f"""
            <div class="error-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">⛔</span>
                    <div style="font-size: 1.1rem; font-weight: 600;">{status['message']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            return
        
        if status["message"]:
            st.markdown(f"""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">⏰</span>
                    <div>{status['message']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        tab_objects = st.tabs([label for label, _ in tabs])
        for i, (_, func) in enumerate(tabs):
            with tab_objects[i]:
                func()
    
    elif form_mode == "class_assignment":
        # MODE D: Class Assignment Submission Mode
        status = get_form_status("class_assignment")
        
        tabs = []
        if tab_visibility.get("form", True):
            tabs.append(("📘 **Class Assignment Submission**", class_assignment_submission_form))
        if tab_visibility.get("instructions", True):
            tabs.append(("ℹ️ **Instructions**", lambda: display_instructions(form_content)))
        
        if not tabs:
            st.warning("⚠️ No tabs are enabled for this mode. Please contact administrator.")
            return
        
        if not status["open"]:
            st.markdown(f"""
            <div class="error-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">⛔</span>
                    <div style="font-size: 1.1rem; font-weight: 600;">{status['message']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            return
        
        if status["message"]:
            st.markdown(f"""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">⏰</span>
                    <div>{status['message']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        tab_objects = st.tabs([label for label, _ in tabs])
        for i, (_, func) in enumerate(tabs):
            with tab_objects[i]:
                func()

def display_project_file_submission_form(form_content, config):
    """Display project file submission form with submission status - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">📁 Project File Submission</h2>', unsafe_allow_html=True)
    
    # Check deadline
    status = get_form_status("project_file_submission")
    if not status["open"]:
        st.markdown(f"""
        <div class="error-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">⛔</span>
                <div style="font-size: 1.1rem; font-weight: 600;">{status['message']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if status["message"]:
        st.markdown(f"""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">⏰</span>
                <div>{status['message']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Create a session state for form persistence
    if 'project_files_data' not in st.session_state:
        st.session_state.project_files_data = {
            'group_number': None,
            'group_verified': False,
            'uploaded_files': [],
            'project_name': '',
            'leader_name': '',
            'has_submitted': False
        }
    
    with st.container():
        # Group verification in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">🔍 Group Verification</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        with col1:
            group_number = st.number_input(
                "**Enter Your Group Number***",
                min_value=1,
                step=1,
                value=st.session_state.project_files_data.get('group_number', 1),
                help="Enter the group number you received after project allocation",
                key="project_file_group_number_input"
            )
        
        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            verify_clicked = st.button("🔍 **Verify Group Number**", use_container_width=True, type="primary", key="verify_group_btn")
        
        if verify_clicked:
            # Verify group exists
            groups = load_data(GROUPS_FILE) or []
            group_exists = any(g['group_number'] == group_number and not g.get('deleted', False) for g in groups)
            
            if not group_exists:
                st.error("❌ Group number not found. Please check your group number.")
                st.info("You must have submitted a project allocation first.")
                st.session_state.project_files_data['group_verified'] = False
            else:
                st.session_state.project_files_data['group_verified'] = True
                st.session_state.project_files_data['group_number'] = group_number
                
                # Get group details
                group = next((g for g in groups if g['group_number'] == group_number), None)
                if group:
                    st.session_state.project_files_data['project_name'] = group.get('project_name', 'N/A')
                    leader_name = ""
                    for member in group.get('members', []):
                        if member.get('is_leader'):
                            leader_name = member.get('name', '')
                            break
                    st.session_state.project_files_data['leader_name'] = leader_name
                
                # Check if group has already submitted files
                file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
                group_files = file_submissions.get(str(group_number), [])
                st.session_state.project_files_data['has_submitted'] = len(group_files) > 0
                
                st.success(f"✅ Group {group_number} verified!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # If group is verified, show details and file upload
        if st.session_state.project_files_data['group_verified']:
            group_number = st.session_state.project_files_data['group_number']
            project_name = st.session_state.project_files_data['project_name']
            leader_name = st.session_state.project_files_data['leader_name']
            has_submitted = st.session_state.project_files_data['has_submitted']
            
            # Show group details in a card
            st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📋 Group Details</h3>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div style="background-color: #111827; padding: 1rem; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #9ca3af;">Group Leader</div>
                    <div style="font-weight: 600; font-size: 1.1rem;">{leader_name}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div style="background-color: #111827; padding: 1rem; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #9ca3af;">Project</div>
                    <div style="font-weight: 600; font-size: 1.1rem;">{project_name}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Display submission status in a card
            st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📊 Submission Status</h3>', unsafe_allow_html=True)
            
            file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
            group_files = file_submissions.get(str(group_number), [])
            
            if group_files:
                status_icon = "✅"
                status_text = "Submitted"
                st.markdown(f"""
                <div class="success-card">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.5rem;">{status_icon}</span>
                        <div>
                            <strong style="font-size: 1.1rem;">Status:</strong> {status_text}
                            <p style="margin: 0.5rem 0 0 0;">✅ You have submitted {len(group_files)} file(s) for your project.</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Check if multiple submissions are allowed
                file_settings = load_data(FILE_SUBMISSION_FILE) or {}
                allow_multiple = file_settings.get("allow_multiple_submissions", False)
                
                if not allow_multiple:
                    st.warning("⚠️ **Note:** Multiple submissions are not allowed. You have already submitted your files.")
            else:
                status_icon = "❌"
                status_text = "Not Submitted"
                st.markdown(f"""
                <div class="error-card">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.5rem;">{status_icon}</span>
                        <div>
                            <strong style="font-size: 1.1rem;">Status:</strong> {status_text}
                            <p style="margin: 0.5rem 0 0 0;">Please submit your project files below.</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # File upload section in a card
            st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📎 Upload Files</h3>', unsafe_allow_html=True)
            
            # Load file submission settings
            file_settings = load_data(FILE_SUBMISSION_FILE) or {}
            allowed_formats = file_settings.get("allowed_formats", [".pdf", ".doc", ".docx"])
            max_size_mb = file_settings.get("max_size_mb", 10)
            max_files = file_settings.get("max_files", 5)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            # Convert formats for file_uploader
            file_types = []
            for fmt in allowed_formats:
                if fmt.startswith('.'):
                    file_types.append(fmt[1:])
                else:
                    file_types.append(fmt)
            
            # Check if multiple submissions are allowed
            allow_multiple = file_settings.get("allow_multiple_submissions", False)
            
            # If already submitted and multiple submissions not allowed, disable upload
            if has_submitted and not allow_multiple:
                st.warning("❌ You have already submitted files. Multiple submissions are not allowed.")
                uploaded_files = []
            else:
                uploaded_files = st.file_uploader(
                    f"**Upload your project files***",
                    type=file_types,
                    accept_multiple_files=True,
                    help=f"📁 Allowed formats: {', '.join(allowed_formats)} | 📦 Maximum files: {max_files} | 💾 Maximum file size: {max_size_mb}MB per file",
                    key="project_file_uploader_main"
                )
            
            # Instructions
            st.markdown(f"""
            <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">ℹ️</span>
                    <div>{file_settings.get("instructions", "Please upload your project files in the specified formats.")}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Validate file count and sizes
            valid_files = True
            if uploaded_files:
                # Check file count
                if len(uploaded_files) > max_files:
                    st.error(f"❌ Maximum {max_files} files allowed. You have uploaded {len(uploaded_files)} files.")
                    valid_files = False
                
                # Check file sizes
                for uploaded_file in uploaded_files:
                    if uploaded_file.size > max_size_bytes:
                        st.error(f"❌ '{uploaded_file.name}' exceeds {max_size_mb}MB limit")
                        valid_files = False
            
            # Extra spacing before submit button
            st.markdown('<div class="extra-spacing"></div>', unsafe_allow_html=True)
            
            # Submit files button
            submit_disabled = has_submitted and not allow_multiple
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("📤 **Submit Files**", use_container_width=True, key="submit_project_files_main", disabled=submit_disabled, type="primary"):
                    if not uploaded_files:
                        st.error("❌ Please select at least one file to upload")
                    elif not valid_files:
                        st.error("❌ Please fix file size issues before submitting")
                    else:
                        # Store files in session state temporarily
                        st.session_state.project_files_data['uploaded_files'] = uploaded_files
                        
                        # Save to database
                        if str(group_number) not in file_submissions:
                            file_submissions[str(group_number)] = []
                        
                        for uploaded_file in uploaded_files:
                            file_info = {
                                "filename": uploaded_file.name,
                                "size": uploaded_file.size,
                                "uploaded_at": datetime.now().isoformat(),
                                "project_name": project_name,
                                "group_leader": leader_name,
                                "submission_count": len(file_submissions[str(group_number)]) + 1
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
                        
                        # Update session state
                        st.session_state.project_files_data['has_submitted'] = True
                        st.session_state.project_files_data['uploaded_files'] = []
                        
                        st.success("✅ Files submitted successfully!")
                        st.balloons()
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def display_allocations_table_for_students():
    """Display allocations table for students with project status and group visibility - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">📊 Current Project Allocations</h2>', unsafe_allow_html=True)
    
    # Load data
    groups = load_data(GROUPS_FILE) or []
    projects = load_data(PROJECTS_FILE) or []
    
    # Filter out deleted groups
    active_groups = [g for g in groups if not g.get('deleted', False)]
    
    # Filter active projects (not deleted)
    active_projects = [p for p in projects if not p.get('deleted', False)]
    
    if not active_groups:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">📋</span>
                <div>
                    <strong>No Project Allocations Yet</strong>
                    <p style="margin: 0.5rem 0 0 0;">Be the first to submit your project allocation!</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Create enhanced DataFrame with Project Status
        summary_data = []
        for group in sorted(active_groups, key=lambda x: x.get('group_number', 0)):
            # Find group leader
            group_leader = ""
            for member in group.get('members', []):
                if member.get('is_leader'):
                    group_leader = member.get('name', '')
                    break
            
            # Get project name (could be empty if optional)
            project_name = group.get('project_name', '')
            if not project_name:
                project_name = "No project selected"
            
            # Get project status
            project_status = "Not Selected"
            for project in active_projects:
                if project['name'] == project_name:
                    project_status = project.get('status', 'Not Selected')
                    break
            
            summary_data.append({
                "Group #": group.get('group_number', ''),
                "Project Name": project_name,
                "Project Status": project_status,
                "Group Leader": group_leader,
                "Members": len([m for m in group.get('members', []) if m.get('name', '').strip()])
            })
        
        df_summary = pd.DataFrame(summary_data)
        
        # Display table with enhanced styling
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.dataframe(
            df_summary,
            use_container_width=True,
            column_config={
                "Group #": st.column_config.NumberColumn(width="small", label="Group #"),
                "Project Name": st.column_config.TextColumn(width="large", label="Project Name"),
                "Project Status": st.column_config.TextColumn(
                    width="medium",
                    label="Project Status",
                    help="Project status: Submitted, Not Selected, Under Review, Approved, Rejected"
                ),
                "Group Leader": st.column_config.TextColumn(width="medium", label="Group Leader"),
                "Members": st.column_config.NumberColumn(width="small", label="Members")
            }
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Show project statistics with enhanced information
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📈 Project Statistics</h3>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Groups", len(active_groups), delta=None, delta_color="normal")
    
    with col2:
        # Count groups with submitted projects (status is 'Submitted')
        submitted_groups = len([g for g in active_groups if g.get('status') == 'Submitted'])
        st.metric("Submitted Groups", submitted_groups, delta=None, delta_color="normal")
    
    with col3:
        st.metric("Total Projects", len(active_projects), delta=None, delta_color="normal")
    
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
        
        st.metric("Available Projects", len(available_projects), delta=None, delta_color="normal")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show project status breakdown
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📋 Project Status Breakdown</h3>', unsafe_allow_html=True)
    
    # Count projects by status
    status_counts = {}
    for project in active_projects:
        status = project.get('status', 'Not Selected')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    if status_counts:
        cols = st.columns(min(3, len(status_counts)))
        for idx, (status, count) in enumerate(sorted(status_counts.items())):
            with cols[idx % len(cols)]:
                st.markdown(f"""
                <div style="background-color: #111827; padding: 1rem; border-radius: 8px; text-align: center;">
                    <div style="font-size: 1.2rem; font-weight: 600; color: #e5e7eb;">{count}</div>
                    <div style="font-size: 0.9rem; color: #9ca3af;">{status}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No projects available.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show available projects list with status
    if available_projects:
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">✅ Available Projects for Selection</h3>', unsafe_allow_html=True)
        for project in available_projects:
            st.markdown(f"• **{project['name']}** - Status: {project.get('status', 'Not Selected')}")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="warning-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">⚠️</span>
                <div>No projects available for selection at the moment.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Show recently allocated projects
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">🔄 Recently Allocated Projects</h3>', unsafe_allow_html=True)
    
    # Sort groups by submission date (newest first)
    recent_groups = sorted(active_groups, 
                          key=lambda x: x.get('submission_timestamp', ''),
                          reverse=True)[:5]
    
    if recent_groups:
        for group in recent_groups:
            submission_time = group.get('submission_date', 'Unknown')
            st.markdown(f"• **Group {group['group_number']}** - {group.get('project_name', 'No project selected')} ({submission_time})")
    else:
        st.info("No recent allocations.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_submission_form(form_content, config):
    """Display the submission form - MAIN CONTENT AREA"""
    # Check deadline
    status = get_form_status("project_allocation")
    if not status["open"]:
        st.markdown(f"""
        <div class="error-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">⛔</span>
                <div style="font-size: 1.1rem; font-weight: 600;">{status['message']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if status["message"]:
        st.markdown(f"""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">⏰</span>
                <div>{status['message']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display cover page if enabled
    display_cover_page(form_content)
    
    # Display form header
    display_form_header(form_content)
    
    # Load configuration
    max_members = config.get("max_members", 3)
    project_optional = config.get("project_allocation_project_optional", False)
    
    # Load projects
    projects = load_data(PROJECTS_FILE) or []
    
    if not projects:
        st.warning("No projects available yet. Please contact administrator.")
        return
    
    # Show available projects count BEFORE form
    available_projects = [p for p in projects if p.get('status') == 'Not Selected' and not p.get('deleted', False)]
    st.markdown(f"""
    <div class="info-card">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.2rem;">📊</span>
            <div>
                <strong>Currently Available Projects:</strong> {len(available_projects)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create form
    with st.form("project_allocation_form", clear_on_submit=True):
        # Group Members Information in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">👥 Group Members Information</h3>', unsafe_allow_html=True)
        st.markdown("<p style='color: #9ca3af; margin-bottom: 1rem;'><strong>Note:</strong> Member 1 will be the Group Leader</p>", unsafe_allow_html=True)
        
        # Dynamic member fields based on max_members
        members_data = []
        
        # Member 1 (Group Leader) - Always required
        st.markdown("### 👑 Group Leader (Member 1)")
        col1, col2 = st.columns(2)
        with col1:
            member1_name = st.text_input("**Full Name***", placeholder="Enter full name", key="member1_name")
        with col2:
            member1_roll = st.text_input("**Roll Number***", placeholder="Enter roll number", key="member1_roll")
        st.markdown('</div>', unsafe_allow_html=True)
        
        members_data.append({
            "name": member1_name,
            "roll_no": member1_roll,
            "is_leader": True
        })
        
        # Additional members (up to max_members-1 more)
        if max_members > 1:
            st.markdown('<div style="background-color: #111827; padding: 1rem; border-radius: 8px; margin: 1rem 0;">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Project selection in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📋 Project Selection</h3>', unsafe_allow_html=True)
        if project_optional:
            st.markdown("*Select a project (optional)*")
        else:
            st.markdown("*Select ONE project from the available options below*")
        
        # Get only unselected projects that are not deleted
        available_projects = [p for p in projects if p.get('status') == 'Not Selected' and not p.get('deleted', False)]
        project_options = [f"{p['name']}" for p in available_projects]
        
        if not project_options:
            if project_optional:
                st.info("No projects currently available – you may submit without a project.")
                project_choice = None
            else:
                st.error("❌ All projects have been selected. No available projects at the moment.")
                st.info("Please contact the administrator for more options.")
                project_choice = None
        else:
            # Check for duplicate roll numbers in submissions
            groups = load_data(GROUPS_FILE) or []
            
            # Filter out projects already selected
            selected_projects = set()
            for group in groups:
                if group.get('project_name') and not group.get('deleted', False):
                    selected_projects.add(group['project_name'])
            
            # Only show projects not already selected and not deleted
            final_available_projects = [
                p for p in available_projects 
                if p['name'] not in selected_projects 
                and not p.get('deleted', False)
            ]
            
            if not final_available_projects:
                if project_optional:
                    st.info("No projects currently available – you may submit without a project.")
                    project_choice = None
                else:
                    st.error("❌ All available projects have already been selected by other groups.")
                    project_choice = None
            else:
                project_options_final = [f"{p['name']}" for p in final_available_projects]
                if project_optional:
                    # Add a blank option to allow no selection
                    project_options_final.insert(0, "")
                
                project_choice = st.selectbox(
                    "**Select Your Project**" + ("" if project_optional else "*"),
                    options=project_options_final,
                    help="Choose only one project from the available options" + (" (optional)" if project_optional else ""),
                    format_func=lambda x: "No project selected" if x == "" else x
                )
                
                # Show project count
                st.markdown(f"""
                <div style="background-color: #0c4a6e; padding: 0.75rem; border-radius: 8px; margin: 1rem 0;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.1rem;">📊</span>
                        <div>{len(project_options_final) - (1 if project_optional else 0)} project(s) available for selection</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Show available projects list with status
                if project_options_final:
                    with st.expander("📋 **View Available Projects with Status**", expanded=False):
                        for project in final_available_projects:
                            status_icon = "✅" if project.get('status') == 'Submitted' else "⏳"
                            st.markdown(f"{status_icon} **{project['name']}** - Status: {project.get('status', 'Not Selected')}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Terms and conditions in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">✅ Confirmation</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            agree_terms = st.checkbox("**I confirm that all information provided is accurate***", value=False)
        with col2:
            agree_final = st.checkbox("**I understand this selection is final***", value=False)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Form submission button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "🚀 **Submit Application**",
                use_container_width=True,
                type="primary"
            )
        
        if submitted:
            # Validation
            errors = []
            
            # Check Member 1 (required)
            if not member1_name.strip() or not member1_roll.strip():
                errors.append("❌ Member 1 (Group Leader) name and roll number are required")
            
            # Project selection required only if not optional
            if not project_optional and not project_choice:
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
            
            # Check if project is still available (only if a project was chosen)
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
                    st.markdown(f'<div class="error-card">{error}</div>', unsafe_allow_html=True)
            else:
                # Load existing groups and config
                groups = load_data(GROUPS_FILE) or []
                config = load_data(CONFIG_FILE)
                
                # Create new group with status 'Submitted'
                new_group = {
                    "group_number": config.get("next_group_number", 1),
                    "project_name": project_choice if project_choice else "",  # empty if no project selected
                    "status": "Submitted",
                    "members": members_data,
                    "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "submission_timestamp": datetime.now().isoformat(),
                    "deleted": False
                }
                
                # Add to groups
                groups.append(new_group)
                save_data(groups, GROUPS_FILE)
                
                # Update project status only if a project was selected
                if project_choice:
                    projects_data = load_data(PROJECTS_FILE) or []
                    for project in projects_data:
                        if project['name'] == project_choice:
                            project['selected_by'] = project.get('selected_by', 0) + 1
                            # AUTOMATICALLY UPDATE PROJECT STATUS TO 'Submitted'
                            project['status'] = 'Submitted'
                            project['selected_by_group'] = new_group['group_number']
                            project['selected_at'] = datetime.now().isoformat()
                            break
                    save_data(projects_data, PROJECTS_FILE)
                
                # Update config for next group number
                config['next_group_number'] = config.get('next_group_number', 1) + 1
                save_data(config, CONFIG_FILE)
                
                # Show success message with animation
                st.markdown("""
                <div style="text-align: center; margin: 2rem 0;">
                    <div style="font-size: 4rem; margin-bottom: 1rem;">🎉</div>
                    <h2 style="color: #10b981; margin-bottom: 1rem;">✅ Application Submitted Successfully!</h2>
                </div>
                """, unsafe_allow_html=True)
                st.balloons()
                
                # Thank you page in a card
                st.markdown("""
                <div class="success-card">
                    <h3 style="color: #a7f3d0; margin-bottom: 1.5rem;">🎉 Thank You!</h3>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div style="background-color: #065f46; padding: 1.5rem; border-radius: 10px;">
                        <h4 style="color: #e5e7eb; margin-bottom: 1rem;">📋 Submission Details</h4>
                        <div style="display: grid; gap: 0.75rem;">
                            <div>
                                <div style="font-size: 0.9rem; color: #a7f3d0;">Group Number</div>
                                <div style="font-weight: 600; font-size: 1.2rem; color: #a78bfa;">{new_group['group_number']}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.9rem; color: #a7f3d0;">Selected Project</div>
                                <div style="font-weight: 600;">{project_choice if project_choice else "No project selected"}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.9rem; color: #a7f3d0;">Project Status</div>
                                <div style="font-weight: 600; color: #10b981;">Submitted ✅</div>
                            </div>
                            <div>
                                <div style="font-size: 0.9rem; color: #a7f3d0;">Group Leader</div>
                                <div style="font-weight: 600;">{member1_name}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.9rem; color: #a7f3d0;">Submission Time</div>
                                <div style="font-weight: 600;">{datetime.now().strftime("%Y-%m-%d %I:%M %p")}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div style="background-color: #065f46; padding: 1.5rem; border-radius: 10px;">
                        <h4 style="color: #e5e7eb; margin-bottom: 1rem;">📝 Next Steps</h4>
                        <div style="display: grid; gap: 1rem;">
                            <div style="display: flex; align-items: start; gap: 10px;">
                                <span style="font-size: 1.2rem; color: #a78bfa;">1.</span>
                                <div>
                                    <strong>Save your Group Number</strong>
                                    <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; color: #a7f3d0;">Keep this number for future reference</p>
                                </div>
                            </div>
                            <div style="display: flex; align-items: start; gap: 10px;">
                                <span style="font-size: 1.2rem; color: #a78bfa;">2.</span>
                                <div>
                                    <strong>Administrator will review</strong>
                                    <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; color: #a7f3d0;">Your application will be reviewed by admin</p>
                                </div>
                            </div>
                            <div style="display: flex; align-items: start; gap: 10px;">
                                <span style="font-size: 1.2rem; color: #a78bfa;">3.</span>
                                <div>
                                    <strong>Project status updates</strong>
                                    <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; color: #a7f3d0;">Status will be updated by admin if needed</p>
                                </div>
                            </div>
                            <div style="display: flex; align-items: start; gap: 10px;">
                                <span style="font-size: 1.2rem; color: #a78bfa;">4.</span>
                                <div>
                                    <strong>Contact for changes</strong>
                                    <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; color: #a7f3d0;">Contact administrator if you need to make changes</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("""
                <div style="margin-top: 1.5rem; padding: 1rem; background-color: #065f46; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.2rem;">📱</span>
                        <div>You may close this window now. Your submission has been recorded.</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# ADMIN FUNCTIONS - MAIN CONTENT AREA
# ============================================

def manage_short_urls():
    """Manage short URLs for the form - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">🔗 Short URL Management</h2>', unsafe_allow_html=True)
    
    # Load short URLs
    short_urls = load_data(SHORT_URLS_FILE) or {}
    
    # Get base URL
    base_url = get_base_url()
    
    # URL generation in a card
    with st.container():
        col1 , col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"""
            <div style="background-color: #111827; padding: 1rem; border-radius: 8px;">
                <div style="font-size: 0.9rem; color: #9ca3af;">Base URL</div>
                <div style="font-weight: 600; font-size: 1.1rem; word-break: break-all;">{base_url}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("🔄 **Generate New Short URL**", use_container_width=True, type="primary"):
                short_code = generate_short_code()
                full_url = f"{base_url}/?short={short_code}"
                short_urls[short_code] = {
                    "url": full_url,
                    "created_at": datetime.now().isoformat(),
                    "clicks": 0,
                    "last_accessed": None
                }
                if save_data(short_urls, SHORT_URLS_FILE):
                    st.success(f"✅ New short URL created!")
                    st.rerun()
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # Display existing short URLs
    if short_urls:
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📋 Existing Short URLs</h3>', unsafe_allow_html=True)
        
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
        st.markdown('</div>', unsafe_allow_html=True)
        
        # URL actions in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">🔧 URL Actions</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_code = st.selectbox(
                "**Select URL to manage**",
                options=[""] + list(short_urls.keys())
            )
        
        with col2:
            if selected_code:
                short_url = f"{base_url}/?short={selected_code}"
                st.code(short_url, language="text")
                
                # Delete URL
                if st.button("🗑️ **Delete URL**", type="secondary", use_container_width=True):
                    # Archive before deletion
                    archive_data("short_url", short_urls[selected_code], "Admin deleted short URL")
                    
                    del short_urls[selected_code]
                    if save_data(short_urls, SHORT_URLS_FILE):
                        st.success(f"✅ Short URL {selected_code} deleted!")
                        st.rerun()
        
        # Copy all URLs
        if st.button("📋 **Copy All URLs to Clipboard**", use_container_width=True, type="primary"):
            all_urls = "\n".join([f"{base_url}/?short={code}" for code in short_urls.keys()])
            st.code(all_urls, language="text")
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">🔗</span>
                <div>
                    <strong>No Short URLs Created Yet</strong>
                    <p style="margin: 0.5rem 0 0 0;">Click 'Generate New Short URL' to create one.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def manage_file_submissions():
    """Admin panel to manage and download submitted files - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">📁 Project File Submissions</h2>', unsafe_allow_html=True)
    
    # Admin upload section in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📤 Admin File Upload</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            admin_group_number = st.number_input("**Group Number**", min_value=1, step=1, key="admin_group_upload")
        with col2:
            # Verify group
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("🔍 **Verify Group**", key="verify_admin_group", use_container_width=True, type="primary"):
                groups = load_data(GROUPS_FILE) or []
                group_exists = any(g['group_number'] == admin_group_number and not g.get('deleted', False) for g in groups)
                
                if group_exists:
                    st.session_state.admin_group_verified = True
                    st.session_state.admin_upload_group = admin_group_number
                    st.success(f"✅ Group {admin_group_number} verified!")
                else:
                    st.error("❌ Group not found")
        
        if st.session_state.get('admin_group_verified', False) and st.session_state.get('admin_upload_group') == admin_group_number:
            # Get group details
            groups = load_data(GROUPS_FILE) or []
            group = next((g for g in groups if g['group_number'] == admin_group_number), None)
            
            if group:
                project_name = group.get('project_name', 'N/A')
                leader_name = ""
                for member in group.get('members', []):
                    if member.get('is_leader'):
                        leader_name = member.get('name', '')
                        break
                
                st.markdown(f"""
                <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <div style="font-size: 0.9rem; color: #93c5fd;">Project</div>
                            <div style="font-weight: 600;">{project_name}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #93c5fd;">Leader</div>
                            <div style="font-weight: 600;">{leader_name}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # File upload
                file_settings = load_data(FILE_SUBMISSION_FILE) or {}
                allowed_formats = file_settings.get("allowed_formats", [".pdf", ".doc", ".docx"])
                max_size_mb = file_settings.get("max_size_mb", 10)
                max_files = file_settings.get("max_files", 5)
                
                file_types = []
                for fmt in allowed_formats:
                    if fmt.startswith('.'):
                        file_types.append(fmt[1:])
                    else:
                        file_types.append(fmt)
                
                admin_uploaded_files = st.file_uploader(
                    f"**Upload files for Group {admin_group_number}**",
                    type=file_types,
                    accept_multiple_files=True,
                    help=f"📁 Allowed formats: {', '.join(allowed_formats)} | 📦 Maximum files: {max_files} | 💾 Maximum file size: {max_size_mb}MB each",
                    key="admin_file_uploader"
                )
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if admin_uploaded_files and st.button("📤 **Upload Files as Admin**", use_container_width=True, type="primary"):
                        # Check file count
                        if len(admin_uploaded_files) > max_files:
                            st.error(f"❌ Maximum {max_files} files allowed. You have uploaded {len(admin_uploaded_files)} files.")
                        else:
                            file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
                            
                            if str(admin_group_number) not in file_submissions:
                                file_submissions[str(admin_group_number)] = []
                            
                            for uploaded_file in admin_uploaded_files:
                                file_info = {
                                    "filename": uploaded_file.name,
                                    "size": uploaded_file.size,
                                    "uploaded_at": datetime.now().isoformat(),
                                    "project_name": project_name,
                                    "group_leader": leader_name,
                                    "uploaded_by": "admin"
                                }
                                file_submissions[str(admin_group_number)].append(file_info)
                                
                                # Save file to disk
                                file_dir = os.path.join(DATA_DIR, "submitted_files", str(admin_group_number))
                                Path(file_dir).mkdir(parents=True, exist_ok=True)
                                file_path = os.path.join(file_dir, uploaded_file.name)
                                try:
                                    with open(file_path, 'wb') as f:
                                        f.write(uploaded_file.getbuffer())
                                except Exception as e:
                                    st.error(f"Error saving file {uploaded_file.name}: {e}")
                                    continue
                            
                            save_data(file_submissions, FILE_SUBMISSIONS_FILE)
                            st.success(f"✅ Files uploaded for Group {admin_group_number}!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # Load file submissions data
    file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
    
    if not file_submissions:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">📁</span>
                <div>
                    <strong>No Project Files Submitted Yet</strong>
                    <p style="margin: 0.5rem 0 0 0;">No project files have been submitted yet.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Display all groups with submitted files
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📋 Submission Status Report</h3>', unsafe_allow_html=True)
    
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
        
        # Get last submission time
        last_submission = "Not submitted"
        if group_files:
            submission_times = [f.get('uploaded_at', '') for f in group_files if f.get('uploaded_at')]
            if submission_times:
                try:
                    last_time = max(submission_times)
                    last_submission = datetime.fromisoformat(last_time).strftime("%Y-%m-%d %H:%M")
                except:
                    last_submission = "Unknown"
        
        status_data.append({
            "Group #": group_num,
            "Project": group['project_name'] if group['project_name'] else "No project selected",
            "Group Leader": leader_name,
            "Files Submitted": len(group_files),
            "Status": "✅ Submitted" if len(group_files) > 0 else "❌ Not Submitted",
            "Last Submission": last_submission,
            "Multiple Submissions": "Yes" if len([f for f in group_files if f.get('submission_count', 0) > 1]) > 0 else "No"
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
            "Group #": st.column_config.NumberColumn(width="small", label="Group #"),
            "Project": st.column_config.TextColumn(width="medium", label="Project"),
            "Group Leader": st.column_config.TextColumn(width="medium", label="Group Leader"),
            "Files Submitted": st.column_config.NumberColumn(width="small", label="Files Submitted"),
            "Status": st.column_config.TextColumn(width="medium", label="Status"),
            "Last Submission": st.column_config.TextColumn(width="medium", label="Last Submission"),
            "Multiple Submissions": st.column_config.TextColumn(width="small", label="Multiple")
        }
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show statistics
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📊 Submission Statistics</h3>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_groups = len(active_groups)
        st.metric("Total Groups", total_groups, delta=None, delta_color="normal")
    
    with col2:
        submitted_groups = len([g for g in status_data if g['Files Submitted'] > 0])
        st.metric("Submitted Groups", submitted_groups, delta=None, delta_color="normal")
    
    with col3:
        not_submitted = total_groups - submitted_groups
        st.metric("Not Submitted", not_submitted, delta=None, delta_color="normal")
    
    with col4:
        submission_rate = (submitted_groups / total_groups * 100) if total_groups > 0 else 0
        st.metric("Submission Rate", f"{submission_rate:.1f}%", delta=None, delta_color="normal")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show groups without submission
    not_submitted_groups = [g for g in status_data if g['Files Submitted'] == 0]
    if not_submitted_groups:
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📝 Groups Without Submission</h3>', unsafe_allow_html=True)
        for group in not_submitted_groups:
            st.markdown(f"• **Group {group['Group #']}**: {group['Project']} (Leader: {group['Group Leader']})")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Download functionality
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📥 Download Submitted Files</h3>', unsafe_allow_html=True)
    
    # Display groups with files
    groups_with_files = [g for g in status_data if g['Files Submitted'] > 0]
    
    if not groups_with_files:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">📁</span>
                <div>No files available for download.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Create tabs for download options
        tab1, tab2 = st.tabs(["📦 **Download All Files**", "📁 **Download by Group**"])
        
        with tab1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            # Download all files button
            if st.button("⬇️ **Download All Project Files as ZIP**", use_container_width=True, type="primary"):
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
                        label="📥 **Download All Project Files**",
                        data=zip_buffer,
                        file_name=f"all_project_files_{timestamp}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            # Download by group
            group_options = [f"Group {g['Group #']}" for g in groups_with_files]
            selected_group = st.selectbox("**Select Group**", options=[""] + group_options)
            
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
                        label=f"📥 **Download {selected_group} Files**",
                        data=zip_buffer,
                        file_name=f"{selected_group}_files.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                else:
                    st.info("No files found for this group.")
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Delete functionality
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">🗑️ Delete Files</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        group_to_delete = st.selectbox(
            "**Select group to delete files**",
            options=[""] + [str(g['Group #']) for g in groups_with_files]
        )
    
    with col2:
        if group_to_delete:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("🗑️ **Delete Group Files**", type="secondary", use_container_width=True):
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
    
    st.markdown('</div>', unsafe_allow_html=True)

def manage_lab_manual():
    """Admin panel to manage lab manual submissions - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">📚 Lab Manual Submissions</h2>', unsafe_allow_html=True)
    
    # Admin upload section in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📤 Admin Upload for Lab Manual</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            admin_lab_name = st.text_input("**Student Name**", placeholder="Enter student name", key="admin_lab_name")
        with col2:
            admin_lab_roll = st.text_input("**Roll Number**", placeholder="Enter roll number", key="admin_lab_roll")
        
        # Load lab settings
        lab_settings = load_data(os.path.join(DATA_DIR, "lab_settings.json")) or {}
        allowed_formats = lab_settings.get("allowed_formats", [".pdf", ".doc", ".docx", ".txt"])
        max_size_mb = lab_settings.get("max_size_mb", 5)
        max_files = lab_settings.get("max_files", 1)
        
        file_types = []
        for fmt in allowed_formats:
            if fmt.startswith('.'):
                file_types.append(fmt[1:])
            else:
                file_types.append(fmt)
        
        admin_lab_files = st.file_uploader(
            f"**Upload Lab Manual Files**",
            type=file_types,
            accept_multiple_files=True,
            help=f"📁 Allowed formats: {', '.join(allowed_formats)} | 📦 Maximum files: {max_files} | 💾 Maximum file size: {max_size_mb}MB each",
            key="admin_lab_uploader"
        )
        
        if admin_lab_name and admin_lab_roll and admin_lab_files:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("📤 **Upload as Admin**", use_container_width=True, type="primary"):
                    # Check file count
                    if len(admin_lab_files) > max_files:
                        st.error(f"❌ Maximum {max_files} file(s) allowed. You have uploaded {len(admin_lab_files)} files.")
                    else:
                        # Load existing submissions
                        lab_manual = load_data(LAB_MANUAL_FILE) or []
                        
                        # Check if roll number already exists
                        existing = next((s for s in lab_manual if s.get('roll_no') == admin_lab_roll.strip()), None)
                        if existing:
                            st.error("❌ This roll number already has a submission")
                        else:
                            # Create submission record
                            submission_record = {
                                "name": admin_lab_name.strip(),
                                "roll_no": admin_lab_roll.strip(),
                                "subject_name": "Admin Uploaded",
                                "submission_date": datetime.now().isoformat(),
                                "status": "Submitted",
                                "uploaded_by": "admin",
                                "files": []
                            }
                            
                            # Save files
                            lab_dir = os.path.join(DATA_DIR, "lab_manual")
                            Path(lab_dir).mkdir(parents=True, exist_ok=True)
                            
                            # Sanitize roll number for directory name
                            sanitized_roll_no = sanitize_filename(admin_lab_roll.strip())
                            
                            # Create directory for this submission
                            submission_dir = os.path.join(lab_dir, sanitized_roll_no)
                            Path(submission_dir).mkdir(parents=True, exist_ok=True)
                            
                            for uploaded_file in admin_lab_files:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                sanitized_filename = sanitize_filename(uploaded_file.name)
                                filename = f"{timestamp}_{sanitized_roll_no}_{sanitized_filename}"
                                file_path = os.path.join(submission_dir, filename)
                                
                                with open(file_path, 'wb') as f:
                                    f.write(uploaded_file.getbuffer())
                                
                                submission_record["files"].append({
                                    "filename": filename,
                                    "original_filename": uploaded_file.name,
                                    "file_size": uploaded_file.size
                                })
                            
                            # Save to database
                            lab_manual.append(submission_record)
                            save_data(lab_manual, LAB_MANUAL_FILE)
                            
                            st.success("✅ Lab manual uploaded successfully by admin!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # Load config for subject name
    config = load_data(CONFIG_FILE) or {}
    
    # Subject name configuration in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Subject Configuration</h3>', unsafe_allow_html=True)
        lab_subject_name = st.text_input("**Lab Subject Name**", value=config.get('lab_subject_name', ''))
        
        if st.button("💾 **Save Subject Name**", use_container_width=True, type="primary"):
            config['lab_subject_name'] = lab_subject_name
            if save_data(config, CONFIG_FILE):
                st.success("✅ Subject name saved!")
        
        if lab_subject_name:
            st.markdown(f"""
            <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">📚</span>
                    <div>
                        <strong>Current Subject:</strong> {lab_subject_name}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Load lab manual submissions
    lab_manual = load_data(LAB_MANUAL_FILE) or []
    
    if not lab_manual:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">📚</span>
                <div>
                    <strong>No Lab Manuals Submitted</strong>
                    <p style="margin: 0.5rem 0 0 0;">No lab manuals submitted yet.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 **View Submissions**", "📥 **Download Files**", "🗑️ **Delete Submissions**"])
    
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
                    "Files": len(submission.get('files', [])),
                    "File Size": f"{sum(f.get('file_size', 0) for f in submission.get('files', [])) / 1024:.1f} KB" if submission.get('files') else "N/A",
                    "Submitted": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M'),
                    "Uploaded By": submission.get('uploaded_by', 'Student')
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Statistics
            st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📊 Statistics</h3>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Submissions", len(lab_manual), delta=None, delta_color="normal")
            with col2:
                with_files = len([s for s in lab_manual if s.get('files') and len(s['files']) > 0])
                st.metric("With Files", with_files, delta=None, delta_color="normal")
            with col3:
                total_files = sum(len(s.get('files', [])) for s in lab_manual)
                st.metric("Total Files", total_files, delta=None, delta_color="normal")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        # Download functionality
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">Download All Lab Manuals</h3>', unsafe_allow_html=True)
        
        # Check if there are files to download
        submissions_with_files = [s for s in lab_manual if s.get('files') and len(s['files']) > 0]
        
        if not submissions_with_files:
            st.markdown("""
            <div class="warning-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">⚠️</span>
                    <div>No files to download.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button("📦 **Download All Lab Manuals as ZIP**", use_container_width=True, type="primary"):
                # Create zip of all files
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    lab_dir = os.path.join(DATA_DIR, "lab_manual")
                    if os.path.exists(lab_dir):
                        for submission in submissions_with_files:
                            roll_no = submission.get('roll_no', '')
                            sanitized_roll_no = sanitize_filename(roll_no)
                            submission_dir = os.path.join(lab_dir, sanitized_roll_no)
                            if os.path.exists(submission_dir):
                                for file_info in submission.get('files', []):
                                    filename = file_info.get('filename')
                                    if filename:
                                        file_path = os.path.join(submission_dir, filename)
                                        if os.path.exists(file_path):
                                            # Create a descriptive name for the file
                                            new_filename = f"{roll_no}_{submission['name']}_{file_info.get('original_filename', filename)}"
                                            zip_file.write(file_path, new_filename)
                
                zip_buffer.seek(0)
                
                # Provide download
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ **Download All Lab Manuals**",
                    data=zip_buffer,
                    file_name=f"lab_manuals_{timestamp}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        # Delete functionality
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">🗑️ Delete Submissions</h3>', unsafe_allow_html=True)
        
        roll_numbers = [s['roll_no'] for s in lab_manual]
        selected_roll = st.selectbox(
            "**Select submission to delete**",
            options=[""] + roll_numbers
        )
        
        if selected_roll:
            submission = next((s for s in lab_manual if s['roll_no'] == selected_roll), None)
            if submission:
                st.markdown(f"""
                <div class="warning-card">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.2rem;">⚠️</span>
                        <div>
                            <strong>Delete submission for {submission['name']} ({selected_roll})?</strong>
                            <p style="margin: 0.5rem 0 0 0;">This action cannot be undone.</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🗑️ **Delete Submission**", type="secondary", use_container_width=True):
                    # Archive before deletion
                    archive_data("lab_manual", submission, "Admin deleted lab manual submission")
                    
                    # Remove from data
                    lab_manual = [s for s in lab_manual if s['roll_no'] != selected_roll]
                    save_data(lab_manual, LAB_MANUAL_FILE)
                    
                    # Delete files if exist
                    if submission.get('files'):
                        sanitized_roll_no = sanitize_filename(selected_roll)
                        submission_dir = os.path.join(DATA_DIR, "lab_manual", sanitized_roll_no)
                        if os.path.exists(submission_dir):
                            try:
                                shutil.rmtree(submission_dir)
                            except Exception as e:
                                st.error(f"Error deleting files: {e}")
                    
                    st.success("✅ Submission deleted successfully!")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def manage_class_assignments():
    """Admin panel to manage class assignment submissions - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">📘 Class Assignment Management</h2>', unsafe_allow_html=True)
    
    # Admin upload section in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📤 Admin Upload for Class Assignment</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            admin_class_name = st.text_input("**Student Name**", placeholder="Enter student name", key="admin_class_name")
        with col2:
            admin_class_roll = st.text_input("**Roll Number**", placeholder="Enter roll number", key="admin_class_roll")
        
        config = load_data(CONFIG_FILE) or {}
        current_assignment_no = config.get("current_assignment_no", 1)
        
        admin_assignment_no = st.number_input("**Assignment Number**", min_value=1, value=current_assignment_no, key="admin_assignment_no")
        
        # Load class settings
        class_settings = load_data(os.path.join(DATA_DIR, "class_settings.json")) or {}
        allowed_formats = class_settings.get("allowed_formats", [".pdf", ".doc", ".docx", ".txt"])
        max_size_mb = class_settings.get("max_size_mb", 10)
        max_files = class_settings.get("max_files", 3)
        
        file_types = []
        for fmt in allowed_formats:
            if fmt.startswith('.'):
                file_types.append(fmt[1:])
            else:
                file_types.append(fmt)
        
        admin_class_files = st.file_uploader(
            f"**Upload Assignment Files**",
            type=file_types,
            accept_multiple_files=True,
            help=f"📁 Allowed formats: {', '.join(allowed_formats)} | 📦 Maximum files: {max_files} | 💾 Maximum file size: {max_size_mb}MB each",
            key="admin_class_uploader"
        )
        
        if admin_class_name and admin_class_roll and admin_class_files:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("📤 **Upload as Admin**", use_container_width=True, type="primary"):
                    # Check file count
                    if len(admin_class_files) > max_files:
                        st.error(f"❌ Maximum {max_files} files allowed. You have uploaded {len(admin_class_files)} files.")
                    else:
                        # Load existing submissions
                        class_assignments = load_data(CLASS_ASSIGNMENTS_FILE) or []
                        
                        # Check if this roll number already submitted this assignment
                        existing = next((s for s in class_assignments if s.get('roll_no') == admin_class_roll.strip() and s.get('assignment_no') == admin_assignment_no), None)
                        if existing:
                            st.error("❌ This roll number already has a submission for this assignment")
                        else:
                            # Create submission record
                            submission_record = {
                                "name": admin_class_name.strip(),
                                "roll_no": admin_class_roll.strip(),
                                "course_name": "Admin Uploaded",
                                "assignment_no": admin_assignment_no,
                                "submission_date": datetime.now().isoformat(),
                                "status": "Submitted",
                                "uploaded_by": "admin",
                                "files": []
                            }
                            
                            # Save files
                            class_dir = os.path.join(DATA_DIR, "class_assignments")
                            Path(class_dir).mkdir(parents=True, exist_ok=True)
                            
                            # Sanitize roll number for directory name
                            sanitized_roll_no = sanitize_filename(admin_class_roll.strip())
                            
                            # Create directory for this submission
                            submission_dir = os.path.join(class_dir, f"{sanitized_roll_no}_assignment_{admin_assignment_no}")
                            Path(submission_dir).mkdir(parents=True, exist_ok=True)
                            
                            for uploaded_file in admin_class_files:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                sanitized_filename = sanitize_filename(uploaded_file.name)
                                filename = f"{timestamp}_{sanitized_roll_no}_{admin_assignment_no}_{sanitized_filename}"
                                file_path = os.path.join(submission_dir, filename)
                                
                                with open(file_path, 'wb') as f:
                                    f.write(uploaded_file.getbuffer())
                                
                                submission_record["files"].append({
                                    "filename": filename,
                                    "original_filename": uploaded_file.name,
                                    "file_size": uploaded_file.size,
                                    "file_type": uploaded_file.type
                                })
                            
                            # Save to database
                            class_assignments.append(submission_record)
                            save_data(class_assignments, CLASS_ASSIGNMENTS_FILE)
                            
                            st.success("✅ Assignment uploaded successfully by admin!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # Load config for course name
    config = load_data(CONFIG_FILE) or {}
    
    # Assignment number control in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Assignment Number Control</h3>', unsafe_allow_html=True)
        current_assignment_no = st.number_input(
            "**Current Assignment Number**",
            min_value=1,
            value=config.get('current_assignment_no', 1),
            help="This number will be shown to students as the current assignment"
        )
        
        if st.button("💾 **Save Assignment Number**", use_container_width=True, type="primary"):
            config['current_assignment_no'] = current_assignment_no
            if save_data(config, CONFIG_FILE):
                st.success(f"✅ Assignment number set to {current_assignment_no}!")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Course name configuration in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Course Configuration</h3>', unsafe_allow_html=True)
        course_name = st.text_input("**Course/Subject Name**", value=config.get('course_name', ''))
        
        if st.button("💾 **Save Course Name**", use_container_width=True, type="primary"):
            config['course_name'] = course_name
            if save_data(config, CONFIG_FILE):
                st.success("✅ Course name saved!")
        
        if course_name:
            st.markdown(f"""
            <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">📚</span>
                    <div>
                        <strong>Current Course:</strong> {course_name}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Load class assignments
    class_assignments = load_data(CLASS_ASSIGNMENTS_FILE) or []
    
    if not class_assignments:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">📘</span>
                <div>
                    <strong>No Class Assignments Submitted</strong>
                    <p style="margin: 0.5rem 0 0 0;">No class assignments submitted yet.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 **View Submissions**", "📥 **Download Files**", "🗑️ **Delete Submissions**"])
    
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
                    "Files": len(submission.get('files', [])),
                    "File Size": f"{sum(f.get('file_size', 0) for f in submission.get('files', [])) / 1024:.1f} KB" if submission.get('files') else "N/A",
                    "Submitted": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M'),
                    "Uploaded By": submission.get('uploaded_by', 'Student')
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Statistics
            st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📊 Statistics</h3>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Submissions", len(class_assignments), delta=None, delta_color="normal")
            with col2:
                unique_students = len(set([s['roll_no'] for s in class_assignments]))
                st.metric("Unique Students", unique_students, delta=None, delta_color="normal")
            with col3:
                assignments_count = len(set([s['assignment_no'] for s in class_assignments]))
                st.metric("Assignments", assignments_count, delta=None, delta_color="normal")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        # Download functionality
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">Download All Class Assignments</h3>', unsafe_allow_html=True)
        
        # Check if there are files to download
        submissions_with_files = [s for s in class_assignments if s.get('files') and len(s['files']) > 0]
        
        if not submissions_with_files:
            st.markdown("""
            <div class="warning-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">⚠️</span>
                    <div>No files to download.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📦 **Download All as ZIP**", use_container_width=True, type="primary"):
                    # Create zip of all files
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        class_dir = os.path.join(DATA_DIR, "class_assignments")
                        if os.path.exists(class_dir):
                            for submission in submissions_with_files:
                                roll_no = submission.get('roll_no', '')
                                assignment_no = submission.get('assignment_no', '')
                                sanitized_roll_no = sanitize_filename(roll_no)
                                submission_dir = os.path.join(class_dir, f"{sanitized_roll_no}_assignment_{assignment_no}")
                                if os.path.exists(submission_dir):
                                    for file_info in submission.get('files', []):
                                        filename = file_info.get('filename')
                                        if filename:
                                            file_path = os.path.join(submission_dir, filename)
                                            if os.path.exists(file_path):
                                                # Create a descriptive name for the file
                                                new_filename = f"Assignment_{assignment_no}_{roll_no}_{submission['name']}_{file_info.get('original_filename', filename)}"
                                                zip_file.write(file_path, new_filename)
                    
                    zip_buffer.seek(0)
                    
                    # Provide download
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="⬇️ **Download ZIP File**",
                        data=zip_buffer,
                        file_name=f"class_assignments_{timestamp}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            
            with col2:
                if st.button("📊 **Export to CSV**", use_container_width=True, type="primary"):
                    if class_assignments:
                        # Convert to DataFrame
                        export_data = []
                        for submission in class_assignments:
                            export_data.append({
                                "Name": submission.get('name', ''),
                                "Roll Number": submission.get('roll_no', ''),
                                "Course": submission.get('course_name', ''),
                                "Assignment No": submission.get('assignment_no', ''),
                                "Files Count": len(submission.get('files', [])),
                                "Total File Size": sum(f.get('file_size', 0) for f in submission.get('files', [])),
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
                            label="⬇️ **Download CSV File**",
                            data=csv_buffer.getvalue(),
                            file_name=f"class_assignments_{timestamp}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        # Delete functionality
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">🗑️ Delete Submissions</h3>', unsafe_allow_html=True)
        
        # Options for deletion
        delete_option = st.radio(
            "**Delete Options:**",
            ["Delete by Roll Number", "Delete by Assignment Number", "Delete All"]
        )
        
        if delete_option == "Delete by Roll Number":
            roll_numbers = list(set([s['roll_no'] for s in class_assignments]))
            selected_roll = st.selectbox("**Select Roll Number**", options=[""] + roll_numbers)
            
            if selected_roll:
                submissions_to_delete = [s for s in class_assignments if s['roll_no'] == selected_roll]
                st.markdown(f"""
                <div class="warning-card">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.2rem;">⚠️</span>
                        <div>Found {len(submissions_to_delete)} submission(s) for roll number {selected_roll}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if submissions_to_delete:
                    if st.button("🗑️ **Delete Submissions**", type="secondary", use_container_width=True):
                        # Archive before deletion
                        for submission in submissions_to_delete:
                            archive_data("class_assignment", submission, f"Admin deleted class assignment for {selected_roll}")
                        
                        # Remove from data
                        class_assignments = [s for s in class_assignments if s['roll_no'] != selected_roll]
                        save_data(class_assignments, CLASS_ASSIGNMENTS_FILE)
                        
                        # Delete files
                        for submission in submissions_to_delete:
                            assignment_no = submission.get('assignment_no', '')
                            sanitized_roll_no = sanitize_filename(selected_roll)
                            submission_dir = os.path.join(DATA_DIR, "class_assignments", f"{sanitized_roll_no}_assignment_{assignment_no}")
                            if os.path.exists(submission_dir):
                                try:
                                    shutil.rmtree(submission_dir)
                                except Exception as e:
                                    st.error(f"Error deleting files for {selected_roll}: {e}")
                        
                        st.success(f"✅ All submissions for {selected_roll} deleted successfully!")
                        st.rerun()
        
        elif delete_option == "Delete by Assignment Number":
            assignment_nos = list(set([s['assignment_no'] for s in class_assignments]))
            selected_assignment = st.selectbox("**Select Assignment Number**", options=[""] + [str(n) for n in assignment_nos])
            
            if selected_assignment:
                selected_assignment = int(selected_assignment)
                submissions_to_delete = [s for s in class_assignments if s['assignment_no'] == selected_assignment]
                st.markdown(f"""
                <div class="warning-card">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.2rem;">⚠️</span>
                        <div>Found {len(submissions_to_delete)} submission(s) for assignment {selected_assignment}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if submissions_to_delete:
                    if st.button("🗑️ **Delete Submissions**", type="secondary", use_container_width=True):
                        # Archive before deletion
                        for submission in submissions_to_delete:
                            archive_data("class_assignment", submission, f"Admin deleted assignment {selected_assignment}")
                        
                        # Remove from data
                        class_assignments = [s for s in class_assignments if s['assignment_no'] != selected_assignment]
                        save_data(class_assignments, CLASS_ASSIGNMENTS_FILE)
                        
                        # Delete files
                        for submission in submissions_to_delete:
                            roll_no = submission.get('roll_no', '')
                            sanitized_roll_no = sanitize_filename(roll_no)
                            submission_dir = os.path.join(DATA_DIR, "class_assignments", f"{sanitized_roll_no}_assignment_{selected_assignment}")
                            if os.path.exists(submission_dir):
                                try:
                                    shutil.rmtree(submission_dir)
                                except Exception as e:
                                    st.error(f"Error deleting files for {roll_no}: {e}")
                        
                        st.success(f"✅ All submissions for assignment {selected_assignment} deleted successfully!")
                        st.rerun()
        
        elif delete_option == "Delete All":
            st.markdown("""
            <div class="error-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">⚠️</span>
                    <div>
                        <strong>Warning: This will delete ALL class assignment submissions!</strong>
                        <p style="margin: 0.5rem 0 0 0;">This action cannot be undone.</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            confirm = st.checkbox("**I understand this action cannot be undone**")
            
            if confirm:
                if st.button("🗑️ **Delete All Submissions**", type="secondary", use_container_width=True):
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
        
        st.markdown('</div>', unsafe_allow_html=True)

def manage_form_settings():
    """Admin interface to manage form settings including deadlines - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">📝 Form Settings & Deadlines</h2>', unsafe_allow_html=True)
    
    # Load current form content and config
    form_content = load_data(FORM_CONTENT_FILE) or {}
    config = load_data(CONFIG_FILE) or {}
    deadlines = load_data(DEADLINES_FILE) or {}
    
    # Mode selection in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">🔄 Submission Mode Configuration</h3>', unsafe_allow_html=True)
        
        form_mode = st.selectbox(
            "**Select Active Mode**",
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
            st.markdown("""
            <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">🔧</span>
                    <div><strong>Project Allocation Mode Settings</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            allow_edit = st.checkbox(
                "**Allow students to edit allocation details**",
                value=config.get("allow_allocation_edit", False),
                help="When enabled, students can modify their group/project details"
            )
            config["allow_allocation_edit"] = allow_edit
            
            project_optional = st.checkbox(
                "**Make project selection optional**",
                value=config.get("project_allocation_project_optional", False),
                help="When enabled, students can submit the allocation form without selecting a project"
            )
            config["project_allocation_project_optional"] = project_optional
        
        elif form_mode == "project_file_submission":
            st.markdown("""
            <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">🔧</span>
                    <div><strong>Project File Submission Mode Settings</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            submission_open = st.checkbox(
                "**Open file submission**",
                value=config.get("project_file_submission_open", False),
                help="When enabled, students can submit project files"
            )
            config["project_file_submission_open"] = submission_open
            
            if submission_open:
                # File submission settings
                file_settings = load_data(FILE_SUBMISSION_FILE) or {}
                
                st.markdown("<hr style='border: 1px solid #374151; margin: 1.5rem 0;'>", unsafe_allow_html=True)
                st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">File Upload Settings</h4>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    # Allowed formats
                    default_formats = [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".zip", ".rar"]
                    allowed_formats = st.multiselect(
                        "**Allowed File Formats**",
                        options=default_formats,
                        default=file_settings.get("allowed_formats", default_formats)
                    )
                    
                    # Max files
                    max_files = st.number_input(
                        "**Maximum Number of Files**",
                        min_value=1,
                        max_value=20,
                        value=file_settings.get("max_files", 5),
                        help="Maximum number of files a group can upload"
                    )
                
                with col2:
                    # Max file size
                    max_size = st.slider(
                        "**Maximum File Size (MB)**",
                        min_value=1,
                        max_value=100,
                        value=file_settings.get("max_size_mb", 10)
                    )
                    
                    # Allow multiple submissions
                    allow_multiple = st.checkbox(
                        "**Allow Multiple Submissions**",
                        value=file_settings.get("allow_multiple_submissions", False),
                        help="Allow groups to submit files multiple times"
                    )
                
                # Instructions
                instructions = st.text_area(
                    "**Upload Instructions**",
                    value=file_settings.get("instructions", "Please upload your project files in the specified formats."),
                    height=100
                )
                
                if st.button("💾 **Save File Settings**", key="save_file_settings", use_container_width=True, type="primary"):
                    file_settings = {
                        "allowed_formats": allowed_formats,
                        "max_size_mb": max_size,
                        "max_files": max_files,
                        "allow_multiple_submissions": allow_multiple,
                        "instructions": instructions
                    }
                    if save_data(file_settings, FILE_SUBMISSION_FILE):
                        st.success("✅ File settings saved!")
        
        elif form_mode == "lab_manual":
            st.markdown("""
            <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">🔧</span>
                    <div><strong>Lab Manual Mode Settings</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            lab_open = st.checkbox(
                "**Open lab manual submission**",
                value=config.get("lab_manual_open", False),
                help="When enabled, students can submit lab manuals"
            )
            config["lab_manual_open"] = lab_open
            
            file_required = st.checkbox(
                "**File upload required**",
                value=config.get("lab_file_upload_required", False),
                help="When enabled, students must upload a file"
            )
            config["lab_file_upload_required"] = file_required
            
            # Lab manual file settings
            lab_settings = load_data(os.path.join(DATA_DIR, "lab_settings.json")) or {}
            
            st.markdown("<hr style='border: 1px solid #374151; margin: 1.5rem 0;'>", unsafe_allow_html=True)
            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Lab Manual File Settings</h4>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                lab_allowed_formats = st.multiselect(
                    "**Allowed File Formats for Lab Manual**",
                    options=[".pdf", ".doc", ".docx", ".txt", ".zip", ".rar"],
                    default=lab_settings.get("allowed_formats", [".pdf", ".doc", ".docx", ".txt"])
                )
            with col2:
                lab_max_files = st.number_input(
                    "**Maximum Number of Files for Lab Manual**",
                    min_value=1,
                    max_value=10,
                    value=lab_settings.get("max_files", 1),
                    help="Maximum number of files a student can upload"
                )
            
            lab_max_size = st.slider(
                "**Maximum File Size for Lab Manual (MB)**",
                min_value=1,
                max_value=50,
                value=lab_settings.get("max_size_mb", 5)
            )
            
            if st.button("💾 **Save Lab File Settings**", key="save_lab_settings", use_container_width=True, type="primary"):
                lab_settings = {
                    "allowed_formats": lab_allowed_formats,
                    "max_size_mb": lab_max_size,
                    "max_files": lab_max_files
                }
                if save_data(lab_settings, os.path.join(DATA_DIR, "lab_settings.json")):
                    st.success("✅ Lab file settings saved!")
        
        elif form_mode == "class_assignment":
            st.markdown("""
            <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">🔧</span>
                    <div><strong>Class Assignment Mode Settings</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            assignment_open = st.checkbox(
                "**Open class assignment submission**",
                value=config.get("class_assignment_open", False),
                help="When enabled, students can submit class assignments"
            )
            config["class_assignment_open"] = assignment_open
            
            # Class assignment file settings
            class_settings = load_data(os.path.join(DATA_DIR, "class_settings.json")) or {}
            
            st.markdown("<hr style='border: 1px solid #374151; margin: 1.5rem 0;'>", unsafe_allow_html=True)
            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Class Assignment File Settings</h4>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                class_allowed_formats = st.multiselect(
                    "**Allowed File Formats for Class Assignments**",
                    options=[".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".zip", ".rar", ".txt"],
                    default=class_settings.get("allowed_formats", [".pdf", ".doc", ".docx", ".txt"])
                )
            with col2:
                class_max_files = st.number_input(
                    "**Maximum Number of Files for Class Assignments**",
                    min_value=1,
                    max_value=10,
                    value=class_settings.get("max_files", 3),
                    help="Maximum number of files a student can upload"
                )
            
            class_max_size = st.slider(
                "**Maximum File Size for Class Assignments (MB)**",
                min_value=1,
                max_value=100,
                value=class_settings.get("max_size_mb", 10)
            )
            
            if st.button("💾 **Save Class File Settings**", key="save_class_settings", use_container_width=True, type="primary"):
                class_settings = {
                    "allowed_formats": class_allowed_formats,
                    "max_size_mb": class_max_size,
                    "max_files": class_max_files
                }
                if save_data(class_settings, os.path.join(DATA_DIR, "class_settings.json")):
                    st.success("✅ Class file settings saved!")
        
        # Save mode configuration
        if st.button("💾 **Save Mode Configuration**", key="save_mode", use_container_width=True, type="primary"):
            config["form_mode"] = form_mode
            if save_data(config, CONFIG_FILE):
                st.success(f"✅ Mode set to: {form_mode.replace('_', ' ').title()}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # NEW: Tab Visibility Settings
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📑 Tab Visibility Settings</h3>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">ℹ️</span>
                <div>Enable or disable tabs shown to students for each mode. Changes take effect immediately.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize tab visibility if not present
        if "tab_visibility" not in config:
            config["tab_visibility"] = {
                "project_allocation": {"form": True, "allocations": True, "instructions": True},
                "project_file_submission": {"form": True, "allocations": True, "instructions": True},
                "lab_manual": {"form": True, "instructions": True},
                "class_assignment": {"form": True, "instructions": True}
            }
        
        visibility = config["tab_visibility"]
        
        # Project Allocation tabs
        with st.expander("📋 **Project Allocation Mode Tabs**", expanded=False):
            pa = visibility.get("project_allocation", {})
            pa["form"] = st.checkbox("Show 'Project Selection Form' tab", value=pa.get("form", True), key="pa_form")
            pa["allocations"] = st.checkbox("Show 'View Allocations' tab", value=pa.get("allocations", True), key="pa_alloc")
            pa["instructions"] = st.checkbox("Show 'Instructions' tab", value=pa.get("instructions", True), key="pa_inst")
            visibility["project_allocation"] = pa
        
        # Project File Submission tabs
        with st.expander("📁 **Project File Submission Mode Tabs**", expanded=False):
            pfs = visibility.get("project_file_submission", {})
            pfs["form"] = st.checkbox("Show 'Submit Files' tab", value=pfs.get("form", True), key="pfs_form")
            pfs["allocations"] = st.checkbox("Show 'View Allocations' tab", value=pfs.get("allocations", True), key="pfs_alloc")
            pfs["instructions"] = st.checkbox("Show 'Instructions' tab", value=pfs.get("instructions", True), key="pfs_inst")
            visibility["project_file_submission"] = pfs
        
        # Lab Manual tabs
        with st.expander("📚 **Lab Manual Mode Tabs**", expanded=False):
            lm = visibility.get("lab_manual", {})
            lm["form"] = st.checkbox("Show 'Lab Manual Submission' tab", value=lm.get("form", True), key="lm_form")
            lm["instructions"] = st.checkbox("Show 'Instructions' tab", value=lm.get("instructions", True), key="lm_inst")
            visibility["lab_manual"] = lm
        
        # Class Assignment tabs
        with st.expander("📘 **Class Assignment Mode Tabs**", expanded=False):
            ca = visibility.get("class_assignment", {})
            ca["form"] = st.checkbox("Show 'Class Assignment Submission' tab", value=ca.get("form", True), key="ca_form")
            ca["instructions"] = st.checkbox("Show 'Instructions' tab", value=ca.get("instructions", True), key="ca_inst")
            visibility["class_assignment"] = ca
        
        # Save tab visibility
        if st.button("💾 **Save Tab Visibility Settings**", key="save_tab_visibility", use_container_width=True, type="primary"):
            config["tab_visibility"] = visibility
            if save_data(config, CONFIG_FILE):
                st.success("✅ Tab visibility settings saved!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # DEADLINE SETTINGS
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">⏰ Form Deadline Settings</h3>', unsafe_allow_html=True)
    
    deadline_types = [
        ("project_allocation", "Project Allocation"),
        ("project_file_submission", "Project File Submission"),
        ("lab_manual", "Lab Manual Submission"),
        ("class_assignment", "Class Assignment Submission")
    ]
    
    for form_type, form_name in deadline_types:
        with st.expander(f"📅 **{form_name} Deadline**", expanded=False):
            form_deadline = deadlines.get(form_type, {})
            
            enabled = st.checkbox(f"**Enable deadline for {form_name}**", 
                                 value=form_deadline.get("enabled", False),
                                 key=f"deadline_enabled_{form_type}")
            
            if enabled:
                # Date and time input
                col1, col2 = st.columns(2)
                with col1:
                    deadline_date = st.date_input(f"**Deadline Date**", 
                                                  value=datetime.now() + timedelta(days=7),
                                                  key=f"deadline_date_{form_type}")
                with col2:
                    deadline_time = st.time_input(f"**Deadline Time**", 
                                                  value=datetime.now().time(),
                                                  key=f"deadline_time_{form_type}")
                
                # Combine date and time
                deadline_datetime = datetime.combine(deadline_date, deadline_time)
                
                # Custom message
                custom_message = st.text_input(f"**Custom Deadline Message**",
                                              value=form_deadline.get("message", ""),
                                              placeholder=f"Submission closes on {deadline_datetime.strftime('%Y-%m-%d %H:%M')}",
                                              key=f"deadline_msg_{form_type}")
                
                # Save button for this deadline
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button(f"💾 **Save {form_name} Deadline**", key=f"save_{form_type}", use_container_width=True, type="primary"):
                        deadlines[form_type] = {
                            "enabled": True,
                            "datetime": deadline_datetime.isoformat(),
                            "message": custom_message
                        }
                        if save_data(deadlines, DEADLINES_FILE):
                            st.success(f"✅ {form_name} deadline saved!")
            
            elif not enabled and form_deadline.get("enabled", False):
                # Disable deadline
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button(f"🗑️ **Remove {form_name} Deadline**", key=f"remove_{form_type}", use_container_width=True, type="secondary"):
                        deadlines[form_type] = {"enabled": False, "datetime": "", "message": ""}
                        if save_data(deadlines, DEADLINES_FILE):
                            st.success(f"✅ {form_name} deadline removed!")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # Publish/Unpublish toggle in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📢 Publication Settings</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            form_published = st.toggle(
                "**Publish Form for Students**",
                value=config.get("form_published", True),
                help="When off, students will see a maintenance message"
            )
        
        with col2:
            if st.button("💾 **Save Publication Status**", use_container_width=True, type="primary"):
                config['form_published'] = form_published
                if save_data(config, CONFIG_FILE):
                    status = "published" if form_published else "unpublished"
                    st.success(f"✅ Form {status} successfully!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # COVER PAGE CONFIGURATION SECTION in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📋 Cover Page Configuration</h3>', unsafe_allow_html=True)
        
        # Load current cover page settings
        cover = form_content.get("cover_page", {})
        
        # Enable/disable cover page
        cover_enabled = st.checkbox(
            "**Enable Cover Page**",
            value=cover.get("enabled", True),
            help="Show/hide cover page in student form"
        )
        
        # Cover page title
        cover_title = st.text_input(
            "**Cover Page Title**",
            value=cover.get("title", "🎓Project Allocation"),
            help="Title displayed on cover page"
        )
        
        # Background and text colors
        col1, col2 = st.columns(2)
        with col1:
            bg_color = st.color_picker(
                "**Background Color**",
                value=cover.get("background_color", "#1f2937"),
                help="Background color for cover page"
            )
        with col2:
            text_color = st.color_picker(
                "**Text Color**",
                value=cover.get("text_color", "#e5e7eb"),
                help="Text color for cover page"
            )
        
        # Save cover page button
        if st.button("💾 **Save Cover Page Settings**", key="save_cover_page", use_container_width=True, type="primary"):
            form_content["cover_page"] = {
                "enabled": cover_enabled,
                "title": cover_title,
                "background_color": bg_color,
                "text_color": text_color,
                "last_updated": datetime.now().isoformat()
            }
            
            if save_data(form_content, FORM_CONTENT_FILE):
                st.success("✅ Cover page settings saved successfully!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # FORM HEADER CONFIGURATION SECTION in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📋 Form Header Configuration</h3>', unsafe_allow_html=True)
        
        # Load current form header
        form_header = form_content.get("form_header", {})
        
        # Form title
        form_title = st.text_input(
            "**Form Title**",
            value=form_header.get("title", "Project Selection Form"),
            help="Title displayed at the top of the form"
        )
        
        # Form description
        form_description = st.text_area(
            "**Form Description**",
            value=form_header.get("description", "Please fill in all required fields to submit your project group allocation. All fields marked with * are mandatory."),
            height=100,
            help="Description displayed below the form title"
        )
        
        # Contact settings
        col3, col4 = st.columns(2)
        with col3:
            show_contact = st.checkbox(
                "**Show Contact Email**",
                value=form_header.get("show_contact", True),
                help="Show contact email to students"
            )
        with col4:
            contact_email = st.text_input(
                "**Contact Email**",
                value=form_header.get("contact_email", "coal@university.edu"),
                help="Email address for student queries"
            )
        
        # Save form header button
        if st.button("💾 **Save Form Header**", key="save_form_header", use_container_width=True, type="primary"):
            form_content["form_header"] = {
                "title": form_title,
                "description": form_description,
                "show_deadline": False,
                "deadline": "",
                "show_contact": show_contact,
                "contact_email": contact_email,
                "last_updated": datetime.now().isoformat()
            }
            
            if save_data(form_content, FORM_CONTENT_FILE):
                st.success("✅ Form header saved successfully!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # Instructions editing in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">📋 Instructions Configuration</h3>', unsafe_allow_html=True)
        
        # Load current instructions
        instructions = form_content.get("instructions", {})
        
        # Instructions visibility settings - FIXED WITH ALL FOUR OPTIONS
        st.markdown("**Visibility Settings:**")
        col1, col2 = st.columns(2)
        with col1:
            show_in_allocation = st.checkbox(
                "**Show in Project Allocation Mode**",
                value=instructions.get("visibility", {}).get("project_allocation", True),
                help="Show instructions when in project allocation mode"
            )
            show_in_file_submission = st.checkbox(
                "**Show in File Submission Mode**",
                value=instructions.get("visibility", {}).get("project_file_submission", True),
                help="Show instructions when in project file submission mode"
            )
        with col2:
            show_in_lab = st.checkbox(
                "**Show in Lab Manual Mode**",
                value=instructions.get("visibility", {}).get("lab_manual", True),
                help="Show instructions when in lab manual mode"
            )
            show_in_class = st.checkbox(
                "**Show in Class Assignment Mode**",
                value=instructions.get("visibility", {}).get("class_assignment", True),
                help="Show instructions when in class assignment mode"
            )
        
        # Enable/disable instructions
        instructions_enabled = st.checkbox(
            "**Enable Instructions**",
            value=instructions.get("enabled", True),
            help="Enable/disable instructions system"
        )
        
        # Instructions title
        instructions_title = st.text_input(
            "**Instructions Tab Title**",
            value=instructions.get("title", "ℹ️ Instructions & Guidelines"),
            help="Title displayed on instructions tab"
        )
        
        # Instructions content (Markdown editor)
        st.markdown("**Instructions Content (Markdown Supported)**")
        instructions_content = st.text_area(
            "**Instructions**",
            value=instructions.get("content", """# Instructions & Guidelines

## Submission Process

### Step-by-Step Guide

1. **Form Your Group**
   - Minimum 1 member required (Group Leader)
   - Maximum members as set by admin
   - First member is Group Leader
   - All members should have unique roll numbers

2. **Select a Project** (if required)
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
            "**Additional Notes (Optional)**",
            value=instructions.get("additional_notes", ""),
            height=100,
            help="Additional information shown below instructions"
        )
        
        # Save button for instructions
        if st.button("💾 **Save Instructions**", key="save_instructions", use_container_width=True, type="primary"):
            form_content["instructions"] = {
                "enabled": instructions_enabled,
                "title": instructions_title,
                "content": instructions_content,
                "additional_notes": additional_notes,
                "visibility": {
                    "project_allocation": show_in_allocation,
                    "project_file_submission": show_in_file_submission,
                    "lab_manual": show_in_lab,
                    "class_assignment": show_in_class
                },
                "last_updated": datetime.now().isoformat()
            }
            if save_data(form_content, FORM_CONTENT_FILE):
                st.success("✅ Instructions saved!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 2px solid #374151; border-radius: 5px; margin: 2rem 0;'>", unsafe_allow_html=True)
    
    # Reset to defaults button in a card
    with st.container():
        if st.button("🔄 **Reset to Default Content**", type="secondary", use_container_width=True):
            # Reload default form content
            init_files()
            st.success("✅ Form content reset to defaults!")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def manage_project_section():
    """Project management section - MAIN CONTENT AREA WITH DELETE AND UPDATE OPTIONS"""
    st.markdown('<h2 class="sub-header">📋 Project Management</h2>', unsafe_allow_html=True)
    
    # Add new project in a card
    with st.expander("➕ **Add New Project**", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_project_name = st.text_input("**Project Name**")
        with col2:
            new_project_status = st.selectbox("**Status**", ["Not Selected", "Submitted", "Under Review", "Approved", "Rejected"])
        
        if st.button("**Add Project**", key="add_project", use_container_width=True, type="primary"):
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
                            st.success(f"✅ Project '{new_project_name}' reactivated successfully!")
                    else:
                        st.error("❌ Project with this name already exists!")
                else:
                    projects.append({
                        "name": new_project_name,
                        "status": new_project_status,
                        "selected_by": 0,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "deleted": False
                    })
                    if save_data(projects, PROJECTS_FILE):
                        st.success(f"✅ Project '{new_project_name}' added successfully!")
                        st.rerun()
            else:
                st.error("❌ Please enter a project name")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display and manage projects
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">Project List</h3>', unsafe_allow_html=True)
    projects = load_data(PROJECTS_FILE) or []
    active_projects = [p for p in projects if not p.get('deleted', False)]
    
    if active_projects:
        # Display each project with edit and delete options
        for i, project in enumerate(active_projects):
            with st.container():
                # st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 2, 2])
                
                with col1:
                    st.markdown(f"**{project['name']}**")
                
                with col2:
                    # Project status with color coding
                    status = project.get('status', 'Not Selected')
                    status_color = {
                        'Not Selected': '#9ca3af',
                        'Submitted': '#3b82f6',
                        'Under Review': '#f59e0b',
                        'Approved': '#10b981',
                        'Rejected': '#ef4444'
                    }.get(status, '#9ca3af')
                    
                    st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{status}</span>", 
                              unsafe_allow_html=True)
                
                with col3:
                    # Count groups that have selected this project
                    groups = load_data(GROUPS_FILE) or []
                    selected_by = len([g for g in groups if g['project_name'] == project['name'] and not g.get('deleted', False)])
                    st.markdown(f"{selected_by} group(s)")
                
                with col4:
                    # Show group numbers
                    groups = load_data(GROUPS_FILE) or []
                    group_nums = [str(g['group_number']) for g in groups if g['project_name'] == project['name'] and not g.get('deleted', False)]
                    st.markdown(", ".join(group_nums) if group_nums else "None")
                
                with col5:
                    st.markdown(project.get('created_at', ''))
                
                with col6:
                    # Edit and Delete buttons in a row
                    edit_col, delete_col = st.columns(2)
                    
                    with edit_col:
                        if st.button("✏️ **Edit**", key=f"edit_project_{i}", use_container_width=True):
                            st.session_state[f'editing_project_{i}'] = not st.session_state.get(f'editing_project_{i}', False)
                    
                    with delete_col:
                        if st.button("🗑️", key=f"delete_project_{i}", use_container_width=True, type="secondary"):
                            if selected_by > 0:
                                st.markdown(f"""
                                <div class="error-card inline-error">
                                    ❌ Cannot delete! Project is selected by {selected_by} group(s).
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                # Mark project as deleted
                                for j, p in enumerate(projects):
                                    if p['name'] == project['name']:
                                        # Add to deleted items for visibility
                                        add_to_deleted_items("project", p, "Admin deleted from project management")
                                        
                                        projects[j]['deleted'] = True
                                        projects[j]['deleted_at'] = datetime.now().isoformat()
                                        projects[j]['deleted_reason'] = "Admin deleted from project management"
                                        break
                                
                                if save_data(projects, PROJECTS_FILE):
                                    st.success(f"✅ Project '{project['name']}' deleted successfully!")
                                    st.rerun()
                
                # Edit form (shown when edit button is clicked)
                if st.session_state.get(f'editing_project_{i}', False):
                    with st.expander(f"✏️ **Edit Project: {project['name']}**", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_project_name = st.text_input(
                                "**Project Name**",
                                value=project['name'],
                                key=f"new_name_{i}"
                            )
                        
                        with col2:
                            new_status = st.selectbox(
                                "**Status**",
                                options=["Not Selected", "Submitted", "Under Review", "Approved", "Rejected"],
                                index=["Not Selected", "Submitted", "Under Review", "Approved", "Rejected"].index(
                                    project.get('status', 'Not Selected')
                                ) if project.get('status', 'Not Selected') in ["Not Selected", "Submitted", "Under Review", "Approved", "Rejected"] else 0,
                                key=f"new_status_{i}"
                            )
                        
                        col_save, col_cancel = st.columns(2)
                        
                        with col_save:
                            if st.button("💾 **Save Changes**", key=f"save_changes_{i}", use_container_width=True, type="primary"):
                                if not new_project_name.strip():
                                    st.error("❌ Project name cannot be empty")
                                else:
                                    # Check for duplicate project name (excluding current project)
                                    projects_data = load_data(PROJECTS_FILE) or []
                                    duplicate = any(
                                        p['name'] == new_project_name.strip() and 
                                        p['name'] != project['name'] and 
                                        not p.get('deleted', False)
                                        for p in projects_data
                                    )
                                    
                                    if duplicate:
                                        st.error("❌ A project with this name already exists.")
                                    else:
                                        old_name = project['name']
                                        new_name = new_project_name.strip()
                                        
                                        # Update project in projects list
                                        for j, p in enumerate(projects_data):
                                            if p['name'] == old_name:
                                                projects_data[j]['name'] = new_name
                                                projects_data[j]['status'] = new_status
                                                projects_data[j]['updated_at'] = datetime.now().isoformat()
                                                break
                                        
                                        # If project name changed, update all groups that have this project
                                        if old_name != new_name:
                                            groups_data = load_data(GROUPS_FILE) or []
                                            for group in groups_data:
                                                if group['project_name'] == old_name:
                                                    group['project_name'] = new_name
                                                    group['updated_at'] = datetime.now().isoformat()
                                            save_data(groups_data, GROUPS_FILE)
                                        
                                        save_data(projects_data, PROJECTS_FILE)
                                        st.success("✅ Project updated successfully!")
                                        st.rerun()
                        
                        with col_cancel:
                            if st.button("❌ **Cancel**", key=f"cancel_edit_{i}", use_container_width=True, type="secondary"):
                                st.session_state[f'editing_project_{i}'] = False
                                st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Project management controls in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">Quick Status Update</h3>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2,1,1])
        
        with col1:
            project_to_manage = st.selectbox(
                "**Select Project to Update Status**",
                options=[""] + [p['name'] for p in active_projects],
                key="manage_project_select"
            )
        
        with col2:
            new_status = st.selectbox(
                "**New Status**",
                options=["Not Selected", "Submitted", "Under Review", "Approved", "Rejected"],
                key="new_status_select"
            )
        
        with col3:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("**Update Status**", key="update_status_btn", use_container_width=True, type="primary"):
                if project_to_manage:
                    for project in projects:
                        if project['name'] == project_to_manage:
                            old_status = project['status']
                            project['status'] = new_status
                            project['updated_at'] = datetime.now().isoformat()
                            project['updated_by'] = "admin"
                            if save_data(projects, PROJECTS_FILE):
                                st.success(f"✅ Status updated from '{old_status}' to '{new_status}' for '{project_to_manage}'!")
                                st.rerun()
                            break
                else:
                    st.error("❌ Please select a project")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">📋</span>
                <div>
                    <strong>No Projects Added Yet</strong>
                    <p style="margin: 0.5rem 0 0 0;">Add your first project above.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def manage_group_editing():
    """Manage group editing and member deletion - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">👥 Group Management</h2>', unsafe_allow_html=True)
    
    # Load groups
    groups = load_data(GROUPS_FILE) or []
    
    if not groups:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">👥</span>
                <div>
                    <strong>No Groups Available</strong>
                    <p style="margin: 0.5rem 0 0 0;">No groups available to edit.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Filter active groups (not deleted)
    active_groups = [g for g in groups if not g.get('deleted', False)]
    
    if not active_groups:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">🗑️</span>
                <div>All groups have been deleted.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Group selection for editing
    st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">Select Group to Edit</h3>', unsafe_allow_html=True)
    
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
            "Project": group['project_name'] if group['project_name'] else "No project selected",
            "Group Leader": leader_name,
            "Status": group['status'],
            "Members": len([m for m in group['members'] if m['name'].strip()]),
            "Submitted": group.get('submission_date', '')
        })
    
    df_groups = pd.DataFrame(group_data)
    st.dataframe(df_groups, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Selection for editing
    group_numbers = [g['group_number'] for g in active_groups]
    selected_group_num = st.selectbox(
        "**Choose a group to edit**",
        options=[""] + group_numbers,
        key="edit_group_select"
    )
    
    if selected_group_num:
        # Get group details
        group_to_edit = next((g for g in groups if g['group_number'] == selected_group_num and not g.get('deleted', False)), None)
        
        if group_to_edit:
            # Show group details in a card
            with st.container():
                st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Group Details</h3>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div style="background-color: #111827; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <div style="font-size: 0.9rem; color: #9ca3af;">Group Number</div>
                        <div style="font-weight: 600; font-size: 1.2rem; color: #a78bfa;">{group_to_edit['group_number']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #111827; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <div style="font-size: 0.9rem; color: #9ca3af;">Project</div>
                        <div style="font-weight: 600;">{group_to_edit['project_name'] if group_to_edit['project_name'] else "No project selected"}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #111827; padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 0.9rem; color: #9ca3af;">Status</div>
                        <div style="font-weight: 600;">{group_to_edit['status']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background-color: #111827; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <div style="font-size: 0.9rem; color: #9ca3af;">Submitted</div>
                        <div style="font-weight: 600;">{group_to_edit.get('submission_date', '')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #111827; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <div style="font-size: 0.9rem; color: #9ca3af;">Total Members</div>
                        <div style="font-weight: 600;">{len([m for m in group_to_edit['members'] if m['name'].strip()])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # GROUP STATUS UPDATE SECTION in a card
            with st.container():
                st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Update Group Status</h3>', unsafe_allow_html=True)
                
                col_status, col_btn = st.columns([2, 1])
                
                with col_status:
                    current_status = group_to_edit['status']
                    new_status = st.selectbox(
                        "**Select New Status**",
                        options=["Not Selected", "Submitted", "Under Review", "Approved", "Rejected"],
                        index=["Not Selected", "Submitted", "Under Review", "Approved", "Rejected"].index(current_status) 
                        if current_status in ["Not Selected", "Submitted", "Under Review", "Approved", "Rejected"] 
                        else 0,
                        key=f"status_update_{selected_group_num}"
                    )
                
                with col_btn:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if st.button("💾 **Update Status**", key=f"update_group_status_{selected_group_num}", use_container_width=True, type="primary"):
                        group_to_edit['status'] = new_status
                        group_to_edit['status_updated_at'] = datetime.now().isoformat()
                        group_to_edit['status_updated_by'] = "admin"
                        
                        if save_data(groups, GROUPS_FILE):
                            st.success(f"✅ Group {selected_group_num} status updated to '{new_status}'!")
                            st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Show members with delete option in a card
            with st.container():
                st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Group Members</h3>', unsafe_allow_html=True)
                
                for i, member in enumerate(group_to_edit['members'], 1):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        leader_badge = "👑 " if member.get('is_leader') else ""
                        st.markdown(f"{leader_badge}**Member {i}:** {member['name']}")
                    with col2:
                        st.markdown(f"**Roll:** {member['roll_no']}")
                    with col3:
                        # Don't allow deleting group leader
                        if not member.get('is_leader'):
                            if st.button(f"🗑️", key=f"delete_member_{selected_group_num}_{i}", use_container_width=True, type="secondary"):
                                # Remove member from group
                                group_to_edit['members'].pop(i-1)
                                if save_data(groups, GROUPS_FILE):
                                    st.success(f"✅ Member {i} deleted from group {selected_group_num}!")
                                    st.rerun()
                        else:
                            st.markdown("👑 **Leader**")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Add new member option in a card
            with st.container():
                st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Add New Member</h3>', unsafe_allow_html=True)
                with st.form(f"add_member_form_{selected_group_num}"):
                    new_member_name = st.text_input("**Full Name**", key=f"new_name_{selected_group_num}")
                    new_member_roll = st.text_input("**Roll Number**", key=f"new_roll_{selected_group_num}")
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.form_submit_button("➕ **Add Member**", use_container_width=True, type="primary"):
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
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Delete entire group option in a card
            with st.container():
                st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Delete Entire Group</h3>', unsafe_allow_html=True)
                reason = st.text_area(
                    "**Reason for deletion (optional)**",
                    placeholder="Enter reason for deleting this group...",
                    key="group_delete_reason"
                )
                
                confirm_delete = st.checkbox(
                    f"**I confirm I want to delete Group {selected_group_num}**",
                    value=False,
                    key="confirm_group_delete"
                )
                
                if confirm_delete:
                    st.markdown(f"""
                    <div class="warning-card">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.5rem;">⚠️</span>
                            <div><strong>Warning:</strong> This will permanently delete Group {selected_group_num}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("🗑️ **Delete Entire Group**", type="secondary", use_container_width=True):
                        # Add to deleted items for visibility
                        add_to_deleted_items("group", group_to_edit, reason)
                        
                        # Archive group data
                        archive_data("group", group_to_edit, reason)
                        
                        # Mark group as deleted
                        for i, group in enumerate(groups):
                            if group['group_number'] == selected_group_num:
                                groups[i]['deleted'] = True
                                groups[i]['deleted_at'] = datetime.now().isoformat()
                                groups[i]['deleted_reason'] = reason
                                break
                        
                        # Update project count and release project back to available pool
                        project_name = group_to_edit['project_name']
                        if project_name:  # Only if a project was selected
                            projects = load_data(PROJECTS_FILE) or []
                            for project in projects:
                                if project['name'] == project_name:
                                    if project.get('selected_by', 0) > 0:
                                        project['selected_by'] -= 1
                                        if project['selected_by'] == 0:
                                            # Release project back to available pool
                                            project['status'] = 'Not Selected'
                                            project['released_at'] = datetime.now().isoformat()
                                            project['released_by_group'] = selected_group_num
                                    break
                            save_data(projects, PROJECTS_FILE)
                        
                        if save_data(groups, GROUPS_FILE):
                            st.success(f"✅ Group {selected_group_num} deleted successfully and project released!")
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

def view_deleted_items():
    """View archived/deleted items - MAIN CONTENT AREA (REMOVED SOFT DELETED ITEMS TAB)"""
    st.markdown('<h2 class="sub-header">🗂️ View Archived Items</h2>', unsafe_allow_html=True)
    
    # Get all archive files
    try:
        archive_files = [f for f in os.listdir(ARCHIVE_DIR) if f.endswith('.json')]
    except FileNotFoundError:
        archive_files = []
    
    if not archive_files:
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 20px;">
                <span style="font-size: 1.5rem;">📄</span>
                <div>
                    <strong>No Archived Items</strong>
                    <p style="margin: 0.2rem 0 0 0;">No deleted items found in archive.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Sort by modification time (newest first)
        archive_files.sort(key=lambda x: os.path.getmtime(os.path.join(ARCHIVE_DIR, x)), reverse=True)
        
        # Delete all button in a card
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">Delete Options</h3>', unsafe_allow_html=True)
        if st.button("🗑️ **Delete All Archived Items**", type="secondary", use_container_width=True):
            for filename in archive_files:
                filepath = os.path.join(ARCHIVE_DIR, filename)
                try:
                    os.remove(filepath)
                except Exception as e:
                    st.error(f"Error deleting {filename}: {e}")
            
            st.success("✅ All archived items deleted permanently!")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display archive files
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">Archived Items</h3>', unsafe_allow_html=True)
        for filename in archive_files:
            filepath = os.path.join(ARCHIVE_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    archive_data_content = json.load(f)
            except Exception as e:
                st.error(f"Error loading {filename}: {e}")
                continue
            
            with st.expander(f"📄 **{filename}**", expanded=False):
                with st.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Display basic info
                        data_type = archive_data_content.get("data_type", "Unknown")
                        deleted_at = archive_data_content.get("deleted_at", "")
                        reason = archive_data_content.get("reason", "")
                        
                        st.markdown(f"**Type:** {data_type}")
                        st.markdown(f"**Deleted At:** {deleted_at[:19] if deleted_at else 'Unknown'}")
                        if reason:                            st.markdown(f"**Reason:** {reason}")
                        
                        # Show preview of data
                        if st.checkbox(f"**Show data for {filename}**", key=f"show_{filename}"):
                            st.json(archive_data_content, expanded=False)
                    
                    with col2:
                        # Delete button for individual file
                        if st.button(f"🗑️ **Delete**", key=f"delete_{filename}", use_container_width=True, type="secondary"):
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
                                label=f"**Download**",
                                data=file_content,
                                file_name=filename,
                                mime="application/json",
                                key=f"download_{filename}",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Error reading {filename}: {e}")
                    st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def export_data_section():
    """Export data section with Submission Tracking System - CSV format - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">📊 Export Data & Submission Tracking System</h2>', unsafe_allow_html=True)

    # Create tabs for different export options
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 **Project Allocations**",
        "📁 **Project File Submission**",
        "📚 **Lab Manual**",
        "📘 **Class Assignment**",
        "📈 **Comprehensive Report**"
    ])

    with tab1:
        # Project Allocations Export
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📋 Project Allocations Export</h3>', unsafe_allow_html=True)

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
                    "Project Name": group['project_name'] if group['project_name'] else "No project selected",
                    "Project Status": group['status'],
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

            df_export = pd.DataFrame(csv_data)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Data Preview</h4>', unsafe_allow_html=True)
            st.dataframe(df_export, use_container_width=True)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Export Options</h4>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                include_deleted = st.checkbox("**Include deleted items**", value=False, key="include_deleted_allocations")
            with col2:
                export_format = st.selectbox("**Export Format**", ["CSV", "Excel"], key="allocations_format")

            if st.button("📥 **Generate Export File**", key="generate_allocations", use_container_width=True, type="primary"):
                if include_deleted:
                    deleted_groups = [g for g in groups if g.get('deleted', False)]
                    for group in deleted_groups:
                        row = {
                            "Group Number": f"{group['group_number']} (DELETED)",
                            "Project Name": group['project_name'] if group['project_name'] else "No project selected",
                            "Project Status": f"{group['status']} (DELETED)",
                            "Submission Date": group.get('submission_date', ''),
                            "Deleted Reason": group.get('deleted_reason', ''),
                            "Deleted At": group.get('deleted_at', '')
                        }
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
                    df_export = pd.DataFrame(csv_data)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if export_format == "Excel":
                    filename = f"project_allocations_{timestamp}.xlsx"
                    try:
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            df_export.to_excel(writer, index=False, sheet_name='Project Allocations')
                        excel_buffer.seek(0)
                        st.download_button(
                            label="⬇️ **Click to Download Excel File**",
                            data=excel_buffer,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.warning("⚠️ Excel export requires 'openpyxl'. Falling back to CSV.")
                        filename = f"project_allocations_{timestamp}.csv"
                        csv_string = df_export.to_csv(index=False)
                        st.download_button(
                            label="⬇️ **Click to Download CSV File**",
                            data=csv_string,
                            file_name=filename,
                            mime="text/csv",
                            use_container_width=True
                        )
                else:
                    filename = f"project_allocations_{timestamp}.csv"
                    csv_string = df_export.to_csv(index=False)
                    st.download_button(
                        label="⬇️ **Click to Download CSV File**",
                        data=csv_string,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )

                st.success(f"✅ File '{filename}' is ready for download!")
        else:
            st.markdown("""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">📋</span>
                    <div>
                        <strong>No Project Allocations</strong>
                        <p style="margin: 0.5rem 0 0 0;">No project allocations to export yet.</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        # Project File Submission Report
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📁 Project File Submission Report</h3>', unsafe_allow_html=True)

        file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
        groups = load_data(GROUPS_FILE) or []
        active_groups = [g for g in groups if not g.get('deleted', False)]

        if not file_submissions:
            st.markdown("""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">📁</span>
                    <div>
                        <strong>No Project File Submissions</strong>
                        <p style="margin: 0.5rem 0 0 0;">No project file submissions yet.</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            status_data = []
            for group in active_groups:
                group_num = group['group_number']
                group_files = file_submissions.get(str(group_num), [])
                leader_name = next((m['name'] for m in group['members'] if m.get('is_leader')), "")
                if group_files:
                    submission_times = [f.get('uploaded_at', '') for f in group_files if f.get('uploaded_at')]
                    first_submission_formatted = "Unknown"
                    last_submission_formatted = "Unknown"
                    if submission_times:
                        try:
                            first_submission = min(submission_times)
                            last_submission = max(submission_times)
                            first_submission_formatted = datetime.fromisoformat(first_submission).strftime("%Y-%m-%d %H:%M")
                            last_submission_formatted = datetime.fromisoformat(last_submission).strftime("%Y-%m-%d %H:%M")
                        except:
                            pass
                    total_size = sum(f.get('size', 0) for f in group_files)
                    status_data.append({
                        "Group #": group_num,
                        "Project": group['project_name'] if group['project_name'] else "No project selected",
                        "Group Leader": leader_name,
                        "Files Submitted": len(group_files),
                        "Total Size (MB)": f"{total_size / (1024*1024):.2f}",
                        "First Submission": first_submission_formatted,
                        "Last Submission": last_submission_formatted,
                        "Submission Count": len(group_files),
                        "Status": "✅ Submitted"
                    })
                else:
                    status_data.append({
                        "Group #": group_num,
                        "Project": group['project_name'] if group['project_name'] else "No project selected",
                        "Group Leader": leader_name,
                        "Files Submitted": 0,
                        "Total Size (MB)": "0.00",
                        "First Submission": "Not submitted",
                        "Last Submission": "Not submitted",
                        "Submission Count": 0,
                        "Status": "❌ Not Submitted"
                    })

            status_data.sort(key=lambda x: x['Group #'])
            df_status = pd.DataFrame(status_data)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Submission Status Report</h4>', unsafe_allow_html=True)
            st.dataframe(df_status, use_container_width=True)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">📊 Statistics</h4>', unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            total_groups = len(active_groups)
            submitted_groups = len([g for g in status_data if g['Files Submitted'] > 0])
            not_submitted = total_groups - submitted_groups
            submission_rate = (submitted_groups / total_groups * 100) if total_groups > 0 else 0
            with col1: st.metric("Total Groups", total_groups)
            with col2: st.metric("Submitted Groups", submitted_groups)
            with col3: st.metric("Not Submitted", not_submitted)
            with col4: st.metric("Submission Rate", f"{submission_rate:.1f}%")

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Export Options</h4>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                report_format = st.selectbox("**Report Format**", ["CSV", "Excel"], key="project_file_format")
            with col2:
                report_type = st.selectbox("**Report Type**", ["Summary Report", "Detailed Report"], key="project_file_type")

            if st.button("📊 **Generate Submission Report**", key="generate_project_file_report", use_container_width=True, type="primary"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if report_type == "Detailed Report":
                    detailed_data = []
                    for group_num, files in file_submissions.items():
                        if files:
                            group_info = next((g for g in active_groups if str(g['group_number']) == group_num), None)
                            if group_info:
                                for file_info in files:
                                    detailed_data.append({
                                        "Group #": group_num,
                                        "Project": group_info['project_name'] if group_info['project_name'] else "No project selected",
                                        "Group Leader": next((m['name'] for m in group_info['members'] if m.get('is_leader')), ""),
                                        "Filename": file_info.get('filename', ''),
                                        "File Size (MB)": f"{file_info.get('size', 0) / (1024*1024):.2f}",
                                        "Uploaded At": datetime.fromisoformat(file_info.get('uploaded_at', '')).strftime("%Y-%m-%d %H:%M") if file_info.get('uploaded_at') else "Unknown",
                                        "Submission Count": file_info.get('submission_count', 1)
                                    })
                    export_df = pd.DataFrame(detailed_data)
                    filename_base = f"project_file_submissions_detailed_{timestamp}"
                else:
                    export_df = df_status
                    filename_base = f"project_file_submissions_summary_{timestamp}"

                if report_format == "Excel":
                    filename = filename_base + ".xlsx"
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False, sheet_name='Project File Submissions')
                    excel_buffer.seek(0)
                    st.download_button(
                        label="⬇️ **Download Excel Report**",
                        data=excel_buffer,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    filename = filename_base + ".csv"
                    csv_string = export_df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ **Download CSV Report**",
                        data=csv_string,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                st.success(f"✅ Report '{filename}' is ready for download!")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        # Lab Manual Submission Report
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📚 Lab Manual Submission Report</h3>', unsafe_allow_html=True)

        lab_manual = load_data(LAB_MANUAL_FILE) or []

        if not lab_manual:
            st.markdown("""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">📚</span>
                    <div>
                        <strong>No Lab Manual Submissions</strong>
                        <p style="margin: 0.5rem 0 0 0;">No lab manual submissions yet.</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            report_data = []
            for submission in lab_manual:
                report_data.append({
                    "Name": submission.get('name', ''),
                    "Roll No": submission.get('roll_no', ''),
                    "Subject": submission.get('subject_name', ''),
                    "Status": submission.get('status', 'Submitted'),
                    "Files Submitted": len(submission.get('files', [])),
                    "Total File Size (MB)": f"{sum(f.get('file_size', 0) for f in submission.get('files', [])) / (1024*1024):.2f}",
                    "Submission Date": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M'),
                    "Uploaded By": submission.get('uploaded_by', 'Student')
                })

            df_lab = pd.DataFrame(report_data)
            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Lab Manual Submission Report</h4>', unsafe_allow_html=True)
            st.dataframe(df_lab, use_container_width=True)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">📊 Statistics</h4>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Total Submissions", len(lab_manual))
            with col2:
                with_files = len([s for s in lab_manual if s.get('files') and len(s['files']) > 0])
                st.metric("With Files", with_files)
            with col3:
                total_files = sum(len(s.get('files', [])) for s in lab_manual)
                st.metric("Total Files", total_files)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Export Options</h4>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                report_format = st.selectbox("**Report Format**", ["CSV", "Excel"], key="lab_manual_format")
            with col2:
                include_files = st.checkbox("**Include file details**", value=False, key="include_lab_files")

            if st.button("📊 **Generate Lab Manual Report**", key="generate_lab_report", use_container_width=True, type="primary"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if include_files:
                    detailed_data = []
                    for submission in lab_manual:
                        if submission.get('files'):
                            for file_info in submission['files']:
                                detailed_data.append({
                                    "Name": submission.get('name', ''),
                                    "Roll No": submission.get('roll_no', ''),
                                    "Subject": submission.get('subject_name', ''),
                                    "Filename": file_info.get('original_filename', ''),
                                    "File Size (MB)": f"{file_info.get('file_size', 0) / (1024*1024):.2f}",
                                    "Submission Date": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M'),
                                    "Uploaded By": submission.get('uploaded_by', 'Student')
                                })
                    if detailed_data:
                        export_df = pd.DataFrame(detailed_data)
                        filename_base = f"lab_manual_submissions_detailed_{timestamp}"
                    else:
                        export_df = df_lab
                        filename_base = f"lab_manual_submissions_summary_{timestamp}"
                else:
                    export_df = df_lab
                    filename_base = f"lab_manual_submissions_summary_{timestamp}"

                if report_format == "Excel":
                    filename = filename_base + ".xlsx"
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False, sheet_name='Lab Manual Submissions')
                    excel_buffer.seek(0)
                    st.download_button(
                        label="⬇️ **Download Excel Report**",
                        data=excel_buffer,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    filename = filename_base + ".csv"
                    csv_string = export_df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ **Download CSV Report**",
                        data=csv_string,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                st.success(f"✅ Report '{filename}' is ready for download!")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab4:
        # Class Assignment Submission Report
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📘 Class Assignment Submission Report</h3>', unsafe_allow_html=True)

        class_assignments = load_data(CLASS_ASSIGNMENTS_FILE) or []

        if not class_assignments:
            st.markdown("""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">📘</span>
                    <div>
                        <strong>No Class Assignment Submissions</strong>
                        <p style="margin: 0.5rem 0 0 0;">No class assignment submissions yet.</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            report_data = []
            for submission in class_assignments:
                report_data.append({
                    "Name": submission.get('name', ''),
                    "Roll No": submission.get('roll_no', ''),
                    "Course": submission.get('course_name', ''),
                    "Assignment No": submission.get('assignment_no', 1),
                    "Files Submitted": len(submission.get('files', [])),
                    "Total File Size (MB)": f"{sum(f.get('file_size', 0) for f in submission.get('files', [])) / (1024*1024):.2f}",
                    "Submission Date": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M'),
                    "Uploaded By": submission.get('uploaded_by', 'Student')
                })

            df_class = pd.DataFrame(report_data)
            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Class Assignment Submission Report</h4>', unsafe_allow_html=True)
            st.dataframe(df_class, use_container_width=True)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">📊 Statistics</h4>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Total Submissions", len(class_assignments))
            with col2:
                unique_students = len(set([s['Roll No'] for s in report_data]))
                st.metric("Unique Students", unique_students)
            with col3:
                assignments_count = len(set([s['Assignment No'] for s in report_data]))
                st.metric("Assignments", assignments_count)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Export Options</h4>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                report_format = st.selectbox("**Report Format**", ["CSV", "Excel"], key="class_assignment_format")
            with col2:
                report_type = st.selectbox("**Report Type**", ["Summary Report", "Detailed Report", "Assignment-wise Report"], key="class_assignment_type")

            if st.button("📊 **Generate Class Assignment Report**", key="generate_class_report", use_container_width=True, type="primary"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if report_type == "Detailed Report":
                    detailed_data = []
                    for submission in class_assignments:
                        if submission.get('files'):
                            for file_info in submission['files']:
                                detailed_data.append({
                                    "Name": submission.get('name', ''),
                                    "Roll No": submission.get('roll_no', ''),
                                    "Course": submission.get('course_name', ''),
                                    "Assignment No": submission.get('assignment_no', 1),
                                    "Filename": file_info.get('original_filename', ''),
                                    "File Size (MB)": f"{file_info.get('file_size', 0) / (1024*1024):.2f}",
                                    "File Type": file_info.get('file_type', ''),
                                    "Submission Date": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M'),
                                    "Uploaded By": submission.get('uploaded_by', 'Student')
                                })
                    if detailed_data:
                        export_df = pd.DataFrame(detailed_data)
                        filename_base = f"class_assignments_detailed_{timestamp}"
                    else:
                        export_df = df_class
                        filename_base = f"class_assignments_summary_{timestamp}"
                elif report_type == "Assignment-wise Report":
                    assignment_groups = {}
                    for submission in class_assignments:
                        a_no = submission.get('assignment_no', 1)
                        if a_no not in assignment_groups:
                            assignment_groups[a_no] = {
                                "Assignment No": a_no,
                                "Total Submissions": 0,
                                "Unique Students": set(),
                                "Total Files": 0,
                                "Total Size": 0
                            }
                        assignment_groups[a_no]["Total Submissions"] += 1
                        assignment_groups[a_no]["Unique Students"].add(submission['roll_no'])
                        assignment_groups[a_no]["Total Files"] += len(submission.get('files', []))
                        assignment_groups[a_no]["Total Size"] += sum(f.get('file_size', 0) for f in submission.get('files', []))
                    assignment_data = []
                    for a_no, data in assignment_groups.items():
                        assignment_data.append({
                            "Assignment No": a_no,
                            "Total Submissions": data["Total Submissions"],
                            "Unique Students": len(data["Unique Students"]),
                            "Submission Rate": f"{(data['Total Submissions'] / len(data['Unique Students']) * 100):.1f}%" if data['Unique Students'] else "0%",
                            "Total Files": data["Total Files"],
                            "Total Size (MB)": f"{data['Total Size'] / (1024*1024):.2f}"
                        })
                    export_df = pd.DataFrame(assignment_data)
                    filename_base = f"class_assignments_by_assignment_{timestamp}"
                else:
                    export_df = df_class
                    filename_base = f"class_assignments_summary_{timestamp}"

                if report_format == "Excel":
                    filename = filename_base + ".xlsx"
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False, sheet_name='Class Assignments')
                    excel_buffer.seek(0)
                    st.download_button(
                        label="⬇️ **Download Excel Report**",
                        data=excel_buffer,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    filename = filename_base + ".csv"
                    csv_string = export_df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ **Download CSV Report**",
                        data=csv_string,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                st.success(f"✅ Report '{filename}' is ready for download!")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab5:
        # Comprehensive Report
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #374151;">📈 Comprehensive Submission Report</h3>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">📊</span>
                <div>This report combines data from all submission types into a single comprehensive view.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        groups = load_data(GROUPS_FILE) or []
        active_groups = [g for g in groups if not g.get('deleted', False)]
        file_submissions = load_data(FILE_SUBMISSIONS_FILE) or {}
        lab_manual = load_data(LAB_MANUAL_FILE) or []
        class_assignments = load_data(CLASS_ASSIGNMENTS_FILE) or []

        comprehensive_data = []
        for group in active_groups:
            group_num = group['group_number']
            group_files = file_submissions.get(str(group_num), [])
            leader_name = next((m['name'] for m in group['members'] if m.get('is_leader')), "")
            comprehensive_data.append({
                "Type": "Project Group",
                "ID": f"Group {group_num}",
                "Name": leader_name,
                "Identifier": f"Roll numbers: {', '.join([m['roll_no'] for m in group['members'] if m['roll_no'].strip()])}",
                "Project/Subject": group['project_name'] if group['project_name'] else "No project selected",
                "Status": group['status'],
                "Files Submitted": len(group_files),
                "Submission Date": group.get('submission_date', ''),
                "Category": "Project Allocation"
            })
        for submission in lab_manual:
            comprehensive_data.append({
                "Type": "Lab Manual",
                "ID": submission['roll_no'],
                "Name": submission['name'],
                "Identifier": f"Roll: {submission['roll_no']}",
                "Project/Subject": submission.get('subject_name', ''),
                "Status": submission.get('status', 'Submitted'),
                "Files Submitted": len(submission.get('files', [])),
                "Submission Date": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M'),
                "Category": "Lab Manual"
            })
        for submission in class_assignments:
            comprehensive_data.append({
                "Type": "Class Assignment",
                "ID": submission['roll_no'],
                "Name": submission['name'],
                "Identifier": f"Roll: {submission['roll_no']}, Assignment: {submission.get('assignment_no', 1)}",
                "Project/Subject": submission.get('course_name', ''),
                "Status": submission.get('status', 'Submitted'),
                "Files Submitted": len(submission.get('files', [])),
                "Submission Date": datetime.fromisoformat(submission.get('submission_date', '')).strftime('%Y-%m-%d %H:%M'),
                "Category": "Class Assignment"
            })

        if comprehensive_data:
            df_comprehensive = pd.DataFrame(comprehensive_data)
            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Comprehensive Submission Report</h4>', unsafe_allow_html=True)
            st.dataframe(df_comprehensive, use_container_width=True)

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">📊 Statistics by Category</h4>', unsafe_allow_html=True)
            categories = df_comprehensive['Category'].unique()
            cols = st.columns(len(categories))
            for idx, category in enumerate(categories):
                with cols[idx]:
                    cat_data = df_comprehensive[df_comprehensive['Category'] == category]
                    total = len(cat_data)
                    with_files = len(cat_data[cat_data['Files Submitted'] > 0])
                    st.metric(label=category, value=total, delta=f"{with_files} with files")

            st.markdown('<h4 style="color: #e5e7eb; margin-bottom: 1rem;">Export Options</h4>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                report_format = st.selectbox("**Report Format**", ["Excel", "CSV"], key="comprehensive_format")
            with col2:
                include_summary = st.checkbox("**Include summary sheet**", value=True, key="include_summary")

            if st.button("📊 **Generate Comprehensive Report**", key="generate_comprehensive", use_container_width=True, type="primary"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if report_format == "Excel":
                    filename = f"comprehensive_submission_report_{timestamp}.xlsx"
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_comprehensive.to_excel(writer, index=False, sheet_name='All Submissions')
                        if include_summary:
                            summary_data = []
                            for category in categories:
                                cat_data = df_comprehensive[df_comprehensive['Category'] == category]
                                total = len(cat_data)
                                with_files = len(cat_data[cat_data['Files Submitted'] > 0])
                                total_files = cat_data['Files Submitted'].sum()
                                summary_data.append({
                                    "Category": category,
                                    "Total Submissions": total,
                                    "With Files": with_files,
                                    "Without Files": total - with_files,
                                    "Total Files": total_files,
                                    "Submission Rate": f"{(with_files / total * 100):.1f}%" if total > 0 else "0%"
                                })
                            df_summary = pd.DataFrame(summary_data)
                            df_summary.to_excel(writer, index=False, sheet_name='Summary')
                            for category in categories:
                                cat_df = df_comprehensive[df_comprehensive['Category'] == category]
                                if not cat_df.empty:
                                    sheet_name = category[:31]
                                    cat_df.to_excel(writer, index=False, sheet_name=sheet_name)
                    excel_buffer.seek(0)
                    st.download_button(
                        label="⬇️ **Download Comprehensive Excel Report**",
                        data=excel_buffer,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    filename = f"comprehensive_submission_report_{timestamp}.csv"
                    csv_string = df_comprehensive.to_csv(index=False)
                    st.download_button(
                        label="⬇️ **Download Comprehensive CSV Report**",
                        data=csv_string,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                st.success(f"✅ Comprehensive report '{filename}' is ready for download!")
        else:
            st.markdown("""
            <div class="info-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">📊</span>
                    <div>
                        <strong>No Submission Data Available</strong>
                        <p style="margin: 0.5rem 0 0 0;">No submission data available for comprehensive report.</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def manage_system_config():
    """System configuration section - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">⚙️ System Configuration</h2>', unsafe_allow_html=True)
    
    config = load_data(CONFIG_FILE) or {}
    
    # Group Size Configuration in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Group Size Configuration</h3>', unsafe_allow_html=True)
        max_members = st.slider(
            "**Maximum Number of Members per Group**",
            min_value=1,
            max_value=10,
            value=config.get('max_members', 3),
            help="Set the maximum number of members allowed per group (1-10)"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Group Numbering in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">Group Numbering</h3>', unsafe_allow_html=True)
        next_group_num = st.number_input(
            "**Next Group Number**",
            min_value=1,
            value=config.get('next_group_number', 1),
            help="This number will be assigned to the next submitted group"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Base URL configuration in a card
    with st.container():
        st.markdown('<div class="card"><h3 style="color: #e5e7eb; margin-bottom: 1rem;">URL Configuration</h3>', unsafe_allow_html=True)
        base_url = st.text_input(
            "**Base URL**",
            value=config.get('base_url', 'http://localhost:8501'),
            help="Base URL for short URL generation"
        )
        
        st.markdown("""
        <div style="background-color: #0c4a6e; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
            <div style="font-size: 0.9rem; color: #93c5fd; font-weight: 600;">URL Format Examples:</div>
            <div style="font-size: 0.85rem; color: #e5e7eb; margin-top: 0.5rem;">
                • Local: http://localhost:8501<br>
                • Cloud: https://your-app.streamlit.app<br>
                • Custom: https://projects.yourdomain.com
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Save button
    if st.button("💾 **Save Configuration**", key="save_config", use_container_width=True, type="primary"):
        config['max_members'] = max_members
        config['next_group_number'] = int(next_group_num)
        config['base_url'] = base_url.strip()
        if save_data(config, CONFIG_FILE):
            st.success("✅ Configuration saved successfully!")

def change_password():
    """Change admin password section - MAIN CONTENT AREA"""
    st.markdown('<h2 class="sub-header">🔐 Change Admin Password</h2>', unsafe_allow_html=True)
    
    with st.form("change_password_form"):
        with st.container():
            current_password = st.text_input("**Current Password**", type="password")
            new_password = st.text_input("**New Password**", type="password")
            confirm_password = st.text_input("**Confirm New Password**", type="password")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submit = st.form_submit_button("**Change Password**", use_container_width=True, type="primary")
            
            if submit:
                admin_data = load_data(ADMIN_CREDENTIALS_FILE)
                current_hash = hash_password(current_password)
                
                if admin_data.get("password_hash") != current_hash:
                    st.error("❌ Current password is incorrect!")
                elif new_password != confirm_password:
                    st.error("❌ New passwords do not match!")
                elif len(new_password) < 6:
                    st.error("❌ New password must be at least 6 characters long!")
                else:
                    admin_data["password_hash"] = hash_password(new_password)
                    if save_data(admin_data, ADMIN_CREDENTIALS_FILE):
                        st.success("✅ Password changed successfully!")
            st.markdown('</div>', unsafe_allow_html=True)

def admin_login_page():
    """Admin login page - MAIN CONTENT AREA - WITH ENTER KEY SUPPORT"""
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 class="main-header">🔐 Admin Login</h1>
        <p style="color: #9ca3af; font-size: 1.1rem;">Administrator Access Portal</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Use st.form to enable Enter key submission
    with st.form("login_form"):
        with st.container():
            st.markdown("""
            <div class="card" style="max-width: 500px; margin: 0 auto;">
                <div style="text-align: center; margin-bottom: 1.5rem;">
                    <div style="font-size: 3rem; margin-bottom: 0.5rem;">🔐</div>
                    <h3 style="color: #e5e7eb; margin: 0;">Administrator Access</h3>
                </div>
            """, unsafe_allow_html=True)
            
            # Form fields
            username = st.text_input("**Username**", placeholder="Enter admin username", key="login_username")
            password = st.text_input("**Password**", type="password", placeholder="Enter admin password", key="login_password")
            
            # Submit button inside the form
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                login_button = st.form_submit_button(
                    "**Login**", 
                    use_container_width=True,
                    type="primary"
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Handle form submission
            if login_button:
                if authenticate(username, password):
                    st.session_state.logged_in = True
                    st.session_state.admin_current_section = "🔗 Short URLs"
                    st.session_state.selected_admin_function = manage_short_urls
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
    
    # Additional info
    st.markdown("""
    <div style="max-width: 500px; margin: 2rem auto 0 auto; text-align: center;">
        <div style="color: #9ca3af; font-size: 0.9rem;">
            <p>💡 <strong>Tip:</strong> Press Enter after typing your password to login quickly</p>
            <p>⚠️ Contact system administrator if you forgot your credentials</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'group_verified' not in st.session_state:
        st.session_state.group_verified = False
    if 'verified_group_number' not in st.session_state:
        st.session_state.verified_group_number = None
    if 'project_files_data' not in st.session_state:
        st.session_state.project_files_data = {
            'group_number': None,
            'group_verified': False,
            'uploaded_files': [],
            'project_name': '',
            'leader_name': '',
            'has_submitted': False
        }
    if 'admin_group_verified' not in st.session_state:
        st.session_state.admin_group_verified = False
    if 'admin_upload_group' not in st.session_state:
        st.session_state.admin_upload_group = None
    if 'admin_current_section' not in st.session_state:
        st.session_state.admin_current_section = "🔗 Short URLs"
    if 'selected_admin_function' not in st.session_state:
        st.session_state.selected_admin_function = manage_short_urls
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Student Form"
    
    # Initialize edit states for projects
    for i in range(100):  # Assuming max 100 projects
        if f'editing_project_{i}' not in st.session_state:
            st.session_state[f'editing_project_{i}'] = False
    
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
            st.markdown("""
            <div class="warning-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem;">⚠️</span>
                    <div>
                        <strong>Invalid Short URL</strong>
                        <p style="margin: 0.5rem 0 0 0;">Invalid short URL code. Please use a valid link.</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Sidebar navigation - ALWAYS SHOWN
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🎓</div>
            <h1 style="color: white; margin: 0; font-size: 1.5rem;">Academic Portal</h1>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.logged_in:
            # Admin is logged in - show admin navigation buttons
            st.markdown("### 🛠️ **Admin Dashboard**")
            st.markdown("<hr style='border-color: #4b5563; margin: 1rem 0;'>", unsafe_allow_html=True)
            
            # Define admin sections with their functions
            admin_sections = [
                ("🔗 Short URLs", manage_short_urls),
                ("📝 Form Settings", manage_form_settings),
                ("📋 Project Management", manage_project_section),
                ("👥 Group Management", manage_group_editing),
                ("🗂️ View Archived", view_deleted_items),
                ("📊 Export Data", export_data_section),
                ("📁 File Submissions", manage_file_submissions),
                ("📚 Lab Manual", manage_lab_manual),
                ("📘 Class Assignments", manage_class_assignments),
                ("⚙️ System Configuration", manage_system_config),
                ("🔐 Change Password", change_password)
            ]
            
            # Display each section as a button
            for section_name, section_function in admin_sections:
                if st.button(section_name, use_container_width=True, key=f"nav_{section_name}"):
                    st.session_state.admin_current_section = section_name
                    st.session_state.selected_admin_function = section_function
                    st.rerun()
            
            # Show current section
            st.markdown("<hr style='border-color: #4b5563; margin: 1.5rem 0;'>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background-color: #374151; padding: 0.75rem; border-radius: 8px;">
                <div style="color: #9ca3af; font-size: 0.9rem;">Current Section:</div>
                <div style="color: white; font-weight: 600;">{st.session_state.admin_current_section}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Logout button
            st.markdown("<hr style='border-color: #4b5563; margin: 1.5rem 0;'>", unsafe_allow_html=True)
            if st.button("🚪 **Logout**", use_container_width=True, type="primary"):
                st.session_state.logged_in = False
                st.session_state.admin_group_verified = False
                st.session_state.admin_upload_group = None
                st.session_state.admin_current_section = "🔗 Short URLs"
                st.session_state.selected_admin_function = manage_short_urls
                st.session_state.current_page = "Student Form"
                st.rerun()
        
        else:
            # Not logged in - show simple navigation buttons
            st.markdown("### 🌐 **Navigation**")
            st.markdown("<hr style='border-color: #4b5563; margin: 1rem 0;'>", unsafe_allow_html=True)
            
            # Student Form button
            if st.button("📝 **Student Form**", use_container_width=True, key="nav_student_form", type="primary"):
                st.session_state.current_page = "Student Form"
                st.rerun()
            
            # Admin Login button
            if st.button("🔐 **Admin Login**", use_container_width=True, key="nav_admin_login", type="primary"):
                st.session_state.current_page = "Admin Login"
                st.rerun()
            
            # Show current page
            st.markdown("<hr style='border-color: #4b5563; margin: 1.5rem 0;'>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background-color: #374151; padding: 0.75rem; border-radius: 8px;">
                <div style="color: #9ca3af; font-size: 0.9rem;">Current Page:</div>
                <div style="color: white; font-weight: 600;">{st.session_state.current_page}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # MAIN CONTENT AREA - OUTSIDE THE SIDEBAR CONTEXT
    if st.session_state.logged_in:
        # Admin is logged in - show selected admin section in main area
        selected_function = st.session_state.get('selected_admin_function', manage_short_urls)
        selected_function()  # This will render in the main content area
    else:
        # Not logged in - show selected page in main area
        if st.session_state.current_page == "Student Form":
            student_form_standalone()
        elif st.session_state.current_page == "Admin Login":
            admin_login_page()

if __name__ == "__main__":
    main()
