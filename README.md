# MedTestGen: AI-Powered Test Case Generator 
https://medtestgen-ishan-genai-hack.streamlit.app/

## NASSCOM Healthcare/MedTech Testing Solution

<div align="center">
  
  ![Version](https://img.shields.io/badge/version-8.0-blue)
  ![Python](https://img.shields.io/badge/python-3.8+-green)
  ![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red)
  ![License](https://img.shields.io/badge/license-MIT-purple)
  
  <p align="center">
    <strong>Automated Test Case Generation with AI for Healthcare Applications</strong><br>
  </p>

</div>

---

## ✨ Features

### Core Capabilities
- **🤖 AI-Powered Generation**: Leverages Google Gemini API for intelligent test case creation
- **📚 RAG Pipeline**: Context-aware generation using FAISS vector database
- **🏥 Healthcare Focus**: Specialized for healthcare/MedTech compliance (HIPAA, FDA, GDPR)
- **📄 Multi-Format Support**: Process PDFs, Word docs, XML, YAML, and more
- **✅ Compliance Validation**: Automatic checking against NASSCOM guidelines
- **🔄 Smart Import**: AI-powered test suite migration from existing formats
- **📤 DevOps Integration**: Export to Jira, Azure DevOps, Postman, JUnit, TestRail

### Modern UI Features
- 🎨 Clean, modern interface with smooth animations
- ⚡ Real-time progress indicators with intelligent feedback
- 💾 Automatic test case persistence
- 🔍 Advanced search and filtering
- 📊 Test coverage metrics and analytics

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.8 or higher required
python --version

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Installation
```bash
# Install dependencies
pip install -r requirements.txt
```

### Configuration
1. Get your Gemini API key
2. Create a `.env` file:
```env
GEMINI_API_KEY=your_api_key_here
```

### Run the Application
```bash
# Run the main app
streamlit run src/app_v14.py

# The app will open at http://localhost:8501
```

## 📁 Project Structure

```
ai-test-generator/
├── src/
│   ├── app.py                 # Main application (v8 - latest)
│   ├── app_v8.py              # Backup of main version
│   └── ui_enhancements.py     # Modern UI components
│
├── data/
│   ├── test_cases/            # Unified test case storage
│   ├── documents/             # RAG knowledge base documents
│   ├── uploaded_documents/    # User uploaded files
│   └── faiss_indices/         # Vector database indices
│
├── experiments/               # Previous versions for reference
│   ├── app_v1.py             # Initial RAG implementation
│   ├── app_v2.py             # Basic test generation
│   ├── app_v3.py             # Enhanced generation
│   ├── app_v4.py             # Refinement features
│   ├── app_v5.py             # Document upload & compliance
│   ├── app_v6.py             # AI-powered import
│   └── app_v7.py             # DevOps export formats
│
├── notebooks/                 # Jupyter notebooks for exploration
│   ├── 01_initial_exploration.ipynb
│   ├── 02_faiss_vector_db_testing.ipynb
│   ├── 03_rag_pipeline_with_gemini.ipynb
│   └── 04_rag_pipeline_fixed.ipynb
│
├── docs/                      # Documentation
├── scripts/                   # Utility scripts
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🎯 Usage Guide

### 1. Generate Test Cases
1. Enter your Gemini API key in the sidebar
2. Navigate to "Generate Tests" tab
3. Enter your requirement (e.g., "Test user registration with email verification")
4. Select test type and priority
5. Click "Generate Test Case"
6. AI will analyze, search knowledge base, and create comprehensive test cases

### 2. Upload Documents
1. Go to "Upload Documents" tab
2. Upload PRDs, user stories, or specifications
3. System automatically validates compliance
4. Documents are added to RAG knowledge base

### 3. Import Existing Tests
1. Navigate to "Import Tests" tab
2. Upload CSV, JSON, or Excel files
3. AI detects schema and converts to standard format
4. Deduplication and validation performed automatically

### 4. Export Test Suite
1. Go to "Export" tab
2. Select target format (Jira, Azure DevOps, etc.)
3. Optionally customize field mappings with AI
4. Download formatted export

## 🛠️ Technology Stack

- **Frontend**: Streamlit with custom CSS/HTML
- **AI/ML**: 
  - Google Gemini API (gemini-2.0-flash-exp)
  - Sentence Transformers (all-MiniLM-L6-v2)
  - FAISS for vector similarity search
- **Document Processing**: PyPDF2, python-docx, lxml
- **Data Storage**: JSON file-based persistence
- **Languages**: Python 3.8+

## 📊 Key Improvements & Features

### Version History
- **v8**: Unified folder structure, enhanced UI
- **v7**: DevOps export formats, auto-save functionality
- **v6**: AI-powered test import, deduplication
- **v5**: Document compliance validation
- **v4**: Test refinement capabilities
- **v3**: Enhanced generation algorithms
- **v2**: Basic test case generation
- **v1**: Initial RAG pipeline implementation

### NASSCOM Compliance
The system adheres to NASSCOM requirements:
- ✅ No-code test authoring
- ✅ Multi-source input support
- ✅ Healthcare domain expertise
- ✅ Comprehensive test case format
- ✅ Natural language enhancement
- ✅ Existing test migration
- ✅ DevOps tool integration
- ✅ Compliance traceability
- ✅ GDPR compliance ready


---

<div align="center">
  <strong>Built with ❤️ for NASSCOM by Ishan (Code Spangers)</strong>
</div>
