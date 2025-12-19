# ===============================================
# pages/home.py
# ===============================================

import streamlit as st
from ui_components import apply_modern_styles, hero_section, feature_card
import os 
import sys

# The function now accepts 'app_instance' instead of using 'self'.
def render_home_page(app_instance):
    """Renders the main application home page."""
    
    # NOTE: The content below is CUT directly from the old render_home(self)
    
    apply_modern_styles()
    
    # Hero Section
    hero_section(
        "CV Robo",
        "Transform your career with AI-powered resume analysis and building. Get personalized insights and create professional resumes that stand out."
    )
    
    # Features Section
    st.markdown('<div class="feature-grid">', unsafe_allow_html=True)
    
    feature_card(
        "fas fa-robot",
        "AI-Powered Analysis",
        "Get instant feedback on your resume with advanced AI analysis that identifies strengths and areas for improvement."
    )
    
    feature_card(
        "fas fa-magic",
        "Smart Resume Builder",
        "Create professional resumes with our intelligent builder that suggests optimal content and formatting."
    )
    
    feature_card(
        "fas fa-chart-line",
        "Career Insights",
        "Access detailed analytics and personalized recommendations to enhance your career prospects."
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.toast("Check out these : [SS-INFOTECH (AI/ML)](https://www.ssinfotech.co/)", icon="ℹ️")

    # Call-to-Action with Streamlit navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Get Started", key="get_started_btn", 
                     help="Click to start analyzing your resume",
                     type="primary",
                     use_container_width=True):
            # FIX: Use the clean, standardized page key 'analyzer'
            st.session_state.page = 'analyzer' 
            st.rerun()

# We only export the main rendering function
# The old self.render_home is now render_home_page