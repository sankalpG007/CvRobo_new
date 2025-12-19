import streamlit as st
from jobs.services.job_search_service import render_job_search 
def render_job_search_page(app_instance):
        """Render the job search page"""
        render_job_search()

        st.toast("Check out these repositories: [Real Time Project Development](https://github.com/sankalpG007/Real-Time-Project-Development)", icon="ℹ️")
