# MedTestGen: AI-Powered Test Case Generator 
https://medtestgen-ishan-genai-hack.streamlit.app/

## NASSCOM Healthcare/MedTech Testing Solution

<div align="center">
  
  ![Version](https://img.shields.io/badge/version-15.0-blue)
  ![Python](https://img.shields.io/badge/python-3.8+-green)
  ![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red)
  ![License](https://img.shields.io/badge/license-MIT-purple)
  ![AI](https://img.shields.io/badge/AI-Gemini_2.0-blueviolet)
  ![Healthcare](https://img.shields.io/badge/Healthcare-HIPAA_Compliant-success)
  
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

### 🆕 Advanced Features (NEW)
- **🔧 Git Integration**: AI-powered code change analysis with automated test generation
  - Analyze commits and code changes with risk scoring
  - Detect healthcare/compliance-related modifications
  - Generate targeted test cases from Git diffs
  - Comprehensive test strategy recommendations
  
- **📊 Feature Gap Analysis**: Intelligent requirement coverage analysis
  - Extract requirements from documents using AI
  - Calculate test coverage with semantic matching
  - Identify critical coverage gaps by priority
  - Auto-generate tests to fill gaps
  
- **🚀 API Test Execution**: Direct API testing capabilities
  - Execute REST API tests within the platform
  - Healthcare compliance validation (HIPAA, GDPR, FDA)
  - Real-time test execution with detailed reports
  - Mock healthcare API for demonstrations

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
# Run the main app (latest version)
streamlit run src/app_v15.py

# The app will open at http://localhost:8501
```

## 📁 Project Structure

```
ai-test-generator/
├── src/
│   ├── app_v15.py             # Main application (v15 - latest)
│   ├── database.py            # SQLite database management
│   ├── git_analyzer.py        # 🆕 Git integration & code analysis
│   ├── feature_gap_analyzer.py # 🆕 Feature gap detection & coverage
│   └── api_test_executor.py   # 🆕 API test execution engine
│
├── data/
│   ├── test_cases/            # Unified test case storage
│   ├── documents/             # RAG knowledge base documents
│   ├── uploaded_documents/    # User uploaded files
│   ├── faiss_indices/         # Vector database indices
│   └── preloaded_docs/        # Pre-loaded healthcare templates
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

### 5. 🆕 Analyze Git Repository (Code Change Testing)
1. Navigate to "Git Analysis" tab
2. Enter path to your Git repository
3. Select date range or number of recent commits
4. Choose branch to analyze
5. Click "Analyze Repository"
6. Review AI-powered insights:
   - Code changes with risk scoring
   - Compliance impact analysis
   - Recommended test cases
   - Test strategy suggestions
7. Generate test cases directly from commits

### 6. 🆕 Feature Gap Analysis (Coverage Analysis)
1. Go to "Feature Gap Analysis" tab
2. Upload requirement documents (PRDs, User Stories)
3. System extracts requirements using AI
4. Analyze coverage against existing tests
5. View detailed gap report:
   - Coverage percentage by requirement
   - Critical gaps highlighted
   - Severity-based prioritization
6. Auto-generate tests to fill identified gaps

### 7. 🆕 Execute API Tests
1. Navigate to "API Test Execution" tab
2. Configure API base URL
3. Set authentication credentials
4. Select test cases to execute
5. Run tests and view real-time results
6. Review compliance checks (HIPAA, GDPR, FDA)
7. Export HTML test report

## 🛠️ Technology Stack

- **Frontend**: Streamlit with custom CSS/HTML
- **AI/ML**: 
  - Google Gemini API (gemini-2.0-flash-exp)
  - Sentence Transformers (all-MiniLM-L6-v2)
  - FAISS for vector similarity search
- **Document Processing**: PyPDF2, python-docx, lxml
- **Data Storage**: 
  - SQLite for persistent storage
  - JSON file-based exports
- **Git Integration**: GitPython for repository analysis
- **API Testing**: Requests library with compliance validation
- **Languages**: Python 3.8+
- **Dependencies**: 
  - numpy, pandas for data processing
  - streamlit for web interface
  - Additional healthcare compliance libraries

## 📊 Key Improvements & Features

### Version History
- **v15** (Latest): Git integration, Feature gap analysis, API test execution
  - Advanced code change analysis with AI insights
  - Intelligent requirement coverage tracking
  - Direct API testing with compliance validation
  - Enhanced database persistence
- **v14**: Enhanced UI/UX, improved test management
- **v8-v13**: Progressive feature enhancements
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

## 🆕 New Modules Documentation

### Git Analyzer (`git_analyzer.py`)
Advanced Git repository analysis module that bridges code changes with test requirements:

**Key Features:**
- **Commit Analysis**: Deep analysis of Git commits with change tracking
- **Risk Scoring**: Automated risk assessment (0-100 scale) based on:
  - File criticality patterns
  - Change magnitude
  - Healthcare/compliance relevance
- **AI-Powered Insights**: Gemini-driven analysis provides:
  - Impact summaries
  - Critical test scenarios
  - Security concerns
  - Compliance testing requirements
  - Regression risk assessment
- **Test Generation**: Automatic test case creation from code changes
- **Compliance Detection**: Identifies HIPAA, GDPR, FDA, ISO 27001 impacts
- **Healthcare Patterns**: Specialized detection for:
  - Patient data handling
  - PHI/PII protection
  - Authentication/Authorization
  - Encryption requirements

**Usage:**
```python
from src.git_analyzer import GitAnalyzer

analyzer = GitAnalyzer(repo_path="./", api_key="your_key")
analysis = analyzer.analyze_repository(days=7)
test_cases = analyzer.generate_test_cases_for_commit(commit_sha)
```

### Feature Gap Analyzer (`feature_gap_analyzer.py`)
Intelligent requirement coverage analysis using semantic similarity:

**Key Features:**
- **Requirement Extraction**: AI-powered extraction from:
  - Product Requirement Documents (PRDs)
  - User Stories
  - API Specifications
  - Technical documentation
- **Coverage Analysis**: Semantic matching using sentence transformers
- **Gap Detection**: Identifies coverage gaps with severity levels:
  - Critical: <20% coverage
  - High: 20-40% coverage
  - Medium: 40-60% coverage
- **Test Prioritization**: Priority-based gap ranking
- **Auto-Fill**: Generate tests to fill identified gaps
- **Compliance Tracking**: Maps requirements to compliance standards

**Usage:**
```python
from src.feature_gap_analyzer import FeatureGapAnalyzer

analyzer = FeatureGapAnalyzer(embedding_model, api_key)
requirements = analyzer.extract_requirements_from_documents(docs)
covered, gaps = analyzer.analyze_coverage(requirements, test_cases)
```

### API Test Executor (`api_test_executor.py`)
Direct API testing with healthcare compliance validation:

**Key Features:**
- **REST API Testing**: Execute GET, POST, PUT, DELETE, PATCH requests
- **Authentication**: Support for:
  - Bearer tokens
  - API keys
  - Basic auth
  - OAuth 2.0
- **Compliance Validation**:
  - HIPAA: HTTPS, authentication, audit trails
  - GDPR: Rate limiting, data protection
  - FDA 21 CFR Part 11: Versioning, validation
- **Assertion Engine**: Automated validation of:
  - Status codes
  - Response times
  - Content types
  - Required fields
- **HTML Reports**: Comprehensive test execution reports
- **Mock API**: Built-in mock healthcare API for demonstrations

**Usage:**
```python
from src.api_test_executor import APITestExecutor

executor = APITestExecutor(base_url="https://api.example.com")
executor.set_authentication('bearer', {'token': 'xxx'})
result = executor.execute_test(test_case)
summary = executor.execute_test_suite(test_cases)
```

## 📈 Performance & Scalability

- **Vector Search**: FAISS-powered similarity search for fast requirement matching
- **Batch Processing**: Efficient processing of multiple documents/commits
- **Caching**: Smart caching of embeddings and AI responses
- **Async Operations**: Support for concurrent test execution
- **Database**: SQLite for reliable persistence with indexing

## 🔐 Security & Compliance

- **API Key Protection**: Secure handling of credentials
- **Data Sanitization**: Sensitive data masking in logs/reports
- **Audit Logging**: Comprehensive activity tracking
- **Compliance Validation**: Built-in checks for healthcare regulations
- **Encryption**: Support for encrypted data transmission

---

<div align="center">
  <strong>Built with ❤️ for NASSCOM by Ishan (Code Spangers)</strong>
</div>
