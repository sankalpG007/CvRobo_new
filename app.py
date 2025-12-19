"""
CV Robo - Main Application with Mandatory User Login
"""
import time
from PIL import Image
from jobs.services.job_search_service import render_job_search
from datetime import datetime
from ui_components import (
    apply_modern_styles, hero_section, feature_card, about_section,
    page_header, render_analytics_section, render_activity_section,
    render_suggestions_section
)
from feedback.managers.feedback_manager import FeedbackManager
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx import Document
import io
import base64
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
from dashboard.managers.dashboard_manager import DashboardManager
from config.courses import COURSES_BY_CATEGORY, RESUME_VIDEOS, INTERVIEW_VIDEOS, get_courses_for_role, get_category_for_role
from config.job_roles import JOB_ROLES
from config.database import (
    get_database_connection, save_resume_data, save_analysis_data,
    init_database, verify_admin, log_admin_action, save_ai_analysis_data,
    get_ai_analysis_stats, reset_ai_analysis_stats, get_detailed_ai_analysis_stats,
    verify_user, add_user, check_user_exists
)
from utils.ai_resume_analyzer import AIResumeAnalyzer
from utils.resume_builder import ResumeBuilder
from utils.resume_analyzer import ResumeAnalyzer
import traceback
import plotly.express as px
import pandas as pd
import json
import streamlit as st
import datetime
import os
import sys
from pages.builder import render_builder_page
from pages.home import render_home_page
from pages.analyzer import render_analyzer_page
from pages.about import render_about_page
from pages.dashboard import render_dashboard_page 
from pages.job_search import render_job_search_page 
from pages.feedback import render_feedback_page_page

# Set page config at the very beginning
st.set_page_config(
    page_title="CV Robo",
    page_icon="🚀",
    layout="wide"
)

# --- START: NEW AUTHENTICATION LOGIC ---

class ResumeApp:
    def __init__(self):
        """Initialize the application"""
        if 'form_data' not in st.session_state:
            st.session_state.form_data = {
                'personal_info': {
                    'full_name': '',
                    'email': '',
                    'phone': '',
                    'location': '',
                    'linkedin': '',
                    'portfolio': ''
                },
                'summary': '',
                'experiences': [],
                'education': [],
                'projects': [],
                'skills_categories': {
                    'technical': [],
                    'soft': [],
                    'languages': [],
                    'tools': []
                }
            }
        
        # --- NEW: Initialize authentication state ---
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_email' not in st.session_state:
            st.session_state.user_email = None

        # Initialize navigation state
        if 'page' not in st.session_state:
            st.session_state.page = 'home'

        # Initialize admin state
        if 'is_admin' not in st.session_state:
            st.session_state.is_admin = False

        # --- FIX: ROBUST PAGE MAPPING ---
        self.PAGE_MAPPING = {
            "🏠 HOME": "home",
            "🔍 RESUME ANALYZER": "analyzer",
            "📝 RESUME BUILDER": "builder",
            "📊 DASHBOARD": "dashboard",
            "🎯 JOB SEARCH": "job_search",
            "💬 FEEDBACK": "feedback",
            "ℹ️ ABOUT": "about"
        }
        
        self.pages = {
            "🏠 HOME": render_home_page,
            "🔍 RESUME ANALYZER": render_analyzer_page, # FIXED: Uses the imported function
            "📝 RESUME BUILDER": render_builder_page,   # FIXED: Uses the imported function
            "📊 DASHBOARD": render_dashboard_page,     # These remain methods for now
            "🎯 JOB SEARCH":  render_job_search_page,    # These remain methods for now
            "💬 FEEDBACK":  render_feedback_page_page,   # These remain methods for now
            "ℹ️ ABOUT": render_about_page,               # These remain methods for now
        }

        # Initialize dashboard manager
        self.dashboard_manager = DashboardManager()

        self.analyzer = ResumeAnalyzer()
        self.ai_analyzer = AIResumeAnalyzer()
        self.builder = ResumeBuilder()
        self.job_roles = JOB_ROLES

        # Initialize session state
        if 'user_id' not in st.session_state:
            st.session_state.user_id = 'default_user'
        if 'selected_role' not in st.session_state:
            st.session_state.selected_role = None

        # Initialize database
        init_database()

        # Load external CSS
        if os.path.exists('style/style.css'):
            with open('style/style.css') as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

        # Load Google Fonts
        st.markdown("""
            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        """, unsafe_allow_html=True)

        if 'resume_data' not in st.session_state:
            st.session_state.resume_data = []
        if 'ai_analysis_stats' not in st.session_state:
            st.session_state.ai_analysis_stats = {
                'score_distribution': {},
                'total_analyses': 0,
                'average_score': 0
            }

    def load_lottie_url(self, url: str):
        """Load Lottie animation from URL"""
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()

    def apply_global_styles(self):
        st.markdown("""
        <style>
        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #1a1a1a;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb {
            background: #B886FD;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #a07cd0;
        }

        /* Global Styles */
        .main-header {
            background: linear-gradient(135deg, #B886FD 0%, #a07cd0 100%);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .main-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, transparent 0%, rgba(255,255,255,0.1) 100%);
            z-index: 1;
        }

        .main-header h1 {
            color: white;
            font-size: 2.5rem;
            font-weight: 600;
            margin: 0;
            position: relative;
            z-index: 2;
        }

        /* Template Card Styles */
        .template-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 2rem;
            padding: 1rem;
        }

        .template-card {
            background: rgba(45, 45, 45, 0.9);
            border-radius: 20px;
            padding: 2rem;
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .template-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            border-color: #B886FD;
        }

        .template-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, transparent 0%, rgba(184, 134, 253, 0.1) 100%);
            z-index: 1;
        }

        .template-icon {
            font-size: 3rem;
            color: #B886FD;
            margin-bottom: 1.5rem;
            position: relative;
            z-index: 2;
        }

        .template-title {
            font-size: 1.8rem;
            font-weight: 600;
            color: white;
            margin-bottom: 1rem;
            position: relative;
            z-index: 2;
        }

        .template-description {
            color: #aaa;
            margin-bottom: 1.5rem;
            position: relative;
            z-index: 2;
            line-height: 1.6;
        }

        /* Feature List Styles */
        .feature-list {
            list-style: none;
            padding: 0;
            margin: 1.5rem 0;
            position: relative;
            z-index: 2;
        }

        .feature-item {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            color: #ddd;
            font-size: 0.95rem;
        }

        .feature-icon {
            color: #B886FD;
            margin-right: 0.8rem;
            font-size: 1.1rem;
        }

        /* Button Styles */
        .action-button {
            background: linear-gradient(135deg, #B886FD 0%, #a07cd0 100%);
            color: white;
            padding: 1rem 2rem;
            border-radius: 50px;
            border: none;
            font-weight: 500;
            cursor: pointer;
            width: 100%;
            text-align: center;
            position: relative;
            overflow: hidden;
            z-index: 2;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .action-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(184, 134, 253, 0.3);
        }

        .action-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.2) 50%, transparent 100%);
            transition: all 0.6s ease;
        }

        .action-button:hover::before {
            left: 100%;
        }

        /* Form Section Styles */
        .form-section {
            background: rgba(45, 45, 45, 0.9);
            border-radius: 20px;
            padding: 2rem;
            margin: 2rem 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }

        .form-section-title {
            font-size: 1.8rem;
            font-weight: 600;
            color: white;
            margin-bottom: 1.5rem;
            padding-bottom: 0.8rem;
            border-bottom: 2px solid #B886FD;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-label {
            color: #ddd;
            font-weight: 500;
            margin-bottom: 0.8rem;
            display: block;
        }

        .form-input {
            width: 100%;
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(30, 30, 30, 0.9);
            color: white;
            transition: all 0.3s ease;
        }

        .form-input:focus {
            border-color: #B886FD;
            box-shadow: 0 0 0 2px rgba(184, 134, 253, 0.2);
            outline: none;
        }

        /* Skill Tags */
        .skill-tag-container {
            display: flex;
            flex-wrap: wrap;
            gap: 0.8rem;
            margin-top: 1rem;
        }

        .skill-tag {
            background: rgba(184, 134, 253, 0.1);
            color: #B886FD;
            padding: 0.6rem 1.2rem;
            border-radius: 50px;
            border: 1px solid #B886FD;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .skill-tag:hover {
            background: #B886FD;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(184, 134, 253, 0.2);
        }

        /* Progress Circle */
        .progress-container {
            position: relative;
            width: 150px;
            height: 150px;
            margin: 2rem auto;
        }

        .progress-circle {
            transform: rotate(-90deg);
            width: 100%;
            height: 100%;
        }

        .progress-circle circle {
            fill: none;
            stroke-width: 8;
            stroke-linecap: round;
            stroke: #B886FD;
            transform-origin: 50% 50%;
            transition: all 0.3s ease;
        }

        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 1.5rem;
            font-weight: 600;
            color: white;
        }
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .feature-card {
            background-color: #333333;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Animations */
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .animate-slide-in {
            animation: slideIn 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .template-container {
                grid-template-columns: 1fr;
            }

            .main-header {
                padding: 1.5rem;
            }

            .main-header h1 {
                font-size: 2rem;
            }

            .template-card {
                padding: 1.5rem;
            }

            .action-button {
                padding: 0.8rem 1.6rem;
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
    def add_footer(self):
        st.markdown("""
        <style>
            .footer {
                width: 100%;
                background-color: #0e1117;
                color: white;
                text-align: center;
                padding: 10px 0;
                font-size: 14px;
                border-top: 1px solid #B886FD;
                position: relative;
                bottom: 0;
                left: 0;
            }
            .footer a {
                color: #B886FD;
                text-decoration: none;
                font-weight: bold;
            }
            .footer p {
                margin: 5px 0;
            }
        </style>
        <div class="footer">
            <p>
                Powered by <b>Streamlit</b> & <b>Google Gemini AI</b> | Developed by 
                <a href="http://linkedin.com/in/sankalp-singh-48670b21a" target="_blank">
                    Sankalp Satendra Singh
                </a>
            </p>
            <p>© 2025 Sankalp Satendra Singh | "Every project is a step closer to your dream — keep building!"</p>
        </div>
    """, unsafe_allow_html=True)

    def load_image(self, image_name):
        """Load image from static directory"""
        try:
            image_path = f"assets/{image_name}"

            with open(image_path, "rb") as f:
                image_bytes = f.read()
            encoded = base64.b64encode(image_bytes).decode()
            return f"data:image/jpeg;base64,{encoded}"
        except Exception as e:
            print(f"Error loading image {image_name}: {e}")
            return None

    def export_to_excel(self):
        """Export resume data to Excel"""
        conn = get_database_connection()

        # Get resume data with analysis
        query = """
            SELECT
                rd.name, rd.email, rd.phone, rd.linkedin, rd.github, rd.portfolio,
                rd.summary, rd.target_role, rd.target_category,
                rd.education, rd.experience, rd.projects, rd.skills,
                ra.ats_score, ra.keyword_match_score, ra.format_score, ra.section_score,
                ra.missing_skills, ra.recommendations,
                rd.created_at
            FROM resume_data rd
            LEFT JOIN resume_analysis ra ON rd.id = ra.resume_id
        """

        try:
            # Read data into DataFrame
            df = pd.read_sql_query(query, conn)

            # Create Excel writer object
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Resume Data')

            return output.getvalue()
        except Exception as e:
            print(f"Error exporting to Excel: {str(e)}")
            return None
        finally:
            conn.close()

    
    def render_empty_state(self, icon, message):
        """Render an empty state with icon and message"""
        return f"""
            <div style='text-align: center; padding: 2rem; color: #666;'>
                <i class='{icon}' style='font-size: 2rem; margin-bottom: 1rem; color: #B886FD;'></i>
                <p style='margin: 0;'>{message}</p>
            </div>
        """

    

    

    

    
    


    
    
    def show_repo_notification(self):
        message = """
<div style="background-color: #333333; border-radius: 10px; border: 1px solid #B886FD; padding: 10px; margin: 10px 0; color: white;">
    <div style="margin-bottom: 10px;">Check out these other Courses:</div>
    <div style="margin-bottom: 5px;"><b>Development:</b></div>
    <ul style="margin-top: 0; padding-left: 20px;">
        <li><a href="https://www.ssinfotech.co/real-time-project.html" target="_blank" style="color: #B886FD;">Real Time Project Development</a></li>
        <li><a href="https://www.ssinfotech.co/softwaredev.html" target="_blank" style="color: #B886FD;">Software Development</a></li>
    </ul>
    <div style="margin-bottom: 5px;"><b>Training Programs:</b></div>
    <ul style="margin-top: 0; padding-left: 20px;">
        <li><a href="https://www.ssinfotech.co/ielts.html" target="_blank" style="color: #B886FD;">IELTS Preparation</a></li>
        <li><a href="https://www.ssinfotech.co/ielts.html" target="_blank" style="color: #B886FD;">TOFEL Preparation</a></li>
    </ul>
    <div style="margin-bottom: 5px;"><b>Job & Career Consultant</b></div>
    <ul style="margin-top: 0; padding-left: 20px;">
        <li><a href="https://www.ssinfotech.co/job.html" target="_blank" style="color: #B886FD;">Job</a></li>
        <li><a href="https://www.ssinfotech.co/career.html" target="_blank" style="color: #B886FD;">Career</a></li>
    </ul>
    <div style="margin-bottom: 5px;"><b>Contact Us:</b></div>
    <ul style="margin-top: 0; padding-left: 20px;">
        <li><a href="https://www.ssinfotech.co/Contact-Us.html" target="_blank" style="color: #B886FD;">Connect and Grow</a></li>
    </ul>
    <div style="margin-top: 10px;">If you find this project helpful, please consider ⭐ starring the Journey!</div>
</div>
"""
        st.sidebar.markdown(message, unsafe_allow_html=True)

    def render_authenticated_app(self):
        """Render the full application pages"""
        self.apply_global_styles()
        
        # Sidebar with navigation
        with st.sidebar:
            st_lottie(self.load_lottie_url("https://assets5.lottiefiles.com/packages/lf20_xyadoh9h.json"), height=200, key="sidebar_animation")
            st.title("CV Robo")
            st.markdown("---")
            
            # Navigation buttons
            for page_name in self.pages.keys():
                if st.button(page_name, use_container_width=True):
                    # FIX: Use robust mapping instead of brittle cleaning
                    st.session_state.page = self.PAGE_MAPPING.get(page_name, 'home')
                    st.rerun()

            # Add some space before admin login
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("---")

            # Admin Login/Logout section at bottom
            if st.session_state.get('is_admin', False):
                st.success(f"Logged in as: {st.session_state.get('current_admin_email')}")
                if st.button("Logout", key="logout_button"):
                    try:
                        log_admin_action(st.session_state.get('current_admin_email'), "logout")
                        st.session_state.is_admin = False
                        st.session_state.current_admin_email = None
                        st.success("Logged out successfully!")
                        # FIX: Deprecated rerun
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during logout: {str(e)}")
            else:
                with st.expander("👤 Admin Login"):
                    admin_email_input = st.text_input("Email", key="admin_email_input")
                    admin_password = st.text_input("Password", type="password", key="admin_password_input")
                    if st.button("Login", key="login_button"):
                        try:
                            if verify_admin(admin_email_input, admin_password):
                                st.session_state.is_admin = True
                                st.session_state.current_admin_email = admin_email_input
                                log_admin_action(admin_email_input, "login")
                                st.success("Logged in successfully!")
                                st.rerun()
                            else:
                                st.error("Invalid credentials")
                        except Exception as e:
                            st.error(f"Error during login: {str(e)}")
        
            # Display the repository notification in the sidebar
            self.show_repo_notification()

        # Get current page and render it
        current_page = st.session_state.get('page', 'home')
        
        # FIX: Use reverse mapping to get the original page name for lookup
        reverse_page_mapping = {v: k for k, v in self.PAGE_MAPPING.items()}
        
        # Render the appropriate page
        if current_page in reverse_page_mapping:
            original_page_name = reverse_page_mapping[current_page]
            self.pages[original_page_name](self)
        else:
            # Default to home page if invalid page
            render_home_page(self)
    
        # Add footer to every page
        self.add_footer()

    def render_login_page(self):
        """Renders the login and registration UI for a normal user."""
        st.markdown(
            f'<div class="login-container">', unsafe_allow_html=True)
        st.title("CV Robo Login")
        st.subheader("Your AI-Powered Career Partner")

        # Login and Register tabs
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        with login_tab:
            st.markdown("### Existing User Login")
            login_email = st.text_input("Email Address", key="login_email_input")
            login_password = st.text_input("Password", type="password", key="login_password_input")
            
            if st.button("Login", key="main_login_button", type="primary"):
                if login_email and login_password:
                    if verify_user(login_email, login_password):
                        st.session_state.authenticated = True
                        st.session_state.user_email = login_email
                        st.success(f"Welcome back, {login_email}!")
                        time.sleep(1) # Give time for the message to display
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                else:
                    st.error("Please enter both email and password.")

        with register_tab:
            st.markdown("### New User Registration")
            register_email = st.text_input("New Email", key="register_email_input")
            register_password = st.text_input("New Password", type="password", key="register_password_input")
            
            if st.button("Register", key="register_button", type="secondary"):
                if register_email and register_password:
                    if check_user_exists(register_email):
                        st.error("A user with that email already exists.")
                    else:
                        if add_user(register_email, register_password):
                            st.success("✅ Registration successful! Please log in.")
                            time.sleep(1)
                            # FIX: Deprecated rerun
                            st.rerun() 
                        else:
                            st.error("Failed to register. Please try again.")
                else:
                    st.error("Please enter a valid email and password.")
        
        st.markdown("</div>", unsafe_allow_html=True)

    def main(self):
        """Main application entry point"""
        # Load global styles for all pages, including login
        self.apply_global_styles()
        self.add_footer()
        
        if st.session_state.authenticated:
            # If authenticated, render the full application
            self.render_authenticated_app()
        else:
            # If not authenticated, only render the login page
            self.render_login_page()


if __name__ == "__main__":
    # Add project root to path for imports
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    # Initialize the app and run
    app = ResumeApp()
    app.main()
