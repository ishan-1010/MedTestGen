"""
AI-Powered Test Case Generator for Healthcare/MedTech
RAG Pipeline with Gemini API - NASSCOM Hackathon
"""

import streamlit as st
import os
import json
import uuid
import numpy as np
import faiss
import yaml
import glob
import re
from pathlib import Path
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List, Dict, Tuple
from datetime import datetime
import pandas as pd

# Load environment variables
load_dotenv()

# Configuration
DOCUMENTS_PATH = "data/documents"
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
GEMINI_MODEL_NAME = 'gemini-2.5-flash'
OUTPUT_DIR = "data/generated_test_cases"

# Page configuration
st.set_page_config(
    page_title="AI Test Case Generator - NASSCOM", 
    page_icon="🧪",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for test counter
if 'test_counter' not in st.session_state:
    st.session_state.test_counter = 0
if 'generated_tests' not in st.session_state:
    st.session_state.generated_tests = []

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

@st.cache_resource
def load_rag_system():
    """
    Load embedding model and build FAISS index from documents.
    Cached to avoid reloading on every interaction.
    """
    # Load embedding model
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    # Create output directory if needed
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Check documents path
    if not os.path.exists(DOCUMENTS_PATH):
        st.error(f"Document path '{DOCUMENTS_PATH}' not found. Creating it...")
        os.makedirs(DOCUMENTS_PATH, exist_ok=True)
        return embedding_model, None, None, []
    
    # Load and process documents
    doc_chunks = []
    doc_metadata = []
    
    doc_files = glob.glob(f"{DOCUMENTS_PATH}/*")
    if not doc_files:
        st.warning(f"No documents found in '{DOCUMENTS_PATH}'. Add your PRDs, user stories, and API specs.")
        return embedding_model, None, None, []
    
    # Process each document
    for file_path in doc_files:
        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix
        
        try:
            if file_ext in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Smart chunking for different document types
                    if 'user_story' in file_name.lower():
                        # Split by acceptance criteria
                        if 'Acceptance Criteria:' in content:
                            parts = content.split('Acceptance Criteria:')
                            if parts[0].strip():
                                doc_chunks.append(parts[0].strip())
                                doc_metadata.append({
                                    'source': file_name,
                                    'type': 'user_story_overview',
                                    'doc_type': 'user_story'
                                })
                            if len(parts) > 1:
                                doc_chunks.append(f"Acceptance Criteria:\n{parts[1].strip()}")
                                doc_metadata.append({
                                    'source': file_name,
                                    'type': 'acceptance_criteria',
                                    'doc_type': 'user_story'
                                })
                        else:
                            doc_chunks.append(content)
                            doc_metadata.append({
                                'source': file_name,
                                'type': 'user_story',
                                'doc_type': 'user_story'
                            })
                    else:
                        # Split by paragraphs for other documents
                        paragraphs = content.split('\n\n')
                        for para in paragraphs:
                            if para.strip() and len(para.strip()) > 50:
                                doc_chunks.append(para.strip())
                                doc_metadata.append({
                                    'source': file_name,
                                    'type': 'prd' if 'prd' in file_name.lower() else 'document',
                                    'doc_type': 'prd' if 'prd' in file_name.lower() else 'general'
                                })
                                
            elif file_ext in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    yaml_content = yaml.safe_load(f)
                    
                    # Process API specs
                    if 'paths' in yaml_content:
                        for path, methods in yaml_content.get('paths', {}).items():
                            endpoint_doc = f"API Endpoint: {path}\n"
                            endpoint_doc += yaml.dump(methods, default_flow_style=False)
                            doc_chunks.append(endpoint_doc)
                            doc_metadata.append({
                                'source': file_name,
                                'type': 'api_endpoint',
                                'endpoint': path,
                                'doc_type': 'api_specification'
                            })
                    else:
                        # General YAML content
                        doc_chunks.append(yaml.dump(yaml_content, default_flow_style=False))
                        doc_metadata.append({
                            'source': file_name,
                            'type': 'config',
                            'doc_type': 'configuration'
                        })
                        
        except Exception as e:
            st.error(f"Error loading {file_name}: {str(e)}")
    
    if not doc_chunks:
        st.warning("No content extracted from documents.")
        return embedding_model, None, None, []
    
    # Generate embeddings
    with st.spinner(f"Creating embeddings for {len(doc_chunks)} document chunks..."):
        contents = doc_chunks
        embeddings = embedding_model.encode(contents, show_progress_bar=True)
        embeddings = np.array(embeddings).astype('float32')
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    return embedding_model, index, doc_chunks, doc_metadata

def retrieve_context(query: str, embedding_model, index, doc_chunks, doc_metadata, k: int = 5):
    """Retrieve relevant documents for a query"""
    if index is None:
        return []
    
    query_embedding = embedding_model.encode([query]).astype('float32')
    distances, indices = index.search(query_embedding, k)
    
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(doc_chunks):
            similarity = 1 / (1 + dist)
            results.append({
                'content': doc_chunks[idx],
                'metadata': doc_metadata[idx] if idx < len(doc_metadata) else {},
                'similarity': similarity
            })
    
    return results

def create_fallback_test_case(requirement: str, error_reason: str = "Unknown") -> Dict:
    """
    Create a fallback test case when generation fails.
    """
    st.session_state.test_counter += 1
    return {
        'id': f'TC_FB_{st.session_state.test_counter:04d}',
        'title': f'Test: {requirement[:60]}',
        'description': f'Verify that {requirement}',
        'category': 'Functional',
        'priority': 'Medium',
        'compliance': ['General'],
        'preconditions': 'System is in stable state',
        'test_steps': [
            'Setup test environment',
            'Execute test scenario',
            'Verify results'
        ],
        'expected_results': 'System behaves as specified',
        'test_data': {'placeholder': 'Add specific test data'},
        'edge_cases': [],
        'automation_feasible': False,
        'estimated_duration': '10 minutes',
        'generated_from': requirement[:100],
        'context_sources': ['Fallback generation'],
        'generation_timestamp': datetime.now().isoformat(),
        'fallback': True,
        'error': error_reason
    }

def generate_test_case_with_gemini(requirement: str, context_docs: List[Dict]) -> Dict:
    """
    Generate test case using Gemini with all improvements:
    - Unique ID generation
    - Consistent formatting
    - Structured test_data
    - Context relevance handling
    - Better error handling
    """
    # Check context relevance
    avg_relevance = sum(doc['similarity'] for doc in context_docs) / len(context_docs) if context_docs else 0
    low_relevance = avg_relevance < 0.3
    
    # Build context string
    if low_relevance:
        context_str = "Note: Limited specific context found. Generating based on general best practices and requirement analysis."
    else:
        context_parts = []
        for doc in context_docs[:3]:
            context_parts.append(f"--- Source: {doc['metadata'].get('source', 'Unknown')} (Type: {doc['metadata'].get('type', 'document')}, Relevance: {doc['similarity']:.2%}) ---")
            context_parts.append(doc['content'][:800])
            context_parts.append("--- End Context ---")
        context_str = "\n\n".join(context_parts)
    
    # Enhanced prompt with formatting rules
    prompt = f"""You are a meticulous QA Engineer specializing in healthcare/MedTech testing.
Generate a comprehensive test case for the following requirement.

REQUIREMENT:
{requirement}

RELEVANT CONTEXT:
{context_str}

Generate a test case with EXACTLY these fields:
- id: Use "TC_PLACEHOLDER" (will be replaced)
- title: Clear, descriptive title
- description: Detailed description of what is being tested
- category: One of [Functional, Security, Integration, Performance, Usability, Compliance]
- priority: One of [Critical, High, Medium, Low]
- compliance: Array of standards like ["HIPAA", "GDPR", "FDA", "ISO 13485"]
- preconditions: String describing what must be true before testing
- test_steps: Array of step descriptions WITHOUT numbering (e.g., ["Navigate to login page", "Enter credentials"])
- expected_results: String describing specific expected outcomes
- test_data: JSON object with test data (e.g., {{"username": "test@example.com", "password": "Test123!"}})
- edge_cases: Array of special scenarios to consider
- automation_feasible: Boolean indicating if this can be automated
- estimated_duration: String like "5 minutes" or "30 minutes"

IMPORTANT:
1. test_steps must be an array of strings without prefixes like "Step 1:" or "1."
2. test_data must be a JSON object, not a string
3. Focus on healthcare/medical domain requirements if applicable

Return ONLY a valid JSON object."""
    
    try:
        # Configure Gemini for JSON output
        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3,
                top_p=0.9,
                top_k=30,
                max_output_tokens=4096  # Increased from 2000 to handle detailed test cases
            )
        )
        
        # Safety settings for healthcare content
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # Check for safety blocks before trying to parse
        if not response.parts:
            # This happens if the response was blocked
            block_reason = "Unknown"
            if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason'):
                block_reason = response.prompt_feedback.block_reason.name if hasattr(response.prompt_feedback.block_reason, 'name') else str(response.prompt_feedback.block_reason)
            st.error(f"Generation failed. Reason: {block_reason}")
            return create_fallback_test_case(requirement, error_reason=f"Content blocked by safety filter: {block_reason}")
        
        test_case = json.loads(response.text)
        
        # IMPROVEMENT 1: Generate unique ID
        unique_id = f"TC_{str(uuid.uuid4())[:8].upper()}"
        test_case['id'] = unique_id
        
        # IMPROVEMENT 2: Clean test_steps formatting
        if 'test_steps' in test_case and isinstance(test_case['test_steps'], list):
            cleaned_steps = []
            for step in test_case['test_steps']:
                # Remove prefixes like "Step 1:", "1.", etc.
                cleaned = re.sub(r'^(Step\s+\d+:|^\d+\.\s*)', '', str(step)).strip()
                cleaned_steps.append(cleaned)
            test_case['test_steps'] = cleaned_steps
        
        # IMPROVEMENT 3: Ensure test_data is always a dict
        if 'test_data' in test_case:
            if isinstance(test_case['test_data'], str):
                try:
                    test_case['test_data'] = json.loads(test_case['test_data'])
                except:
                    test_case['test_data'] = {"raw_data": test_case['test_data']}
        else:
            test_case['test_data'] = {}
        
        # IMPROVEMENT 4: Add metadata and context tracking
        test_case['generated_from'] = requirement[:100]
        test_case['generation_timestamp'] = datetime.now().isoformat()
        test_case['avg_context_relevance'] = f"{avg_relevance:.2%}"
        
        if low_relevance:
            test_case['context_sources'] = ["Generated using best practices - limited specific context"]
            test_case['low_context_confidence'] = True
        else:
            test_case['context_sources'] = [
                doc['metadata'].get('source', 'Unknown') for doc in context_docs[:3]
            ]
            test_case['low_context_confidence'] = False
        
        # Increment counter
        st.session_state.test_counter += 1
        
        return test_case
        
    except json.JSONDecodeError as e:
        st.error(f"Generation error: Failed to parse JSON from the model. Error: {e}")
        
        # Check if the output was truncated due to token limit
        try:
            if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'finish_reason'):
                finish_reason = response.prompt_feedback.finish_reason.name if hasattr(response.prompt_feedback.finish_reason, 'name') else str(response.prompt_feedback.finish_reason)
                if finish_reason == "MAX_TOKENS":
                    st.warning("The model's response may have been cut short. Consider increasing the 'max_output_tokens' limit in the code.")
                    return create_fallback_test_case(requirement, error_reason=f"Response truncated (max tokens reached): {e}")
        except:
            pass
        
        return create_fallback_test_case(requirement, error_reason=f"JSON Parse Error: {e}")
    
    except Exception as e:
        st.error(f"An unexpected error occurred with the Gemini API: {e}")
        return create_fallback_test_case(requirement, error_reason=str(e))

def save_test_case(test_case: Dict, format: str = 'json'):
    """Save test case to file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format == 'json':
        filename = f"{OUTPUT_DIR}/test_case_{test_case['id']}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(test_case, f, indent=2, default=str)
        return filename
    elif format == 'csv':
        filename = f"{OUTPUT_DIR}/test_case_{test_case['id']}_{timestamp}.csv"
        df = pd.DataFrame([test_case])
        df.to_csv(filename, index=False)
        return filename
    return None

# MAIN UI
def main():
    # Header
    st.title("🧪 AI-Powered Test Case Generator")
    st.markdown("### Healthcare/MedTech Testing with RAG Pipeline")
    st.markdown("Generate comprehensive test cases from your project documents using AI")
    
    # Sidebar for system info
    with st.sidebar:
        st.header("📊 System Status")
        
        # Load RAG system
        embedding_model, index, doc_chunks, doc_metadata = load_rag_system()
        
        if index:
            st.success(f"✅ RAG System Ready")
            st.info(f"📚 {len(doc_chunks)} document chunks indexed")
            st.info(f"📁 {len(set(m.get('source', 'Unknown') for m in doc_metadata))} source files")
            
            # Show loaded documents
            with st.expander("📄 Loaded Documents"):
                sources = set(m.get('source', 'Unknown') for m in doc_metadata)
                for source in sources:
                    st.write(f"• {source}")
        else:
            st.warning("⚠️ No documents loaded")
            st.info(f"Add documents to: {DOCUMENTS_PATH}/")
        
        st.markdown("---")
        st.metric("Test Cases Generated", st.session_state.test_counter)
        
        # Export options
        if st.session_state.generated_tests:
            st.markdown("### 💾 Export All Tests")
            if st.button("Export to JSON"):
                all_tests = {
                    "generated_on": datetime.now().isoformat(),
                    "total_tests": len(st.session_state.generated_tests),
                    "test_cases": st.session_state.generated_tests
                }
                filename = f"{OUTPUT_DIR}/all_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(all_tests, f, indent=2, default=str)
                st.success(f"Saved to {filename}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🎯 Generate New Test Case")
        
        # Predefined examples
        examples = [
            "Test user registration with valid email and password meeting all acceptance criteria",
            "Verify HIPAA compliance for patient data handling and encryption",
            "Test API authentication with invalid JWT token",
            "Validate password complexity requirements including special characters",
            "Test concurrent user sessions and race conditions",
            "Verify audit trail generation for all PHI access"
        ]
        
        selected_example = st.selectbox("Choose an example or write your own:", 
                                       ["Custom requirement..."] + examples)
        
        if selected_example == "Custom requirement...":
            requirement = st.text_area(
                "Enter your test requirement:",
                height=100,
                placeholder="Describe what you want to test..."
            )
        else:
            requirement = selected_example
            st.info(f"Selected: {requirement}")
        
        # Generation button
        if st.button("🚀 Generate Test Case", type="primary"):
            if not requirement or requirement == "Custom requirement...":
                st.warning("Please enter a requirement")
            elif not index:
                st.error("RAG system not initialized. Check your documents folder.")
            else:
                with st.spinner("🔍 Retrieving context and generating test case..."):
                    # Retrieve context
                    context_docs = retrieve_context(
                        requirement, 
                        embedding_model, 
                        index, 
                        doc_chunks, 
                        doc_metadata,
                        k=5
                    )
                    
                    # Generate test case
                    test_case = generate_test_case_with_gemini(requirement, context_docs)
                    
                    # Store in session
                    st.session_state.generated_tests.append(test_case)
                    
                    # Display results
                    if not test_case.get('fallback'):
                        st.success(f"✅ Test Case Generated: {test_case['id']}")
                    else:
                        st.warning("⚠️ Generated with fallback (limited context)")
                    
                    # Display test case
                    display_test_case(test_case, context_docs)
    
    with col2:
        st.header("📝 Recent Test Cases")
        if st.session_state.generated_tests:
            for tc in reversed(st.session_state.generated_tests[-5:]):
                with st.expander(f"{tc['id']}: {tc.get('title', 'Untitled')[:30]}..."):
                    st.write(f"**Category:** {tc.get('category')}")
                    st.write(f"**Priority:** {tc.get('priority')}")
                    st.write(f"**Generated:** {tc.get('generation_timestamp', 'Unknown')[:19]}")
                    if tc.get('low_context_confidence'):
                        st.warning("Low context confidence")
        else:
            st.info("No test cases generated yet")

def display_test_case(test_case: Dict, context_docs: List[Dict]):
    """Display generated test case in a formatted way"""
    
    # Header with metrics
    st.markdown("---")
    st.subheader(f"📋 {test_case['id']}: {test_case.get('title', 'Generated Test Case')}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Priority", test_case.get('priority', 'N/A'))
    with col2:
        st.metric("Category", test_case.get('category', 'N/A'))
    with col3:
        compliance = test_case.get('compliance', [])
        st.metric("Compliance", len(compliance) if compliance else 'None')
    with col4:
        st.metric("Duration", test_case.get('estimated_duration', 'N/A'))
    
    # Main content
    st.markdown("### 📝 Description")
    st.write(test_case.get('description', 'N/A'))
    
    # Preconditions
    st.markdown("### ⚙️ Preconditions")
    st.info(test_case.get('preconditions', 'None specified'))
    
    # Test steps
    st.markdown("### 📋 Test Steps")
    steps = test_case.get('test_steps', [])
    for i, step in enumerate(steps, 1):
        st.write(f"{i}. {step}")
    
    # Expected results
    st.markdown("### ✅ Expected Results")
    st.success(test_case.get('expected_results', 'N/A'))
    
    # Test data
    if test_case.get('test_data'):
        st.markdown("### 📊 Test Data")
        st.json(test_case.get('test_data'))
    
    # Edge cases
    if test_case.get('edge_cases'):
        st.markdown("### ⚠️ Edge Cases")
        for edge in test_case['edge_cases']:
            st.write(f"• {edge}")
    
    # Metadata
    with st.expander("🔍 Generation Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Automation Feasible:** {'Yes' if test_case.get('automation_feasible') else 'No'}")
            st.write(f"**Context Relevance:** {test_case.get('avg_context_relevance', 'N/A')}")
            if test_case.get('compliance'):
                st.write(f"**Standards:** {', '.join(test_case['compliance'])}")
        with col2:
            st.write(f"**Generated From:** {test_case.get('generated_from', 'N/A')[:50]}...")
            st.write(f"**Timestamp:** {test_case.get('generation_timestamp', 'N/A')[:19]}")
            if test_case.get('low_context_confidence'):
                st.warning("Generated with limited context")
    
    # Context sources
    with st.expander("📚 Context Sources Used"):
        if test_case.get('context_sources'):
            for source in test_case['context_sources']:
                st.write(f"• {source}")
        
        if context_docs and not test_case.get('fallback'):
            st.markdown("### Retrieved Context:")
            for i, doc in enumerate(context_docs[:3], 1):
                st.write(f"**{i}. {doc['metadata'].get('source', 'Unknown')}** (Relevance: {doc['similarity']:.2%})")
                #st.text_area("", value=doc['content'][:300] + "...", height=100, disabled=True, key=f"ctx_{i}")
                
                # NEW, FIXED CODE 
                label = f"Retrieved Context from {doc['metadata'].get('source', 'Unknown')}"
                st.text_area(label, value=doc['content'], height=100, disabled=True, key=f"ctx_{i}", label_visibility="collapsed")
    
    # Save options
    st.markdown("### 💾 Save Test Case")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Save as JSON", key=f"save_json_{test_case['id']}"):
            filename = save_test_case(test_case, 'json')
            st.success(f"Saved to {filename}")
    with col2:
        if st.button(f"Save as CSV", key=f"save_csv_{test_case['id']}"):
            filename = save_test_case(test_case, 'csv')
            st.success(f"Saved to {filename}")

if __name__ == "__main__":
    main()
