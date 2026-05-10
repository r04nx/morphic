"""
Agent Orchestrator - Manages concurrent execution of Claude Code Agents
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import json
import logging

from claude_code_agent import ClaudeCodeAgentInvoker
from exceptions import OrchestratorError, RateLimitError, ValidationError
from result_processor import ResultProcessor, ResultAggregator
from models import AgentTask, AgentResult, TaskStatus, TaskPriority


class AgentOrchestrator:
    """Orchestrates concurrent execution of Claude Code Agents"""
    
    def __init__(
        self,
        max_concurrent_tasks: int = 3,
        default_timeout: int = 300,
        result_processor: Optional[ResultProcessor] = None,
        enable_rate_limiting: bool = True,
        rate_limit_per_minute: int = 10
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout
        self.result_processor = result_processor or ResultProcessor()
        self.enable_rate_limiting = enable_rate_limiting
        
        # Task management
        self.tasks: Dict[str, AgentTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: Dict[str, AgentResult] = {}
        
        # Rate limiting
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_timestamps: List[datetime] = []
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Event callbacks
        self.task_callbacks: Dict[str, List[Callable]] = {
            'task_started': [],
            'task_completed': [],
            'task_failed': [],
            'task_retry': []
        }
    
    def add_task(self, task: AgentTask) -> str:
        """Add a task to the orchestration queue"""
        self._validate_task(task)
        task.id = task.id or str(uuid.uuid4())
        self.tasks[task.id] = task
        self.task_queue.put_nowait(task)
        
        self.logger.info(f"Task {task.id} ({task.name}) added to queue")
        return task.id
    
    def add_rca_task(
        self,
        name: str,
        project_dir: str,
        system_prompt: str,
        log_input: str,
        custom_prompt: Optional[str] = None,
        priority: TaskPriority = TaskPriority.HIGH,
        **kwargs
    ) -> str:
        """Convenience method to add RCA task"""
        task = AgentTask(
            name=name,
            description=f"RCA analysis for {name}",
            task_type="rca",
            project_dir=project_dir,
            system_prompt=system_prompt,
            log_input=log_input,
            custom_prompt=custom_prompt,
            priority=priority,
            **kwargs
        )
        return self.add_task(task)
    
    def add_code_review_task(
        self,
        name: str,
        project_dir: str,
        system_prompt: str,
        task_prompt: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        **kwargs
    ) -> str:
        """Convenience method to add code review task"""
        task = AgentTask(
            name=name,
            description=f"Code review for {name}",
            task_type="code_review",
            project_dir=project_dir,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            priority=priority,
            **kwargs
        )
        return self.add_task(task)
    
    async def start(self):
        """Start the orchestrator and begin processing tasks"""
        self.logger.info("Starting agent orchestrator")
        
        # Start worker tasks
        workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.max_concurrent_tasks)
        ]
        
        # Start rate limit cleaner
        if self.enable_rate_limiting:
            rate_limit_cleaner = asyncio.create_task(self._rate_limit_cleaner())
            workers.append(rate_limit_cleaner)
        
        try:
            await asyncio.gather(*workers)
        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            raise OrchestratorError(f"Orchestrator failed: {e}")
    
    async def stop(self, timeout: int = 30):
        """Stop the orchestrator gracefully"""
        self.logger.info("Stopping agent orchestrator")
        
        # Cancel running tasks
        for task_id, task in self.running_tasks.items():
            task.cancel()
            self.tasks[task_id].status = TaskStatus.CANCELLED
        
        # Wait for tasks to complete
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.running_tasks.values(), return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self.logger.warning("Some tasks did not complete within timeout")
    
    async def get_task_status(self, task_id: str) -> Optional[AgentTask]:
        """Get current status of a specific task"""
        return self.tasks.get(task_id)
    
    async def get_task_result(self, task_id: str) -> Optional[AgentResult]:
        """Get result of a completed task"""
        return self.completed_tasks.get(task_id)
    
    async def wait_for_task(self, task_id: str, timeout: Optional[int] = None) -> AgentResult:
        """Wait for a specific task to complete"""
        start_time = datetime.now()
        timeout = timeout or self.default_timeout
        
        while task_id not in self.completed_tasks:
            if (datetime.now() - start_time).seconds > timeout:
                raise OrchestratorError(f"Task {task_id} timed out")
            
            await asyncio.sleep(1)
        
        return self.completed_tasks[task_id]
    
    async def wait_for_all_tasks(self, timeout: Optional[int] = None) -> Dict[str, AgentResult]:
        """Wait for all tasks to complete"""
        start_time = datetime.now()
        timeout = timeout or 600  # 10 minutes default
        
        while len(self.completed_tasks) < len(self.tasks):
            if (datetime.now() - start_time).seconds > timeout:
                raise OrchestratorError("Wait for all tasks timed out")
            
            await asyncio.sleep(1)
        
        return self.completed_tasks.copy()
    
    def add_callback(self, event: str, callback: Callable):
        """Add event callback"""
        if event in self.task_callbacks:
            self.task_callbacks[event].append(callback)
    
    async def _worker(self, worker_name: str):
        """Worker task that processes tasks from queue"""
        self.logger.info(f"Worker {worker_name} started")
        
        while True:
            try:
                # Get task from queue
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # Check rate limiting
                if self.enable_rate_limiting and not self._check_rate_limit():
                    await asyncio.sleep(60)  # Wait 1 minute
                    continue
                
                # Execute task
                await self._execute_task(task, worker_name)
                
            except asyncio.TimeoutError:
                continue  # No task available, continue
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
    
    async def _execute_task(self, task: AgentTask, worker_name: str):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running_tasks[task.id] = asyncio.current_task()
        
        self.logger.info(f"Worker {worker_name} executing task {task.id} ({task.name})")
        await self._trigger_callbacks('task_started', task)
        
        try:
            # Create agent invoker
            invoker = ClaudeCodeAgentInvoker(
                task.project_dir,
                task.system_prompt,
                log_dir=f"agent_logs/{task.id}"
            )
            
            # Execute based on task type
            start_time = datetime.now()
            
            if task.task_type == "rca":
                result_data = await invoker.perform_rca(
                    task.log_input,
                    task.custom_prompt
                )
            elif task.task_type == "code_review":
                result_data = await invoker.execute_task(task.task_prompt)
            else:
                result_data = await invoker.execute_task(task.task_prompt)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = AgentResult(
                task_id=task.id,
                success=result_data.get('success', False),
                data=result_data,
                execution_time=execution_time,
                error=result_data.get('error'),
                confidence_score=self._extract_confidence_score(result_data)
            )
            
            task.result = result
            task.completed_at = datetime.now()
            task.status = TaskStatus.COMPLETED
            
            self.completed_tasks[task.id] = result
            
            # Process result
            if self.result_processor:
                await self.result_processor.process_result(result)
            
            self.logger.info(f"Task {task.id} completed successfully")
            await self._trigger_callbacks('task_completed', task, result)
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                self.task_queue.put_nowait(task)
                
                self.logger.warning(f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries})")
                await self._trigger_callbacks('task_retry', task, e)
            else:
                # Create failed result
                result = AgentResult(
                    task_id=task.id,
                    success=False,
                    data={},
                    execution_time=0,
                    error=str(e)
                )
                
                task.result = result
                self.completed_tasks[task.id] = result
                
                self.logger.error(f"Task {task.id} failed permanently: {e}")
                await self._trigger_callbacks('task_failed', task, e)
        
        finally:
            self.running_tasks.pop(task.id, None)
    
    async def _rate_limit_cleaner(self):
        """Clean up old rate limit timestamps"""
        while True:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)
            
            # Remove timestamps older than 1 minute
            self.request_timestamps = [
                ts for ts in self.request_timestamps 
                if ts > cutoff
            ]
            
            await asyncio.sleep(10)  # Clean every 10 seconds
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        if not self.enable_rate_limiting:
            return True
        
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Count recent requests
        recent_requests = sum(
            1 for ts in self.request_timestamps 
            if ts > cutoff
        )
        
        if recent_requests >= self.rate_limit_per_minute:
            return False
        
        # Add current request
        self.request_timestamps.append(now)
        return True
    
    def _validate_task(self, task: AgentTask):
        """Validate task configuration"""
        if not task.name:
            raise ValidationError("Task name is required")
        
        if not task.project_dir:
            raise ValidationError("Project directory is required")
        
        if not task.system_prompt:
            raise ValidationError("System prompt is required")
        
        if task.task_type == "rca" and not task.log_input:
            raise ValidationError("Log input is required for RCA tasks")
        
        if task.task_type in ["general", "code_review"] and not task.task_prompt:
            raise ValidationError("Task prompt is required for this task type")
    
    def _extract_confidence_score(self, result_data: Dict[str, Any]) -> float:
        """Extract confidence score from agent result"""
        if isinstance(result_data, dict):
            return float(result_data.get('confidence_score', 0.0))
        return 0.0
    
    async def _trigger_callbacks(self, event: str, *args):
        """Trigger event callbacks"""
        for callback in self.task_callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
            except Exception as e:
                self.logger.error(f"Callback error for {event}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestration statistics"""
        total_tasks = len(self.tasks)
        completed_tasks = len([
            t for t in self.tasks.values() 
            if t.status == TaskStatus.COMPLETED
        ])
        failed_tasks = len([
            t for t in self.tasks.values() 
            if t.status == TaskStatus.FAILED
        ])
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'running_tasks': len(self.running_tasks),
            'queued_tasks': self.task_queue.qsize(),
            'success_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'average_execution_time': self._calculate_avg_execution_time()
        }
    
    def _calculate_avg_execution_time(self) -> float:
        """Calculate average execution time for completed tasks"""
        completed_results = [
            r for r in self.completed_tasks.values() 
            if r.success
        ]
        
        if not completed_results:
            return 0.0
        
        total_time = sum(r.execution_time for r in completed_results)
        return total_time / len(completed_results)
