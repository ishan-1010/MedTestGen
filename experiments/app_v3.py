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
if 'refinement_mode' not in st.session_state:
    st.session_state.refinement_mode = False
if 'test_to_refine' not in st.session_state:
    st.session_state.test_to_refine = None
if 'refinement_history' not in st.session_state:
    st.session_state.refinement_history = {}
if 'edited_test' not in st.session_state:
    st.session_state.edited_test = None
if 'test_versions' not in st.session_state:
    st.session_state.test_versions = {}  # Store original versions for diff view

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

def load_document_content(file_path: str) -> Tuple[str, Dict]:
    """
    Load and return the content of a document along with its metadata.
    """
    file_name = Path(file_path).name
    file_ext = Path(file_path).suffix
    metadata = {
        'filename': file_name,
        'extension': file_ext,
        'size': os.path.getsize(file_path),
        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
    }
    
    try:
        if file_ext in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata['type'] = 'text'
                metadata['lines'] = len(content.split('\n'))
                metadata['characters'] = len(content)
                return content, metadata
                
        elif file_ext in ['.yaml', '.yml']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata['type'] = 'yaml'
                # Try to parse YAML to get structure info
                try:
                    yaml_data = yaml.safe_load(content)
                    if isinstance(yaml_data, dict):
                        metadata['top_level_keys'] = list(yaml_data.keys())
                        if 'paths' in yaml_data:
                            metadata['endpoints'] = list(yaml_data['paths'].keys())
                except:
                    pass
                metadata['lines'] = len(content.split('\n'))
                return content, metadata
        else:
            return f"Unsupported file type: {file_ext}", metadata
    except Exception as e:
        return f"Error reading file: {str(e)}", metadata

def display_document_viewer():
    """
    Display the document viewer interface for transparency.
    """
    st.header("📚 Backend Documents")
    st.markdown("View the documents being used by the RAG system for test case generation.")
    
    # Check if documents path exists
    if not os.path.exists(DOCUMENTS_PATH):
        st.warning(f"Documents folder not found at: {DOCUMENTS_PATH}")
        return
    
    # Get list of documents
    doc_files = glob.glob(f"{DOCUMENTS_PATH}/*")
    if not doc_files:
        st.info("No documents found in the documents folder.")
        st.markdown(f"Add your documents to: `{DOCUMENTS_PATH}/`")
        return
    
    # Create two columns for document list and viewer
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📁 Available Documents")
        
        # Document selection
        selected_doc = None
        for file_path in sorted(doc_files):
            file_name = Path(file_path).name
            file_size = os.path.getsize(file_path)
            
            # Determine document type icon
            if 'user_story' in file_name.lower():
                icon = "📋"
                doc_type = "User Story"
            elif 'prd' in file_name.lower():
                icon = "📄"
                doc_type = "PRD"
            elif 'api' in file_name.lower():
                icon = "🔌"
                doc_type = "API Spec"
            elif 'test' in file_name.lower():
                icon = "🧪"
                doc_type = "Test Plan"
            elif 'bug' in file_name.lower():
                icon = "🐛"
                doc_type = "Bug Template"
            else:
                icon = "📝"
                doc_type = "Document"
            
            # Create button for each document
            if st.button(f"{icon} {file_name}", key=f"doc_{file_name}", use_container_width=True):
                selected_doc = file_path
                st.session_state.selected_doc = file_path
            
            # Show document info
            st.caption(f"{doc_type} • {file_size:,} bytes")
        
        # Document statistics
        st.markdown("---")
        st.subheader("📊 Document Statistics")
        total_size = sum(os.path.getsize(f) for f in doc_files)
        st.metric("Total Documents", len(doc_files))
        st.metric("Total Size", f"{total_size:,} bytes")
        
        # Document types breakdown
        doc_types = {}
        for file_path in doc_files:
            ext = Path(file_path).suffix
            doc_types[ext] = doc_types.get(ext, 0) + 1
        
        st.markdown("**File Types:**")
        for ext, count in doc_types.items():
            st.write(f"• {ext}: {count} file(s)")
    
    with col2:
        st.subheader("📖 Document Content")
        
        # Use session state to maintain selected document
        if 'selected_doc' in st.session_state:
            selected_doc = st.session_state.selected_doc
        
        if selected_doc and os.path.exists(selected_doc):
            file_name = Path(selected_doc).name
            
            # Load document content
            content, metadata = load_document_content(selected_doc)
            
            # Display metadata
            with st.expander("📋 Document Metadata", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Filename:** {metadata['filename']}")
                    st.write(f"**Type:** {metadata.get('type', 'Unknown')}")
                    st.write(f"**Size:** {metadata['size']:,} bytes")
                with col_b:
                    st.write(f"**Extension:** {metadata['extension']}")
                    st.write(f"**Modified:** {metadata['modified']}")
                    if 'lines' in metadata:
                        st.write(f"**Lines:** {metadata['lines']:,}")
                
                # Show additional metadata for specific types
                if 'top_level_keys' in metadata:
                    st.write(f"**Top-level Keys:** {', '.join(metadata['top_level_keys'])}")
                if 'endpoints' in metadata:
                    st.write(f"**API Endpoints:** {len(metadata['endpoints'])}")
                    with st.expander("View Endpoints"):
                        for endpoint in metadata['endpoints']:
                            st.code(endpoint)
            
            # Display content with syntax highlighting
            st.markdown(f"**Viewing:** `{file_name}`")
            
            # Determine language for syntax highlighting
            if metadata['extension'] in ['.yaml', '.yml']:
                language = 'yaml'
            elif metadata['extension'] == '.md':
                language = 'markdown'
            elif metadata['extension'] == '.json':
                language = 'json'
            else:
                language = 'text'
            
            # Show content in a code block with appropriate syntax highlighting
            st.code(content, language=language, line_numbers=True)
            
            # Download button
            st.download_button(
                label="📥 Download Document",
                data=content,
                file_name=file_name,
                mime="text/plain"
            )
        else:
            st.info("👈 Select a document from the list to view its content")
            
            # Show quick overview of what each document type contains
            st.markdown("### 📝 Document Types Overview")
            st.markdown("""
            - **User Stories** (📋): Feature requirements with acceptance criteria
            - **PRDs** (📄): Product requirement documents with functional specs
            - **API Specs** (🔌): OpenAPI/Swagger specifications for endpoints
            - **Test Plans** (🧪): Existing test strategies and scenarios
            - **Bug Templates** (🐛): Templates for bug reporting
            """)

def refine_test_case_with_feedback(test_case: Dict, feedback: str, specific_field: str = None) -> Dict:
    """
    Refine an existing test case based on human feedback.
    """
    # Create a copy without the retrieved_context field for JSON serialization
    test_case_for_prompt = {k: v for k, v in test_case.items() if k != 'retrieved_context'}
    
    # Build refinement prompt
    if specific_field:
        prompt = f"""You are a QA Engineer. Refine the following test case based on user feedback.

CURRENT TEST CASE:
{json.dumps(test_case_for_prompt, indent=2, default=str)}

USER FEEDBACK FOR '{specific_field}':
{feedback}

Generate an improved version of this test case, specifically improving the '{specific_field}' field based on the feedback.
Maintain all other fields unless they need adjustment to be consistent with the change.

Return ONLY a valid JSON object with the same structure."""
    else:
        prompt = f"""You are a QA Engineer. Refine the following test case based on user feedback.

CURRENT TEST CASE:
{json.dumps(test_case_for_prompt, indent=2, default=str)}

USER FEEDBACK:
{feedback}

Generate an improved version of this test case incorporating the feedback.
Maintain the same structure and format.

Return ONLY a valid JSON object."""
    
    try:
        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3,
                top_p=0.9,
                max_output_tokens=4096
            )
        )
        
        response = model.generate_content(prompt)
        refined_test = json.loads(response.text)
        
        # Preserve metadata
        refined_test['id'] = test_case['id']
        refined_test['refinement_timestamp'] = datetime.now().isoformat()
        refined_test['refinement_feedback'] = feedback
        refined_test['version'] = test_case.get('version', 1) + 1
        
        # Preserve the retrieved_context if it exists
        if 'retrieved_context' in test_case:
            refined_test['retrieved_context'] = test_case['retrieved_context']
        
        return refined_test
        
    except Exception as e:
        st.error(f"Error refining test case: {e}")
        return test_case

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
        
        # Add version tracking
        test_case['version'] = 1
        
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

def display_test_diff(original: Dict, refined: Dict):
    """Display differences between original and refined test cases"""
    st.markdown("### 📊 Changes Made")
    
    # Compare key fields
    fields_to_compare = [
        ('title', 'Title'),
        ('description', 'Description'),
        ('category', 'Category'),
        ('priority', 'Priority'),
        ('preconditions', 'Preconditions'),
        ('test_steps', 'Test Steps'),
        ('expected_results', 'Expected Results'),
        ('edge_cases', 'Edge Cases'),
        ('test_data', 'Test Data')
    ]
    
    for field_key, field_name in fields_to_compare:
        original_value = original.get(field_key, '')
        refined_value = refined.get(field_key, '')
        
        # Convert lists and dicts to strings for comparison
        if isinstance(original_value, list):
            original_str = '\n'.join([f"• {item}" for item in original_value])
            refined_str = '\n'.join([f"• {item}" for item in refined_value]) if isinstance(refined_value, list) else str(refined_value)
        elif isinstance(original_value, dict):
            original_str = json.dumps(original_value, indent=2)
            refined_str = json.dumps(refined_value, indent=2) if isinstance(refined_value, dict) else str(refined_value)
        else:
            original_str = str(original_value)
            refined_str = str(refined_value)
        
        # Only show fields that changed
        if original_str != refined_str:
            with st.expander(f"**{field_name}** - ✏️ Modified", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🔴 Original:**")
                    if len(original_str) > 500:
                        st.text_area("", value=original_str[:500] + "...", height=150, disabled=True, 
                                   key=f"diff_orig_{field_key}", label_visibility="collapsed")
                    else:
                        st.text_area("", value=original_str, height=150, disabled=True,
                                   key=f"diff_orig_{field_key}", label_visibility="collapsed")
                with col2:
                    st.markdown("**🟢 Refined:**")
                    if len(refined_str) > 500:
                        st.text_area("", value=refined_str[:500] + "...", height=150, disabled=True,
                                   key=f"diff_refined_{field_key}", label_visibility="collapsed")
                    else:
                        st.text_area("", value=refined_str, height=150, disabled=True,
                                   key=f"diff_refined_{field_key}", label_visibility="collapsed")
    
    # Show version info
    st.info(f"📌 Version {original.get('version', 1)} → Version {refined.get('version', 2)}")
    if refined.get('refinement_feedback'):
        st.write(f"**Refinement Reason:** {refined.get('refinement_feedback')}")

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

    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["🧪 Generate New Tests", "🗂️ Test Suite & Refinement", "📚 Backend Documents"])

    with tab1:
        st.header("🎯 Generate New Test Case")
        st.markdown("Describe the feature or requirement you want to test.")

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
            st.info(f"Using example: {requirement}")
        
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
                    
                    # Add context to test case object for later display
                    test_case['retrieved_context'] = context_docs
                    
                    # Store in session
                    st.session_state.generated_tests.insert(0, test_case) # Insert at the beginning
                    
                    # Display results
                    if not test_case.get('fallback'):
                        st.success(f"✅ Test Case Generated: {test_case['id']}. View it in the 'Test Suite' tab.")
                    else:
                        st.warning("⚠️ Generated with fallback (limited context). View it in the 'Test Suite' tab.")
                    
                    st.balloons()

    with tab2:
        st.header("🗂️ Test Suite & Refinement")

        if not st.session_state.generated_tests:
            st.info("No test cases generated yet. Go to the 'Generate New Tests' tab to start.")
        else:
            # Handle refinement mode
            if st.session_state.get('refinement_mode') and st.session_state.get('test_to_refine'):
                test_to_refine = st.session_state.test_to_refine
                
                st.markdown("---")
                display_refinement_interface(test_to_refine)
                
                # Button to exit refinement mode
                if st.button("✅ Done Refining", key="done_refining"):
                    st.session_state.refinement_mode = False
                    st.session_state.test_to_refine = None
                    st.rerun()
            else:
                st.markdown(f"You have generated **{len(st.session_state.generated_tests)}** test case(s).")
                
                for i, tc in enumerate(st.session_state.generated_tests):
                    with st.expander(f"**{tc['id']}**: {tc.get('title', 'Untitled')} (v{tc.get('version', 1)})", expanded=(i==0)):
                        display_test_case(tc, tc.get('retrieved_context', [])) # Pass stored context
                        
                        # Refine button inside the expander
                        if st.button(f"🔄 Refine Test Case", key=f"refine_tc_{tc['id']}", type="secondary"):
                            st.session_state.refinement_mode = True
                            st.session_state.test_to_refine = tc
                            st.rerun()
    
    with tab3:
        # Display the document viewer
        display_document_viewer()


def display_refinement_interface(test_case: Dict):
    """Display interface for refining test cases with human feedback"""
    st.markdown("### 🔄 Refine Test Case with Human Feedback")
    
    # Show current test case info
    st.success(f"**Refining:** {test_case['id']} - {test_case.get('title', 'Untitled')}")
    
    # Store original version if not already stored
    test_id = test_case['id']
    if test_id not in st.session_state.test_versions:
        # This is the first refinement, store the original
        st.session_state.test_versions[test_id] = []
        # Store a clean copy without retrieved_context
        original_copy = {k: v for k, v in test_case.items() if k != 'retrieved_context'}
        st.session_state.test_versions[test_id].append(original_copy)
    
    # Show diff if this test has been refined before (version > 1)
    if test_case.get('version', 1) > 1 and test_id in st.session_state.test_versions:
        with st.expander("🔍 View Changes from Original", expanded=False):
            original = st.session_state.test_versions[test_id][0]  # Get the first (original) version
            display_test_diff(original, test_case)
    
    # Instructions
    with st.expander("ℹ️ How to Refine Test Cases", expanded=True):
        st.markdown("""
        **Three ways to refine your test case:**
        
        1. **💬 AI Refinement with Prompts** - Provide natural language feedback and let AI improve the test case
        2. **✏️ Direct Edit** - Manually edit any field yourself
        3. **🎯 Targeted Feedback** - Improve specific fields with focused prompts
        
        **Examples of refinement prompts:**
        - "Make this test case more focused on security vulnerabilities"
        - "Add negative test scenarios and edge cases"
        - "Include HIPAA compliance checks"
        - "Make the test steps more detailed with exact validation points"
        - "Add performance benchmarks and timing requirements"
        """)
    
    # Create tabs for different refinement options
    tab1, tab2, tab3 = st.tabs(["💬 AI Refinement with Prompts", "✏️ Direct Edit", "🎯 Targeted Field Improvement"])
    
    with tab1:
        st.markdown("#### 🤖 Provide Your Feedback as Natural Language Prompts")
        st.write("Tell the AI how you want to improve this test case using natural language.")
        
        # Quick prompt suggestions
        st.markdown("**Quick Prompts:** (Click to use)")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔒 Add Security Focus", key="sec_prompt"):
                st.session_state['prompt_suggestion'] = "Make this test case more focused on security vulnerabilities, add authentication checks, authorization validations, and data encryption verification"
            if st.button("📊 Add Performance Metrics", key="perf_prompt"):
                st.session_state['prompt_suggestion'] = "Add performance benchmarks, response time requirements, load testing scenarios, and resource utilization checks"
            if st.button("🚫 Add Negative Scenarios", key="neg_prompt"):
                st.session_state['prompt_suggestion'] = "Add negative test scenarios, error handling cases, boundary value tests, and invalid input validations"
        with col2:
            if st.button("🏥 Add Healthcare Compliance", key="health_prompt"):
                st.session_state['prompt_suggestion'] = "Add HIPAA compliance checks, PHI data handling verification, audit trail validation, and healthcare regulatory requirements"
            if st.button("🔄 Add Integration Tests", key="int_prompt"):
                st.session_state['prompt_suggestion'] = "Add API integration tests, database consistency checks, third-party service validations, and end-to-end workflow verification"
            if st.button("📝 Make More Detailed", key="detail_prompt"):
                st.session_state['prompt_suggestion'] = "Make the test steps more detailed with exact validation points, specific data values, clear acceptance criteria, and measurable outcomes"
        
        # Main feedback input
        default_prompt = st.session_state.get('prompt_suggestion', '')
        comprehensive_feedback = st.text_area(
            "✍️ Enter your refinement prompt:",
            value=default_prompt,
            placeholder="Example: 'Make this test case more comprehensive by adding edge cases, security validations, and performance requirements. Include specific test data for boundary conditions.'",
            height=150,
            key="ai_feedback_prompt"
        )
        
        # Show current test case summary
        with st.expander("📄 Current Test Case Summary"):
            st.write(f"**Title:** {test_case.get('title', 'N/A')}")
            st.write(f"**Description:** {test_case.get('description', 'N/A')[:200]}...")
            st.write(f"**Priority:** {test_case.get('priority', 'N/A')} | **Category:** {test_case.get('category', 'N/A')}")
            st.write(f"**Number of Steps:** {len(test_case.get('test_steps', []))}")
        
        if st.button("🚀 Apply AI Refinement", type="primary", key="apply_ai_refinement"):
            if comprehensive_feedback:
                with st.spinner("🤖 AI is refining your test case based on your feedback..."):
                    refined_test = refine_test_case_with_feedback(test_case, comprehensive_feedback)
                    
                    # Store version history if this is first refinement
                    test_id = test_case['id']
                    if test_id not in st.session_state.test_versions:
                        st.session_state.test_versions[test_id] = []
                        # Store the original version (without retrieved_context)
                        original_copy = {k: v for k, v in test_case.items() if k != 'retrieved_context'}
                        st.session_state.test_versions[test_id].append(original_copy)
                    
                    # Update in session state - find and replace the test case
                    test_updated = False
                    for i in range(len(st.session_state.generated_tests)):
                        if st.session_state.generated_tests[i]['id'] == test_case['id']:
                            st.session_state.generated_tests[i] = refined_test
                            test_updated = True
                            break
                    
                    if not test_updated:
                        st.error("Failed to update test case in the list. Please try again.")
                        return
                    
                    # Track refinement history
                    if test_case['id'] not in st.session_state.refinement_history:
                        st.session_state.refinement_history[test_case['id']] = []
                    st.session_state.refinement_history[test_case['id']].append({
                        'timestamp': datetime.now().isoformat(),
                        'type': 'ai_refinement',
                        'feedback': comprehensive_feedback,
                        'version': refined_test.get('version', 1)
                    })
                    
                    st.success("✅ Test case refined successfully using AI!")
                    st.balloons()
                    
                    # Clear prompt suggestion
                    if 'prompt_suggestion' in st.session_state:
                        del st.session_state['prompt_suggestion']
                    
                    # Exit refinement mode to show the updated test
                    st.session_state.refinement_mode = False
                    st.session_state.test_to_refine = None
                    st.rerun()
            else:
                st.warning("Please provide a refinement prompt to improve the test case")
    
    with tab2:
        st.markdown("#### ✏️ Manually Edit Test Case Fields")
        
        # Create editable fields
        edited_test = test_case.copy()
        
        edited_test['title'] = st.text_input("Title", value=test_case.get('title', ''), key="edit_title")
        edited_test['description'] = st.text_area("Description", value=test_case.get('description', ''), height=100, key="edit_desc")
        
        col1, col2 = st.columns(2)
        with col1:
            category_options = ['Functional', 'Security', 'Integration', 'Performance', 'Usability', 'Compliance']
            current_category = test_case.get('category', 'Functional')
            category_index = category_options.index(current_category) if current_category in category_options else 0
            edited_test['category'] = st.selectbox("Category", 
                                                  options=category_options,
                                                  index=category_index,
                                                  key="edit_category")
        with col2:
            priority_options = ['Critical', 'High', 'Medium', 'Low']
            current_priority = test_case.get('priority', 'Medium')
            priority_index = priority_options.index(current_priority) if current_priority in priority_options else 0
            edited_test['priority'] = st.selectbox("Priority",
                                                  options=priority_options,
                                                  index=priority_index,
                                                  key="edit_priority")
        
        edited_test['preconditions'] = st.text_area("Preconditions", value=test_case.get('preconditions', ''), key="edit_precon")
        
        # Test steps editing
        st.write("**Test Steps:**")
        steps = test_case.get('test_steps', [])
        edited_steps = []
        for i, step in enumerate(steps):
            col1, col2 = st.columns([10, 1])
            with col1:
                edited_step = st.text_input(f"Step {i+1}", value=step, key=f"step_{i}", label_visibility="collapsed")
                edited_steps.append(edited_step)
            with col2:
                if st.button("🗑️", key=f"del_step_{i}"):
                    steps.pop(i)
                    st.rerun()
        edited_test['test_steps'] = edited_steps
        
        # Add new step
        if st.button("➕ Add Step", key="add_step"):
            edited_test['test_steps'].append("")
            st.rerun()
        
        edited_test['expected_results'] = st.text_area("Expected Results", value=test_case.get('expected_results', ''), key="edit_expected")
        edited_test['estimated_duration'] = st.text_input("Estimated Duration", value=test_case.get('estimated_duration', ''), key="edit_duration")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Manual Edits", type="primary", key="save_edits"):
                edited_test['manually_edited'] = True
                edited_test['edit_timestamp'] = datetime.now().isoformat()
                edited_test['version'] = test_case.get('version', 1) + 1
                
                # Store version history if this is first refinement
                test_id = test_case['id']
                if test_id not in st.session_state.test_versions:
                    st.session_state.test_versions[test_id] = []
                    # Store the original version (without retrieved_context)
                    original_copy = {k: v for k, v in test_case.items() if k != 'retrieved_context'}
                    st.session_state.test_versions[test_id].append(original_copy)
                
                # Preserve the retrieved_context if it exists
                if 'retrieved_context' in test_case:
                    edited_test['retrieved_context'] = test_case['retrieved_context']
                
                # Update in session state
                test_updated = False
                for i in range(len(st.session_state.generated_tests)):
                    if st.session_state.generated_tests[i]['id'] == test_case['id']:
                        st.session_state.generated_tests[i] = edited_test
                        test_updated = True
                        break
                
                if not test_updated:
                    st.error("Failed to update test case in the list. Please try again.")
                    return
                
                st.success("✅ Test case updated successfully!")
                
                # Exit refinement mode to show the updated test
                st.session_state.refinement_mode = False
                st.session_state.test_to_refine = None
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel Edits", key="cancel_edits"):
                st.session_state.refinement_mode = False
                st.session_state.test_to_refine = None
                st.rerun()
    
    with tab3:
        st.markdown("#### 🎯 Improve Specific Fields with Targeted Prompts")
        st.write("Focus your feedback on improving individual fields of the test case.")
        
        field_to_refine = st.selectbox(
            "Select field to improve:",
            options=['title', 'description', 'test_steps', 'expected_results', 'preconditions', 'edge_cases', 'test_data'],
            key="field_select"
        )
        
        # Show current value
        current_value = test_case.get(field_to_refine, 'Not set')
        if isinstance(current_value, list):
            current_value = '\n'.join([f"• {item}" for item in current_value])
        elif isinstance(current_value, dict):
            current_value = json.dumps(current_value, indent=2)
        
        with st.expander(f"Current {field_to_refine}"):
            st.text(str(current_value)[:500] + ('...' if len(str(current_value)) > 500 else ''))
        
        # Field-specific prompt suggestions
        field_suggestions = {
            'title': "Make it more descriptive and specific to the test scenario",
            'description': "Add more context about what is being tested and why it's important",
            'test_steps': "Make each step more detailed with specific actions and validation points",
            'expected_results': "Add measurable outcomes and specific success criteria",
            'preconditions': "Include all system states, data requirements, and environment setup needed",
            'edge_cases': "Add boundary conditions, error scenarios, and unusual user behaviors",
            'test_data': "Include specific test values, invalid inputs, and boundary values"
        }
        
        st.info(f"💡 Suggestion: {field_suggestions.get(field_to_refine, 'Provide specific improvements for this field')}")
        
        feedback = st.text_area(
            f"How should the '{field_to_refine}' be improved?",
            placeholder=f"Example: {field_suggestions.get(field_to_refine, 'Describe your improvements...')}",
            height=100,
            key="field_feedback"
        )
        
        if st.button("🔄 Refine This Field", type="primary", key="refine_field"):
            if feedback:
                with st.spinner(f"🤖 AI is refining {field_to_refine}..."):
                    refined_test = refine_test_case_with_feedback(test_case, feedback, field_to_refine)
                    
                    # Store version history if this is first refinement
                    test_id = test_case['id']
                    if test_id not in st.session_state.test_versions:
                        st.session_state.test_versions[test_id] = []
                        # Store the original version (without retrieved_context)
                        original_copy = {k: v for k, v in test_case.items() if k != 'retrieved_context'}
                        st.session_state.test_versions[test_id].append(original_copy)
                    
                    # Update in session state
                    test_updated = False
                    for i in range(len(st.session_state.generated_tests)):
                        if st.session_state.generated_tests[i]['id'] == test_case['id']:
                            st.session_state.generated_tests[i] = refined_test
                            test_updated = True
                            break
                    
                    if not test_updated:
                        st.error("Failed to update test case in the list. Please try again.")
                        return
                    
                    # Track refinement history
                    if test_case['id'] not in st.session_state.refinement_history:
                        st.session_state.refinement_history[test_case['id']] = []
                    st.session_state.refinement_history[test_case['id']].append({
                        'timestamp': datetime.now().isoformat(),
                        'field': field_to_refine,
                        'feedback': feedback,
                        'version': refined_test.get('version', 1)
                    })
                    
                    st.success(f"✅ {field_to_refine} refined successfully!")
                    
                    # Exit refinement mode to show the updated test
                    st.session_state.refinement_mode = False
                    st.session_state.test_to_refine = None
                    st.rerun()
            else:
                st.warning("Please provide feedback for refinement")
    
    # Show refinement history
    if test_case['id'] in st.session_state.refinement_history and st.session_state.refinement_history[test_case['id']]:
        with st.expander("📜 Refinement History"):
            for entry in st.session_state.refinement_history[test_case['id']]:
                st.write(f"**Version {entry.get('version', 'N/A')}** - {entry['timestamp'][:19]}")
                if 'field' in entry:
                    st.write(f"Field refined: {entry['field']}")
                st.write(f"Feedback: {entry['feedback']}")
                st.divider()

def display_test_case(test_case: Dict, context_docs: List[Dict]):
    """Display generated test case in a formatted way"""
    
    # Header with metrics
    st.markdown("---")
    
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
    
    # Show version and diff button if refined
    test_id = test_case['id']
    current_version = test_case.get('version', 1)
    if current_version > 1:
        st.info(f"📌 Version {current_version} - This test case has been refined")
        
        # Show diff if we have the original version stored
        if test_id in st.session_state.test_versions and st.session_state.test_versions[test_id]:
            with st.expander("🔍 View Changes from Original Version", expanded=False):
                original = st.session_state.test_versions[test_id][0]
                display_test_diff(original, test_case)
    
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
    
    if context_docs:
        with st.expander("📚 Context Sources Used"):
            if test_case.get('context_sources'):
                for source in test_case['context_sources']:
                    st.write(f"• {source}")
            
            if context_docs and not test_case.get('fallback'):
                st.markdown("### Retrieved Context:")
                for i, doc in enumerate(context_docs[:3], 1):
                    st.write(f"**{i}. {doc['metadata'].get('source', 'Unknown')}** (Relevance: {doc['similarity']:.2%})")
                    
                    # Use test case ID in the key to make it unique
                    label = f"Retrieved Context from {doc['metadata'].get('source', 'Unknown')}"
                    unique_key = f"ctx_{test_case.get('id', 'unknown')}_{i}"
                    st.text_area(label, value=doc['content'], height=100, disabled=True, key=unique_key, label_visibility="collapsed")
    
    # Save options
    st.markdown("#### 💾 Save Options")
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
