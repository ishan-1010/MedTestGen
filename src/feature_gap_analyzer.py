"""
Feature Gap Analysis Module for AI-Powered Test Generation
Analyzes requirements vs test coverage and identifies gaps
Real-world implementation using Gemini AI and semantic matching
"""

import re
import json
import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class Requirement:
    """Represents a single requirement extracted from documentation"""
    id: str
    title: str
    description: str
    source_document: str
    priority: str  # Critical, High, Medium, Low
    category: str  # Functional, Security, Integration, etc.
    acceptance_criteria: List[str]
    compliance_standards: List[str]
    extracted_at: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class CoverageGap:
    """Represents a requirement with insufficient test coverage"""
    requirement: Requirement
    coverage_score: float  # 0-100
    matched_tests: List[Dict]  # Tests that partially cover this
    gap_severity: str  # Critical, High, Medium, Low
    recommended_test_count: int
    gap_description: str
    suggested_test_types: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['requirement'] = self.requirement.to_dict()
        return data

class FeatureGapAnalyzer:
    """
    Analyzes feature/requirement coverage gaps in test suites
    Uses AI and semantic similarity for intelligent gap detection
    """
    
    def __init__(self, embedding_model: SentenceTransformer, api_key: str):
        """
        Initialize the Feature Gap Analyzer
        
        Args:
            embedding_model: Sentence transformer model for embeddings
            api_key: Gemini API key for AI analysis
        """
        self.embedding_model = embedding_model
        self.api_key = api_key
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        logger.info("[FEATURE_GAP] Feature Gap Analyzer initialized with AI capabilities")
    
    def extract_requirements_from_documents(self, 
                                           documents: List[Dict[str, Any]]) -> List[Requirement]:
        """
        Extract requirements from uploaded documents using AI
        
        Args:
            documents: List of document dictionaries with 'filename' and 'content'
        
        Returns:
            List of extracted Requirement objects
        """
        logger.info(f"[FEATURE_GAP] Extracting requirements from {len(documents)} documents")
        all_requirements = []
        
        for doc in documents:
            logger.info(f"[FEATURE_GAP] Processing document: {doc.get('filename', 'unknown')}")
            
            try:
                requirements = self._extract_requirements_from_single_document(
                    doc.get('content', ''),
                    doc.get('filename', 'unknown'),
                    doc.get('doc_type', 'unknown')
                )
                all_requirements.extend(requirements)
                logger.info(f"[FEATURE_GAP] Extracted {len(requirements)} requirements from {doc.get('filename')}")
            except Exception as e:
                logger.error(f"[FEATURE_GAP] Failed to extract from {doc.get('filename')}: {str(e)}")
        
        logger.info(f"[FEATURE_GAP] Total requirements extracted: {len(all_requirements)}")
        return all_requirements
    
    def _extract_requirements_from_single_document(self, 
                                                   content: str, 
                                                   filename: str,
                                                   doc_type: str) -> List[Requirement]:
        """
        Extract requirements from a single document using Gemini AI
        
        Args:
            content: Document text content
            filename: Name of the document
            doc_type: Type of document (prd, user_story, api_spec, etc.)
        
        Returns:
            List of Requirement objects
        """
        logger.info(f"[FEATURE_GAP_AI] Using AI to extract requirements from {filename}")
        
        prompt = f"""You are a requirements analyst for healthcare software.
Extract all testable requirements from the following document.

DOCUMENT: {filename}
TYPE: {doc_type}

CONTENT:
{content[:4000]}  # First 4000 chars to stay within token limits

For each requirement found, extract:
1. A unique identifier (REQ-001, REQ-002, etc.)
2. Clear title
3. Detailed description
4. Priority (Critical/High/Medium/Low)
5. Category (Functional/Security/Integration/Performance/Compliance/Usability)
6. Acceptance criteria (list of testable conditions)
7. Applicable compliance standards (HIPAA, GDPR, FDA, etc.)

Return as JSON array:
[
  {{
    "id": "REQ-001",
    "title": "User Authentication",
    "description": "System must authenticate users with multi-factor authentication",
    "priority": "Critical",
    "category": "Security",
    "acceptance_criteria": [
      "User can login with email and password",
      "MFA required for sensitive operations",
      "Session expires after 30 minutes"
    ],
    "compliance_standards": ["HIPAA", "ISO 27001"]
  }}
]

IMPORTANT:
- Only extract TESTABLE requirements
- Be specific and detailed
- Focus on healthcare/medical domain requirements
- Include all acceptance criteria
- Identify relevant compliance standards

Return ONLY a valid JSON array."""

        try:
            # Use structured output for reliable JSON
            model_with_json = genai.GenerativeModel(
                'gemini-2.0-flash-exp',
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            
            response = model_with_json.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            logger.info(f"[FEATURE_GAP_AI] Received response length: {len(response_text)} chars")
            
            # Parse JSON response
            try:
                requirements_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON array from text
                logger.warning(f"[FEATURE_GAP_AI] Direct JSON parse failed, attempting extraction")
                json_match = re.search(r'\[[\s\S]*\]', response_text)
                if json_match:
                    requirements_data = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not extract JSON from response: {response_text[:200]}")
            
            # Convert to Requirement objects
            requirements = []
            for req_data in requirements_data:
                req = Requirement(
                    id=req_data.get('id', f"REQ_{len(requirements)+1:03d}"),
                    title=req_data.get('title', 'Untitled Requirement'),
                    description=req_data.get('description', ''),
                    source_document=filename,
                    priority=req_data.get('priority', 'Medium'),
                    category=req_data.get('category', 'Functional'),
                    acceptance_criteria=req_data.get('acceptance_criteria', []),
                    compliance_standards=req_data.get('compliance_standards', []),
                    extracted_at=datetime.now().isoformat()
                )
                requirements.append(req)
            
            logger.info(f"[FEATURE_GAP_AI] Successfully extracted {len(requirements)} requirements from {filename}")
            return requirements
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for API quota errors
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                logger.error("="*80)
                logger.error("🚨 GEMINI API QUOTA EXCEEDED - Feature Gap Analysis")
                logger.error(f"Document: {filename}")
                logger.error(f"Error: {error_msg}")
                if "50" in error_msg:
                    logger.error("FREE TIER LIMIT: 50 requests/day reached")
                logger.error("="*80)
            else:
                logger.error(f"[FEATURE_GAP_AI] AI extraction failed for {filename}: {error_msg}")
            
            return []
    
    def analyze_coverage(self,
                        requirements: List[Requirement],
                        test_cases: List[Dict]) -> Tuple[List[Requirement], List[CoverageGap]]:
        """
        Analyze test coverage for requirements and identify gaps
        
        Args:
            requirements: List of extracted requirements
            test_cases: List of existing test case dictionaries
        
        Returns:
            Tuple of (covered_requirements, coverage_gaps)
        """
        logger.info(f"[COVERAGE] Analyzing coverage for {len(requirements)} requirements against {len(test_cases)} tests")
        
        if not requirements:
            logger.warning("[COVERAGE] No requirements to analyze")
            return [], []
        
        if not test_cases:
            logger.warning("[COVERAGE] No test cases available, all requirements are gaps")
            # All requirements are gaps
            gaps = [self._create_gap_for_uncovered_requirement(req, []) for req in requirements]
            return [], gaps
        
        # Create embeddings for requirements
        logger.info("[COVERAGE] Creating embeddings for requirements")
        req_texts = [f"{req.title}. {req.description}" for req in requirements]
        req_embeddings = self.embedding_model.encode(req_texts)
        
        # Create embeddings for test cases
        logger.info("[COVERAGE] Creating embeddings for test cases")
        test_texts = [f"{tc.get('title', '')}. {tc.get('description', '')}" for tc in test_cases]
        test_embeddings = self.embedding_model.encode(test_texts)
        
        # Analyze coverage for each requirement
        covered_requirements = []
        coverage_gaps = []
        
        for idx, req in enumerate(requirements):
            logger.info(f"[COVERAGE] Analyzing requirement {idx+1}/{len(requirements)}: {req.id}")
            
            # Calculate similarity scores with all tests
            req_embedding = req_embeddings[idx].reshape(1, -1)
            similarities = np.dot(test_embeddings, req_embedding.T).flatten()
            
            # Find tests that match this requirement
            # Threshold: 0.6 = good match, 0.4 = partial match, <0.4 = no match
            matched_tests = []
            for test_idx, similarity in enumerate(similarities):
                if similarity > 0.4:  # Partial or full match
                    matched_tests.append({
                        'test': test_cases[test_idx],
                        'similarity': float(similarity),
                        'match_type': 'full' if similarity > 0.6 else 'partial'
                    })
            
            # Sort by similarity
            matched_tests.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Calculate coverage score
            if not matched_tests:
                coverage_score = 0.0
            else:
                # Coverage based on best matches
                top_matches = matched_tests[:3]  # Consider top 3 matches
                coverage_score = sum(m['similarity'] for m in top_matches) / len(top_matches) * 100
            
            logger.info(f"[COVERAGE] Requirement {req.id} coverage: {coverage_score:.1f}%, Matches: {len(matched_tests)}")
            
            # Determine if this is a gap
            if coverage_score < 60:  # Less than 60% coverage is a gap
                gap = self._create_coverage_gap(req, matched_tests, coverage_score)
                coverage_gaps.append(gap)
                logger.info(f"[COVERAGE] Gap identified for {req.id}. Severity: {gap.gap_severity}")
            else:
                covered_requirements.append(req)
                logger.info(f"[COVERAGE] Requirement {req.id} has adequate coverage")
        
        logger.info(f"[COVERAGE] Analysis complete. Covered: {len(covered_requirements)}, Gaps: {len(coverage_gaps)}")
        return covered_requirements, coverage_gaps
    
    def _create_coverage_gap(self,
                            requirement: Requirement,
                            matched_tests: List[Dict],
                            coverage_score: float) -> CoverageGap:
        """
        Create a CoverageGap object with AI-powered recommendations
        
        Args:
            requirement: The requirement object
            matched_tests: List of partially matching tests
            coverage_score: Coverage percentage (0-100)
        
        Returns:
            CoverageGap object
        """
        # Determine gap severity
        if coverage_score < 20:
            gap_severity = "Critical"
            recommended_tests = 3
        elif coverage_score < 40:
            gap_severity = "High"
            recommended_tests = 2
        else:
            gap_severity = "Medium"
            recommended_tests = 1
        
        # Adjust by requirement priority
        if requirement.priority in ["Critical", "High"]:
            if gap_severity == "Medium":
                gap_severity = "High"
            recommended_tests += 1
        
        # Generate gap description
        if coverage_score == 0:
            gap_desc = f"No tests found for requirement '{requirement.title}'"
        elif matched_tests:
            gap_desc = f"Only {len(matched_tests)} partial test(s) found. Coverage: {coverage_score:.0f}%"
        else:
            gap_desc = f"Insufficient test coverage ({coverage_score:.0f}%)"
        
        # Suggest test types based on category
        test_type_mapping = {
            'Functional': ['unit', 'integration', 'e2e'],
            'Security': ['security', 'penetration', 'compliance'],
            'Integration': ['integration', 'api', 'e2e'],
            'Performance': ['performance', 'load', 'stress'],
            'Compliance': ['compliance', 'audit', 'security'],
            'Usability': ['usability', 'e2e', 'acceptance']
        }
        suggested_types = test_type_mapping.get(requirement.category, ['integration'])
        
        return CoverageGap(
            requirement=requirement,
            coverage_score=coverage_score,
            matched_tests=[m['test'] for m in matched_tests],
            gap_severity=gap_severity,
            recommended_test_count=recommended_tests,
            gap_description=gap_desc,
            suggested_test_types=suggested_types
        )
    
    def _create_gap_for_uncovered_requirement(self,
                                             requirement: Requirement,
                                             matched_tests: List[Dict]) -> CoverageGap:
        """
        Create a gap for a completely uncovered requirement
        
        Args:
            requirement: The requirement with no coverage
            matched_tests: Empty list or partial matches
        
        Returns:
            CoverageGap object
        """
        return self._create_coverage_gap(requirement, matched_tests, 0.0)
    
    def generate_tests_for_gap(self,
                               gap: CoverageGap,
                               context_docs: List[Dict] = None) -> List[Dict]:
        """
        Generate test cases to fill a coverage gap using AI
        
        Args:
            gap: CoverageGap object
            context_docs: Optional context documents for RAG
        
        Returns:
            List of generated test case dictionaries
        """
        logger.info(f"[GAP_FILL] Generating tests to fill gap for requirement: {gap.requirement.id}")
        logger.info(f"[GAP_FILL] Severity: {gap.gap_severity}, Recommended tests: {gap.recommended_test_count}")
        
        req = gap.requirement
        
        # Build context string
        context_str = ""
        if context_docs:
            context_parts = []
            for doc in context_docs[:2]:
                context_parts.append(f"Context: {doc.get('content', '')[:500]}")
            context_str = "\n".join(context_parts)
        
        # Build prompt for test generation
        prompt = f"""You are a QA Engineer generating test cases to fill coverage gaps.

REQUIREMENT TO TEST:
ID: {req.id}
Title: {req.title}
Description: {req.description}
Category: {req.category}
Priority: {req.priority}
Compliance Standards: {', '.join(req.compliance_standards)}

ACCEPTANCE CRITERIA:
{chr(10).join(f"- {ac}" for ac in req.acceptance_criteria)}

EXISTING PARTIAL TESTS:
{len(gap.matched_tests)} test(s) provide partial coverage

COVERAGE GAP:
{gap.gap_description}

CONTEXT FROM DOCUMENTS:
{context_str}

Generate {gap.recommended_test_count} comprehensive test case(s) to fill this gap.

For EACH test case, provide:
{{
  "id": "TC_GAP_XXXXX",
  "title": "Clear, specific title",
  "description": "Detailed description",
  "category": "{req.category}",
  "priority": "{req.priority}",
  "compliance": {json.dumps(req.compliance_standards)},
  "preconditions": "What must be true before testing",
  "test_steps": ["Step 1", "Step 2", "Step 3"],
  "expected_results": "Specific expected outcomes",
  "test_data": {{"key": "value"}},
  "edge_cases": ["Edge case 1", "Edge case 2"],
  "negative_tests": ["Negative scenario 1"],
  "automation_feasible": true/false,
  "estimated_duration": "X minutes",
  "traceability": "{req.id} - {req.title}",
  "covers_requirement": "{req.id}",
  "gap_filled": true
}}

Return as JSON array of {gap.recommended_test_count} test case(s)."""

        try:
            response = self.model.generate_content(prompt)
            test_cases_data = json.loads(response.text)
            
            # Ensure it's an array
            if not isinstance(test_cases_data, list):
                test_cases_data = [test_cases_data]
            
            # Add metadata
            for tc in test_cases_data:
                tc['generated_for_gap'] = True
                tc['gap_severity'] = gap.gap_severity
                tc['requirement_id'] = req.id
                tc['generation_timestamp'] = datetime.now().isoformat()
                tc['nasscom_compliant'] = True
            
            logger.info(f"[GAP_FILL] Successfully generated {len(test_cases_data)} test(s) for {req.id}")
            return test_cases_data
            
        except Exception as e:
            logger.error(f"[GAP_FILL] Failed to generate tests for {req.id}: {str(e)}")
            # Return a basic fallback test
            return [self._create_fallback_gap_test(req)]
    
    def _create_fallback_gap_test(self, requirement: Requirement) -> Dict:
        """
        Create a basic fallback test when AI generation fails
        
        Args:
            requirement: The requirement to test
        
        Returns:
            Basic test case dictionary
        """
        return {
            'id': f"TC_GAP_{requirement.id}",
            'title': f"Test {requirement.title}",
            'description': f"Verify that {requirement.description}",
            'category': requirement.category,
            'priority': requirement.priority,
            'compliance': requirement.compliance_standards,
            'preconditions': 'System is in stable state',
            'test_steps': [
                f"Setup test environment for {requirement.title}",
                "Execute test scenario",
                "Verify expected behavior",
                "Validate compliance requirements"
            ],
            'expected_results': f"Requirement {requirement.id} is satisfied",
            'test_data': {},
            'edge_cases': [],
            'negative_tests': [],
            'automation_feasible': True,
            'estimated_duration': '15 minutes',
            'traceability': f"{requirement.id} - {requirement.title}",
            'covers_requirement': requirement.id,
            'gap_filled': True,
            'fallback': True,
            'nasscom_compliant': True
        }
    
    def calculate_overall_coverage(self,
                                   total_requirements: int,
                                   covered_requirements: int,
                                   gaps: List[CoverageGap]) -> Dict[str, Any]:
        """
        Calculate overall coverage statistics
        
        Args:
            total_requirements: Total number of requirements
            covered_requirements: Number of adequately covered requirements
            gaps: List of coverage gaps
        
        Returns:
            Coverage statistics dictionary
        """
        logger.info(f"[COVERAGE_STATS] Calculating overall coverage statistics")
        
        if total_requirements == 0:
            return {
                'total_requirements': 0,
                'covered_requirements': 0,
                'coverage_percentage': 0.0,
                'gaps_count': 0,
                'critical_gaps': 0,
                'high_gaps': 0,
                'medium_gaps': 0,
                'recommended_tests_to_add': 0
            }
        
        # Count gaps by severity
        critical_gaps = sum(1 for g in gaps if g.gap_severity == "Critical")
        high_gaps = sum(1 for g in gaps if g.gap_severity == "High")
        medium_gaps = sum(1 for g in gaps if g.gap_severity == "Medium")
        
        # Calculate total recommended tests
        recommended_tests = sum(g.recommended_test_count for g in gaps)
        
        coverage_pct = (covered_requirements / total_requirements) * 100
        
        stats = {
            'total_requirements': total_requirements,
            'covered_requirements': covered_requirements,
            'coverage_percentage': coverage_pct,
            'gaps_count': len(gaps),
            'critical_gaps': critical_gaps,
            'high_gaps': high_gaps,
            'medium_gaps': medium_gaps,
            'recommended_tests_to_add': recommended_tests
        }
        
        logger.info(f"[COVERAGE_STATS] Coverage: {coverage_pct:.1f}%, Gaps: {len(gaps)} (Critical: {critical_gaps}, High: {high_gaps}, Medium: {medium_gaps})")
        
        return stats
    
    def prioritize_gaps(self, gaps: List[CoverageGap]) -> List[CoverageGap]:
        """
        Prioritize coverage gaps by severity and requirement priority
        
        Args:
            gaps: List of coverage gaps
        
        Returns:
            Sorted list of gaps (highest priority first)
        """
        logger.info(f"[GAP_PRIORITIZE] Prioritizing {len(gaps)} coverage gaps")
        
        # Define priority scores
        severity_scores = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        priority_scores = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        
        def gap_score(gap: CoverageGap) -> int:
            severity = severity_scores.get(gap.gap_severity, 1)
            priority = priority_scores.get(gap.requirement.priority, 1)
            # Combined score (severity weighted more heavily)
            return (severity * 2) + priority
        
        sorted_gaps = sorted(gaps, key=gap_score, reverse=True)
        
        logger.info(f"[GAP_PRIORITIZE] Gaps prioritized. Top gap: {sorted_gaps[0].requirement.id if sorted_gaps else 'None'}")
        
        return sorted_gaps
    
    def generate_gap_analysis_report(self,
                                    requirements: List[Requirement],
                                    covered_reqs: List[Requirement],
                                    gaps: List[CoverageGap],
                                    stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive gap analysis report
        
        Args:
            requirements: All requirements
            covered_reqs: Adequately covered requirements
            gaps: Coverage gaps
            stats: Coverage statistics
        
        Returns:
            Comprehensive report dictionary
        """
        logger.info("[REPORT] Generating comprehensive gap analysis report")
        
        # Group gaps by category
        gaps_by_category = {}
        for gap in gaps:
            category = gap.requirement.category
            if category not in gaps_by_category:
                gaps_by_category[category] = []
            gaps_by_category[category].append(gap)
        
        # Group gaps by severity
        gaps_by_severity = {
            'Critical': [g for g in gaps if g.gap_severity == "Critical"],
            'High': [g for g in gaps if g.gap_severity == "High"],
            'Medium': [g for g in gaps if g.gap_severity == "Medium"],
            'Low': [g for g in gaps if g.gap_severity == "Low"]
        }
        
        # Find most critical gaps
        critical_gaps_list = gaps_by_severity.get('Critical', [])
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': stats,
            'covered_requirements': [req.to_dict() for req in covered_reqs],
            'coverage_gaps': [gap.to_dict() for gap in gaps],
            'gaps_by_category': {cat: len(gaps_list) for cat, gaps_list in gaps_by_category.items()},
            'gaps_by_severity': {sev: len(gaps_list) for sev, gaps_list in gaps_by_severity.items()},
            'most_critical_gaps': [gap.to_dict() for gap in critical_gaps_list[:5]],  # Top 5
            'recommendations': self._generate_recommendations(gaps, stats)
        }
        
        logger.info("[REPORT] Gap analysis report generated successfully")
        
        return report
    
    def _generate_recommendations(self, gaps: List[CoverageGap], stats: Dict) -> List[str]:
        """
        Generate actionable recommendations based on gaps
        
        Args:
            gaps: List of coverage gaps
            stats: Coverage statistics
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        coverage_pct = stats.get('coverage_percentage', 0)
        
        if coverage_pct < 50:
            recommendations.append("⚠️ CRITICAL: Less than 50% requirement coverage. Immediate action required.")
        elif coverage_pct < 70:
            recommendations.append("⚠️ Coverage below 70%. Focus on high-priority gaps.")
        elif coverage_pct < 90:
            recommendations.append("✅ Good coverage. Address remaining gaps for completeness.")
        else:
            recommendations.append("✅ Excellent coverage! Focus on maintenance and regression testing.")
        
        # Category-specific recommendations
        critical_gaps = [g for g in gaps if g.gap_severity == "Critical"]
        if critical_gaps:
            recommendations.append(f"🔴 {len(critical_gaps)} critical gap(s) require immediate attention")
        
        # Compliance recommendations
        compliance_gaps = [g for g in gaps if g.requirement.compliance_standards]
        if compliance_gaps:
            standards = set()
            for g in compliance_gaps:
                standards.update(g.requirement.compliance_standards)
            recommendations.append(f"⚖️ Compliance gaps found for: {', '.join(standards)}")
        
        # Suggested next steps
        if stats.get('recommended_tests_to_add', 0) > 0:
            recommendations.append(f"💡 Generate {stats['recommended_tests_to_add']} test(s) to achieve 100% coverage")
        
        return recommendations

# Helper function for standalone use
def analyze_feature_gaps(documents: List[Dict],
                        test_cases: List[Dict],
                        embedding_model: SentenceTransformer,
                        api_key: str) -> Dict[str, Any]:
    """
    Standalone function to perform complete feature gap analysis
    
    Args:
        documents: List of requirement documents
        test_cases: List of existing test cases
        embedding_model: Sentence transformer model
        api_key: Gemini API key
    
    Returns:
        Complete gap analysis report
    """
    analyzer = FeatureGapAnalyzer(embedding_model, api_key)
    
    # Extract requirements
    requirements = analyzer.extract_requirements_from_documents(documents)
    
    # Analyze coverage
    covered, gaps = analyzer.analyze_coverage(requirements, test_cases)
    
    # Calculate statistics
    stats = analyzer.calculate_overall_coverage(len(requirements), len(covered), gaps)
    
    # Generate report
    report = analyzer.generate_gap_analysis_report(requirements, covered, gaps, stats)
    
    return report

