import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import traceback as tb # Needed for error logging

# Import constants and utilities used directly in the function
from config.job_roles import JOB_ROLES 
from config.courses import COURSES_BY_CATEGORY, RESUME_VIDEOS, INTERVIEW_VIDEOS, get_courses_for_role, get_category_for_role
from config.database import save_resume_data, save_analysis_data, save_ai_analysis_data, get_detailed_ai_analysis_stats, reset_ai_analysis_stats

# Import components/functions from your main app structure
from ui_components import apply_modern_styles, page_header 
from utils.ai_resume_analyzer import AIResumeAnalyzer 
from utils.resume_analyzer import ResumeAnalyzer

def render_analyzer_page(app_instance):
        """Render the resume analyzer page"""
        apply_modern_styles()

        # Page Header
        page_header(
            "Resume Analyzer",
            "Get instant AI-powered feedback to optimize your resume"
        )

        # Create tabs for Normal Analyzer and AI Analyzer
        analyzer_tabs = st.tabs(["Standard Analyzer", "AI Analyzer"])

        with analyzer_tabs[0]:
            # Job Role Selection
            categories = list(app_instance.job_roles.keys())
            selected_category = st.selectbox(
    "Job Category", categories, key="standard_category")

            roles = list(app_instance.job_roles[selected_category].keys())
            selected_role = st.selectbox(
    "Specific Role", roles, key="standard_role")

            role_info = app_instance.job_roles[selected_category][selected_role]

            # Display role information
            st.markdown(f"""
            <div style='background-color: #333333; padding: 20px; border-radius: 10px; margin: 10px 0;'>
                <h3>{selected_role}</h3>
                <p>{role_info['description']}</p>
                <h4>Required Skills:</h4>
                <p>{', '.join(role_info['required_skills'])}</p>
            </div>
            """, unsafe_allow_html=True)

            # File Upload
            uploaded_file = st.file_uploader(
    "Upload your resume", type=[
        'pdf', 'docx'], key="standard_file")

            if not uploaded_file:
                # Display empty state with a prominent upload button
                st.markdown(
                    app_instance.render_empty_state(
                    "fas fa-cloud-upload-alt",
                    "Upload your resume to get started with standard analysis"
                    ),
                    unsafe_allow_html=True
                )
                # Add a prominent upload button
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown("""
                    <style>
                    .upload-button {
                        background: linear-gradient(90deg, #B886FD, #5d35b2);
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 15px 25px;
                        font-size: 18px;
                        font-weight: bold;
                        cursor: pointer;
                        width: 100%;
                        text-align: center;
                        margin: 20px 0;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                        transition: all 0.3s ease;
                    }
                    .upload-button:hover {
                        transform: translateY(-3px);
                        box-shadow: 0 6px 15px rgba(0,0,0,0.3);
                    }

                    """, unsafe_allow_html=True)

            if uploaded_file:
                # Add a prominent analyze button
                analyze_standard = st.button("🔍 Analyze My Resume",
                                         type="primary",
                                         use_container_width=True,
                                         key="analyze_standard_button")

                if analyze_standard:
                    with st.spinner("Analyzing your document..."):
                        # Get file content
                        text = ""
                        try:
                            if uploaded_file.type == "application/pdf":
                                try:
                                    text = app_instance.analyzer.extract_text_from_pdf(uploaded_file)
                                except Exception as pdf_error:
                                    st.error(f"PDF extraction failed: {str(pdf_error)}")
                                    st.info("Trying alternative PDF extraction method...")
                                    # Try AI analyzer as backup
                                    try:
                                        text = app_instance.ai_analyzer.extract_text_from_pdf(uploaded_file)
                                    except Exception as backup_error:
                                        st.error(f"All PDF extraction methods failed: {str(backup_error)}")
                                        return
                            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                                try:
                                    text = app_instance.analyzer.extract_text_from_docx(uploaded_file)
                                except Exception as docx_error:
                                    st.error(f"DOCX extraction failed: {str(docx_error)}")
                                    # Try AI analyzer as backup
                                    try:
                                        text = app_instance.ai_analyzer.extract_text_from_docx(uploaded_file)
                                    except Exception as backup_error:
                                        st.error(f"All DOCX extraction methods failed: {str(backup_error)}")
                                        return
                            else:
                                text = uploaded_file.getvalue().decode()
                                
                            if not text or text.strip() == "":
                                st.error("Could not extract any text from the uploaded file. Please try a different file.")
                                return
                        except Exception as e:
                            st.error(f"Error reading file: {str(e)}")
                            return

                        # Analyze the document
                        analysis = app_instance.analyzer.analyze_resume({'raw_text': text}, role_info)
                        
                        # Check if analysis returned an error
                        if 'error' in analysis:
                            st.error(analysis['error'])
                            return

                        # Show snowflake effect
                        st.snow()

                        # Save resume data to database
                        resume_data = {
                            'personal_info': {
                                'name': analysis.get('name', ''),
                                'email': analysis.get('email', ''),
                                'phone': analysis.get('phone', ''),
                                'linkedin': analysis.get('linkedin', ''),
                                'github': analysis.get('github', ''),
                                'portfolio': analysis.get('portfolio', '')
                            },
                            'summary': analysis.get('summary', ''),
                            'target_role': selected_role,
                            'target_category': selected_category,
                            'education': analysis.get('education', []),
                            'experience': analysis.get('experience', []),
                            'projects': analysis.get('projects', []),
                            'skills': analysis.get('skills', []),
                            'template': ''
                        }

                        # Save to database
                        try:
                            resume_id = save_resume_data(resume_data)

                            # Save analysis data
                            analysis_data = {
                                'resume_id': resume_id,
                                'ats_score': analysis['ats_score'],
                                'keyword_match_score': analysis['keyword_match']['score'],
                                'format_score': analysis['format_score'],
                                'section_score': analysis['section_score'],
                                'missing_skills': ','.join(analysis['keyword_match']['missing_skills']),
                                'recommendations': ','.join(analysis['suggestions'])
                            }
                            save_analysis_data(resume_id, analysis_data)
                            st.success("Resume data saved successfully!")
                        except Exception as e:
                            st.error(f"Error saving to database: {str(e)}")
                            print(f"Database error: {e}")

                        # Show results based on document type
                        if analysis.get('document_type') != 'resume':
                            st.error(f"⚠️ This appears to be a {analysis['document_type']} document, not a resume!")
                            st.warning(
                                "Please upload a proper resume for ATS analysis.")
                            return
                        # Display results in a modern card layout
                    col1, col2 = st.columns(2)

                    with col1:
                        # ATS Score Card with circular progress
                        st.markdown("""
                        <div class="feature-card">
                            <h2>ATS Score</h2>
                            <div style="position: relative; width: 150px; height: 150px; margin: 0 auto;">
                                <div style="
                                    position: absolute;
                                    width: 150px;
                                    height: 150px;
                                    border-radius: 50%;
                                    background: conic-gradient(
                                        #B886FD 0% {score}%,
                                        #2c2c2c {score}% 100%
                                    );
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                ">
                                    <div style="
                                        width: 120px;
                                        height: 120px;
                                        background: #1a1a1a;
                                        border-radius: 50%;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        font-size: 24px;
                                        font-weight: bold;
                                        color: {color};
                                    ">
                                        {score}
                                    </div>
                                </div>
                            </div>
                            <div style="text-align: center; margin-top: 10px;">
                                <span style="
                                    font-size: 1.2em;
                                    color: {color};
                                    font-weight: bold;
                                ">
                                    {status}
                                </span>
                            </div>
                        """.format(
                            score=analysis['ats_score'],
                            color='#B886FD' if analysis['ats_score'] >= 80 else '#FFA500' if analysis[
                                'ats_score'] >= 60 else '#FF4444',
                            status='Excellent' if analysis['ats_score'] >= 80 else 'Good' if analysis[
                                'ats_score'] >= 60 else 'Needs Improvement'
                        ), unsafe_allow_html=True)

                        st.markdown("</div>", unsafe_allow_html=True)

                        # app_instance.display_analysis_results(analysis_results)

                        # Skills Match Card
                        st.markdown("""
                        <div class="feature-card">
                            <h2>Skills Match</h2>
                        """, unsafe_allow_html=True)

                        st.metric(
                            "Keyword Match", f"{int(analysis.get('keyword_match', {}).get('score', 0))}%")

                        if analysis['keyword_match']['missing_skills']:
                            st.markdown("#### Missing Skills:")
                            for skill in analysis['keyword_match']['missing_skills']:
                                st.markdown(f"- {skill}")

                        st.markdown("</div>", unsafe_allow_html=True)

                    with col2:
                        # Format Score Card
                        st.markdown("""
                        <div class="feature-card">
                            <h2>Format Analysis</h2>
                        """, unsafe_allow_html=True)

                        st.metric("Format Score",
                                  f"{int(analysis.get('format_score', 0))}%")
                        st.metric("Section Score",
                                  f"{int(analysis.get('section_score', 0))}%")

                        st.markdown("</div>", unsafe_allow_html=True)

                        # Suggestions Card with improved UI
                        st.markdown("""
                        <div class="feature-card">
                            <h2>📋 Resume Improvement Suggestions</h2>
                        """, unsafe_allow_html=True)

                        # Contact Section
                        if analysis.get('contact_suggestions'):
                            st.markdown("""
                                <div style='background-color: #333333; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                                    <h3 style='color: #B886FD; margin-bottom: 10px;'>📞 Contact Information</h3>
                                    <ul style='list-style-type: none; padding-left: 0;'>
                                """, unsafe_allow_html=True)
                            for suggestion in analysis.get(
                                'contact_suggestions', []):
                                st.markdown(
    f"<li style='margin-bottom: 8px;'>✓ {suggestion}</li>",
    unsafe_allow_html=True)
                            st.markdown(
    "</ul></div>", unsafe_allow_html=True)

                        # Summary Section
                        if analysis.get('summary_suggestions'):
                            st.markdown("""
                                <div style='background-color: #333333; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                                    <h3 style='color: #B886FD; margin-bottom: 10px;'>📝 Professional Summary</h3>
                                    <ul style='list-style-type: none; padding-left: 0;'>
                                """, unsafe_allow_html=True)
                            for suggestion in analysis.get(
                                'summary_suggestions', []):
                                st.markdown(
    f"<li style='margin-bottom: 8px;'>✓ {suggestion}</li>",
    unsafe_allow_html=True)
                            st.markdown(
    "</ul></div>", unsafe_allow_html=True)

                        # Skills Section
                        if analysis.get(
                                'skills_suggestions') or analysis['keyword_match']['missing_skills']:
                            st.markdown("""
                                <div style='background-color: #333333; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                                    <h3 style='color: #B886FD; margin-bottom: 10px;'>🎯 Skills</h3>
                                    <ul style='list-style-type: none; padding-left: 0;'>
                                """, unsafe_allow_html=True)
                            for suggestion in analysis.get(
                                'skills_suggestions', []):
                                st.markdown(
    f"<li style='margin-bottom: 8px;'>✓ {suggestion}</li>",
    unsafe_allow_html=True)
                            if analysis['keyword_match']['missing_skills']:
                                st.markdown(
    "<li style='margin-bottom: 8px;'>✓ Consider adding these relevant skills:</li>",
    unsafe_allow_html=True)
                                for skill in analysis['keyword_match']['missing_skills']:
                                    st.markdown(
    f"<li style='margin-left: 20px; margin-bottom: 4px;'>• {skill}</li>",
    unsafe_allow_html=True)
                            st.markdown(
    "</ul></div>", unsafe_allow_html=True)

                        # Experience Section
                        if analysis.get('experience_suggestions'):
                            st.markdown("""
                                <div style='background-color: #333333; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                                    <h3 style='color: #B886FD; margin-bottom: 10px;'>💼 Work Experience</h3>
                                    <ul style='list-style-type: none; padding-left: 0;'>
                                """, unsafe_allow_html=True)
                            for suggestion in analysis.get(
                                'experience_suggestions', []):
                                st.markdown(
    f"<li style='margin-bottom: 8px;'>✓ {suggestion}</li>",
    unsafe_allow_html=True)
                            st.markdown(
    "</ul></div>", unsafe_allow_html=True)

                        # Education Section
                        if analysis.get('education_suggestions'):
                            st.markdown("""
                                <div style='background-color: #333333; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                                    <h3 style='color: #B886FD; margin-bottom: 10px;'>🎓 Education</h3>
                                    <ul style='list-style-type: none; padding-left: 0;'>
                                """, unsafe_allow_html=True)
                            for suggestion in analysis.get(
                                'education_suggestions', []):
                                st.markdown(
    f"<li style='margin-bottom: 8px;'>✓ {suggestion}</li>",
    unsafe_allow_html=True)
                            st.markdown(
    "</ul></div>", unsafe_allow_html=True)

                        # General Formatting Suggestions
                        if analysis.get('format_suggestions'):
                            st.markdown("""
                                <div style='background-color: #333333; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                                    <h3 style='color: #B886FD; margin-bottom: 10px;'>📄 Formatting</h3>
                                    <ul style='list-style-type: none; padding-left: 0;'>
                                """, unsafe_allow_html=True)
                            for suggestion in analysis.get(
                                'format_suggestions', []):
                                st.markdown(
    f"<li style='margin-bottom: 8px;'>✓ {suggestion}</li>",
    unsafe_allow_html=True)
                            st.markdown(
    "</ul></div>", unsafe_allow_html=True)

                        st.markdown("</div>", unsafe_allow_html=True)

                        # Course Recommendations
                    st.markdown("""
                        <div class="feature-card">
                            <h2>📚 Recommended Courses</h2>
                        """, unsafe_allow_html=True)

                    # Get courses based on role and category
                    courses = get_courses_for_role(selected_role)
                    if not courses:
                        category = get_category_for_role(selected_role)
                        courses = COURSES_BY_CATEGORY.get(
                            category, {}).get(selected_role, [])

                    # Display courses in a grid
                    cols = st.columns(2)
                    for i, course in enumerate(
                        courses[:6]):  # Show top 6 courses
                        with cols[i % 2]:
                            st.markdown(f"""
                                <div style='background-color: #333333; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                                    <h4>{course[0]}</h4>
                                    <a href='{course[1]}' target='_blank'>View Course</a>
                                </div>
                                """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                        # Learning Resources
                    st.markdown("""
                        <div class="feature-card">
                            <h2>📺 Helpful Videos</h2>
                        """, unsafe_allow_html=True)

                    tab1, tab2 = st.tabs(["Resume Tips", "Interview Tips"])

                    with tab1:
                        # Resume Videos
                        for category, videos in RESUME_VIDEOS.items():
                            st.subheader(category)
                            cols = st.columns(2)
                            for i, video in enumerate(videos):
                                with cols[i % 2]:
                                    st.video(video[1])

                    with tab2:
                        # Interview Videos
                        for category, videos in INTERVIEW_VIDEOS.items():
                            st.subheader(category)
                            cols = st.columns(2)
                            for i, video in enumerate(videos):
                                with cols[i % 2]:
                                    st.video(video[1])

                    st.markdown("</div>", unsafe_allow_html=True)

            with analyzer_tabs[1]:
                st.markdown("""
                <div style='background-color: #333333; padding: 20px; border-radius: 10px; margin: 10px 0;'>
                    <h3>AI-Powered Resume Analysis</h3>
                    <p>Get detailed insights from advanced AI models that analyze your resume and provide personalized recommendations.</p>
                    <p><strong>Upload your resume to get AI-powered analysis and recommendations.</strong></p>
                </div>
                """, unsafe_allow_html=True)

                # AI Model Selection
                ai_model = st.selectbox(
                    "Select AI Model",
                    ["Google Gemini"],
                    help="Choose the AI model to analyze your resume"
                )
                    
                # Add job description input option
                use_custom_job_desc = st.checkbox("Use custom job description", value=False, 
                                                help="Enable this to provide a specific job description for more targeted analysis")
                    
                custom_job_description = ""
                if use_custom_job_desc:
                    custom_job_description = st.text_area(
                        "Paste the job description here",
                        height=200,
                        placeholder="Paste the full job description from the company here for more targeted analysis...",
                        help="Providing the actual job description will help the AI analyze your resume specifically for this position"
                    )
                        
                    st.markdown("""
                    <div style='background-color: #5d35b2; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                        <p><i class="fas fa-lightbulb"></i> <strong>Pro Tip:</strong> Including the actual job description significantly improves the accuracy of the analysis and provides more relevant recommendations tailored to the specific position.</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                        # Add AI Analyzer Stats in an expander
                with st.expander("📊 AI Analyzer Statistics", expanded=False):
                    try:
                        # Add a reset button for admin users
                        if st.session_state.get('is_admin', False):
                            if st.button(
    "🔄 Reset AI Analysis Statistics",
    type="secondary",
    key="reset_ai_stats_button_2"):
                                from config.database import reset_ai_analysis_stats
                                result = reset_ai_analysis_stats()
                                if result["success"]:
                                    st.success(result["message"])
                                else:
                                    st.error(result["message"])
                                # Refresh the page to show updated stats
                                st.rerun()

                        # Get detailed AI analysis statistics
                        from config.database import get_detailed_ai_analysis_stats
                        ai_stats = get_detailed_ai_analysis_stats()

                        if ai_stats["total_analyses"] > 0:
                            # Create a more visually appealing layout
                            st.markdown("""
                            <style>
                            .stats-card {
                                background: linear-gradient(135deg, #5d35b2, #B886FD);
                                border-radius: 10px;
                                padding: 15px;
                                margin-bottom: 15px;
                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                text-align: center;
                            }
                            .stats-value {
                                font-size: 28px;
                                font-weight: bold;
                                color: white;
                                margin: 10px 0;
                            }
                            .stats-label {
                                font-size: 14px;
                                color: rgba(255, 255, 255, 0.8);
                                text-transform: uppercase;
                                letter-spacing: 1px;
                            }
                            .score-card {
                                background: linear-gradient(135deg, #11998e, #38ef7d);
                                border-radius: 10px;
                                padding: 15px;
                                margin-bottom: 15px;
                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                text-align: center;
                            }
                            </style>
                            """, unsafe_allow_html=True)

                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.markdown(f"""
                                <div class="stats-card">
                                    <div class="stats-label">Total AI Analyses</div>
                                    <div class="stats-value">{ai_stats["total_analyses"]}</div>
                                </div>
                                """, unsafe_allow_html=True)

                            with col2:
                                # Determine color based on score
                                score_color = "#38ef7d" if ai_stats["average_score"] >= 80 else "#FFEB3B" if ai_stats[
                                    "average_score"] >= 60 else "#FF5252"
                                st.markdown(f"""
                                <div class="stats-card" style="background: linear-gradient(135deg, #2c3e50, {score_color});">
                                    <div class="stats-label">Average Resume Score</div>
                                    <div class="stats-value">{ai_stats["average_score"]}/100</div>
                                </div>
                                """, unsafe_allow_html=True)

                            with col3:
                                # Create a gauge chart for average score
                                import plotly.graph_objects as go
                                fig = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=ai_stats["average_score"],
                                    domain={'x': [0, 1], 'y': [0, 1]},
                                    title={
    'text': "Score", 'font': {
        'size': 14, 'color': 'white'}},
                                    gauge={
                                        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                                        'bar': {'color': "#38ef7d" if ai_stats["average_score"] >= 80 else "#FFEB3B" if ai_stats["average_score"] >= 60 else "#FF5252"},
                                        'bgcolor': "rgba(0,0,0,0)",
                                        'borderwidth': 2,
                                        'bordercolor': "white",
                                        'steps': [
                                            {'range': [
                                                0, 40], 'color': 'rgba(255, 82, 82, 0.3)'},
                                            {'range': [
                                                40, 70], 'color': 'rgba(255, 235, 59, 0.3)'},
                                            {'range': [
                                                70, 100], 'color': 'rgba(56, 239, 125, 0.3)'}
                                        ],
                                    }
                                ))

                                fig.update_layout(
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font={'color': "white"},
                                    height=150,
                                    margin=dict(l=10, r=10, t=30, b=10)
                                )

                                st.plotly_chart(fig, use_container_width=True)

                            # Display model usage with enhanced visualization
                            if ai_stats["model_usage"]:
                                st.markdown("### 🤖 Model Usage")
                                model_data = pd.DataFrame(ai_stats["model_usage"])

                                # Create a more colorful pie chart
                                import plotly.express as px
                                fig = px.pie(
                                    model_data,
                                    values="count",
                                    names="model",
                                    color_discrete_sequence=px.colors.qualitative.Bold,
                                    hole=0.4
                                )

                                fig.update_traces(
                                    textposition='inside',
                                    textinfo='percent+label',
                                    marker=dict(
    line=dict(
        color='#000000',
        width=1.5))
                                )

                                fig.update_layout(
                                    margin=dict(l=20, r=20, t=30, b=20),
                                    height=300,
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color="#ffffff", size=14),
                                    legend=dict(
                                        orientation="h",
                                        yanchor="bottom",
                                        y=-0.1,
                                        xanchor="center",
                                        x=0.5
                                    ),
                                    title={
                                        'text': 'AI Model Distribution',
                                        'y': 0.95,
                                        'x': 0.5,
                                        'xanchor': 'center',
                                        'yanchor': 'top',
                                        'font': {'size': 18, 'color': 'white'}
                                    }
                                )

                                st.plotly_chart(fig, use_container_width=True)

                            # Display top job roles with enhanced visualization
                            if ai_stats["top_job_roles"]:
                                st.markdown("### 🎯 Top Job Roles")
                                roles_data = pd.DataFrame(
                                    ai_stats["top_job_roles"])

                                # Create a more colorful bar chart
                                fig = px.bar(
                                    roles_data,
                                    x="role",
                                    y="count",
                                    color="count",
                                    color_continuous_scale=px.colors.sequential.Viridis,
                                    labels={
    "role": "Job Role", "count": "Number of Analyses"}
                                )

                                fig.update_traces(
                                    marker_line_width=1.5,
                                    marker_line_color="white",
                                    opacity=0.9
                                )

                                fig.update_layout(
                                    margin=dict(l=20, r=20, t=50, b=30),
                                    height=350,
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color="#ffffff", size=14),
                                    title={
                                        'text': 'Most Analyzed Job Roles',
                                        'y': 0.95,
                                        'x': 0.5,
                                        'xanchor': 'center',
                                        'yanchor': 'top',
                                        'font': {'size': 18, 'color': 'white'}
                                    },
                                    xaxis=dict(
                                        title="",
                                        tickangle=-45,
                                        tickfont=dict(size=12)
                                    ),
                                    yaxis=dict(
                                        title="Number of Analyses",
                                        gridcolor="rgba(255, 255, 255, 0.1)"
                                    ),
                                    coloraxis_showscale=False
                                )

                                st.plotly_chart(fig, use_container_width=True)

                                # Add a timeline chart for analysis over time (mock
                                # data for now)
                            st.markdown("### 📈 Analysis Trend")
                            st.info(
                                "This is a conceptual visualization. To implement actual time-based analysis, additional data collection would be needed.")

                            # Create mock data for timeline
                            import datetime
                            import numpy as np

                            today = datetime.datetime.now()
                            dates = [
    (today -
    datetime.timedelta(
        days=i)).strftime('%Y-%m-%d') for i in range(7)]
                            dates.reverse()

                            # Generate some random data that sums to
                            # total_analyses
                            total = ai_stats["total_analyses"]
                            if total > 7:
                                values = np.random.dirichlet(
                                    np.ones(7)) * total
                                values = [round(v) for v in values]
                                # Adjust to make sure sum equals total
                                diff = total - sum(values)
                                values[-1] += diff
                            else:
                                values = [0] * 7
                                for i in range(total):
                                    values[-(i % 7) - 1] += 1

                            trend_data = pd.DataFrame({
                                'Date': dates,
                                'Analyses': values
                            })

                            fig = px.line(
                                trend_data,
                                x='Date',
                                y='Analyses',
                                markers=True,
                                line_shape='spline',
                                color_discrete_sequence=["#B886FD"]
                            )

                            fig.update_traces(
                                line=dict(width=3),
                                marker=dict(
    size=8, line=dict(
        width=2, color='white'))
                            )

                            fig.update_layout(
                                margin=dict(l=20, r=20, t=50, b=30),
                                height=300,
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color="#ffffff", size=14),
                                title={
                                    'text': 'Analysis Activity (Last 7 Days)',
                                    'y': 0.95,
                                    'x': 0.5,
                                    'xanchor': 'center',
                                    'yanchor': 'top',
                                    'font': {'size': 18, 'color': 'white'}
                                },
                                xaxis=dict(
                                    title="",
                                    gridcolor="rgba(255, 255, 255, 0.1)"
                                ),
                                yaxis=dict(
                                    title="Number of Analyses",
                                    gridcolor="rgba(255, 255, 255, 0.1)"
                                )
                            )

                            st.plotly_chart(fig, use_container_width=True)

                            # Display score distribution if available
                            if ai_stats["score_distribution"]:
                                st.markdown("""
                                <h3 style='text-align: center; margin-bottom: 20px; background: linear-gradient(90deg, #B886FD, #5d35b2); padding: 15px; border-radius: 10px; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.2);'>
                                    📊 Score Distribution Analysis
                                </h3>
                                """, unsafe_allow_html=True)

                                score_data = pd.DataFrame(
                                    ai_stats["score_distribution"])

                                # Create a more visually appealing bar chart for
                                # score distribution
                                fig = px.bar(
                                    score_data,
                                    x="range",
                                    y="count",
                                    color="range",
                                    color_discrete_map={
                                        "0-20": "#FF5252",
                                        "21-40": "#FF7043",
                                        "41-60": "#FFEB3B",
                                        "61-80": "#8BC34A",
                                        "81-100": "#B886FD"
                                    },
                                    labels={
    "range": "Score Range",
    "count": "Number of Resumes"},
                                    text="count"  # Display count values on bars
                                )

                                fig.update_traces(
                                    marker_line_width=2,
                                    marker_line_color="white",
                                    opacity=0.9,
                                    textposition='outside',
                                    textfont=dict(
    color="white", size=14, family="Arial, sans-serif"),
                                    hovertemplate="<b>Score Range:</b> %{x}<br><b>Number of Resumes:</b> %{y}<extra></extra>"
                                )

                                # Add a gradient background to the chart
                                fig.update_layout(
                                    margin=dict(l=20, r=20, t=50, b=30),
                                    height=400,  # Increase height for better visibility
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(
    color="#ffffff", size=14, family="Arial, sans-serif"),
                                    xaxis=dict(
                                        title=dict(
    text="Score Range", font=dict(
        size=16, color="white")),
                                        categoryorder="array",
                                        categoryarray=[
    "0-20", "21-40", "41-60", "61-80", "81-100"],
                                        tickfont=dict(size=14, color="white"),
                                        gridcolor="rgba(255, 255, 255, 0.1)"
                                    ),
                                    yaxis=dict(
                                        title=dict(
    text="Number of Resumes", font=dict(
        size=16, color="white")),
                                        tickfont=dict(size=14, color="white"),
                                        gridcolor="rgba(255, 255, 255, 0.1)",
                                        zeroline=False
                                    ),
                                    showlegend=False,
                                    bargap=0.2,  # Adjust gap between bars
                                    shapes=[
                                        # Add gradient background
                                        dict(
                                            type="rect",
                                            xref="paper",
                                            yref="paper",
                                            x0=0,
                                            y0=0,
                                            x1=1,
                                            y1=1,
                                            fillcolor="rgba(26, 26, 44, 0.5)",
                                            layer="below",
                                            line_width=0,
                                        )
                                    ]
                                )

                                st.plotly_chart(fig, use_container_width=True)

                                # Add descriptive text below the chart
                                st.markdown("""
                                <p style='color: white; text-align: center; font-style: italic; margin-top: 10px;'>
                                    This chart shows the distribution of resume scores across different ranges, helping identify common performance levels.
                                </p>
                                </div>
                                """, unsafe_allow_html=True)

                            # Display recent analyses if available
                            if ai_stats["recent_analyses"]:
                                st.markdown("""
                                <h3 style='text-align: center; margin-bottom: 20px; background: linear-gradient(90deg, #B886FD, #5d35b2); padding: 15px; border-radius: 10px; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.2);'>
                                    🕒 Recent Resume Analyses
                                </h3>
                                """, unsafe_allow_html=True)

                                # Create a more modern styled table for recent
                                # analyses
                                st.markdown("""
                                <style>
                                .modern-analyses-table {
                                    width: 100%;
                                    border-collapse: separate;
                                    border-spacing: 0 8px;
                                    margin-bottom: 20px;
                                    font-family: 'Arial', sans-serif;
                                }
                                .modern-analyses-table th {
                                    background: linear-gradient(135deg, #1e3c72, #2a5298);
                                    color: white;
                                    padding: 15px;
                                    text-align: left;
                                    font-weight: bold;
                                    font-size: 14px;
                                    text-transform: uppercase;
                                    letter-spacing: 1px;
                                    border-radius: 8px;
                                }
                                .modern-analyses-table td {
                                    padding: 15px;
                                    background-color: rgba(30, 30, 30, 0.7);
                                    border-top: 1px solid rgba(255, 255, 255, 0.05);
                                    border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                                    color: white;
                                }
                                .modern-analyses-table tr td:first-child {
                                    border-top-left-radius: 8px;
                                    border-bottom-left-radius: 8px;
                                }
                                .modern-analyses-table tr td:last-child {
                                    border-top-right-radius: 8px;
                                    border-bottom-right-radius: 8px;
                                }
                                .modern-analyses-table tr:hover td {
                                    background-color: rgba(60, 60, 60, 0.7);
                                    transform: translateY(-2px);
                                    transition: all 0.2s ease;
                                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
                                }
                                .model-badge {
                                    display: inline-block;
                                    padding: 6px 12px;
                                    border-radius: 20px;
                                    font-weight: bold;
                                    text-align: center;
                                    font-size: 12px;
                                    letter-spacing: 0.5px;
                                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                                }
                                .model-gemini {
                                    background: linear-gradient(135deg, #B886FD, #5d35b2);
                                    color: white;
                                }
                                .model-claude {
                                    background: linear-gradient(135deg, #834d9b, #d04ed6);
                                    color: white;
                                }
                                .score-pill {
                                    display: inline-block;
                                    padding: 8px 15px;
                                    border-radius: 20px;
                                    font-weight: bold;
                                    text-align: center;
                                    min-width: 70px;
                                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                                }
                                .score-high {
                                    background: linear-gradient(135deg, #905dcf, #B886FD);
                                    color: white;
                                }
                                .score-medium {
                                    background: linear-gradient(135deg, #f2994a, #f2c94c);
                                    color: white;
                                }
                                .score-low {
                                    background: linear-gradient(135deg, #cb2d3e, #ef473a);
                                    color: white;
                                }
                                .date-badge {
                                    display: inline-block;
                                    padding: 6px 12px;
                                    border-radius: 20px;
                                    background-color: rgba(255, 255, 255, 0.1);
                                    color: #e0e0e0;
                                    font-size: 12px;
                                }
                                .role-badge {
                                    display: inline-block;
                                    padding: 6px 12px;
                                    border-radius: 8px;
                                    background-color: rgba(33, 150, 243, 0.2);
                                    color: #90caf9;
                                    font-size: 13px;
                                    max-width: 200px;
                                    white-space: nowrap;
                                    overflow: hidden;
                                    text-overflow: ellipsis;
                                }
                                </style>

                                <div style='background: linear-gradient(135deg, #5d35b2, #B886FD); padding: 20px; border-radius: 15px; margin: 10px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.2);'>
                                <table class="modern-analyses-table">
                                    <tr>
                                        <th>AI Model</th>
                                        <th>Score</th>
                                        <th>Job Role</th>
                                        <th>Date</th>
                                    </tr>
                                """, unsafe_allow_html=True)

                                for analysis in ai_stats["recent_analyses"]:
                                    score = analysis["score"]
                                    score_class = "score-high" if score >= 80 else "score-medium" if score >= 60 else "score-low"

                                    # Determine model class
                                    model_name = analysis["model"]
                                    model_class = "model-gemini" if "Gemini" in model_name else "model-claude" if "Claude" in model_name else ""

                                    # Format the date
                                    try:
                                        from datetime import datetime
                                        date_obj = datetime.strptime(
                                            analysis["date"], "%Y-%m-%d %H:%M:%S")
                                        formatted_date = date_obj.strftime(
                                            "%b %d, %Y")
                                    except:
                                        formatted_date = analysis["date"]

                                    st.markdown(f"""
                                    <tr>
                                        <td><div class="model-badge {model_class}">{model_name}</div></td>
                                        <td><div class="score-pill {score_class}">{score}/100</div></td>
                                        <td><div class="role-badge">{analysis["job_role"]}</div></td>
                                        <td><div class="date-badge">{formatted_date}</div></td>
                                    </tr>
                                    """, unsafe_allow_html=True)

                                st.markdown("""
                                </table>

                                <p style='color: white; text-align: center; font-style: italic; margin-top: 15px;'>
                                    These are the most recent resume analyses performed by our AI models.
                                </p>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info(
                                "No AI analysis data available yet. Upload and analyze resumes to see statistics here.")
                    except Exception as e:
                        st.error(f"Error loading AI analysis statistics: {str(e)}")
                        import traceback as tb
                        st.code(tb.format_exc())

                # Job Role Selection for AI Analysis
                categories = list(app_instance.job_roles.keys())
                selected_category = st.selectbox(
    "Job Category", categories, key="ai_category")

                roles = list(app_instance.job_roles[selected_category].keys())
                selected_role = st.selectbox("Specific Role", roles, key="ai_role")

                role_info = app_instance.job_roles[selected_category][selected_role]

                # Display role information
                st.markdown(f"""
                <div style='background-color: #333333; padding: 20px; border-radius: 10px; margin: 10px 0;'>
                    <h3>{selected_role}</h3>
                    <p>{role_info['description']}</p>
                    <h4>Required Skills:</h4>
                    <p>{', '.join(role_info['required_skills'])}</p>
                </div>
                """, unsafe_allow_html=True)

                # File Upload for AI Analysis
                uploaded_file = st.file_uploader(
    "Upload your resume", type=[
        'pdf', 'docx'], key="ai_file")

                if not uploaded_file:
                # Display empty state with a prominent upload button
                    st.markdown(
                    app_instance.render_empty_state(
                    "fas fa-robot",
                                 "Upload your resume to get AI-powered analysis and recommendations"
                    ),
                    unsafe_allow_html=True
    )
                else:
                    # Add a prominent analyze button
                    analyze_ai = st.button("🤖 Analyze with AI",
                                           type="primary",
                                           use_container_width=True,
                                           key="analyze_ai_button")

                    if analyze_ai:
                        with st.spinner(f"Analyzing your resume with {ai_model}..."):
                            # Get file content
                            text = ""
                            try:
                                if uploaded_file.type == "application/pdf":
                                    text = app_instance.analyzer.extract_text_from_pdf(
                                        uploaded_file)
                                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                                    text = app_instance.analyzer.extract_text_from_docx(
                                        uploaded_file)
                                else:
                                    # For text files or other formats
                                    text = uploaded_file.getvalue().decode('utf-8')
                            except Exception as e:
                                st.error(f"Error reading file: {str(e)}")
                                st.stop()

                            # Analyze with AI
                            try:
                                # Show a loading animation
                                with st.spinner("🧠 AI is analyzing your resume..."):
                                    progress_bar = st.progress(0)
                                    
                                    # Get the selected model
                                    selected_model = "Google Gemini"
                                    
                                    # Update progress
                                    progress_bar.progress(10)
                                    
                                    # Extract text from the resume
                                    analyzer = AIResumeAnalyzer()
                                    if uploaded_file.type == "application/pdf":
                                        resume_text = analyzer.extract_text_from_pdf(
                                            uploaded_file)
                                    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                                        resume_text = analyzer.extract_text_from_docx(
                                            uploaded_file)
                                    else:
                                        # For text files or other formats
                                        resume_text = uploaded_file.getvalue().decode('utf-8')
                                    
                                    # Initialize the AI analyzer (moved after text extraction)
                                    progress_bar.progress(30)
                                    
                                    # Get the job role
                                    job_role = selected_role if selected_role else "Not specified"
                                    
                                    # Update progress
                                    progress_bar.progress(50)
                                    
                                    # Analyze the resume with Google Gemini
                                    if use_custom_job_desc and custom_job_description:
                                        # Use custom job description for analysis
                                        analysis_result = analyzer.analyze_resume_with_gemini(
                                            resume_text, job_role=job_role, job_description=custom_job_description)
                                        # Show that custom job description was used
                                        st.session_state['used_custom_job_desc'] = True
                                    else:
                                        # Use standard role-based analysis
                                        analysis_result = analyzer.analyze_resume_with_gemini(
                                            resume_text, job_role=job_role)
                                        st.session_state['used_custom_job_desc'] = False

                                    
                                    # Update progress
                                    progress_bar.progress(80)
                                    
                                    # Save the analysis to the database
                                    if analysis_result and "error" not in analysis_result:
                                        # Extract the resume score
                                        resume_score = analysis_result.get(
                                            "resume_score", 0)
                                        
                                        # Save to database
                                        save_ai_analysis_data(
                                            None,  # No user_id needed
                                            {
                                                "model_used": selected_model,
                                                "resume_score": resume_score,
                                                "job_role": job_role
                                            }
                                        )
                                        # show snowflake effect
                                        st.snow()

                                        # Complete the progress
                                        progress_bar.progress(100)
                                        
                                        # Display the analysis result
                                        if analysis_result and "error" not in analysis_result:
                                            st.success("✅ Analysis complete!")
                                            
                                            # Extract data from the analysis
                                            full_response = analysis_result.get(
                                                "analysis", "")
                                            resume_score = analysis_result.get(
                                                "resume_score", 0)
                                            ats_score = analysis_result.get(
                                                "ats_score", 0)
                                            model_used = analysis_result.get(
                                                "model_used", selected_model)
                                            
                                            # Store the full response in session state for download
                                            st.session_state['full_analysis'] = full_response
                                            
                                            # Display the analysis in a nice format
                                            st.markdown("## Full Analysis Report")
                                            
                                            # Get current date
                                            from datetime import datetime
                                            current_date = datetime.now().strftime("%B %d, %Y")
                                            
                                            # Create a modern styled header for the report
                                            st.markdown(f"""
                                            <div style="background-color: #262730; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                                                <h2 style="color: #ffffff; margin-bottom: 10px;">AI Resume Analysis Report</h2>
                                                <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                                                    <div style="flex: 1; min-width: 200px;">
                                                        <p style="color: #ffffff;"><strong>Job Role:</strong> {job_role if job_role else "Not specified"}</p>
                                                        <p style="color: #ffffff;"><strong>Analysis Date:</strong> {current_date}</p>                                                                                                                </div>
                                                    <div style="flex: 1; min-width: 200px;">
                                                        <p style="color: #ffffff;"><strong>AI Model:</strong> {model_used}</p>
                                                        <p style="color: #ffffff;"><strong>Overall Score:</strong> {resume_score}/100 - {"Excellent" if resume_score >= 80 else "Good" if resume_score >= 60 else "Needs Improvement"}</p>
                                                        {f'<p style="color: #B886FD;"><strong>✓ Custom Job Description Used</strong></p>' if st.session_state.get('used_custom_job_desc', False) else ''}
                                                </div>
                                            """, unsafe_allow_html=True)
                                            
                                            # Add gauge charts for scores
                                            import plotly.graph_objects as go
                                            
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                # Resume Score Gauge
                                                fig1 = go.Figure(go.Indicator(
                                                    mode="gauge+number",
                                                    value=resume_score,
                                                    domain={'x': [0, 1], 'y': [0, 1]},
                                                    title={'text': "Resume Score", 'font': {'size': 16}},
                                                    gauge={
                                                        'axis': {'range': [0, 100], 'tickwidth': 1},
                                                        'bar': {'color': "#B886FD" if resume_score >= 80 else "#FFA500" if resume_score >= 60 else "#FF4444"},
                                                        'bgcolor': "white",
                                                        'borderwidth': 2,
                                                        'bordercolor': "gray",
                                                        'steps': [
                                                            {'range': [0, 40], 'color': 'rgba(255, 68, 68, 0.2)'},
                                                            {'range': [40, 60], 'color': 'rgba(255, 165, 0, 0.2)'},
                                                            {'range': [60, 80], 'color': 'rgba(255, 214, 0, 0.2)'},
                                                            {'range': [80, 100], 'color': 'rgba(76, 175, 80, 0.2)'}
                                                        ],
                                                        'threshold': {
                                                            'line': {'color': "red", 'width': 4},
                                                            'thickness': 0.75,
                                                            'value': 60
                                                        }
                                                    }
                                                ))
                                                
                                                fig1.update_layout(
                                                    height=250,
                                                    margin=dict(l=20, r=20, t=50, b=20),
                                                )
                                                
                                                st.plotly_chart(fig1, use_container_width=True)
                                                
                                                status = "Excellent" if resume_score >= 80 else "Good" if resume_score >= 60 else "Needs Improvement"
                                                st.markdown(f"<div style='text-align: center; font-weight: bold;'>{status}</div>", unsafe_allow_html=True)
                                            
                                            with col2:
                                                # ATS Score Gauge
                                                fig2 = go.Figure(go.Indicator(
                                                    mode="gauge+number",
                                                    value=ats_score,
                                                    domain={'x': [0, 1], 'y': [0, 1]},
                                                    title={'text': "ATS Optimization Score", 'font': {'size': 16}},
                                                    gauge={
                                                        'axis': {'range': [0, 100], 'tickwidth': 1},
                                                        'bar': {'color': "#B886FD" if ats_score >= 80 else "#FFA500" if ats_score >= 60 else "#FF4444"},
                                                        'bgcolor': "white",
                                                        'borderwidth': 2,
                                                        'bordercolor': "gray",
                                                        'steps': [
                                                            {'range': [0, 40], 'color': 'rgba(255, 68, 68, 0.2)'},
                                                            {'range': [40, 60], 'color': 'rgba(255, 165, 0, 0.2)'},
                                                            {'range': [60, 80], 'color': 'rgba(255, 214, 0, 0.2)'},
                                                            {'range': [80, 100], 'color': 'rgba(76, 175, 80, 0.2)'}
                                                        ],
                                                        'threshold': {
                                                            'line': {'color': "red", 'width': 4},
                                                            'thickness': 0.75,
                                                            'value': 60
                                                        }
                                                    }
                                                ))
                                                
                                                fig2.update_layout(
                                                    height=250,
                                                    margin=dict(l=20, r=20, t=50, b=20),
                                                )
                                                
                                                st.plotly_chart(fig2, use_container_width=True)
                                                
                                                status = "Excellent" if ats_score >= 80 else "Good" if ats_score >= 60 else "Needs Improvement"
                                                st.markdown(f"<div style='text-align: center; font-weight: bold;'>{status}</div>", unsafe_allow_html=True)

                                            # Add Job Description Match Score if custom job description was used
                                            if st.session_state.get('used_custom_job_desc', False) and custom_job_description:
                                                # Extract job match score from analysis result or calculate it
                                                job_match_score = analysis_result.get("job_match_score", 0)
                                                if not job_match_score and "job_match" in analysis_result:
                                                    job_match_score = analysis_result["job_match"].get("score", 0)
                                                
                                                # If we have a job match score, display it
                                                if job_match_score:
                                                    st.markdown("""
                                                    <h3 style="background: linear-gradient(90deg, #4d7c0f, #84cc16); color: white; padding: 10px; border-radius: 5px; margin-top: 20px;">
                                                        <i class="fas fa-handshake"></i> Job Description Match Analysis
                                                    </h3>
                                                    """, unsafe_allow_html=True)
                                                    
                                                    col1, col2 = st.columns(2)
                                                    
                                                    with col1:
                                                        # Job Match Score Gauge
                                                        fig3 = go.Figure(go.Indicator(
                                                            mode="gauge+number",
                                                            value=job_match_score,
                                                            domain={'x': [0, 1], 'y': [0, 1]},
                                                            title={'text': "Job Match Score", 'font': {'size': 16}},
                                                            gauge={
                                                                'axis': {'range': [0, 100], 'tickwidth': 1},
                                                                'bar': {'color': "#B886FD" if job_match_score >= 80 else "#FFA500" if job_match_score >= 60 else "#FF4444"},
                                                                'bgcolor': "white",
                                                                'borderwidth': 2,
                                                                'bordercolor': "gray",
                                                                'steps': [
                                                                    {'range': [0, 40], 'color': 'rgba(255, 68, 68, 0.2)'},
                                                                    {'range': [40, 60], 'color': 'rgba(255, 165, 0, 0.2)'},
                                                                    {'range': [60, 80], 'color': 'rgba(255, 214, 0, 0.2)'},
                                                                    {'range': [80, 100], 'color': 'rgba(76, 175, 80, 0.2)'}
                                                                ],
                                                                'threshold': {
                                                                    'line': {'color': "red", 'width': 4},
                                                                    'thickness': 0.75,
                                                                    'value': 60
                                                                }
                                                            }
                                                        ))
                                                        
                                                        fig3.update_layout(
                                                            height=250,
                                                            margin=dict(l=20, r=20, t=50, b=20),
                                                        )
                                                        
                                                        st.plotly_chart(fig3, use_container_width=True)
                                                        
                                                        match_status = "Excellent Match" if job_match_score >= 80 else "Good Match" if job_match_score >= 60 else "Low Match"
                                                        st.markdown(f"<div style='text-align: center; font-weight: bold;'>{match_status}</div>", unsafe_allow_html=True)
                                                    
                                                    with col2:
                                                        st.markdown("""
                                                        <div style="background-color: #262730; padding: 20px; border-radius: 10px; height: 100%;">
                                                            <h4 style="color: #ffffff; margin-bottom: 15px;">What This Means</h4>
                                                            <p style="color: #ffffff;">This score represents how well your resume matches the specific job description you provided.</p>
                                                            <ul style="color: #ffffff; padding-left: 20px;">
                                                                <li><strong>80-100:</strong> Excellent match - your resume is highly aligned with this job</li>
                                                                <li><strong>60-79:</strong> Good match - your resume matches many requirements</li>
                                                                <li><strong>Below 60:</strong> Consider tailoring your resume more specifically to this job</li>
                                                            </ul>
                                                        </div>
                                                        """, unsafe_allow_html=True)
                                                    
                                            
                                            # Format the full response with better styling
                                            formatted_analysis = full_response
                                            
                                            # Replace section headers with styled headers
                                            section_styles = {
                                                "## Overall Assessment": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #1e3a8a, #3b82f6); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-chart-line"></i> Overall Assessment
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Professional Profile Analysis": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #047857, #10b981); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-user-tie"></i> Professional Profile Analysis
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Skills Analysis": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #4f46e5, #818cf8); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-tools"></i> Skills Analysis
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Experience Analysis": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #9f1239, #e11d48); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-briefcase"></i> Experience Analysis
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Education Analysis": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #854d0e, #eab308); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-graduation-cap"></i> Education Analysis
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Key Strengths": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #166534, #22c55e); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-check-circle"></i> Key Strengths
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Areas for Improvement": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #9f1239, #fb7185); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-exclamation-circle"></i> Areas for Improvement
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## ATS Optimization Assessment": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #0e7490, #06b6d4); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-robot"></i> ATS Optimization Assessment
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Recommended Courses": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #5b21b6, #8b5cf6); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-book"></i> Recommended Courses
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Resume Score": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #0369a1, #0ea5e9); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-star"></i> Resume Score
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Role Alignment Analysis": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #7c2d12, #ea580c); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-bullseye"></i> Role Alignment Analysis
                                                </h3>
                                                <div class="section-content">""",
                                                
                                                "## Job Match Analysis": """<div class="report-section">
                                                <h3 style="background: linear-gradient(90deg, #4d7c0f, #84cc16); color: white; padding: 10px; border-radius: 5px;">
                                                    <i class="fas fa-handshake"></i> Job Match Analysis
                                                </h3>
                                                <div class="section-content">""",
                                            }
                                            
                                            # Apply the styling to each section
                                            for section, style in section_styles.items():
                                                if section in formatted_analysis:
                                                    formatted_analysis = formatted_analysis.replace(
                                                        section, style)
                                                    # Add closing div tags
                                                    next_section = False
                                                    for next_sec in section_styles.keys():
                                                        if next_sec != section and next_sec in formatted_analysis.split(style)[1]:
                                                            split_text = formatted_analysis.split(style)[1].split(next_sec)
                                                            formatted_analysis = formatted_analysis.split(style)[0] + style + split_text[0] + "</div></div>" + next_sec + "".join(split_text[1:])
                                                            next_section = True
                                                            break
                                                    if not next_section:
                                                        formatted_analysis = formatted_analysis + "</div></div>"
                                            
                                            # Remove any extra closing div tags that might have been added
                                            formatted_analysis = formatted_analysis.replace("</div></div></div></div>", "</div></div>")
                                            
                                            # Ensure we don't have any orphaned closing tags at the end
                                            if formatted_analysis.endswith("</div>"):
                                                # Count opening and closing div tags
                                                open_tags = formatted_analysis.count("<div")
                                                close_tags = formatted_analysis.count("</div>")
                                                
                                                # If we have more closing than opening tags, remove the extras
                                                if close_tags > open_tags:
                                                    excess = close_tags - open_tags
                                                    formatted_analysis = formatted_analysis[:-6 * excess]
                                            
                                            # Clean up any visible HTML tags that might appear in the text
                                            formatted_analysis = formatted_analysis.replace("&lt;/div&gt;", "")
                                            formatted_analysis = formatted_analysis.replace("&lt;div&gt;", "")
                                            formatted_analysis = formatted_analysis.replace("<div>", "<div>")  # Ensure proper opening
                                            formatted_analysis = formatted_analysis.replace("</div>", "</div>")  # Ensure proper closing
                                            
                                            # Add CSS for the report
                                            st.markdown("""
                                            <style>
                                                .report-section {
                                                    margin-bottom: 25px;
                                                    border: 1px solid #4B4B4B;
                                                    border-radius: 8px;
                                                    overflow: hidden;
                                                }
                                                .section-content {
                                                    padding: 15px;
                                                    background-color: #262730;
                                                    color: #ffffff;
                                                }
                                                .report-section h3 {
                                                    margin-top: 0;
                                                    font-weight: 600;
                                                }
                                                .report-section ul {
                                                    padding-left: 20px;
                                                }
                                                .report-section p {
                                                    color: #ffffff;
                                                    margin-bottom: 10px;
                                                }
                                                .report-section li {
                                                    color: #ffffff;
                                                    margin-bottom: 5px;
                                                }
                                            </style>
                                            """, unsafe_allow_html=True)

                                            # Display the formatted analysis
                                            st.markdown(f"""
                                            <div style="background-color: #262730; padding: 20px; border-radius: 10px; border: 1px solid #4B4B4B; color: #ffffff;">
                                                {formatted_analysis}
                                            </div>
                                            """, unsafe_allow_html=True)

                                            # Create a PDF report
                                            pdf_buffer = app_instance.ai_analyzer.generate_pdf_report(
                                                analysis_result={
                                                    "score": resume_score,
                                                    "ats_score": ats_score,
                                                    "model_used": model_used,
                                                    "full_response": full_response,
                                                    "strengths": analysis_result.get("strengths", []),
                                                    "weaknesses": analysis_result.get("weaknesses", []),
                                                    "used_custom_job_desc": st.session_state.get('used_custom_job_desc', False),
                                                    "custom_job_description": custom_job_description if st.session_state.get('used_custom_job_desc', False) else ""
                                                },
                                                candidate_name=st.session_state.get(
                                                    'candidate_name', 'Candidate'),
                                                job_role=selected_role
                                            )

                                            # PDF download button
                                            if pdf_buffer:
                                                st.download_button(
                                                    label="📊 Download PDF Report",
                                                    data=pdf_buffer,
                                                    file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                                    mime="application/pdf",
                                                    use_container_width=True,
                                                    on_click=lambda: st.balloons()
                                                )
                                            else:
                                                st.error("PDF generation failed. Please try again later.")
                                        else:
                                            st.error(f"Analysis failed: {analysis_result.get('error', 'Unknown error')}")
                            except Exception as ai_error:
                                st.error(f"Error during AI analysis: {str(ai_error)}")
                                import traceback as tb
                                st.code(tb.format_exc())

                st.toast("Check out these repositories: [Awesome-CV-Robo](https://github.com/sankalpG007/CV-Robo)", icon="ℹ️")