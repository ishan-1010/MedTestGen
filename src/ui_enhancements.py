"""
UI Enhancement Module for AI Test Generator
Modern animations, loading states, and user feedback
"""

import streamlit as st
import time
import random
from typing import List

# Enhanced thinking messages for AI processing
THINKING_MESSAGES = [
    "🧠 Analyzing your requirements deeply...",
    "🔍 Searching knowledge base for similar patterns...",
    "⚡ Applying healthcare domain expertise...",
    "🎯 Identifying critical test scenarios...",
    "📊 Evaluating comprehensive test coverage...",
    "🏥 Incorporating NASSCOM healthcare standards...",
    "🔐 Adding security validation patterns...",
    "⚙️ Optimizing test case structure...",
    "✨ Crafting detailed test steps...",
    "🎨 Formatting for maximum clarity...",
    "🚀 Applying industry best practices...",
    "💡 Generating intelligent test data..."
]

COMPLIANCE_MESSAGES = [
    "📋 Parsing document structure and metadata...",
    "🏥 Validating against healthcare standards...",
    "✅ Checking NASSCOM compliance criteria...",
    "🔍 Analyzing technical specifications...",
    "📊 Computing comprehensive compliance score...",
    "🔧 Identifying improvement areas...",
    "📝 Generating detailed recommendations..."
]

IMPORT_MESSAGES = [
    "🔍 Detecting test suite schema intelligently...",
    "🧩 Mapping fields to NASSCOM format...",
    "🔄 Converting test cases with AI...",
    "🔗 Identifying test relationships...",
    "✨ Optimizing imported structure...",
    "🔍 Detecting and removing duplicates...",
    "✅ Validating imported data integrity..."
]

EXPORT_MESSAGES = [
    "🔄 Converting to target format...",
    "📦 Structuring test suite data...",
    "🔧 Applying custom field mappings...",
    "✅ Validating export schema...",
    "📤 Preparing optimized export...",
    "🎯 Ensuring compatibility...",
    "✨ Finalizing export package..."
]

def inject_modern_css():
    """Inject modern CSS styles into the app"""
    st.markdown("""
    <style>
        /* Modern color palette */
        :root {
            --primary: #6366F1;
            --secondary: #8B5CF6;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --dark: #1F2937;
            --light: #F9FAFB;
        }
        
        /* Smooth transitions for all elements */
        * {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        /* Modern gradient buttons */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            border: none;
            padding: 0.75rem 2rem;
            border-radius: 50px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        
        /* Glass morphism cards */
        .stExpander {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
        }
        
        /* Modern metrics */
        [data-testid="metric-container"] {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border: 1px solid rgba(99, 102, 241, 0.2);
            padding: 1.2rem;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        }
        
        [data-testid="metric-container"]:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        }
        
        /* Animated progress bars */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, 
                #667eea 0%, 
                #764ba2 50%, 
                #667eea 100%);
            background-size: 200% 100%;
            animation: shimmer 2s infinite;
            border-radius: 10px;
        }
        
        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        
        /* Modern tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
            padding: 6px;
            border-radius: 15px;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06);
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 600;
            background: transparent;
            border: none;
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background: white;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            color: #6366F1;
        }
        
        /* Pulsing animation for loading */
        @keyframes pulse {
            0%, 100% { 
                opacity: 1;
                transform: scale(1);
            }
            50% { 
                opacity: 0.7;
                transform: scale(0.98);
            }
        }
        
        .loading-pulse {
            animation: pulse 2s infinite;
        }
        
        /* Modern success/error states */
        .stSuccess {
            background: linear-gradient(135deg, #10B98115 0%, #10B98108 100%);
            border-left: 4px solid #10B981;
            border-radius: 10px;
            padding: 1rem;
        }
        
        .stError {
            background: linear-gradient(135deg, #EF444415 0%, #EF444408 100%);
            border-left: 4px solid #EF4444;
            border-radius: 10px;
            padding: 1rem;
        }
        
        .stWarning {
            background: linear-gradient(135deg, #F59E0B15 0%, #F59E0B08 100%);
            border-left: 4px solid #F59E0B;
            border-radius: 10px;
            padding: 1rem;
        }
        
        .stInfo {
            background: linear-gradient(135deg, #3B82F615 0%, #3B82F608 100%);
            border-left: 4px solid #3B82F6;
            border-radius: 10px;
            padding: 1rem;
        }
        
        /* Modern sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1F2937 0%, #111827 100%);
        }
        
        section[data-testid="stSidebar"] .stMarkdown {
            color: white;
        }
        
        /* Floating animation */
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        .floating {
            animation: float 3s ease-in-out infinite;
        }
        
        /* Gradient text */
        .gradient-text {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

def show_thinking_animation(messages: List[str] = None, duration: float = 0.3):
    """Display animated thinking messages while AI processes"""
    if messages is None:
        messages = THINKING_MESSAGES
    
    placeholder = st.empty()
    
    # Shuffle messages for variety
    shuffled_messages = messages.copy()
    random.shuffle(shuffled_messages)
    
    for message in shuffled_messages[:8]:  # Show max 8 messages
        placeholder.markdown(f"""
        <div class="loading-pulse" style="
            font-size: 1.1rem;
            color: #6366F1;
            padding: 1rem 1.5rem;
            margin: 0.5rem 0;
            border-left: 4px solid #6366F1;
            background: linear-gradient(90deg, rgba(99,102,241,0.1) 0%, transparent 100%);
            border-radius: 10px;
        ">
            {message}
        </div>
        """, unsafe_allow_html=True)
        time.sleep(duration)
    
    placeholder.empty()

def show_progress_with_status(messages: List[str], task_name: str = "Processing"):
    """Show progress bar with changing status messages"""
    progress_container = st.container()
    
    with progress_container:
        st.markdown(f"### {task_name}")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_steps = len(messages)
        
        for i, message in enumerate(messages):
            progress = (i + 1) / total_steps
            progress_bar.progress(progress)
            
            status_text.markdown(f"""
            <div style="
                text-align: center;
                padding: 1rem;
                background: linear-gradient(135deg, #667eea10 0%, #764ba210 100%);
                border-radius: 10px;
                margin: 1rem 0;
            ">
                <span style="color: #6366F1; font-weight: 600; font-size: 1.1rem;">
                    {message}
                </span>
                <br>
                <span style="color: #9CA3AF; font-size: 0.9rem;">
                    Step {i+1} of {total_steps}
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            time.sleep(0.5)
        
        # Completion animation
        progress_bar.progress(1.0)
        status_text.markdown("""
        <div style="
            text-align: center;
            padding: 1.5rem;
            background: linear-gradient(135deg, #10B98120 0%, #10B98110 100%);
            border-radius: 10px;
            margin: 1rem 0;
        ">
            <span style="color: #10B981; font-weight: 700; font-size: 1.2rem;">
                ✅ {task_name} Complete!
            </span>
        </div>
        """.format(task_name=task_name), unsafe_allow_html=True)
        
        time.sleep(1)
        progress_container.empty()

def display_metric_card(title: str, value: str, delta: str = None, color: str = "#6366F1"):
    """Display a modern metric card"""
    delta_html = f'<div style="color: #10B981; font-size: 0.9rem;">▲ {delta}</div>' if delta else ""
    
    st.markdown(f"""
    <div class="floating" style="
        background: linear-gradient(135deg, {color}15 0%, {color}08 100%);
        border: 1px solid {color}30;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        margin: 1rem 0;
    ">
        <div style="color: #6B7280; font-size: 0.9rem; font-weight: 600; text-transform: uppercase;">
            {title}
        </div>
        <div style="color: {color}; font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">
            {value}
        </div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def show_success_animation():
    """Display success animation with confetti"""
    st.balloons()
    st.success("✨ Operation completed successfully!")
    
    # Additional success message
    st.markdown("""
    <div class="floating" style="
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #10B98120 0%, #10B98110 100%);
        border-radius: 20px;
        margin: 2rem auto;
        max-width: 600px;
    ">
        <div style="font-size: 3rem; margin-bottom: 1rem;">🎉</div>
        <div class="gradient-text" style="font-size: 1.5rem; margin-bottom: 0.5rem;">
            Excellent Work!
        </div>
        <div style="color: #6B7280;">
            Your test case has been generated and saved successfully.
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_welcome_screen():
    """Create an engaging welcome screen"""
    st.markdown("""
    <div style="
        text-align: center;
        padding: 3rem;
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-radius: 25px;
        margin: 2rem 0;
    ">
        <h1 class="gradient-text" style="font-size: 3.5rem; margin-bottom: 1rem;">
            🧪 AI Test Generator
        </h1>
        <p style="font-size: 1.3rem; color: #6B7280; margin-bottom: 2rem;">
            NASSCOM Healthcare/MedTech Testing Solution
        </p>
        
        <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin-top: 3rem;">
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                flex: 1;
                max-width: 280px;
            ">
                <div style="font-size: 2rem; margin-bottom: 1rem;">✨</div>
                <h3 style="color: #6366F1; margin-bottom: 0.5rem;">Smart Generation</h3>
                <p style="color: #6B7280;">AI-powered test cases with healthcare expertise</p>
            </div>
            
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                flex: 1;
                max-width: 280px;
            ">
                <div style="font-size: 2rem; margin-bottom: 1rem;">📚</div>
                <h3 style="color: #8B5CF6; margin-bottom: 0.5rem;">RAG Pipeline</h3>
                <p style="color: #6B7280;">Context-aware generation from knowledge base</p>
            </div>
            
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                flex: 1;
                max-width: 280px;
            ">
                <div style="font-size: 2rem; margin-bottom: 1rem;">🔄</div>
                <h3 style="color: #10B981; margin-bottom: 0.5rem;">DevOps Ready</h3>
                <p style="color: #6B7280;">Export to Jira, Azure DevOps, and more</p>
            </div>
        </div>
        
        <div style="margin-top: 3rem;">
            <p style="color: #9CA3AF; font-size: 1.1rem;">
                👈 Enter your Gemini API key in the sidebar to begin
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
