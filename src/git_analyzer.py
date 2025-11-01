"""
Git Repository Analysis Module for AI-Powered Test Generation
Advanced code change analysis with AI-driven insights and test recommendations
Healthcare & MedTech Compliance Focus
"""

import git
import os
import re
import json
import uuid
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import difflib
import ast
import logging
import google.generativeai as genai
from dataclasses import dataclass, asdict

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class CodeChange:
    """Represents a code change with enhanced metadata"""
    filepath: str
    change_type: str  # A=added, M=modified, D=deleted, R=renamed
    language: str
    insertions: int
    deletions: int
    diff_text: str
    functions_changed: List[str]
    classes_changed: List[str]
    imports_changed: List[str]
    risk_level: str  # high, medium, low
    compliance_impact: List[str]  # HIPAA, FDA, ISO, etc.
    test_priority: int  # 1-5, 1 being highest
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

@dataclass
class CommitAnalysis:
    """Comprehensive commit analysis result"""
    commit_sha: str
    message: str
    author: str
    timestamp: datetime
    files_changed: List[CodeChange]
    risk_score: float  # 0-100
    modules_affected: List[str]
    test_areas: List[str]
    suggested_test_count: int
    ai_insights: Dict[str, Any]
    compliance_concerns: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class GitAnalyzer:
    """
    Advanced Git repository analyzer with AI-powered insights
    Designed for healthcare/medical software compliance testing
    """
    
    # Healthcare and compliance-related patterns
    HEALTHCARE_PATTERNS = {
        'patient_data': [r'patient', r'medical', r'health', r'clinical', r'diagnosis', r'treatment'],
        'phi_handling': [r'phi', r'pii', r'personal.*info', r'ssn', r'dob', r'birth.*date'],
        'encryption': [r'encrypt', r'decrypt', r'crypto', r'hash', r'salt', r'secure'],
        'authentication': [r'auth', r'login', r'logout', r'session', r'token', r'jwt', r'oauth'],
        'authorization': [r'permission', r'role', r'access', r'privilege', r'rbac'],
        'audit': [r'audit', r'log', r'trace', r'track', r'monitor'],
        'api': [r'api', r'endpoint', r'rest', r'graphql', r'route', r'controller'],
        'database': [r'database', r'db', r'sql', r'query', r'orm', r'migration'],
        'validation': [r'validate', r'sanitize', r'verify', r'check', r'assert'],
        'error_handling': [r'error', r'exception', r'catch', r'throw', r'handle'],
        'integration': [r'integration', r'interface', r'adapter', r'connector', r'bridge'],
        'compliance': [r'hipaa', r'gdpr', r'fda', r'iso', r'hl7', r'dicom', r'fhir']
    }
    
    # Risk scoring weights
    RISK_WEIGHTS = {
        'file_criticality': 0.3,
        'change_size': 0.2,
        'healthcare_relevance': 0.25,
        'compliance_impact': 0.25
    }
    
    def __init__(self, repo_path: str, api_key: Optional[str] = None):
        """
        Initialize Git analyzer with repository path and optional Gemini API key
        
        Args:
            repo_path: Path to the Git repository
            api_key: Optional Gemini API key for AI analysis
        """
        self.repo_path = Path(repo_path)
        self.api_key = api_key
        
        try:
            self.repo = git.Repo(repo_path)
            self.is_valid = True
            logger.info(f"Successfully connected to repository at {repo_path}")
        except git.InvalidGitRepositoryError:
            self.repo = None
            self.is_valid = False
            logger.error(f"Invalid Git repository at {repo_path}")
        
        # Configure Gemini if API key provided
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.ai_enabled = True
            logger.info("AI analysis enabled with Gemini")
        else:
            self.model = None
            self.ai_enabled = False
            logger.info("AI analysis disabled (no API key provided)")
    
    def analyze_repository(self, 
                          days: int = 7, 
                          branch: Optional[str] = None,
                          max_commits: int = 20,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Perform comprehensive repository analysis with AI insights
        
        Args:
            days: Number of days to look back (used if start_date/end_date not provided)
            branch: Branch to analyze (None for current branch)
            max_commits: Maximum number of commits to analyze
            start_date: Optional start date for analysis (overrides days parameter)
            end_date: Optional end date for analysis (default to today)
        
        Returns:
            Comprehensive repository analysis report
        """
        if not self.is_valid:
            return {'error': 'Invalid repository'}
        
        # Get branch info
        if branch is None:
            branch = self.repo.active_branch.name
        
        # Analyze commits with date range if provided
        if start_date and end_date:
            commits = self.get_commits_between_dates(start_date, end_date, branch, max_commits)
        else:
            commits = self.get_recent_commits(days, branch, max_commits)
        commit_analyses = []
        
        for commit in commits:
            analysis = self.analyze_commit(commit)
            commit_analyses.append(analysis)
        
        # Generate repository-wide insights
        repo_insights = self._generate_repository_insights(commit_analyses)
        
        # Use AI to generate comprehensive test strategy
        test_strategy = None
        if self.ai_enabled:
            test_strategy = self._generate_ai_test_strategy(repo_insights)
        
        # Determine analysis period description
        if start_date and end_date:
            analysis_period = f"From {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        else:
            analysis_period = f"Last {days} days"
        
        return {
            'repository': str(self.repo_path),
            'branch': branch,
            'analysis_period': analysis_period,
            'total_commits': len(commits),
            'commit_analyses': [ca.to_dict() for ca in commit_analyses],
            'repository_insights': repo_insights,
            'ai_test_strategy': test_strategy,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_recent_commits(self, 
                          days: int = 7, 
                          branch: Optional[str] = None,
                          max_commits: int = 20) -> List[git.Commit]:
        """Get recent commits from the repository"""
        if not self.is_valid:
            return []
        
        if branch is None:
            branch = self.repo.active_branch.name
        
        commits = []
        since_date = datetime.now() - timedelta(days=days)
        
        for commit in self.repo.iter_commits(branch, since=since_date, max_count=max_commits):
            commits.append(commit)
        
        return commits
    
    def get_commits_between_dates(self,
                                  start_date: datetime,
                                  end_date: datetime,
                                  branch: Optional[str] = None,
                                  max_commits: int = 20) -> List[git.Commit]:
        """
        Get commits between two dates
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            branch: Branch to analyze (None for current branch)
            max_commits: Maximum number of commits to return
        
        Returns:
            List of Git commits between the specified dates
        """
        if not self.is_valid:
            return []
        
        if branch is None:
            branch = self.repo.active_branch.name
        
        commits = []
        
        # Convert dates to datetime objects with time for comparison
        if isinstance(start_date, datetime):
            since_datetime = start_date
        else:
            since_datetime = datetime.combine(start_date, datetime.min.time())
        
        if isinstance(end_date, datetime):
            until_datetime = end_date
        else:
            until_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Get all commits and filter manually for accurate date range
        # GitPython's since/until parameters are confusing, so we filter manually
        all_commits = list(self.repo.iter_commits(branch, max_count=max_commits * 3))  # Get extra to ensure we catch all in range
        
        for commit in all_commits:
            commit_date = commit.committed_datetime.replace(tzinfo=None)
            # Check if commit is within the date range (inclusive)
            if since_datetime.replace(tzinfo=None) <= commit_date <= until_datetime.replace(tzinfo=None):
                commits.append(commit)
                if len(commits) >= max_commits:
                    break
        
        logger.info(f"Found {len(commits)} commits between {start_date} and {end_date}")
        return commits
    
    def analyze_commit(self, commit: git.Commit) -> CommitAnalysis:
        """
        Perform deep analysis of a single commit with AI insights
        
        Args:
            commit: Git commit object to analyze
        
        Returns:
            Comprehensive commit analysis
        """
        # Get changed files
        changed_files = self._analyze_changed_files(commit)
        
        # Calculate risk score
        risk_score = self._calculate_commit_risk_score(changed_files)
        
        # Identify affected modules and test areas
        modules_affected = self._identify_modules(changed_files)
        test_areas = self._identify_test_areas(changed_files)
        
        # Detect compliance concerns
        compliance_concerns = self._detect_compliance_concerns(changed_files)
        
        # Calculate suggested test count based on complexity
        suggested_test_count = self._calculate_suggested_test_count(changed_files)
        
        # Generate AI insights if enabled
        ai_insights = {}
        if self.ai_enabled:
            ai_insights = self._generate_commit_ai_insights(
                commit, changed_files, modules_affected, test_areas
            )
        
        return CommitAnalysis(
            commit_sha=commit.hexsha[:8],
            message=commit.message.strip(),
            author=str(commit.author),
            timestamp=commit.committed_datetime,
            files_changed=changed_files,
            risk_score=risk_score,
            modules_affected=modules_affected,
            test_areas=test_areas,
            suggested_test_count=suggested_test_count,
            ai_insights=ai_insights,
            compliance_concerns=compliance_concerns
        )
    
    def _analyze_changed_files(self, commit: git.Commit) -> List[CodeChange]:
        """Analyze files changed in a commit"""
        changed_files = []
        
        # Get diffs
        if not commit.parents:
            # For initial commits, compare against empty tree
            diffs = commit.diff(git.NULL_TREE, create_patch=True)
        else:
            diffs = commit.parents[0].diff(commit, create_patch=True)
        
        for diff in diffs:
            filepath = diff.b_path if diff.b_path else diff.a_path
            
            # Extract detailed change information
            diff_text = ""
            insertions = 0
            deletions = 0
            
            if diff.diff:
                diff_text = diff.diff.decode('utf-8', errors='ignore')
                insertions = len([l for l in diff_text.split('\n') if l.startswith('+')])
                deletions = len([l for l in diff_text.split('\n') if l.startswith('-')])
            
            # Parse code changes for functions, classes, imports
            functions_changed = self._extract_functions_from_diff(diff_text)
            classes_changed = self._extract_classes_from_diff(diff_text)
            imports_changed = self._extract_imports_from_diff(diff_text)
            
            # Detect language
            language = self._detect_language(filepath)
            
            # Assess risk level
            risk_level = self._assess_file_risk_level(
                filepath, insertions, deletions, diff_text
            )
            
            # Detect compliance impact
            compliance_impact = self._detect_file_compliance_impact(filepath, diff_text)
            
            # Calculate test priority
            test_priority = self._calculate_test_priority(
                risk_level, compliance_impact, insertions + deletions
            )
            
            changed_files.append(CodeChange(
                filepath=filepath,
                change_type=diff.change_type,
                language=language,
                insertions=insertions,
                deletions=deletions,
                diff_text=diff_text[:5000],  # Limit diff text size
                functions_changed=functions_changed,
                classes_changed=classes_changed,
                imports_changed=imports_changed,
                risk_level=risk_level,
                compliance_impact=compliance_impact,
                test_priority=test_priority
            ))
        
        return changed_files
    
    def _detect_language(self, filepath: str) -> str:
        """Detect programming language from file extension"""
        if not filepath:
            return 'unknown'
        
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.rs': 'rust',
            '.sql': 'sql',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass'
        }
        
        ext = Path(filepath).suffix.lower()
        return ext_map.get(ext, 'unknown')
    
    def _extract_functions_from_diff(self, diff_text: str) -> List[str]:
        """Extract function names from diff text"""
        functions = []
        
        # Python functions
        functions.extend(re.findall(r'^\+?\s*def\s+(\w+)', diff_text, re.MULTILINE))
        
        # JavaScript/TypeScript functions
        functions.extend(re.findall(r'^\+?\s*function\s+(\w+)', diff_text, re.MULTILINE))
        functions.extend(re.findall(r'^\+?\s*const\s+(\w+)\s*=\s*\(', diff_text, re.MULTILINE))
        functions.extend(re.findall(r'^\+?\s*(\w+)\s*:\s*\(.*?\)\s*=>', diff_text, re.MULTILINE))
        
        # Java/C++/C# methods
        functions.extend(re.findall(r'^\+?\s*(?:public|private|protected)?\s*\w+\s+(\w+)\s*\(', 
                                   diff_text, re.MULTILINE))
        
        return list(set(functions))
    
    def _extract_classes_from_diff(self, diff_text: str) -> List[str]:
        """Extract class names from diff text"""
        classes = []
        
        # Python classes
        classes.extend(re.findall(r'^\+?\s*class\s+(\w+)', diff_text, re.MULTILINE))
        
        # JavaScript/TypeScript classes
        classes.extend(re.findall(r'^\+?\s*(?:export\s+)?class\s+(\w+)', diff_text, re.MULTILINE))
        
        # Java/C++/C# classes
        classes.extend(re.findall(r'^\+?\s*(?:public|private|protected)?\s*class\s+(\w+)', 
                                 diff_text, re.MULTILINE))
        
        return list(set(classes))
    
    def _extract_imports_from_diff(self, diff_text: str) -> List[str]:
        """Extract import statements from diff text"""
        imports = []
        
        # Python imports
        imports.extend(re.findall(r'^\+?\s*import\s+(\S+)', diff_text, re.MULTILINE))
        imports.extend(re.findall(r'^\+?\s*from\s+(\S+)\s+import', diff_text, re.MULTILINE))
        
        # JavaScript/TypeScript imports
        imports.extend(re.findall(r'^\+?\s*import\s+.*?\s+from\s+[\'"](.+?)[\'"]', 
                                 diff_text, re.MULTILINE))
        
        # Java imports
        imports.extend(re.findall(r'^\+?\s*import\s+([\w\.]+);', diff_text, re.MULTILINE))
        
        return list(set(imports))
    
    def _assess_file_risk_level(self, filepath: str, insertions: int, 
                                deletions: int, diff_text: str) -> str:
        """Assess risk level of file changes"""
        filepath_lower = filepath.lower()
        total_changes = insertions + deletions
        
        # Critical file patterns (high risk)
        high_risk_patterns = [
            r'auth', r'security', r'crypto', r'payment', r'billing',
            r'patient', r'medical', r'health', r'phi', r'pii',
            r'database', r'migration', r'config', r'settings', r'env'
        ]
        
        # Check for high-risk patterns
        if any(re.search(pattern, filepath_lower) for pattern in high_risk_patterns):
            return 'high'
        
        # Check for security-sensitive changes in diff
        security_patterns = [
            r'password', r'token', r'secret', r'key', r'credential',
            r'encrypt', r'decrypt', r'hash', r'salt', r'vulnerable'
        ]
        
        if any(re.search(pattern, diff_text.lower()) for pattern in security_patterns):
            return 'high'
        
        # Large changes are higher risk
        if total_changes > 100:
            return 'high'
        elif total_changes > 50:
            return 'medium'
        
        # API and service changes
        if re.search(r'api|service|controller|endpoint', filepath_lower):
            return 'medium'
        
        return 'low'
    
    def _detect_file_compliance_impact(self, filepath: str, diff_text: str) -> List[str]:
        """Detect which compliance standards are impacted by file changes"""
        compliance_impact = []
        combined_text = (filepath + ' ' + diff_text).lower()
        
        # HIPAA indicators
        hipaa_patterns = [
            r'patient', r'medical', r'health', r'phi', r'protected.*health',
            r'diagnosis', r'treatment', r'prescription'
        ]
        if any(re.search(pattern, combined_text) for pattern in hipaa_patterns):
            compliance_impact.append('HIPAA')
        
        # GDPR indicators
        gdpr_patterns = [
            r'personal.*data', r'pii', r'privacy', r'consent', r'gdpr',
            r'data.*subject', r'right.*to.*forget'
        ]
        if any(re.search(pattern, combined_text) for pattern in gdpr_patterns):
            compliance_impact.append('GDPR')
        
        # FDA indicators
        fda_patterns = [
            r'medical.*device', r'fda', r'clinical', r'validation',
            r'quality.*system', r'510k', r'premarket'
        ]
        if any(re.search(pattern, combined_text) for pattern in fda_patterns):
            compliance_impact.append('FDA')
        
        # ISO 27001 (Security)
        iso_patterns = [
            r'security', r'access.*control', r'audit', r'risk.*assessment',
            r'incident', r'vulnerability', r'iso.*27001'
        ]
        if any(re.search(pattern, combined_text) for pattern in iso_patterns):
            compliance_impact.append('ISO 27001')
        
        # HL7/FHIR (Healthcare Interoperability)
        hl7_patterns = [
            r'hl7', r'fhir', r'interoperability', r'message.*format',
            r'clinical.*document'
        ]
        if any(re.search(pattern, combined_text) for pattern in hl7_patterns):
            compliance_impact.append('HL7/FHIR')
        
        return compliance_impact
    
    def _calculate_test_priority(self, risk_level: str, 
                                 compliance_impact: List[str], 
                                 change_size: int) -> int:
        """
        Calculate test priority (1-5, 1 being highest)
        
        Args:
            risk_level: Risk level (high/medium/low)
            compliance_impact: List of affected compliance standards
            change_size: Total lines changed
        
        Returns:
            Priority score 1-5
        """
        priority_score = 5  # Start with lowest priority
        
        # Risk level impact
        if risk_level == 'high':
            priority_score -= 2
        elif risk_level == 'medium':
            priority_score -= 1
        
        # Compliance impact
        if len(compliance_impact) >= 2:
            priority_score -= 2
        elif len(compliance_impact) == 1:
            priority_score -= 1
        
        # Change size impact
        if change_size > 100:
            priority_score -= 1
        
        return max(1, priority_score)  # Ensure priority is at least 1
    
    def _calculate_commit_risk_score(self, changed_files: List[CodeChange]) -> float:
        """
        Calculate overall risk score for a commit (0-100)
        
        Args:
            changed_files: List of CodeChange objects
        
        Returns:
            Risk score from 0 (low risk) to 100 (high risk)
        """
        if not changed_files:
            return 0.0
        
        total_score = 0.0
        
        for file_change in changed_files:
            file_score = 0.0
            
            # Risk level contribution
            if file_change.risk_level == 'high':
                file_score += 40
            elif file_change.risk_level == 'medium':
                file_score += 25
            else:
                file_score += 10
            
            # Compliance impact contribution
            file_score += len(file_change.compliance_impact) * 10
            
            # Change size contribution
            total_lines = file_change.insertions + file_change.deletions
            if total_lines > 100:
                file_score += 20
            elif total_lines > 50:
                file_score += 15
            elif total_lines > 20:
                file_score += 10
            else:
                file_score += 5
            
            # Test priority contribution
            file_score += (6 - file_change.test_priority) * 5
            
            total_score += min(100, file_score)
        
        # Average across all files
        return min(100.0, total_score / len(changed_files))
    
    def _identify_modules(self, changed_files: List[CodeChange]) -> List[str]:
        """Identify affected modules from changed files"""
        modules = set()
        
        for file_change in changed_files:
            filepath = Path(file_change.filepath)
            
            # Extract module from path
            parts = filepath.parts
            if len(parts) >= 2:
                if parts[0] in ['src', 'lib', 'app', 'core', 'modules']:
                    modules.add(parts[1])
                else:
                    modules.add(parts[0])
            elif filepath.stem:
                modules.add(filepath.stem)
        
        return list(modules)
    
    def _identify_test_areas(self, changed_files: List[CodeChange]) -> List[str]:
        """Identify test areas based on changed files"""
        test_areas = set()
        
        for file_change in changed_files:
            filepath_lower = file_change.filepath.lower()
            diff_lower = file_change.diff_text.lower()
            
            # Check against healthcare patterns
            for area, patterns in self.HEALTHCARE_PATTERNS.items():
                if any(re.search(pattern, filepath_lower + ' ' + diff_lower) 
                       for pattern in patterns):
                    # Map to readable test area names
                    area_mapping = {
                        'patient_data': 'Patient Data Management',
                        'phi_handling': 'PHI/PII Protection',
                        'encryption': 'Data Encryption',
                        'authentication': 'Authentication',
                        'authorization': 'Authorization & Access Control',
                        'audit': 'Audit Logging',
                        'api': 'API Integration',
                        'database': 'Database Operations',
                        'validation': 'Input Validation',
                        'error_handling': 'Error Handling',
                        'integration': 'System Integration',
                        'compliance': 'Regulatory Compliance'
                    }
                    test_areas.add(area_mapping.get(area, area))
        
        return list(test_areas) if test_areas else ['General Functionality']
    
    def _detect_compliance_concerns(self, changed_files: List[CodeChange]) -> List[str]:
        """Aggregate compliance concerns from all changed files"""
        all_concerns = set()
        
        for file_change in changed_files:
            all_concerns.update(file_change.compliance_impact)
        
        return list(all_concerns)
    
    def _calculate_suggested_test_count(self, changed_files: List[CodeChange]) -> int:
        """
        Calculate suggested number of test cases based on change complexity
        
        Args:
            changed_files: List of CodeChange objects
        
        Returns:
            Suggested number of test cases
        """
        base_tests = 0
        
        for file_change in changed_files:
            # Base count by risk level
            if file_change.risk_level == 'high':
                base_tests += 5
            elif file_change.risk_level == 'medium':
                base_tests += 3
            else:
                base_tests += 1
            
            # Add tests for functions changed
            base_tests += len(file_change.functions_changed)
            
            # Add tests for classes changed
            base_tests += len(file_change.classes_changed) * 2
            
            # Add tests for compliance impact
            base_tests += len(file_change.compliance_impact)
        
        return max(1, base_tests)  # At least 1 test
    
    def _generate_commit_ai_insights(self, 
                                     commit: git.Commit,
                                     changed_files: List[CodeChange],
                                     modules_affected: List[str],
                                     test_areas: List[str]) -> Dict[str, Any]:
        """
        Generate AI-powered insights for a commit using Gemini
        
        Args:
            commit: Git commit object
            changed_files: List of CodeChange objects
            modules_affected: List of affected modules
            test_areas: List of test areas
        
        Returns:
            AI-generated insights dictionary
        """
        if not self.ai_enabled or not self.model:
            logger.warning(f"[GIT_AI] AI insights disabled for commit {commit.hexsha[:8]}")
            return {}
        
        logger.info(f"[GIT_AI] Generating AI insights for commit {commit.hexsha[:8]}")
        try:
            # Prepare context for AI
            files_summary = []
            for cf in changed_files[:10]:  # Limit to first 10 files
                files_summary.append({
                    'path': cf.filepath,
                    'type': cf.change_type,
                    'risk': cf.risk_level,
                    'lines_changed': cf.insertions + cf.deletions,
                    'functions': cf.functions_changed[:5],
                    'compliance': cf.compliance_impact
                })
            
            prompt = f"""
Analyze this code commit for a healthcare/medical software application and provide testing insights.

COMMIT INFORMATION:
- SHA: {commit.hexsha[:8]}
- Message: {commit.message.strip()}
- Author: {commit.author}
- Files Changed: {len(changed_files)}

FILES MODIFIED:
{json.dumps(files_summary, indent=2)}

AFFECTED MODULES: {', '.join(modules_affected)}
TEST AREAS IDENTIFIED: {', '.join(test_areas)}

Provide a comprehensive analysis with:
1. Impact Summary: Brief description of what this commit changes
2. Critical Test Scenarios: 3-5 specific test scenarios that MUST be covered
3. Edge Cases: 2-3 edge cases to consider
4. Security Concerns: Any security testing needed
5. Compliance Testing: Specific compliance checks required
6. Regression Risks: Areas that might break due to these changes
7. Integration Points: External systems or modules to test integration with
8. Performance Considerations: Any performance tests needed

Format as JSON with these keys:
{{
  "impact_summary": "...",
  "critical_test_scenarios": [...],
  "edge_cases": [...],
  "security_concerns": [...],
  "compliance_testing": [...],
  "regression_risks": [...],
  "integration_points": [...],
  "performance_considerations": [...]
}}
"""
            
            response = self.model.generate_content(prompt)
            
            # Parse AI response
            ai_text = response.text.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', ai_text)
            if json_match:
                insights = json.loads(json_match.group())
                logger.info(f"[GIT_AI] Successfully generated AI insights for commit {commit.hexsha[:8]}")
                logger.info(f"[GIT_AI] Insights include: {list(insights.keys())}")
            else:
                insights = {'raw_response': ai_text}
                logger.warning(f"[GIT_AI] Could not parse AI response as JSON for commit {commit.hexsha[:8]}")
            
            return insights
            
        except Exception as e:
            logger.error(f"[GIT_AI] AI insight generation failed for commit {commit.hexsha[:8]}: {str(e)}")
            return {'error': str(e)}
    
    def _generate_repository_insights(self, commit_analyses: List[CommitAnalysis]) -> Dict[str, Any]:
        """
        Generate repository-wide insights from multiple commit analyses
        
        Args:
            commit_analyses: List of CommitAnalysis objects
        
        Returns:
            Repository-level insights
        """
        if not commit_analyses:
            return {}
        
        # Aggregate statistics
        total_files_changed = sum(len(ca.files_changed) for ca in commit_analyses)
        all_modules = set()
        all_test_areas = set()
        all_compliance = set()
        risk_scores = []
        
        for ca in commit_analyses:
            all_modules.update(ca.modules_affected)
            all_test_areas.update(ca.test_areas)
            all_compliance.update(ca.compliance_concerns)
            risk_scores.append(ca.risk_score)
        
        # Calculate hotspots (most frequently changed files)
        file_change_count = {}
        for ca in commit_analyses:
            for fc in ca.files_changed:
                file_change_count[fc.filepath] = file_change_count.get(fc.filepath, 0) + 1
        
        hotspots = sorted(file_change_count.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_commits_analyzed': len(commit_analyses),
            'total_files_changed': total_files_changed,
            'unique_modules_affected': list(all_modules),
            'test_areas_coverage': list(all_test_areas),
            'compliance_standards_impacted': list(all_compliance),
            'average_risk_score': sum(risk_scores) / len(risk_scores) if risk_scores else 0,
            'highest_risk_commit': max(commit_analyses, key=lambda x: x.risk_score).commit_sha 
                                   if commit_analyses else None,
            'suggested_total_tests': sum(ca.suggested_test_count for ca in commit_analyses),
            'code_hotspots': [{'file': f, 'changes': c} for f, c in hotspots],
            'risk_distribution': {
                'high': len([ca for ca in commit_analyses if ca.risk_score > 70]),
                'medium': len([ca for ca in commit_analyses if 30 <= ca.risk_score <= 70]),
                'low': len([ca for ca in commit_analyses if ca.risk_score < 30])
            }
        }
    
    def _generate_ai_test_strategy(self, repo_insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive AI-powered test strategy for the repository
        
        Args:
            repo_insights: Repository-level insights
        
        Returns:
            AI-generated test strategy
        """
        if not self.ai_enabled or not self.model:
            return {}
        
        try:
            prompt = f"""
Create a comprehensive test strategy for a healthcare/medical software repository based on recent changes.

REPOSITORY ANALYSIS:
{json.dumps(repo_insights, indent=2)}

Generate a detailed test strategy that includes:
1. Test Priority Matrix: Which areas to test first and why
2. Test Type Distribution: Unit vs Integration vs E2E vs Security vs Compliance tests
3. Critical Path Testing: Must-test scenarios for patient safety
4. Compliance Verification: Specific compliance tests needed
5. Risk Mitigation Plan: How to address high-risk areas
6. Resource Allocation: Suggested team focus areas
7. Automation Recommendations: What to automate first
8. Test Data Requirements: Types of test data needed

Format as JSON with these keys:
{{
  "test_priority_matrix": {{
    "priority_1": [...],
    "priority_2": [...],
    "priority_3": [...]
  }},
  "test_type_distribution": {{
    "unit_tests": {{"percentage": X, "focus_areas": [...]}},
    "integration_tests": {{"percentage": X, "focus_areas": [...]}},
    "e2e_tests": {{"percentage": X, "focus_areas": [...]}},
    "security_tests": {{"percentage": X, "focus_areas": [...]}},
    "compliance_tests": {{"percentage": X, "focus_areas": [...]}}
  }},
  "critical_path_scenarios": [...],
  "compliance_verification": [...],
  "risk_mitigation": [...],
  "resource_allocation": [...],
  "automation_priorities": [...],
  "test_data_requirements": [...]
}}
"""
            
            response = self.model.generate_content(prompt)
            
            # Parse AI response
            ai_text = response.text.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', ai_text)
            if json_match:
                strategy = json.loads(json_match.group())
            else:
                strategy = {'raw_response': ai_text}
            
            return strategy
            
        except Exception as e:
            logger.error(f"AI test strategy generation failed: {str(e)}")
            return {'error': str(e)}
    
    def generate_test_cases_for_commit(self, 
                                       commit_sha: str,
                                       test_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generate specific test cases for a commit using AI
        
        Args:
            commit_sha: Commit SHA to generate tests for
            test_types: Types of tests to generate (unit, integration, etc.)
        
        Returns:
            List of generated test cases
        """
        logger.info(f"[GIT_TEST_GEN] Starting test generation for commit {commit_sha[:8]}")
        if not self.is_valid:
            logger.error(f"[GIT_TEST_GEN] Invalid repository, cannot generate tests")
            return []
        
        # Get commit and analyze it
        commit = self.repo.commit(commit_sha)
        logger.info(f"[GIT_TEST_GEN] Analyzing commit: {commit.message.strip()[:50]}")
        analysis = self.analyze_commit(commit)
        logger.info(f"[GIT_TEST_GEN] Commit analysis complete. Risk: {analysis.risk_score:.0f}/100, Files: {len(analysis.files_changed)}")
        
        if not test_types:
            test_types = ['unit', 'integration', 'security', 'compliance']
        
        test_cases = []
        
        if self.ai_enabled:
            logger.info(f"[GIT_TEST_GEN] Using AI to generate tests for {len(analysis.files_changed[:5])} files")
            for file_change in analysis.files_changed[:5]:  # Limit to first 5 files
                logger.info(f"[GIT_TEST_GEN] Generating tests for file: {file_change.filepath}")
                tests = self._generate_file_test_cases(file_change, analysis, test_types)
                logger.info(f"[GIT_TEST_GEN] Generated {len(tests)} tests for {file_change.filepath}")
                test_cases.extend(tests)
        else:
            # Generate basic test cases without AI
            logger.warning(f"[GIT_TEST_GEN] AI disabled, using basic test generation")
            for file_change in analysis.files_changed:
                test_cases.append(self._create_basic_test_case(file_change, analysis))
        
        logger.info(f"[GIT_TEST_GEN] Total tests generated for commit {commit_sha[:8]}: {len(test_cases)}")
        return test_cases
    
    def _generate_file_test_cases(self, 
                                  file_change: CodeChange,
                                  commit_analysis: CommitAnalysis,
                                  test_types: List[str]) -> List[Dict[str, Any]]:
        """
        Generate test cases for a specific file change using AI
        
        Args:
            file_change: CodeChange object
            commit_analysis: CommitAnalysis object
            test_types: Types of tests to generate
        
        Returns:
            List of test cases for the file
        """
        if not self.ai_enabled or not self.model:
            return [self._create_basic_test_case(file_change, commit_analysis)]
        
        try:
            # Limit diff text for API call
            diff_preview = file_change.diff_text[:2000] if len(file_change.diff_text) > 2000 else file_change.diff_text
            
            prompt = f"""
Generate comprehensive test cases for a code change in a healthcare application.

FILE: {file_change.filepath}
LANGUAGE: {file_change.language}
CHANGE TYPE: {file_change.change_type}
RISK LEVEL: {file_change.risk_level}
COMPLIANCE IMPACT: {', '.join(file_change.compliance_impact)}
FUNCTIONS CHANGED: {', '.join(file_change.functions_changed[:5])}
CLASSES CHANGED: {', '.join(file_change.classes_changed[:5])}

DIFF PREVIEW:
```
{diff_preview}
```

COMMIT MESSAGE: {commit_analysis.message}
TEST AREAS: {', '.join(commit_analysis.test_areas)}

Generate test cases for these test types: {', '.join(test_types)}

For EACH test case, provide:
1. Test Case ID (format: TC_GIT_XXXXXX)
2. Title (clear and descriptive)
3. Description
4. Category (Functional/Security/Integration/Performance/Compliance)
5. Priority (Critical/High/Medium/Low)
6. Test Type (unit/integration/e2e/security/compliance)
7. Preconditions
8. Test Steps (detailed, numbered list)
9. Expected Results
10. Test Data requirements
11. Automation feasibility (true/false)
12. Estimated duration

Return as JSON array with exactly this structure:
[
  {{
    "id": "TC_GIT_XXXXXX",
    "title": "...",
    "description": "...",
    "category": "...",
    "priority": "...",
    "test_type": "...",
    "preconditions": "...",
    "test_steps": [...],
    "expected_results": "...",
    "test_data": {{...}},
    "automation_feasible": true/false,
    "estimated_duration": "X minutes",
    "source_file": "{file_change.filepath}",
    "commit_sha": "{commit_analysis.commit_sha}",
    "compliance": [...]
  }}
]

Generate at least {len(test_types)} test cases covering different aspects.
"""
            
            response = self.model.generate_content(prompt)
            ai_text = response.text.strip()
            
            # Extract JSON array from response
            json_match = re.search(r'\[[\s\S]*\]', ai_text)
            if json_match:
                test_cases = json.loads(json_match.group())
                
                # Add metadata to each test case
                for tc in test_cases:
                    tc['generated_from_git'] = True
                    tc['risk_level'] = file_change.risk_level
                    tc['generated_at'] = datetime.now().isoformat()
                
                return test_cases
            else:
                logger.warning("Could not parse AI response for test generation")
                return [self._create_basic_test_case(file_change, commit_analysis)]
                
        except Exception as e:
            logger.error(f"AI test generation failed: {str(e)}")
            return [self._create_basic_test_case(file_change, commit_analysis)]
    
    def _create_basic_test_case(self, 
                                file_change: CodeChange,
                                commit_analysis: CommitAnalysis) -> Dict[str, Any]:
        """
        Create a basic test case without AI
        
        Args:
            file_change: CodeChange object
            commit_analysis: CommitAnalysis object
        
        Returns:
            Basic test case dictionary
        """
        return {
            'id': f"TC_GIT_{uuid.uuid4().hex[:8].upper()}",
            'title': f"Test {file_change.change_type} in {Path(file_change.filepath).name}",
            'description': f"Verify changes from commit {commit_analysis.commit_sha}: {commit_analysis.message[:100]}",
            'category': 'Functional',
            'priority': 'High' if file_change.risk_level == 'high' else 'Medium',
            'test_type': 'integration',
            'preconditions': f"Code from commit {commit_analysis.commit_sha} is deployed",
            'test_steps': [
                f"Test functionality in {file_change.filepath}",
                "Verify changed functions work correctly",
                "Check for regression in related features",
                "Validate error handling"
            ],
            'expected_results': "All functionality works as expected without regression",
            'test_data': {},
            'automation_feasible': True,
            'estimated_duration': "15 minutes",
            'source_file': file_change.filepath,
            'commit_sha': commit_analysis.commit_sha,
            'compliance': file_change.compliance_impact,
            'generated_from_git': True,
            'risk_level': file_change.risk_level,
            'generated_at': datetime.now().isoformat()
        }
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """Get basic repository statistics"""
        if not self.is_valid:
            return {}
        
        try:
            return {
                'current_branch': self.repo.active_branch.name,
                'total_branches': len(list(self.repo.branches)),
                'total_commits': len(list(self.repo.iter_commits())),
                'remote_url': list(self.repo.remotes[0].urls)[0] if self.repo.remotes else None,
                'is_dirty': self.repo.is_dirty(),
                'untracked_files': self.repo.untracked_files
            }
        except Exception as e:
            logger.error(f"Failed to get repository stats: {str(e)}")
            return {}

# Helper function for standalone use
def analyze_repository_standalone(repo_path: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Standalone function to analyze a repository
    
    Args:
        repo_path: Path to the Git repository
        api_key: Optional Gemini API key for AI features
    
    Returns:
        Complete repository analysis
    """
    analyzer = GitAnalyzer(repo_path, api_key)
    
    if not analyzer.is_valid:
        return {'error': 'Invalid repository path'}
    
    return analyzer.analyze_repository()
