"""
Incident Service - Creates incidents from LogAI anomalies, generates RCA, and triggers remediation.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid

logger = logging.getLogger("morphic.incident_service")


class IncidentService:
    """Service for creating and managing incidents from log anomalies."""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_incident_from_anomaly(
        self,
        monitor_id: str,
        trace_id: str,
        logs: List[Dict],
        analysis: Dict,
        github_owner: Optional[str] = None,
        github_repo: Optional[str] = None,
        github_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an incident from a LogAI anomaly detection.
        
        Args:
            monitor_id: Monitor that detected the anomaly
            trace_id: Trace ID from the logs
            logs: List of log entries
            analysis: LogAI analysis results
            github_repo: GitHub repository for remediation
            github_branch: GitHub branch for remediation
            
        Returns:
            Dict with incident details
        """
        try:
            incident_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            # Extract error signals from logs
            error_logs = [l for l in logs if l.get('level', '').upper() in ('ERROR', 'CRITICAL', 'FATAL')]
            error_types = list(set(l.get('error_type', 'UNKNOWN') for l in error_logs))
            services = list(set(l.get('service', 'unknown') for l in logs))
            
            # Determine severity based on analysis
            score = analysis.get('score', 0)
            error_rate = analysis.get('error_rate', 0)
            
            if score > 0.7 or error_rate > 0.2:
                severity = 'CRITICAL'
            elif score > 0.5 or error_rate > 0.1:
                severity = 'HIGH'
            elif score > 0.3 or error_rate > 0.05:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'
            
            # Generate RCA using Claude (or placeholder)
            rca = self._generate_rca(logs, analysis, error_types, services)
            
            # Store incident in database
            with self.db.postgres_conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO incidents 
                    (id, trace_id, title, description, severity, status, 
                     error_type, service, created_at, updated_at, rca_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id""",
                    (
                        incident_id,
                        trace_id,
                        f"Anomaly detected in {services[0] if services else 'unknown'}",
                        f"LogAI detected anomaly with score {score:.2f}. "
                        f"Error rate: {error_rate:.2%}. "
                        f"Error types: {', '.join(error_types[:5])}",
                        severity,
                        'OPEN',
                        error_types[0] if error_types else 'UNKNOWN',
                        services[0] if services else 'unknown',
                        now,
                        now,
                        json.dumps(rca),
                    )
                )
                self.db.postgres_conn.commit()
            
            # Also create an agent run record
            self._create_agent_run(
                monitor_id=monitor_id,
                trace_id=trace_id,
                github_owner=github_owner,
                github_repo=github_repo,
                log_snapshot=logs[:50],  # Store first 50 logs
                anomalies=analysis
            )
            
            logger.info(f"Created incident {incident_id} for trace {trace_id}")
            
            return {
                "incident_id": incident_id,
                "trace_id": trace_id,
                "severity": severity,
                "rca": rca,
                "status": "OPEN",
                "created_at": now.isoformat(),
                "github_owner": github_owner,
                "github_repo": github_repo,
            }
            
        except Exception as e:
            logger.error(f"Failed to create incident: {e}", exc_info=True)
            try:
                self.db.postgres_conn.rollback()
            except:
                pass
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _generate_rca(
        self,
        logs: List[Dict],
        analysis: Dict,
        error_types: List[str],
        services: List[str]
    ) -> Dict[str, Any]:
        """
        Generate Root Cause Analysis from log data.
        In production, this would use Claude to generate detailed RCA.
        """
        # Extract key patterns
        error_count = len([l for l in logs if l.get('level', '').upper() in ('ERROR', 'CRITICAL', 'FATAL')])
        warn_count = len([l for l in logs if l.get('level', '').upper() in ('WARN', 'WARNING')])
        
        # Build RCA JSON
        rca = {
            "classification": self._classify_error(error_types),
            "root_cause": self._infer_root_cause(error_types, services, logs),
            "blast_radius": self._determine_blast_radius(analysis.get('score', 0)),
            "impact": f"{error_count} errors and {warn_count} warnings detected in recent logs",
            "trace_id": logs[0].get('trace_id', 'unknown') if logs else 'unknown',
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log_signals": {
                "service": services[0] if services else "unknown",
                "endpoint": "unknown",
                "exception_class": error_types[0] if error_types else "UNKNOWN",
                "error_message": logs[0].get('message', '')[:200] if logs else ''
            },
            "suggested_fix": {
                "language": "java",
                "target_class": self._guess_target_class(services, error_types),
                "patch": "// Fix would be generated by Claude agent",
                "rationale": "To be determined by Claude agent analysis",
                "tests": []
            },
            "github_pr": {
                "title": f"Fix: {error_types[0] if error_types else 'Unknown Error'}",
                "body": "PR body to be generated by Claude agent",
                "labels": ["bug", "automated"]
            },
            "confidence_score": min(1.0, analysis.get('score', 0) * 1.5)
        }
        
        return rca
    
    def _classify_error(self, error_types: List[str]) -> str:
        """Classify the error type."""
        if not error_types:
            return "UNKNOWN"
        
        error_str = ' '.join(error_types).lower()
        
        if 'timeout' in error_str or 'gateway' in error_str:
            return "GATEWAY_TIMEOUT"
        elif 'partial' in error_str or 'orphan' in error_str:
            return "PARTIAL_WRITE"
        elif 'race' in error_str or 'reservation' in error_str:
            return "RACE_CONDITION"
        elif 'stale' in error_str or 'inconsistent' in error_str:
            return "INCONSISTENT_STATE"
        else:
            return error_types[0]
    
    def _infer_root_cause(self, error_types: List[str], services: List[str], logs: List[Dict]) -> str:
        """Infer the root cause from error patterns."""
        if not error_types:
            return "Unknown - insufficient data"
        
        error_str = ' '.join(error_types).lower()
        
        if 'timeout' in error_str:
            return "Upstream service timeout causing cascading failures"
        elif 'partial' in error_str:
            return "Transaction rollback failure leaving orphaned records"
        elif 'race' in error_str or 'reservation' in error_str:
            return "Concurrent inventory updates causing stock inconsistency"
        elif 'stale' in error_str:
            return "Background worker not processing orders within SLA"
        else:
            return f"Service {services[0] if services else 'unknown'} experiencing {error_types[0]}"
    
    def _determine_blast_radius(self, score: float) -> str:
        """Determine blast radius from anomaly score."""
        if score > 0.7:
            return "CRITICAL"
        elif score > 0.5:
            return "HIGH"
        elif score > 0.3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _guess_target_class(self, services: List[str], error_types: List[str]) -> str:
        """Guess the target Java class for the fix."""
        service_map = {
            'OrderService': 'OrderController',
            'InventoryService': 'InventoryManager',
            'PaymentService': 'PaymentProcessor',
            'BackgroundWorker': 'OrderProcessor'
        }
        
        for service in services:
            if service in service_map:
                return service_map[service]
        
        return "UnknownService"
    
    def _create_agent_run(
        self,
        monitor_id: str,
        trace_id: str,
        github_owner: Optional[str],
        github_repo: Optional[str],
        log_snapshot: List[Dict],
        anomalies: Dict
    ):
        """Create an agent run record in the database."""
        try:
            with self.db.postgres_conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO agent_runs 
                    (monitor_id, trace_id, status, github_repo, log_snapshot, anomalies, rca_summary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        monitor_id,
                        trace_id,
                        'QUEUED',
                        (f"{github_owner}/{github_repo}" if github_owner and github_repo else github_repo),
                        json.dumps(log_snapshot),
                        json.dumps(anomalies),
                        (f"github_owner={github_owner}" if github_owner else None),
                    )
                )
                self.db.postgres_conn.commit()
        except Exception as e:
            logger.error(f"Failed to create agent run record: {e}")
            try:
                self.db.postgres_conn.rollback()
            except:
                pass
    
    def update_incident_status(self, incident_id: str, status: str, metadata: Optional[Dict] = None) -> bool:
        """Update incident status."""
        try:
            with self.db.postgres_conn.cursor() as cur:
                if metadata:
                    cur.execute(
                        """UPDATE incidents 
                        SET status=%s, updated_at=%s, metadata=%s 
                        WHERE id=%s""",
                        (status, datetime.now(timezone.utc), json.dumps(metadata), incident_id)
                    )
                else:
                    cur.execute(
                        """UPDATE incidents 
                        SET status=%s, updated_at=%s 
                        WHERE id=%s""",
                        (status, datetime.now(timezone.utc), incident_id)
                    )
                self.db.postgres_conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update incident status: {e}")
            try:
                self.db.postgres_conn.rollback()
            except:
                pass
            return False


# Singleton instance
incident_service = None

def get_incident_service(db_manager) -> IncidentService:
    global incident_service
    if incident_service is None:
        incident_service = IncidentService(db_manager)
    return incident_service
