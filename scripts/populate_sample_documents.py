#!/usr/bin/env python3
"""
Populate MongoDB with sample documents for demo purposes.
These documents will be available to all users for testing document upload and RAG features.
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

# Sample documents configuration
SAMPLE_DOCS = [
    {
        'path': 'data/sample_files/sample_user_story.txt',
        'name': 'sample_user_story.txt',
        'type': 'user_stories',
        'description': 'Complete user story with acceptance criteria for patient portal dashboard',
        'tags': ['user-story', 'agile', 'dashboard', 'patient-portal', 'demo'],
        'usage': 'Upload this to test document processing and generate related test cases.'
    },
    {
        'path': 'data/sample_files/sample_prd.md',
        'name': 'sample_prd_telemedicine.md',
        'type': 'requirements',
        'description': 'Comprehensive PRD for telemedicine platform with compliance requirements',
        'tags': ['prd', 'requirements', 'telemedicine', 'compliance', 'demo'],
        'usage': 'Use for testing PRD upload and compliance-based test generation.'
    },
    {
        'path': 'data/sample_files/sample_api_spec.yaml',
        'name': 'sample_api_spec_patient.yaml',
        'type': 'api_specification',
        'description': 'OpenAPI 3.0 specification for patient management REST API',
        'tags': ['api', 'openapi', 'rest', 'patient-management', 'demo'],
        'usage': 'Upload to test API spec parsing and generate API test cases.'
    }
]

def main():
    logger.info("="*60)
    logger.info("     SAMPLE DOCUMENTS POPULATION SCRIPT")
    logger.info("     Adding Demo Documents for Upload Testing")
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
    
    # Process each sample document
    successful = 0
    failed = 0
    
    for doc_info in SAMPLE_DOCS:
        try:
            file_path = Path(doc_info['path'])
            
            # Check if file exists
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                failed += 1
                continue
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Processing: {doc_info['name']} ({len(content):,} chars)")
            
            # Save to MongoDB shared documents
            doc_id = db_manager.save_shared_document(
                filename=doc_info['name'],
                content=content,
                doc_type=doc_info['type'],
                metadata={
                    'description': doc_info['description'],
                    'tags': doc_info['tags'],
                    'usage': doc_info['usage'],
                    'source': 'NASSCOM_Demo_Documents',
                    'version': '1.0',
                    'created_for': 'Document Upload Testing',
                    'file_format': doc_info['name'].split('.')[-1].upper(),
                    'is_sample': True,
                    'is_document': True
                }
            )
            
            if doc_id:
                logger.info(f"  ✅ Saved: {doc_info['name']}")
                successful += 1
            else:
                logger.error(f"  ❌ Failed to save: {doc_info['name']}")
                failed += 1
                
        except Exception as e:
            logger.error(f"Error processing {doc_info.get('name', 'unknown')}: {e}")
            failed += 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SAMPLE DOCUMENTS POPULATION COMPLETE")
    logger.info("="*60)
    logger.info(f"✅ Successfully loaded: {successful} documents")
    if failed > 0:
        logger.info(f"❌ Failed: {failed} documents")
    
    logger.info("\n📄 Available Sample Documents:")
    logger.info("1. User Story - Complete with acceptance criteria")
    logger.info("2. PRD - Telemedicine platform requirements")
    logger.info("3. API Spec - OpenAPI 3.0 patient management")
    
    logger.info("\n💡 These documents are now available for:")
    logger.info("• Testing document upload functionality")
    logger.info("• RAG-based test generation")
    logger.info("• Compliance analysis")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
