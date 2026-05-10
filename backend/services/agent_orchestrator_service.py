"""Clean agent orchestration service for Morphic"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from config.settings import Config
from services.alert_service import AlertService


logger = logging.getLogger(__name__)


class AgentOrchestratorService:
    """
    Clean orchestration layer for incident management workflow.
    Coordinates RCA generation, alert dispatch, and remediation.
    """
    
    def __init__(self, db_manager, alert_service: Optional[AlertService] = None):
        self.db = db_manager
        self.alert_service = alert_service or AlertService()
        self._orchestrator = None
        
        # Try to import the full agent orchestrator if available
        try:
            from agent_orchestrator import AgentOrchestrator
            self._orchestrator = AgentOrchestrator(db_manager)
            logger.info("[AgentOrchestratorService] Full agent orchestrator loaded")
        except Exception as e:
            logger.warning(f"[AgentOrchestratorService] Full orchestrator not available: {e}")
            self._orchestrator = None
    
    def orchestrate(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration entry point.
        Coordinates the full incident handling workflow.
        
        Args:
            incident_data: {
                'trace_id': str,
                'severity': str,
                'classification': str,
                'root_cause': str (optional),
                'impact': str (optional),
                'confidence_score': float (optional),
                'logs': list (optional),
                'monitor_id': str (optional)
            }
        
        Returns:
            Orchestration result with RCA status, alert status, and workflow info
        """
        trace_id = incident_data.get('trace_id', 'unknown')
        logger.info(f"[Orchestrator] Starting workflow for trace {trace_id}")
        
        result = {
            'trace_id': trace_id,
            'timestamp': datetime.utcnow().isoformat(),
            'orchestration_id': f"orch-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{trace_id[:8]}",
            'rca': {'status': 'pending', 'result': None},
            'alerts': {'status': 'pending', 'result': None},
            'remediation': {'status': 'pending', 'result': None},
            'success': False
        }
        
        try:
            # Step 1: Store incident in database
            incident_id = self._store_incident(incident_data)
            result['incident_id'] = incident_id
            
            # Step 2: Generate or use provided RCA
            rca_result = self._handle_rca(incident_data)
            result['rca'] = rca_result
            
            # Step 3: Dispatch alerts
            alert_result = self._dispatch_alerts(incident_data, rca_result)
            result['alerts'] = alert_result
            
            # Step 4: Trigger remediation workflow if confidence is high
            if rca_result.get('confidence_score', 0) >= 0.7:
                remediation_result = self._trigger_remediation(incident_data, rca_result)
                result['remediation'] = remediation_result
            else:
                result['remediation'] = {
                    'status': 'skipped',
                    'reason': 'Confidence below threshold (0.7)'
                }
            
            result['success'] = True
            logger.info(f"[Orchestrator] Workflow completed for trace {trace_id}")
            
        except Exception as e:
            logger.error(f"[Orchestrator] Workflow failed: {e}")
            result['error'] = str(e)
            result['success'] = False
        
        return result
    
    def _store_incident(self, incident_data: Dict[str, Any]) -> Optional[str]:
        """Store incident in database, return incident_id"""
        try:
            import uuid
            from psycopg2.extras import RealDictCursor
            
            incident_id = str(uuid.uuid4())
            trace_id = incident_data.get('trace_id', 'unknown')
            
            with self.db.postgres_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO incidents 
                        (id, trace_id, timestamp, classification, root_cause, 
                         blast_radius, impact, confidence_score, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (trace_id) DO UPDATE SET
                        classification = EXCLUDED.classification,
                        root_cause = EXCLUDED.root_cause,
                        blast_radius = EXCLUDED.blast_radius,
                        impact = EXCLUDED.impact,
                        confidence_score = EXCLUDED.confidence_score,
                        updated_at = NOW()
                    RETURNING id
                    """,
                    (
                        incident_id,
                        trace_id,
                        incident_data.get('timestamp', datetime.utcnow().isoformat()),
                        incident_data.get('classification', 'Unknown'),
                        incident_data.get('root_cause', 'Pending analysis'),
                        incident_data.get('severity', 'MEDIUM'),
                        incident_data.get('impact', 'Assessing impact...'),
                        incident_data.get('confidence_score', 0.0),
                        'active'
                    )
                )
                result = cur.fetchone()
                self.db.postgres_conn.commit()
                
                incident_id = result[0] if result else incident_id
                logger.info(f"[Orchestrator] Incident stored: {incident_id}")
                return incident_id
                
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to store incident: {e}")
            return None
    
    def _handle_rca(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate or use provided RCA"""
        # If RCA is already provided, use it
        if incident_data.get('root_cause') and incident_data.get('confidence_score'):
            return {
                'status': 'provided',
                'classification': incident_data.get('classification'),
                'root_cause': incident_data.get('root_cause'),
                'impact': incident_data.get('impact'),
                'confidence_score': incident_data.get('confidence_score'),
                'blast_radius': incident_data.get('severity', 'MEDIUM')
            }
        
        # If full orchestrator available, use it for RCA
        if self._orchestrator and incident_data.get('logs'):
            try:
                # Trigger async agent run for RCA
                run_id = self._orchestrator.trigger_async(
                    monitor_id=incident_data.get('monitor_id', 'manual'),
                    trace_id=incident_data.get('trace_id'),
                    logs=incident_data.get('logs', []),
                    analysis={'pending': True},
                    github_repo=incident_data.get('github_repo'),
                    github_token=incident_data.get('github_token')
                )
                
                return {
                    'status': 'queued',
                    'run_id': run_id,
                    'message': 'RCA generation queued via agent'
                }
            except Exception as e:
                logger.error(f"[Orchestrator] Agent RCA failed: {e}")
        
        # Fallback: Return pending status
        return {
            'status': 'pending',
            'message': 'RCA not available - no logs or orchestrator unavailable'
        }
    
    def _dispatch_alerts(self, incident_data: Dict[str, Any], rca_result: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch alerts through configured channels"""
        alert_payload = {
            'severity': incident_data.get('severity', 'MEDIUM'),
            'trace_id': incident_data.get('trace_id', 'unknown'),
            'classification': incident_data.get('classification', 'Unknown'),
            'root_cause': rca_result.get('root_cause', incident_data.get('root_cause', 'Analyzing...')),
            'impact': rca_result.get('impact', incident_data.get('impact', 'Assessing...')),
            'confidence_score': rca_result.get('confidence_score', incident_data.get('confidence_score', 0.0)),
            'timestamp': datetime.utcnow().isoformat(),
            'blast_radius': rca_result.get('blast_radius', incident_data.get('severity')),
            'incident_id': incident_data.get('incident_id')
        }
        
        return self.alert_service.send_alert(alert_payload)
    
    def _trigger_remediation(self, incident_data: Dict[str, Any], rca_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger automated remediation workflow"""
        remediation_actions = []
        
        # GitHub PR creation (if orchestrator available)
        if self._orchestrator and incident_data.get('github_repo'):
            try:
                run_id = self._orchestrator.trigger_async(
                    monitor_id=incident_data.get('monitor_id', 'manual'),
                    trace_id=incident_data.get('trace_id'),
                    logs=incident_data.get('logs', []),
                    analysis=rca_result,
                    github_repo=incident_data.get('github_repo'),
                    github_token=incident_data.get('github_token')
                )
                remediation_actions.append({
                    'type': 'github_pr',
                    'status': 'queued',
                    'run_id': run_id
                })
            except Exception as e:
                logger.error(f"[Orchestrator] PR creation failed: {e}")
                remediation_actions.append({
                    'type': 'github_pr',
                    'status': 'failed',
                    'error': str(e)
                })
        
        return {
            'status': 'triggered' if remediation_actions else 'skipped',
            'actions': remediation_actions,
            'confidence_threshold_met': True
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator service status"""
        return {
            'orchestrator_available': self._orchestrator is not None,
            'alert_channels': self.alert_service.get_channel_status(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def test_channels(self) -> Dict[str, Any]:
        """Test all configured alert channels"""
        return self.alert_service.test_channels()
