import streamlit as st
import streamlit as st
def render_dashboard_page(app_instance):
        """Render the dashboard page"""
        app_instance.dashboard_manager.render_dashboard()

        st.toast("Check out these repositories: [Awesome-CV-Robo](https://github.com/sankalpG007/CV-Robo)", icon="ℹ️")
