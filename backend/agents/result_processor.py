"""
Result Processor - Handles processing and aggregation of agent results
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging

from models import AgentResult


@dataclass
class ProcessedResult:
    """Processed result with additional metadata"""
    original_result: AgentResult
    insights: List[str]
    recommendations: List[str]
    artifacts: Dict[str, Any]
    summary: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    category: str  # security, performance, reliability, etc.


class ResultProcessor:
    """Processes and enhances agent results"""
    
    def __init__(self, output_dir: str = "processed_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Processing history
        self.processed_results: List[ProcessedResult] = []
        
        # Analysis patterns
        self.severity_keywords = {
            'CRITICAL': ['critical', 'security', 'breach', 'compromise', 'outage'],
            'HIGH': ['high', 'urgent', 'immediate', 'severe', 'major'],
            'MEDIUM': ['medium', 'moderate', 'important', 'significant'],
            'LOW': ['low', 'minor', 'cosmetic', 'suggestion']
        }
        
        self.category_keywords = {
            'security': ['security', 'vulnerability', 'auth', 'permission', 'encryption'],
            'performance': ['performance', 'slow', 'timeout', 'memory', 'cpu'],
            'reliability': ['reliability', 'stability', 'crash', 'error', 'failure'],
            'maintainability': ['maintainability', 'code', 'refactor', 'technical debt'],
            'functionality': ['bug', 'feature', 'requirement', 'behavior']
        }
    
    async def process_result(self, result: AgentResult) -> ProcessedResult:
        """Process a single agent result"""
        try:
            # Extract insights and recommendations
            insights = self._extract_insights(result)
            recommendations = self._generate_recommendations(result)
            artifacts = self._extract_artifacts(result)
            summary = self._generate_summary(result)
            severity = self._determine_severity(result)
            category = self._determine_category(result)
            
            # Create processed result
            processed = ProcessedResult(
                original_result=result,
                insights=insights,
                recommendations=recommendations,
                artifacts=artifacts,
                summary=summary,
                severity=severity,
                category=category
            )
            
            # Store processed result
            self.processed_results.append(processed)
            
            # Save to file
            await self._save_processed_result(processed)
            
            self.logger.info(f"Processed result for task {result.task_id}")
            return processed
            
        except Exception as e:
            self.logger.error(f"Failed to process result {result.task_id}: {e}")
            raise
    
    async def process_batch(self, results: List[AgentResult]) -> List[ProcessedResult]:
        """Process multiple results concurrently"""
        tasks = [self.process_result(result) for result in results]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _extract_insights(self, result: AgentResult) -> List[str]:
        """Extract key insights from result data"""
        insights = []
        data = result.data
        
        if not isinstance(data, dict):
            return insights
        
        # RCA specific insights
        if 'log_analysis' in data:
            log_analysis = data['log_analysis']
            insights.append(f"Found {log_analysis.get('total_errors', 0)} errors in logs")
            
            error_patterns = log_analysis.get('error_patterns', {})
            if error_patterns:
                top_pattern = max(error_patterns, key=error_patterns.get)
                insights.append(f"Most common error pattern: {top_pattern} ({error_patterns[top_pattern]} occurrences)")
            
            components = log_analysis.get('affected_components', [])
            if components:
                insights.append(f"Affected components: {', '.join(components)}")
        
        # General insights
        if result.execution_time > 60:
            insights.append("Analysis took longer than expected (>60s)")
        
        if result.confidence_score < 0.5:
            insights.append("Low confidence score - results may need manual review")
        
        return insights
    
    def _generate_recommendations(self, result: AgentResult) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        data = result.data
        
        if not isinstance(data, dict):
            return recommendations
        
        # RCA recommendations
        if 'log_analysis' in data:
            log_analysis = data['log_analysis']
            error_patterns = log_analysis.get('error_patterns', {})
            
            if 'timeout' in error_patterns:
                recommendations.append("Implement circuit breakers and timeout handling")
                recommendations.append("Review and optimize slow database queries")
            
            if 'connection' in error_patterns:
                recommendations.append("Implement retry logic with exponential backoff")
                recommendations.append("Add connection pooling and health checks")
            
            if 'null_pointer' in error_patterns:
                recommendations.append("Add null checks and defensive programming")
                recommendations.append("Improve input validation")
        
        # Performance recommendations
        if result.execution_time > 30:
            recommendations.append("Consider optimizing analysis pipeline for performance")
        
        # Confidence-based recommendations
        if result.confidence_score < 0.7:
            recommendations.append("Manual review recommended due to low confidence")
            recommendations.append("Consider providing more context or data")
        
        return recommendations
    
    def _extract_artifacts(self, result: AgentResult) -> Dict[str, Any]:
        """Extract artifacts from result data"""
        artifacts = {}
        data = result.data
        
        if not isinstance(data, dict):
            return artifacts
        
        # RCA artifacts
        if 'suggested_fix' in data:
            fix = data['suggested_fix']
            artifacts['code_fix'] = {
                'target_class': fix.get('target_class'),
                'language': fix.get('language'),
                'patch': fix.get('patch'),
                'rationale': fix.get('rationale')
            }
        
        if 'github_pr' in data:
            artifacts['pull_request'] = data['github_pr']
        
        # Log artifacts
        if 'log_analysis' in data:
            artifacts['log_analysis'] = data['log_analysis']
        
        # Session artifacts
        artifacts['session_files'] = result.artifacts
        
        return artifacts
    
    def _generate_summary(self, result: AgentResult) -> str:
        """Generate concise summary of the result"""
        if not result.success:
            return f"Task failed: {result.error or 'Unknown error'}"
        
        data = result.data
        if not isinstance(data, dict):
            return "Task completed successfully"
        
        # RCA summary
        if 'log_analysis' in data:
            log_analysis = data['log_analysis']
            total_errors = log_analysis.get('total_errors', 0)
            components = log_analysis.get('affected_components', [])
            
            summary = f"RCA completed: {total_errors} errors identified"
            if components:
                summary += f" affecting {len(components)} components"
            
            if 'root_cause' in data:
                summary += f". Root cause: {data['root_cause'][:100]}..."
            
            return summary
        
        # General summary
        return f"Task completed successfully in {result.execution_time:.1f}s with confidence {result.confidence_score:.2f}"
    
    def _determine_severity(self, result: AgentResult) -> str:
        """Determine severity level of the result"""
        if not result.success:
            return 'HIGH'
        
        data = result.data
        if not isinstance(data, dict):
            return 'LOW'
        
        # Check for severity indicators
        text_content = json.dumps(data).lower()
        
        for severity, keywords in self.severity_keywords.items():
            if any(keyword in text_content for keyword in keywords):
                return severity
        
        # RCA severity
        if 'blast_radius' in data:
            blast_radius = data['blast_radius'].upper()
            if blast_radius in self.severity_keywords:
                return blast_radius
        
        return 'MEDIUM'
    
    def _determine_category(self, result: AgentResult) -> str:
        """Determine category of the result"""
        data = result.data
        if not isinstance(data, dict):
            return 'general'
        
        text_content = json.dumps(data).lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_content)
            category_scores[category] = score
        
        # Return category with highest score
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return 'general'
    
    async def _save_processed_result(self, processed: ProcessedResult):
        """Save processed result to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processed_{processed.original_result.task_id}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Prepare data for serialization
        data = {
            'task_id': processed.original_result.task_id,
            'success': processed.original_result.success,
            'summary': processed.summary,
            'severity': processed.severity,
            'category': processed.category,
            'insights': processed.insights,
            'recommendations': processed.recommendations,
            'artifacts': processed.artifacts,
            'execution_time': processed.original_result.execution_time,
            'confidence_score': processed.original_result.confidence_score,
            'created_at': processed.original_result.created_at.isoformat(),
            'original_data': processed.original_result.data
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.debug(f"Saved processed result to {filepath}")


class ResultAggregator:
    """Aggregates multiple processed results"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def aggregate_results(self, results: List[ProcessedResult]) -> Dict[str, Any]:
        """Aggregate multiple processed results into a comprehensive report"""
        if not results:
            return {}
        
        # Basic statistics
        total_tasks = len(results)
        successful_tasks = len([r for r in results if r.original_result.success])
        failed_tasks = total_tasks - successful_tasks
        
        # Severity distribution
        severity_counts = {}
        for result in results:
            severity_counts[result.severity] = severity_counts.get(result.severity, 0) + 1
        
        # Category distribution
        category_counts = {}
        for result in results:
            category_counts[result.category] = category_counts.get(result.category, 0) + 1
        
        # Aggregate insights
        all_insights = []
        all_recommendations = []
        all_artifacts = {}
        
        for result in results:
            all_insights.extend(result.insights)
            all_recommendations.extend(result.recommendations)
            all_artifacts.update(result.artifacts)
        
        # Performance metrics
        execution_times = [r.original_result.execution_time for r in results if r.original_result.success]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        confidence_scores = [r.original_result.confidence_score for r in results if r.original_result.success]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Generate summary
        summary = self._generate_aggregated_summary(
            successful_tasks, failed_tasks, severity_counts, category_counts
        )
        
        return {
            'summary': summary,
            'statistics': {
                'total_tasks': total_tasks,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'success_rate': successful_tasks / total_tasks if total_tasks > 0 else 0,
                'average_execution_time': avg_execution_time,
                'average_confidence_score': avg_confidence
            },
            'severity_distribution': severity_counts,
            'category_distribution': category_counts,
            'insights': self._deduplicate_list(all_insights),
            'recommendations': self._deduplicate_list(all_recommendations),
            'artifacts': all_artifacts,
            'detailed_results': [
                {
                    'task_id': r.original_result.task_id,
                    'name': r.original_result.data.get('name', 'Unknown'),
                    'summary': r.summary,
                    'severity': r.severity,
                    'category': r.category,
                    'success': r.original_result.success
                }
                for r in results
            ]
        }
    
    def _generate_aggregated_summary(
        self, 
        successful: int, 
        failed: int, 
        severity_counts: Dict[str, int],
        category_counts: Dict[str, int]
    ) -> str:
        """Generate summary of aggregated results"""
        total = successful + failed
        
        summary = f"Processed {total} agent tasks: {successful} successful, {failed} failed"
        
        if severity_counts:
            top_severity = max(severity_counts, key=severity_counts.get)
            summary += f". Highest severity: {top_severity} ({severity_counts[top_severity]} tasks)"
        
        if category_counts:
            top_category = max(category_counts, key=category_counts.get)
            summary += f". Main category: {top_category} ({category_counts[top_category]} tasks)"
        
        return summary
    
    def _deduplicate_list(self, items: List[str]) -> List[str]:
        """Remove duplicates from list while preserving order"""
        seen = set()
        deduplicated = []
        
        for item in items:
            if item not in seen:
                seen.add(item)
                deduplicated.append(item)
        
        return deduplicated
