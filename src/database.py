"""
MongoDB Database Integration Module
For AI Test Generator - NASSCOM Healthcare Testing Solution
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import ConnectionFailure, DuplicateKeyError, ServerSelectionTimeoutError
import json
from bson import ObjectId
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class MongoDBManager:
    """Production-ready MongoDB integration for test case management"""
    
    def __init__(self, connection_string: str = None):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB URI. If None, uses env variable
        """
        if connection_string is None:
            # Try environment variable first
            connection_string = os.getenv('MONGODB_URI')
            
        if not connection_string:
            raise ValueError("MongoDB connection string not provided")
        
        try:
            # Create client with connection pooling and timeout settings
            self.client = MongoClient(
                connection_string,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True
            )
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB successfully")
            print("✅ Connected to MongoDB successfully")
            
            # Select database (genai_hack_app from connection string)
            try:
                self.db = self.client.get_default_database()
                if self.db is None:
                    # Fallback to explicit database name if not in connection string
                    self.db = self.client['genai_hack_app']
                    logger.info("Using fallback database: genai_hack_app")
            except Exception:
                # If no database in URI, use explicit name
                self.db = self.client['genai_hack_app']
                logger.info("No database in URI, using: genai_hack_app")
            
            # Initialize collections
            self.test_cases = self.db['test_cases']
            self.test_suites = self.db['test_suites']
            self.documents = self.db['documents']
            self.shared_documents = self.db['shared_documents']  # Pre-loaded docs for all users
            self.compliance_reports = self.db['compliance_reports']
            self.audit_logs = self.db['audit_logs']
            self.rag_embeddings = self.db['rag_embeddings']
            self.user_sessions = self.db['user_sessions']
            self.users = self.db['users']  # User authentication collection
            
            # Create indexes for optimal performance
            self._create_indexes()
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"❌ MongoDB connection timeout: {e}")
            print(f"❌ MongoDB connection timeout. Please check your connection string and network.")
            raise
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Create indexes for optimal query performance"""
        try:
            # Test cases indexes
            self.test_cases.create_index([("test_id", ASCENDING)], unique=True, sparse=True)
            self.test_cases.create_index([("created_at", DESCENDING)])
            self.test_cases.create_index([("category", ASCENDING)])
            self.test_cases.create_index([("priority", ASCENDING)])
            self.test_cases.create_index([("nasscom_compliant", ASCENDING)])
            self.test_cases.create_index([
                ("title", TEXT),
                ("description", TEXT),
                ("requirement", TEXT)
            ], name="text_search_index")
            
            # Test suites indexes
            self.test_suites.create_index([("suite_id", ASCENDING)], unique=True, sparse=True)
            self.test_suites.create_index([("created_at", DESCENDING)])
            
            # Documents indexes
            self.documents.create_index([("filename", ASCENDING)])
            self.documents.create_index([("uploaded_at", DESCENDING)])
            self.documents.create_index([("doc_type", ASCENDING)])
            
            # Compliance reports indexes
            self.compliance_reports.create_index([("filename", ASCENDING)])
            self.compliance_reports.create_index([("analyzed_at", DESCENDING)])
            self.compliance_reports.create_index([("is_compliant", ASCENDING)])
            
            # Audit logs indexes
            self.audit_logs.create_index([("timestamp", DESCENDING)])
            self.audit_logs.create_index([("action", ASCENDING)])
            
            # User indexes
            self.users.create_index([("email", ASCENDING)], unique=True)
            self.users.create_index([("username", ASCENDING)], unique=True, sparse=True)
            self.users.create_index([("created_at", DESCENDING)])
            
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not create some indexes: {e}")
    
    # ========================================
    # TEST CASE OPERATIONS
    # ========================================
    
    def save_test_case(self, test_case: Dict, session_id: str = None, user_id: str = None) -> Tuple[bool, str]:
        """
        Save or update a test case in MongoDB with user ownership
        
        Returns:
            Tuple of (success: bool, test_id: str)
        """
        try:
            # Ensure test has an ID
            if 'id' not in test_case:
                test_case['id'] = f"TC_{ObjectId()}"
            
            # Clean the test case for MongoDB
            test_case_copy = test_case.copy()
            test_case_copy['test_id'] = test_case_copy['id']  # Use test_id as index
            
            # Add metadata
            now = datetime.utcnow()
            
            # Check if exists for this user
            query = {'test_id': test_case_copy['test_id']}
            if user_id:
                query['user_id'] = user_id
            
            existing = self.test_cases.find_one(query)
            
            if existing:
                # Update existing
                test_case_copy['updated_at'] = now
                test_case_copy['version'] = existing.get('version', 1) + 1
                test_case_copy['user_id'] = user_id  # Ensure user_id is set
                
                result = self.test_cases.replace_one(
                    query,
                    test_case_copy
                )
                success = result.modified_count > 0
            else:
                # Insert new
                test_case_copy['created_at'] = now
                test_case_copy['updated_at'] = now
                test_case_copy['version'] = 1
                test_case_copy['session_id'] = session_id
                test_case_copy['user_id'] = user_id  # Add user ownership
                
                result = self.test_cases.insert_one(test_case_copy)
                success = result.inserted_id is not None
            
            # Audit log
            self._audit_log('test_case_saved', session_id, {
                'test_id': test_case_copy['test_id'],
                'action': 'update' if existing else 'create'
            })
            
            return success, test_case_copy['test_id']
            
        except Exception as e:
            logger.error(f"Failed to save test case: {e}")
            return False, None
    
    def save_test_cases_batch(self, test_cases: List[Dict], session_id: str = None, user_id: str = None) -> Tuple[bool, List[str]]:
        """
        Save multiple test cases in a batch operation with user ownership
        
        Returns:
            Tuple of (success: bool, test_ids: List[str])
        """
        try:
            test_ids = []
            operations = []
            now = datetime.utcnow()
            
            for tc in test_cases:
                # Ensure each test has an ID
                if 'id' not in tc:
                    tc['id'] = f"TC_{ObjectId()}"
                
                tc_copy = tc.copy()
                tc_copy['test_id'] = tc_copy['id']
                tc_copy['updated_at'] = now
                tc_copy['session_id'] = session_id
                tc_copy['user_id'] = user_id  # Add user ownership
                
                # Check if we need to set created_at
                existing = self.test_cases.find_one({'test_id': tc_copy['test_id']})
                if not existing:
                    tc_copy['created_at'] = now
                    tc_copy['version'] = 1
                else:
                    tc_copy['version'] = existing.get('version', 1) + 1
                
                operations.append({
                    'replaceOne': {
                        'filter': {'test_id': tc_copy['test_id']},
                        'replacement': tc_copy,
                        'upsert': True
                    }
                })
                test_ids.append(tc_copy['test_id'])
            
            if operations:
                # MongoDB expects a list of operations, not individual operations
                from pymongo import ReplaceOne
                bulk_ops = [
                    ReplaceOne(
                        filter={'test_id': tc['test_id']},
                        replacement=tc,
                        upsert=True
                    ) for tc in test_cases
                ]
                result = self.test_cases.bulk_write(bulk_ops)
                success = result.modified_count + result.upserted_count > 0
                
                # Audit log
                self._audit_log('test_cases_batch_saved', session_id, {
                    'count': len(test_cases),
                    'test_ids': test_ids[:10]  # Log first 10 IDs only
                })
                
                return success, test_ids
            
            return False, []
            
        except Exception as e:
            logger.error(f"Failed to save test cases batch: {e}")
            return False, []
    
    def get_test_case(self, test_id: str) -> Optional[Dict]:
        """Get a single test case by ID"""
        try:
            test_case = self.test_cases.find_one({'test_id': test_id})
            if test_case:
                test_case.pop('_id', None)  # Remove MongoDB's _id
                # Restore id from test_id
                if 'test_id' in test_case:
                    test_case['id'] = test_case['test_id']
            return test_case
        except Exception as e:
            logger.error(f"Failed to get test case: {e}")
            return None
    
    def get_all_test_cases(self, 
                          session_id: str = None,
                          user_id: str = None,
                          category: str = None,
                          priority: str = None,
                          nasscom_compliant: bool = None,
                          limit: int = 100,
                          skip: int = 0,
                          search_text: str = None) -> List[Dict]:
        """
        Get test cases with filtering, pagination, and user data isolation
        """
        try:
            # Build query - prioritize user_id for data isolation
            query = {}
            if user_id:  # User-specific data isolation
                query['user_id'] = user_id
            elif session_id:
                query['session_id'] = session_id
            if category:
                query['category'] = category
            if priority:
                query['priority'] = priority
            if nasscom_compliant is not None:
                query['nasscom_compliant'] = nasscom_compliant
            if search_text:
                query['$text'] = {'$search': search_text}
            
            # Execute query with pagination
            cursor = self.test_cases.find(query).sort('created_at', -1).skip(skip).limit(limit)
            
            # Convert to list and clean up
            test_cases = []
            for tc in cursor:
                tc.pop('_id', None)
                # Restore id from test_id
                if 'test_id' in tc:
                    tc['id'] = tc['test_id']
                test_cases.append(tc)
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to get test cases: {e}")
            return []
    
    def delete_test_case(self, test_id: str, session_id: str = None) -> bool:
        """Permanently delete a test case"""
        try:
            result = self.test_cases.delete_one({'test_id': test_id})
            
            if result.deleted_count > 0:
                # Audit log
                self._audit_log('test_case_deleted', session_id, {'test_id': test_id})
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete test case: {e}")
            return False
    
    # ========================================
    # TEST SUITE OPERATIONS
    # ========================================
    
    def create_test_suite(self, name: str, test_ids: List[str], 
                         metadata: Dict = None, session_id: str = None) -> Optional[str]:
        """Create a test suite (collection of test cases)"""
        try:
            suite_id = f"TS_{ObjectId()}"
            suite = {
                'suite_id': suite_id,
                'name': name,
                'test_ids': test_ids,
                'metadata': metadata or {},
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'session_id': session_id,
                'test_count': len(test_ids)
            }
            
            result = self.test_suites.insert_one(suite)
            
            if result.inserted_id:
                # Audit log
                self._audit_log('test_suite_created', session_id, {
                    'suite_id': suite_id,
                    'test_count': len(test_ids)
                })
                return suite_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create test suite: {e}")
            return None
    
    def get_test_suite(self, suite_id: str) -> Optional[Dict]:
        """Get a test suite with all its test cases"""
        try:
            suite = self.test_suites.find_one({'suite_id': suite_id})
            if suite:
                suite.pop('_id', None)
                # Fetch all test cases in the suite
                test_cases = []
                for test_id in suite.get('test_ids', []):
                    tc = self.get_test_case(test_id)
                    if tc:
                        test_cases.append(tc)
                suite['test_cases'] = test_cases
            return suite
        except Exception as e:
            logger.error(f"Failed to get test suite: {e}")
            return None
    
    # ========================================
    # DOCUMENT OPERATIONS
    # ========================================
    
    def save_document(self, filename: str, content: str, doc_type: str, 
                     metadata: Dict = None, session_id: str = None, user_id: str = None) -> Optional[str]:
        """Save uploaded document content with user ownership"""
        try:
            doc_id = str(ObjectId())
            document = {
                '_id': doc_id,
                'filename': filename,
                'content': content[:500000],  # Limit content size to 500KB
                'doc_type': doc_type,
                'metadata': metadata or {},
                'uploaded_at': datetime.utcnow(),
                'session_id': session_id,
                'user_id': user_id,  # Add user ownership
                'content_length': len(content)
            }
            
            result = self.documents.insert_one(document)
            
            if result.inserted_id:
                # Audit log
                self._audit_log('document_uploaded', session_id, {
                    'doc_id': doc_id,
                    'filename': filename,
                    'size': len(content)
                })
                return doc_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return None
    
    def get_all_documents(self, session_id: str = None, user_id: str = None, limit: int = 50) -> List[Dict]:
        """Get all uploaded documents with user data isolation"""
        try:
            query = {}
            if user_id:  # Priority to user_id for data isolation
                query['user_id'] = user_id
            elif session_id:
                query['session_id'] = session_id
            
            cursor = self.documents.find(query).sort('uploaded_at', -1).limit(limit)
            docs = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                # Don't send full content in list view
                doc.pop('content', None)
                docs.append(doc)
            return docs
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a specific document with full content"""
        try:
            doc = self.documents.find_one({'_id': doc_id})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    # ========================================
    # SHARED DOCUMENTS OPERATIONS
    # ========================================
    
    def save_shared_document(self, filename: str, content: str, doc_type: str, 
                            metadata: Dict = None) -> Optional[str]:
        """Save a shared document accessible to all users"""
        try:
            doc_id = str(ObjectId())
            document = {
                '_id': doc_id,
                'filename': filename,
                'content': content[:500000],  # Limit content size
                'doc_type': doc_type,
                'metadata': metadata or {},
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_shared': True,
                'content_length': len(content)
            }
            
            # Check if document already exists
            existing = self.shared_documents.find_one({'filename': filename})
            if existing:
                # Update existing document
                document['_id'] = existing['_id']
                document['created_at'] = existing.get('created_at', datetime.utcnow())
                self.shared_documents.replace_one(
                    {'_id': existing['_id']}, 
                    document
                )
                logger.info(f"Updated shared document: {filename}")
                return existing['_id']
            else:
                result = self.shared_documents.insert_one(document)
                if result.inserted_id:
                    logger.info(f"Created shared document: {filename}")
                    return doc_id
                    
        except Exception as e:
            logger.error(f"Failed to save shared document: {e}")
            return None
    
    def get_all_shared_documents(self, limit: int = 50) -> List[Dict]:
        """Get all shared documents available to all users"""
        try:
            cursor = self.shared_documents.find({}).sort('created_at', -1).limit(limit)
            docs = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                # Don't send full content in list view
                doc.pop('content', None)
                docs.append(doc)
            
            logger.info(f"Retrieved {len(docs)} shared documents")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to get shared documents: {e}")
            return []
    
    def get_shared_document(self, doc_id: str) -> Optional[Dict]:
        """Get a specific shared document with full content"""
        try:
            doc = self.shared_documents.find_one({'_id': doc_id})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Failed to get shared document: {e}")
            return None
    
    # ========================================
    # COMPLIANCE OPERATIONS
    # ========================================
    
    def save_compliance_report(self, report: Dict, session_id: str = None, user_id: str = None) -> Optional[str]:
        """Save compliance analysis report with user ownership"""
        try:
            report['_id'] = str(ObjectId())
            report['analyzed_at'] = datetime.utcnow()
            report['session_id'] = session_id
            report['user_id'] = user_id  # Add user ownership
            
            result = self.compliance_reports.insert_one(report)
            
            if result.inserted_id:
                return report['_id']
            return None
            
        except Exception as e:
            logger.error(f"Failed to save compliance report: {e}")
            return None
    
    def get_compliance_reports(self, filename: str = None, 
                              session_id: str = None, user_id: str = None, limit: int = 50) -> List[Dict]:
        """Get compliance reports with user data isolation"""
        try:
            query = {}
            if filename:
                query['filename'] = filename
            if user_id:  # Priority to user_id for data isolation
                query['user_id'] = user_id
            elif session_id:
                query['session_id'] = session_id
            
            cursor = self.compliance_reports.find(query).sort('analyzed_at', -1).limit(limit)
            reports = []
            for report in cursor:
                report['_id'] = str(report['_id'])
                reports.append(report)
            return reports
            
        except Exception as e:
            logger.error(f"Failed to get compliance reports: {e}")
            return []
    
    # ========================================
    # RAG EMBEDDINGS OPERATIONS
    # ========================================
    
    def save_embedding(self, content: str, embedding: List[float], 
                      metadata: Dict, session_id: str = None) -> bool:
        """Save document embedding for RAG system"""
        try:
            doc = {
                'content': content,
                'embedding': embedding,
                'metadata': metadata,
                'created_at': datetime.utcnow(),
                'session_id': session_id
            }
            
            result = self.rag_embeddings.insert_one(doc)
            return result.inserted_id is not None
            
        except Exception as e:
            logger.error(f"Failed to save embedding: {e}")
            return False
    
    def get_embeddings(self, session_id: str = None) -> List[Dict]:
        """Get all embeddings for rebuilding FAISS index"""
        try:
            query = {}
            if session_id:
                query['session_id'] = session_id
            
            cursor = self.rag_embeddings.find(query)
            embeddings = []
            for doc in cursor:
                doc.pop('_id', None)
                embeddings.append(doc)
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            return []
    
    # ========================================
    # STATISTICS & ANALYTICS
    # ========================================
    
    def get_statistics(self, session_id: str = None) -> Dict:
        """Get database statistics and metrics"""
        try:
            query = {}
            if session_id:
                query['session_id'] = session_id
            
            stats = {
                'total_test_cases': self.test_cases.count_documents(query),
                'test_cases_by_category': {},
                'test_cases_by_priority': {},
                'compliance_status': {},
                'total_test_suites': self.test_suites.count_documents(query),
                'total_documents': self.documents.count_documents(query),
                'total_compliance_reports': self.compliance_reports.count_documents(query),
                'recent_activity': []
            }
            
            # Aggregate by category
            pipeline = [
                {'$match': query},
                {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
            ]
            for item in self.test_cases.aggregate(pipeline):
                if item['_id']:
                    stats['test_cases_by_category'][item['_id']] = item['count']
            
            # Aggregate by priority
            pipeline[1] = {'$group': {'_id': '$priority', 'count': {'$sum': 1}}}
            for item in self.test_cases.aggregate(pipeline):
                if item['_id']:
                    stats['test_cases_by_priority'][item['_id']] = item['count']
            
            # Aggregate by compliance
            pipeline[1] = {'$group': {'_id': '$nasscom_compliant', 'count': {'$sum': 1}}}
            for item in self.test_cases.aggregate(pipeline):
                stats['compliance_status'][
                    'compliant' if item['_id'] else 'non_compliant'
                ] = item['count']
            
            # Recent activity
            recent = self.audit_logs.find(query).sort('timestamp', -1).limit(10)
            for log in recent:
                log.pop('_id', None)
                stats['recent_activity'].append(log)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    # ========================================
    # AUDIT & LOGGING
    # ========================================
    
    def _audit_log(self, action: str, session_id: str, details: Dict):
        """Create audit log entry"""
        try:
            log_entry = {
                'action': action,
                'session_id': session_id or 'anonymous',
                'timestamp': datetime.utcnow(),
                'details': details
            }
            self.audit_logs.insert_one(log_entry)
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")
    
    def get_audit_logs(self, session_id: str = None, limit: int = 100) -> List[Dict]:
        """Get audit logs"""
        try:
            query = {}
            if session_id:
                query['session_id'] = session_id
            
            cursor = self.audit_logs.find(query).sort('timestamp', -1).limit(limit)
            logs = []
            for log in cursor:
                log.pop('_id', None)
                logs.append(log)
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return []
    
    # ========================================
    # SESSION MANAGEMENT
    # ========================================
    
    def create_session(self, user_id: str = None) -> str:
        """Create a new user session linked to user"""
        try:
            session_id = f"SESSION_{ObjectId()}"
            session = {
                'session_id': session_id,
                'user_id': user_id,  # Link session to user
                'created_at': datetime.utcnow(),
                'last_active': datetime.utcnow(),
                'is_active': True
            }
            self.user_sessions.insert_one(session)
            logger.info(f"Session created: {session_id} for user: {user_id}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return f"SESSION_{ObjectId()}"  # Return a session ID anyway
    
    def get_or_create_session_for_user(self, user_id: str) -> str:
        """Get existing active session for user or create new one"""
        try:
            # Find active session for user
            existing_session = self.user_sessions.find_one(
                {'user_id': user_id, 'is_active': True},
                sort=[('last_active', -1)]
            )
            
            if existing_session:
                # Update activity and return existing session
                session_id = existing_session['session_id']
                self.update_session_activity(session_id)
                logger.info(f"Reusing session {session_id} for user {user_id}")
                return session_id
            else:
                # Create new session for user
                return self.create_session(user_id)
        except Exception as e:
            logger.error(f"Failed to get/create session for user: {e}")
            return self.create_session(user_id)
    
    def update_session_activity(self, session_id: str):
        """Update session last activity time"""
        try:
            self.user_sessions.update_one(
                {'session_id': session_id},
                {'$set': {'last_active': datetime.utcnow()}}
            )
        except Exception as e:
            logger.warning(f"Failed to update session activity: {e}")
    
    # ========================================
    # USER AUTHENTICATION OPERATIONS
    # ========================================
    
    def create_user(self, email: str, password_hash: str, full_name: str = None) -> Tuple[bool, Optional[str]]:
        """
        Create a new user account
        
        Args:
            email: User's email address
            password_hash: Hashed password (never store plain text)
            full_name: User's full name (encrypted, optional)
            
        Returns:
            Tuple of (success: bool, user_id: str or error_message: str)
        """
        try:
            user_doc = {
                'email': email.lower(),
                'password': password_hash,
                'full_name': full_name or '',  # Should be encrypted
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'last_login': None,
                'is_active': True,
                'role': 'user'  # Could be 'user', 'admin', 'premium'
            }
            
            result = self.users.insert_one(user_doc)
            
            if result.inserted_id:
                self._audit_log('user_created', str(result.inserted_id), {'email': email})
                return True, str(result.inserted_id)
            return False, "Failed to create user"
            
        except DuplicateKeyError:
            return False, "Email already exists"
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False, str(e)
    
    def authenticate_user(self, email: str, password_hash: str) -> Optional[Dict]:
        """
        Authenticate a user and return their profile
        
        Args:
            email: User's email
            password_hash: Hashed password to verify
            
        Returns:
            User document if authenticated, None otherwise
        """
        try:
            user = self.users.find_one({
                'email': email.lower(),
                'password': password_hash,
                'is_active': True
            })
            
            if user:
                # Update last login
                self.users.update_one(
                    {'_id': user['_id']},
                    {
                        '$set': {'last_login': datetime.utcnow()},
                        '$inc': {'login_count': 1}
                    }
                )
                
                self._audit_log('user_login', str(user['_id']), {'email': email})
                
                # Convert ObjectId to string for JSON serialization
                user['_id'] = str(user['_id'])
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user profile by email"""
        try:
            user = self.users.find_one({'email': email.lower()})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    def update_user_api_key(self, user_id: str, encrypted_api_key: str = None) -> bool:
        """Update or remove user's API key"""
        try:
            update_data = {
                'api_key': encrypted_api_key,
                'updated_at': datetime.utcnow()
            }
            
            result = self.users.update_one(
                {'_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                self._audit_log('api_key_updated', user_id, {
                    'action': 'removed' if encrypted_api_key is None else 'updated'
                })
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update API key: {e}")
            return False
    
    def update_user_credits(self, user_id: str, credits_used: int = 1) -> Tuple[bool, int]:
        """
        Update user's remaining credits
        
        Returns:
            Tuple of (success: bool, remaining_credits: int)
        """
        try:
            result = self.users.find_one_and_update(
                {'_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id},
                {
                    '$inc': {'credits_remaining': -credits_used},
                    '$set': {'updated_at': datetime.utcnow()}
                },
                return_document=True
            )
            
            if result:
                return True, result.get('credits_remaining', 0)
            return False, 0
            
        except Exception as e:
            logger.error(f"Failed to update credits: {e}")
            return False, 0
    
    def reset_monthly_credits(self) -> int:
        """
        Reset all users' credits to their monthly allocation
        (Should be run via scheduled job)
        
        Returns:
            Number of users updated
        """
        try:
            result = self.users.update_many(
                {},
                {
                    '$set': {
                        'credits_remaining': '$monthly_credits',
                        'credits_reset_at': datetime.utcnow()
                    }
                }
            )
            
            self._audit_log('credits_reset', 'system', {
                'users_updated': result.modified_count
            })
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Failed to reset credits: {e}")
            return 0
    
    def update_user_profile(self, user_id: str, updates: Dict) -> bool:
        """Update user profile information"""
        try:
            # Sanitize updates - only allow certain fields
            allowed_fields = {'full_name', 'email', 'role', 'monthly_credits'}
            sanitized_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not sanitized_updates:
                return False
            
            sanitized_updates['updated_at'] = datetime.utcnow()
            
            result = self.users.update_one(
                {'_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id},
                {'$set': sanitized_updates}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            return False
    
    # ========================================
    # UTILITIES
    # ========================================
    
    def ping(self) -> bool:
        """Check if database connection is alive"""
        try:
            self.client.admin.command('ping')
            return True
        except:
            return False
    
    def close(self):
        """Close database connection"""
        try:
            self.client.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
