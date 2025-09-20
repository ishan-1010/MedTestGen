#!/usr/bin/env python3
"""
Populate MongoDB with sample test files for demo purposes.
These files will be available to all users for testing import/export features.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import MongoDBManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Sample files configuration
SAMPLE_FILES = [
    {
        'path': 'data/sample_files/sample_test_cases.csv',
        'name': 'sample_test_cases_basic.csv',
        'type': 'test_samples',
        'description': 'Basic CSV format test cases for healthcare portal testing',
        'tags': ['csv', 'basic', 'functional', 'compliance', 'demo'],
        'usage': 'Use this file to test CSV import functionality. Contains 10 diverse test cases.'
    },
    {
        'path': 'data/sample_files/sample_test_cases.json',
        'name': 'sample_test_cases_api.json',
        'type': 'test_samples',
        'description': 'JSON format test suite with API and integration test cases',
        'tags': ['json', 'api', 'integration', 'advanced', 'demo'],
        'usage': 'Perfect for testing JSON import and API test case structures.'
    },
    {
        'path': 'data/sample_files/sample_test_cases.xml',
        'name': 'sample_test_cases_compliance.xml',
        'type': 'test_samples',
        'description': 'XML format test cases focusing on healthcare compliance (HIPAA, FDA, FHIR)',
        'tags': ['xml', 'compliance', 'hipaa', 'fda', 'fhir', 'demo'],
        'usage': 'Import this to test XML parsing and compliance-focused test cases.'
    },
    {
        'path': 'data/sample_files/sample_test_cases_jira.csv',
        'name': 'sample_test_cases_jira.csv',
        'type': 'test_samples',
        'description': 'Jira-compatible CSV format with acceptance criteria and epic links',
        'tags': ['jira', 'agile', 'csv', 'user-stories', 'demo'],
        'usage': 'Use for testing Jira import/export functionality.'
    },
    {
        'path': 'data/sample_files/sample_azure_devops_tests.csv',
        'name': 'sample_test_cases_azure.csv',
        'type': 'test_samples',
        'description': 'Azure DevOps test case format with work item types and area paths',
        'tags': ['azure-devops', 'microsoft', 'csv', 'enterprise', 'demo'],
        'usage': 'Import to test Azure DevOps integration capabilities.'
    }
]

def create_sample_file_document(file_info: dict, content: str) -> dict:
    """Create a document structure for MongoDB storage"""
    return {
        'filename': file_info['name'],
        'original_path': file_info['path'],
        'content': content,
        'doc_type': file_info['type'],
        'metadata': {
            'description': file_info['description'],
            'tags': file_info['tags'],
            'usage': file_info['usage'],
            'source': 'NASSCOM_Demo_Samples',
            'version': '1.0',
            'created_for': 'Import/Export Testing',
            'file_format': file_info['name'].split('.')[-1].upper()
        },
        'is_shared': True,
        'is_sample': True,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

def main():
    logger.info("="*60)
    logger.info("     SAMPLE TEST FILES POPULATION SCRIPT")
    logger.info("     Adding Demo Files for Import/Export Testing")
    logger.info("="*60)
    
    # Get MongoDB URI
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        logger.error("MONGODB_URI not set. Please configure your .env file.")
        return 1
    
    # Connect to MongoDB
    try:
        db_manager = MongoDBManager(mongodb_uri)
        logger.info("✅ Connected to MongoDB successfully")
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        return 1
    
    # Process each sample file
    successful = 0
    failed = 0
    
    for file_info in SAMPLE_FILES:
        try:
            file_path = Path(file_info['path'])
            
            # Check if file exists
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                failed += 1
                continue
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Processing: {file_info['name']} ({len(content):,} chars)")
            
            # Save to MongoDB shared documents
            doc_id = db_manager.save_shared_document(
                filename=file_info['name'],
                content=content,
                doc_type=file_info['type'],
                metadata={
                    'description': file_info['description'],
                    'tags': file_info['tags'],
                    'usage': file_info['usage'],
                    'source': 'NASSCOM_Demo_Samples',
                    'version': '1.0',
                    'created_for': 'Import/Export Testing',
                    'file_format': file_info['name'].split('.')[-1].upper(),
                    'is_sample': True
                }
            )
            
            if doc_id:
                logger.info(f"  ✅ Saved: {file_info['name']}")
                successful += 1
            else:
                logger.error(f"  ❌ Failed to save: {file_info['name']}")
                failed += 1
                
        except Exception as e:
            logger.error(f"Error processing {file_info.get('name', 'unknown')}: {e}")
            failed += 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SAMPLE FILES POPULATION COMPLETE")
    logger.info("="*60)
    logger.info(f"✅ Successfully loaded: {successful} files")
    if failed > 0:
        logger.info(f"❌ Failed: {failed} files")
    
    logger.info("\n📁 Available Sample Files:")
    logger.info("1. Basic CSV - 10 diverse test cases")
    logger.info("2. API JSON - API and integration tests")
    logger.info("3. Compliance XML - HIPAA, FDA, FHIR tests")
    logger.info("4. Jira CSV - Agile format with epics")
    logger.info("5. Azure DevOps CSV - Enterprise format")
    
    logger.info("\n💡 These files are now available to ALL users for testing!")
    logger.info("Users can download these from the app and use them to test import functionality.")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
