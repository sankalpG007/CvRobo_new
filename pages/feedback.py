import streamlit as st
from ui_components import apply_modern_styles, page_header
from feedback.managers.feedback_manager import FeedbackManager 
from feedback.managers.feedback_manager import FeedbackManager
def render_feedback_page_page(app_instance):
        """Render the feedback page"""
        apply_modern_styles()
        
        # Page Header
        page_header(
            "Feedback & Suggestions",
            "Help us improve by sharing your thoughts"
        )
        
        # Initialize feedback manager
        feedback_manager = FeedbackManager()
        
        # Create tabs for form and stats
        form_tab, stats_tab = st.tabs(["Submit Feedback", "Feedback Stats"])
        
        with form_tab:
            feedback_manager.render_feedback_form()
            
        with stats_tab:
            feedback_manager.render_feedback_stats()

        st.toast("Check out these repositories: [Real Time Project Development ](https://www.ssinfotech.co/real-time-project.html)", icon="ℹ️")

