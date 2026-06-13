import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import json
import os
import re
from datetime import datetime
import tempfile

# Page configuration
st.set_page_config(
    page_title="AI Resume Screening System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .qualified-badge {
        background-color: #28a745;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        display: inline-block;
        margin-left: 10px;
    }
    .not-qualified-badge {
        background-color: #dc3545;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        display: inline-block;
        margin-left: 10px;
    }
    .score-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .candidate-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: white;
    }
    .skill-match {
        background-color: #d4edda;
        color: #155724;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
        margin: 2px;
        display: inline-block;
    }
    .skill-missing {
        background-color: #f8d7da;
        color: #721c24;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
        margin: 2px;
        display: inline-block;
    }
    .metric-box {
        background-color: #e3f2fd;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .candidate-name {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)


class ResumeScreeningUI:
    """Streamlit UI for AI Resume Screening System."""
    
    def __init__(self):
        """Initialize the UI and session state."""
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables."""
        if 'job_description' not in st.session_state:
            st.session_state.job_description = ""
        if 'resumes' not in st.session_state:
            st.session_state.resumes = []
        if 'results' not in st.session_state:
            st.session_state.results = None
        if 'settings' not in st.session_state:
            st.session_state.settings = {
                "provider": "OpenAI",
                "model": "gpt-4",
                "weights": {
                    "skills": 0.35,
                    "experience": 0.30,
                    "education": 0.20,
                    "certifications": 0.15
                },
                "threshold": 60
            }
        if 'processing' not in st.session_state:
            st.session_state.processing = False
    
    def _extract_name_from_resume(self, resume_text: str, filename: str) -> str:
        """Extract candidate name from resume text or filename."""
        # Try to find name patterns in resume text
        # Look for common patterns like "Name:", "Full Name:", or capitalized words at start
        name_patterns = [
            r'[Nn]ame\s*[:\\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'[Ff]ull\s*[Nn]ame\s*[:\\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*\n',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*[-–]\s*(?:Resume|CV|Curriculum)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, resume_text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # Fallback: use filename (remove extension)
        name = os.path.splitext(filename)[0]
        # Clean up filename: replace underscores/hyphens with spaces, title case
        name = name.replace('_', ' ').replace('-', ' ').title()
        return name if name else "Unknown Candidate"
    
    def _extract_email_from_resume(self, resume_text: str) -> str:
        """Extract email from resume text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, resume_text)
        return match.group(0) if match else "N/A"
    
    def _render_settings(self):
        """Render the Settings/Configuration tab."""
        st.title("⚙️ Settings")
        
        st.markdown("---")
        
        # Model Configuration
        st.subheader("🤖 Model Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            model_provider = st.selectbox(
                "Model Provider",
                ["OpenAI", "Anthropic", "Local/Ollama", "Azure OpenAI"],
                index=["OpenAI", "Anthropic", "Local/Ollama", "Azure OpenAI"].index(
                    st.session_state.settings.get("provider", "OpenAI")
                ),
                key="settings_provider"
            )
        
        with col2:
            model_name = st.text_input(
                "Model Name",
                value=st.session_state.settings.get("model", "gpt-4"),
                key="settings_model_name"
            )
        
        # API Key
        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="Enter your API key",
            value=st.session_state.settings.get("api_key", ""),
            key="settings_api_key"
        )
        
        st.markdown("---")
        
        # Scoring Weights
        st.subheader("📊 Scoring Weights")
        col1, col2, col3, col4 = st.columns(4)
        
        current_weights = st.session_state.settings.get("weights", {})
        
        with col1:
            skills_weight = st.slider(
                "Skills", 
                0.0, 1.0, 
                current_weights.get("skills", 0.35), 
                key="weight_skills"
            )
        with col2:
            exp_weight = st.slider(
                "Experience", 
                0.0, 1.0, 
                current_weights.get("experience", 0.30), 
                key="weight_exp"
            )
        with col3:
            edu_weight = st.slider(
                "Education", 
                0.0, 1.0, 
                current_weights.get("education", 0.20), 
                key="weight_edu"
            )
        with col4:
            cert_weight = st.slider(
                "Certifications", 
                0.0, 1.0, 
                current_weights.get("certifications", 0.15), 
                key="weight_cert"
            )
        
        # Validate weights
        total = skills_weight + exp_weight + edu_weight + cert_weight
        if abs(total - 1.0) > 0.01:
            st.warning(f"⚠️ Weights sum to {total:.2f}. They should ideally sum to 1.0")
        else:
            st.success(f"✅ Weights sum to {total:.2f}")
        
        st.markdown("---")
        
        # Threshold Settings
        st.subheader("🎯 Qualification Threshold")
        match_threshold = st.slider(
            "Minimum Score to Qualify (%)",
            0, 100,
            st.session_state.settings.get("threshold", 60),
            key="settings_threshold"
        )
        st.caption(f"Candidates scoring ≥ {match_threshold}% will be marked as **Qualified**")
        
        st.markdown("---")
        
        # Save Button
        if st.button("💾 Save Settings", type="primary", key="btn_save_settings"):
            st.session_state.settings = {
                "provider": model_provider,
                "model": model_name,
                "api_key": api_key,
                "weights": {
                    "skills": skills_weight,
                    "experience": exp_weight,
                    "education": edu_weight,
                    "certifications": cert_weight
                },
                "threshold": match_threshold
            }
            st.success("✅ Settings saved successfully!")
            st.balloons()
    
    def _render_input_section(self):
        """Render the job description and resume upload section."""
        st.markdown("### 📄 Job Description")
        
        # Job description input
        job_desc = st.text_area(
            "Paste the job description here",
            value=st.session_state.job_description,
            height=200,
            placeholder="Enter the job description, requirements, and qualifications...",
            key="job_desc_input"
        )
        
        if job_desc != st.session_state.job_description:
            st.session_state.job_description = job_desc
        
        st.markdown("---")
        
        # Resume upload
        st.markdown("### 📎 Upload Resumes")
        
        uploaded_files = st.file_uploader(
            "Upload resume files (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="resume_uploader"
        )
        
        if uploaded_files:
            st.session_state.resumes = uploaded_files
            st.success(f"✅ {len(uploaded_files)} resume(s) uploaded successfully!")
        
        # Display uploaded files with extracted names preview
        if st.session_state.resumes:
            st.markdown("**📋 Uploaded Files:**")
            for i, file in enumerate(st.session_state.resumes, 1):
                # Try to get a preview name
                preview_name = os.path.splitext(file.name)[0].replace('_', ' ').replace('-', ' ').title()
                st.write(f"{i}. 📄 **{preview_name}** ({file.size:,} bytes)")
    
    def _render_results_section(self):
        """Render the results and ranking section with qualification status."""
        st.markdown("### 📊 Screening Results")
        
        if st.session_state.results is None:
            st.info("👈 Upload job description and resumes, then click '🔍 Screen Resumes' to see results")
            return
        
        results = st.session_state.results
        threshold = st.session_state.settings.get('threshold', 60)
        
        # Separate qualified vs not qualified
        qualified = [r for r in results if r.get('score', 0) >= threshold]
        not_qualified = [r for r in results if r.get('score', 0) < threshold]
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Candidates", len(results))
        with col2:
            avg_score = np.mean([r.get('score', 0) for r in results]) if results else 0
            st.metric("Average Score", f"{avg_score:.1f}%")
        with col3:
            st.metric("✅ Qualified", len(qualified))
        with col4:
            st.metric("❌ Not Qualified", len(not_qualified))
        with col5:
            top_score = max([r.get('score', 0) for r in results]) if results else 0
            st.metric("Top Score", f"{top_score:.1f}%")
        
        st.markdown("---")
        
        # Qualified Candidates Section
        if qualified:
            st.subheader(f"✅ Qualified Candidates (Score ≥ {threshold}%)")
            
            for i, candidate in enumerate(qualified, 1):
                self._render_candidate_card(candidate, i, threshold, is_qualified=True)
        
        # Not Qualified Candidates Section
        if not_qualified:
            st.subheader(f"❌ Not Qualified (Score < {threshold}%)")
            
            for i, candidate in enumerate(not_qualified, 1):
                self._render_candidate_card(candidate, i, threshold, is_qualified=False)
    
    def _render_candidate_card(self, candidate: Dict, rank: int, threshold: float, is_qualified: bool):
        """Render a single candidate card with qualification badge."""
        score = candidate.get('score', 0)
        name = candidate.get('name', 'Unknown Candidate')
        email = candidate.get('email', 'N/A')
        
        # Color coding based on score
        if score >= 80:
            border_color = "#28a745"
            bg_color = "#d4edda"
        elif score >= threshold:
            border_color = "#ffc107"
            bg_color = "#fff3cd"
        else:
            border_color = "#dc3545"
            bg_color = "#f8d7da"
        
        # Qualification badge
        badge_class = "qualified-badge" if is_qualified else "not-qualified-badge"
        badge_text = "✅ QUALIFIED" if is_qualified else "❌ NOT QUALIFIED"
        
        st.markdown(f"""
        <div style="border: 2px solid {border_color}; background-color: {bg_color}; 
                    border-radius: 10px; padding: 15px; margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; flex-wrap: wrap;">
                        <span class="candidate-name">#{rank} {name}</span>
                        <span class="{badge_class}">{badge_text}</span>
                    </div>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9rem;">📧 {email}</p>
                </div>
                <div style="text-align: right; min-width: 120px;">
                    <h2 style="margin: 0; color: {border_color}; font-size: 2rem;">{score:.1f}%</h2>
                    <p style="margin: 0; font-size: 0.8rem; color: #666;">Match Score</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Expandable details
        with st.expander("🔍 View Full Details"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**✅ Matched Skills:**")
                matched_skills = candidate.get('matched_skills', [])
                if matched_skills:
                    for skill in matched_skills:
                        st.markdown(f'<span class="skill-match">✓ {skill}</span>', unsafe_allow_html=True)
                else:
                    st.write("No specific skills matched")
            
            with col2:
                st.markdown("**❌ Missing Skills:**")
                missing_skills = candidate.get('missing_skills', [])
                if missing_skills:
                    for skill in missing_skills:
                        st.markdown(f'<span class="skill-missing">✗ {skill}</span>', unsafe_allow_html=True)
                else:
                    st.write("All required skills matched! ✅")
            
            # Detailed breakdown
            st.markdown("**📈 Score Breakdown:**")
            breakdown = candidate.get('breakdown', {})
            if breakdown:
                breakdown_data = []
                for category, score_val in breakdown.items():
                    weight = st.session_state.settings['weights'].get(category, 0.25)
                    weighted_score = score_val * weight
                    breakdown_data.append({
                        'Category': category.title(),
                        'Raw Score': f"{score_val:.1f}%",
                        'Weight': f"{weight:.2f}",
                        'Weighted': f"{weighted_score:.1f}%"
                    })
                
                breakdown_df = pd.DataFrame(breakdown_data)
                st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
            
            # Experience summary
            st.markdown("**💼 Experience Summary:**")
            st.write(candidate.get('experience_summary', 'No experience summary available'))
            
            # Education
            st.markdown("**🎓 Education:**")
            st.write(candidate.get('education', 'No education details available'))
            
            # Recommendation
            st.markdown("**📝 AI Recommendation:**")
            rec = candidate.get('recommendation', 'No recommendation available')
            if is_qualified:
                st.success(rec)
            else:
                st.warning(rec)
    
    def _screen_resumes(self):
        """Process and screen resumes against job description."""
        if not st.session_state.job_description:
            st.error("❌ Please enter a job description first!")
            return
        
        if not st.session_state.resumes:
            st.error("❌ Please upload at least one resume!")
            return
        
        st.session_state.processing = True
        
        with st.spinner("🔍 AI is analyzing resumes... This may take a few minutes"):
            # Read resume contents and extract real names
            results = []
            
            for i, resume_file in enumerate(st.session_state.resumes):
                # Read file content
                try:
                    resume_text = resume_file.read().decode('utf-8', errors='ignore')
                    resume_file.seek(0)  # Reset file pointer for potential re-reading
                except:
                    resume_text = ""
                
                # Extract real name and email
                real_name = self._extract_name_from_resume(resume_text, resume_file.name)
                real_email = self._extract_email_from_resume(resume_text)
                
                # Mock scoring - REPLACE THIS with your actual AI logic
                # In real implementation, send resume_text + job_description to your AI model
                np.random.seed(hash(real_name) % 1000)  # Consistent random for demo
                mock_score = np.random.uniform(45, 95)
                
                result = {
                    'name': real_name,
                    'email': real_email,
                    'score': mock_score,
                    'matched_skills': ['Python', 'Machine Learning', 'Data Analysis', 'SQL'] if mock_score > 70 else ['Python', 'SQL'],
                    'missing_skills': ['Kubernetes', 'AWS', 'Docker'] if mock_score < 80 else ['AWS'],
                    'breakdown': {
                        'skills': np.random.uniform(60, 95),
                        'experience': np.random.uniform(50, 90),
                        'education': np.random.uniform(70, 100),
                        'certifications': np.random.uniform(40, 85)
                    },
                    'experience_summary': f"{np.random.randint(2, 10)} years of relevant experience in software development",
                    'education': "Bachelor's in Computer Science",
                    'recommendation': "🌟 Strong candidate - Recommend for interview" if mock_score > 75 else 
                                    "✅ Good match - Consider for interview" if mock_score > 60 else 
                                    "❌ Not a strong match - Does not meet minimum requirements"
                }
                results.append(result)
            
            # Sort by score descending
            results.sort(key=lambda x: x['score'], reverse=True)
            st.session_state.results = results
        
        st.session_state.processing = False
        st.success(f"✅ Screening complete! {len([r for r in results if r['score'] >= st.session_state.settings.get('threshold', 60)])} candidates qualified.")
    
    def _render_sidebar(self):
        """Render the sidebar with controls."""
        with st.sidebar:
            st.markdown("## 🎛️ Controls")
            
            st.markdown("---")
            
            # Screen button
            if st.button("🔍 Screen Resumes", type="primary", use_container_width=True):
                self._screen_resumes()
            
            st.markdown("---")
            
            # Clear button
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.job_description = ""
                st.session_state.resumes = []
                st.session_state.results = None
                st.rerun()
            
            st.markdown("---")
            
            # Export results
            if st.session_state.results:
                if st.button("📥 Export Results", use_container_width=True):
                    # Create exportable dataframe with qualification status
                    export_data = []
                    threshold = st.session_state.settings.get('threshold', 60)
                    for r in st.session_state.results:
                        export_data.append({
                            'Rank': 0,  # Will be filled
                            'Name': r.get('name', 'Unknown'),
                            'Email': r.get('email', 'N/A'),
                            'Score (%)': f"{r.get('score', 0):.1f}",
                            'Status': 'QUALIFIED' if r.get('score', 0) >= threshold else 'NOT QUALIFIED',
                            'Matched Skills': ', '.join(r.get('matched_skills', [])),
                            'Missing Skills': ', '.join(r.get('missing_skills', [])),
                            'Recommendation': r.get('recommendation', '')
                        })
                    
                    export_df = pd.DataFrame(export_data)
                    export_df['Rank'] = range(1, len(export_df) + 1)
                    
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        "⬇️ Download CSV",
                        csv,
                        "screening_results.csv",
                        "text/csv",
                        use_container_width=True
                    )
            
            st.markdown("---")
            
            # Current threshold display
            threshold = st.session_state.settings.get('threshold', 60)
            st.info(f"📌 Current Qualification Threshold: **{threshold}%**")
            
            # About
            st.markdown("### ℹ️ About")
            st.write("""
            This AI-powered resume screening system helps you:
            - Extract candidate names automatically
            - Score and rank candidates
            - Identify qualified vs not qualified
            - Export results for HR team
            """)
            
            st.markdown("---")
            st.caption("v2.0 | AI Resume Screening System")
    
    def run(self):
        """Main application loop."""
        # Header
        st.markdown('<h1 class="main-header">🤖 AI Resume Screening System</h1>', unsafe_allow_html=True)
        
        # Render sidebar
        self._render_sidebar()
        
        # Main content tabs
        tab1, tab2, tab3 = st.tabs(["📄 Input", "📊 Results", "⚙️ Settings"])
        
        with tab1:
            self._render_input_section()
        
        with tab2:
            self._render_results_section()
        
        with tab3:
            self._render_settings()


def main():
    """Entry point for the application."""
    ui = ResumeScreeningUI()
    ui.run()


if __name__ == "__main__":
    main()