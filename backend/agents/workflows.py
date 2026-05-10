"""
Predefined workflows for common agent tasks
"""

import asyncio
from typing import Dict, List, Any, Optional
from agent_orchestrator import AgentOrchestrator
from models import AgentTask, TaskPriority
from exceptions import WorkflowError


class BaseWorkflow:
    """Base class for agent workflows"""
    
    def __init__(self, orchestrator: AgentOrchestrator):
        self.orchestrator = orchestrator
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the workflow - must be implemented by subclasses"""
        raise NotImplementedError


class RCAWorkflow(BaseWorkflow):
    """Root Cause Analysis workflow"""
    
    async def execute(
        self,
        project_dir: str,
        system_prompt: str,
        log_inputs: List[str],
        custom_prompts: Optional[List[str]] = None,
        concurrent: bool = True
    ) -> Dict[str, Any]:
        """Execute RCA workflow on multiple log sources"""
        
        if not log_inputs:
            raise WorkflowError("At least one log input is required")
        
        custom_prompts = custom_prompts or [None] * len(log_inputs)
        
        if concurrent:
            return await self._execute_concurrent(
                project_dir, system_prompt, log_inputs, custom_prompts
            )
        else:
            return await self._execute_sequential(
                project_dir, system_prompt, log_inputs, custom_prompts
            )
    
    async def _execute_concurrent(
        self,
        project_dir: str,
        system_prompt: str,
        log_inputs: List[str],
        custom_prompts: List[Optional[str]]
    ) -> Dict[str, Any]:
        """Execute RCA tasks concurrently"""
        
        task_ids = []
        for i, (log_input, custom_prompt) in enumerate(zip(log_inputs, custom_prompts)):
            task_id = self.orchestrator.add_rca_task(
                name=f"rca-task-{i+1}",
                project_dir=project_dir,
                system_prompt=system_prompt,
                log_input=log_input,
                custom_prompt=custom_prompt,
                priority=TaskPriority.HIGH
            )
            task_ids.append(task_id)
        
        # Wait for all tasks to complete
        results = await self.orchestrator.wait_for_all_tasks()
        
        return {
            'workflow_type': 'concurrent_rca',
            'task_ids': task_ids,
            'results': {tid: results[tid] for tid in task_ids if tid in results},
            'total_tasks': len(task_ids),
            'successful_tasks': len([r for r in results.values() if r.success])
        }
    
    async def _execute_sequential(
        self,
        project_dir: str,
        system_prompt: str,
        log_inputs: List[str],
        custom_prompts: List[Optional[str]]
    ) -> Dict[str, Any]:
        """Execute RCA tasks sequentially"""
        
        task_ids = []
        results = {}
        
        for i, (log_input, custom_prompt) in enumerate(zip(log_inputs, custom_prompts)):
            task_id = self.orchestrator.add_rca_task(
                name=f"rca-task-{i+1}",
                project_dir=project_dir,
                system_prompt=system_prompt,
                log_input=log_input,
                custom_prompt=custom_prompt,
                priority=TaskPriority.HIGH
            )
            
            # Wait for this task before starting next
            result = await self.orchestrator.wait_for_task(task_id)
            results[task_id] = result
            task_ids.append(task_id)
        
        return {
            'workflow_type': 'sequential_rca',
            'task_ids': task_ids,
            'results': results,
            'total_tasks': len(task_ids),
            'successful_tasks': len([r for r in results.values() if r.success])
        }


class CodeReviewWorkflow(BaseWorkflow):
    """Code review workflow"""
    
    async def execute(
        self,
        project_dir: str,
        system_prompt: str,
        review_tasks: List[Dict[str, str]],
        concurrent: bool = True
    ) -> Dict[str, Any]:
        """
        Execute code review workflow
        
        Args:
            project_dir: Directory to review
            system_prompt: System prompt for code review
            review_tasks: List of {'name': str, 'prompt': str} tasks
            concurrent: Whether to run reviews concurrently
        """
        
        if not review_tasks:
            raise WorkflowError("At least one review task is required")
        
        if concurrent:
            return await self._execute_concurrent(
                project_dir, system_prompt, review_tasks
            )
        else:
            return await self._execute_sequential(
                project_dir, system_prompt, review_tasks
            )
    
    async def _execute_concurrent(
        self,
        project_dir: str,
        system_prompt: str,
        review_tasks: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Execute code review tasks concurrently"""
        
        task_ids = []
        for task in review_tasks:
            task_id = self.orchestrator.add_code_review_task(
                name=task['name'],
                project_dir=project_dir,
                system_prompt=system_prompt,
                task_prompt=task['prompt'],
                priority=TaskPriority.MEDIUM
            )
            task_ids.append(task_id)
        
        # Wait for all tasks to complete
        results = await self.orchestrator.wait_for_all_tasks()
        
        return {
            'workflow_type': 'concurrent_code_review',
            'task_ids': task_ids,
            'results': {tid: results[tid] for tid in task_ids if tid in results},
            'total_tasks': len(task_ids),
            'successful_tasks': len([r for r in results.values() if r.success])
        }
    
    async def _execute_sequential(
        self,
        project_dir: str,
        system_prompt: str,
        review_tasks: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Execute code review tasks sequentially"""
        
        task_ids = []
        results = {}
        
        for task in review_tasks:
            task_id = self.orchestrator.add_code_review_task(
                name=task['name'],
                project_dir=project_dir,
                system_prompt=system_prompt,
                task_prompt=task['prompt'],
                priority=TaskPriority.MEDIUM
            )
            
            # Wait for this task before starting next
            result = await self.orchestrator.wait_for_task(task_id)
            results[task_id] = result
            task_ids.append(task_id)
        
        return {
            'workflow_type': 'sequential_code_review',
            'task_ids': task_ids,
            'results': results,
            'total_tasks': len(task_ids),
            'successful_tasks': len([r for r in results.values() if r.success])
        }


class SecurityAnalysisWorkflow(BaseWorkflow):
    """Security analysis workflow"""
    
    async def execute(
        self,
        project_dir: str,
        system_prompt: str,
        security_tasks: List[Dict[str, Any]],
        concurrent: bool = True
    ) -> Dict[str, Any]:
        """
        Execute security analysis workflow
        
        Args:
            project_dir: Directory to analyze
            system_prompt: Security-focused system prompt
            security_tasks: List of security analysis tasks
            concurrent: Whether to run analyses concurrently
        """
        
        if not security_tasks:
            raise WorkflowError("At least one security task is required")
        
        if concurrent:
            return await self._execute_concurrent(
                project_dir, system_prompt, security_tasks
            )
        else:
            return await self._execute_sequential(
                project_dir, system_prompt, security_tasks
            )
    
    async def _execute_concurrent(
        self,
        project_dir: str,
        system_prompt: str,
        security_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute security analysis tasks concurrently"""
        
        task_ids = []
        for task in security_tasks:
            task_id = self.orchestrator.add_task(
                AgentTask(
                    name=task['name'],
                    description=f"Security analysis: {task['name']}",
                    task_type="security",
                    project_dir=project_dir,
                    system_prompt=system_prompt,
                    task_prompt=task.get('prompt', ''),
                    log_input=task.get('log_input'),
                    priority=TaskPriority.CRITICAL if task.get('critical') else TaskPriority.HIGH,
                    metadata=task.get('metadata', {})
                )
            )
            task_ids.append(task_id)
        
        # Wait for all tasks to complete
        results = await self.orchestrator.wait_for_all_tasks()
        
        return {
            'workflow_type': 'concurrent_security_analysis',
            'task_ids': task_ids,
            'results': {tid: results[tid] for tid in task_ids if tid in results},
            'total_tasks': len(task_ids),
            'successful_tasks': len([r for r in results.values() if r.success])
        }
    
    async def _execute_sequential(
        self,
        project_dir: str,
        system_prompt: str,
        security_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute security analysis tasks sequentially"""
        
        task_ids = []
        results = {}
        
        for task in security_tasks:
            agent_task = AgentTask(
                name=task['name'],
                description=f"Security analysis: {task['name']}",
                task_type="security",
                project_dir=project_dir,
                system_prompt=system_prompt,
                task_prompt=task.get('prompt', ''),
                log_input=task.get('log_input'),
                priority=TaskPriority.CRITICAL if task.get('critical') else TaskPriority.HIGH,
                metadata=task.get('metadata', {})
            )
            
            task_id = self.orchestrator.add_task(agent_task)
            
            # Wait for this task before starting next
            result = await self.orchestrator.wait_for_task(task_id)
            results[task_id] = result
            task_ids.append(task_id)
        
        return {
            'workflow_type': 'sequential_security_analysis',
            'task_ids': task_ids,
            'results': results,
            'total_tasks': len(task_ids),
            'successful_tasks': len([r for r in results.values() if r.success])
        }


class IncidentResponseWorkflow(BaseWorkflow):
    """Incident response workflow combining RCA and remediation"""
    
    async def execute(
        self,
        project_dir: str,
        system_prompt: str,
        incident_data: Dict[str, Any],
        phases: List[str] = None
    ) -> Dict[str, Any]:
        """
        Execute incident response workflow
        
        Args:
            project_dir: Project directory
            system_prompt: Incident response system prompt
            incident_data: Incident information including logs, context, etc.
            phases: List of phases to execute ['triage', 'rca', 'remediation', 'prevention']
        """
        
        phases = phases or ['triage', 'rca', 'remediation']
        phase_results = {}
        
        for phase in phases:
            try:
                if phase == 'triage':
                    phase_results[phase] = await self._execute_triage(
                        project_dir, system_prompt, incident_data
                    )
                elif phase == 'rca':
                    phase_results[phase] = await self._execute_rca_phase(
                        project_dir, system_prompt, incident_data
                    )
                elif phase == 'remediation':
                    phase_results[phase] = await self._execute_remediation(
                        project_dir, system_prompt, incident_data, phase_results.get('rca', {})
                    )
                elif phase == 'prevention':
                    phase_results[phase] = await self._execute_prevention(
                        project_dir, system_prompt, incident_data, phase_results
                    )
                
            except Exception as e:
                phase_results[phase] = {
                    'success': False,
                    'error': str(e)
                }
        
        return {
            'workflow_type': 'incident_response',
            'incident_data': incident_data,
            'phases_executed': phases,
            'phase_results': phase_results,
            'overall_success': all(
                result.get('success', False) for result in phase_results.values()
            )
        }
    
    async def _execute_triage(
        self, project_dir: str, system_prompt: str, incident_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute triage phase"""
        
        triage_prompt = f"""
        Perform incident triage for the following incident:
        
        Incident Data: {incident_data}
        
        Provide:
        1. Severity assessment (LOW/MEDIUM/HIGH/CRITICAL)
        2. Blast radius estimation
        3. Immediate impact assessment
        4. Urgency level
        5. Recommended immediate actions
        """
        
        task_id = self.orchestrator.add_task(
            AgentTask(
                name="incident-triage",
                description="Incident triage and severity assessment",
                task_type="triage",
                project_dir=project_dir,
                system_prompt=system_prompt,
                task_prompt=triage_prompt,
                priority=TaskPriority.CRITICAL
            )
        )
        
        result = await self.orchestrator.wait_for_task(task_id)
        return {
            'success': result.success,
            'result': result.data,
            'execution_time': result.execution_time
        }
    
    async def _execute_rca_phase(
        self, project_dir: str, system_prompt: str, incident_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute RCA phase"""
        
        log_input = incident_data.get('logs', '')
        custom_prompt = f"""
        Incident Context: {incident_data.get('context', '')}
        Triage Results: {incident_data.get('triage_results', '')}
        """
        
        task_id = self.orchestrator.add_rca_task(
            name="incident-rca",
            project_dir=project_dir,
            system_prompt=system_prompt,
            log_input=log_input,
            custom_prompt=custom_prompt,
            priority=TaskPriority.HIGH
        )
        
        result = await self.orchestrator.wait_for_task(task_id)
        return {
            'success': result.success,
            'result': result.data,
            'execution_time': result.execution_time
        }
    
    async def _execute_remediation(
        self,
        project_dir: str,
        system_prompt: str,
        incident_data: Dict[str, Any],
        rca_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute remediation phase"""
        
        remediation_prompt = f"""
        Based on the following incident analysis, generate remediation actions:
        
        Incident Data: {incident_data}
        RCA Results: {rca_results.get('result', {})}
        
        Provide:
        1. Immediate containment actions
        2. Code fixes and patches
        3. Configuration changes needed
        4. Rollback procedures if needed
        5. Validation steps
        """
        
        task_id = self.orchestrator.add_task(
            AgentTask(
                name="incident-remediation",
                description="Generate remediation actions",
                task_type="remediation",
                project_dir=project_dir,
                system_prompt=system_prompt,
                task_prompt=remediation_prompt,
                priority=TaskPriority.HIGH
            )
        )
        
        result = await self.orchestrator.wait_for_task(task_id)
        return {
            'success': result.success,
            'result': result.data,
            'execution_time': result.execution_time
        }
    
    async def _execute_prevention(
        self,
        project_dir: str,
        system_prompt: str,
        incident_data: Dict[str, Any],
        phase_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute prevention phase"""
        
        prevention_prompt = f"""
        Based on the complete incident analysis, generate prevention measures:
        
        Incident Data: {incident_data}
        All Phase Results: {phase_results}
        
        Provide:
        1. Monitoring improvements
        2. Alerting enhancements
        3. Process changes
        4. Architecture improvements
        5. Training recommendations
        """
        
        task_id = self.orchestrator.add_task(
            AgentTask(
                name="incident-prevention",
                description="Generate prevention measures",
                task_type="prevention",
                project_dir=project_dir,
                system_prompt=system_prompt,
                task_prompt=prevention_prompt,
                priority=TaskPriority.MEDIUM
            )
        )
        
        result = await self.orchestrator.wait_for_task(task_id)
        return {
            'success': result.success,
            'result': result.data,
            'execution_time': result.execution_time
        }
