"""
Base Agent class - all agenets inherit from this
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime

class AgentState(Enum):
    """Agent execution states"""
    IDLE = 'idle'
    PROCESSING = 'processing'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRY = 'retry'

class BaseAgent(ABC):
    """
    Abstract base class for all InsightForge agents.
    
    Each agent must implement:
    - execute(): Main logic
    - validate_input(): Input validation
    
    Provides buit-in:
    - State management
    - Error handling with retry
    - Execution history tracking
    - logging
    """
    def __init__(self, agent_id: str, config: Optional[Dict] = None):
        self.agent_id = agent_id
        self.state = AgentState.IDLE
        self.config = config or {}
        self.logger = self._setup_logger()

        # Execution tracking
        self.execution_history = []
        self.retry_count = 0
        self.max_retries = self.config.get('max_retries', 3)

        # Metrics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.total_execution_time = 0.0

    def _setup_logger(self) -> logging.Logger:
        """Setup agent-specific logger"""
        logger = logging.getLogger(f"Agent.{self.agent_id}")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.agent_id} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution logic - MUST be implemented by each agent
        
        Args:
            input_data: Input parameters for agent
            
        Returns:
            Dict with agent results
        """
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input before processing
        
        Args:
            input_data: Input to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point with error handling and state management
        
        Args:
            input_data: Inpur parameters
        
        Returns:
            Agent execution result with metadata
        """
        start_time = time.time()
        self.state = AgentState.PROCESSING
        self.total_executions += 1

        try:
            # Validate input
            if not self.validate_input(input_data):
                raise ValueError(f"Invalid input for agent {self.agent_id}")
            
            self.logger.info(f"Starting execution with input keys: {list(input_data.keys())}")

            # Execute main logic
            result = await self.execute(input_data)

            # Track success
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            self.successful_executions += 1

            # log execution
            self.execution_history.append({
                'timestamp': datetime.now().isoformat(),
                'input': input_data,
                'output': result,
                'execution_time': round(execution_time, 3),
                'state': 'success'
            })

            self.state = AgentState.SUCCESS
            self.logger.info(f"Execution successful in {execution_time:.2f}s")
            
            return {
                'status': 'success',
                'agent_id': self.agent_id,
                'result': result,
                'execution_time': round(execution_time, 3),
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Execution failed: {str(e)}", exc_info=True)
            
            # Retry logic
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                self.state = AgentState.RETRY
                self.logger.info(f"Retrying... (attempt {self.retry_count}/{self.max_retries})")
                
                # Exponential backoff
                import asyncio
                await asyncio.sleep(2 ** self.retry_count)
                
                return await self.run(input_data)
            
            # Max retries exceeded
            self.failed_executions += 1
            self.state = AgentState.FAILED

            execution_time = time.time() - start_time
            
            self.execution_history.append({
                'timestamp': datetime.now().isoformat(),
                'input': input_data,
                'error': str(e),
                'execution_time': round(execution_time, 3),
                'state': 'failed'
            })
            
            return {
                'status': 'failed',
                'agent_id': self.agent_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'execution_time': round(execution_time, 3),
                'timestamp': datetime.now().isoformat()
            }
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        avg_time = (self.total_execution_time / self.total_execution_time
                    if self.total_executions > 0 else 0)

        success_rate = (self.successful_executions / self.total_executions * 100
                        if self.total_executions > 0 else 0)
        
        return {
            'agent_id': self.agent_id,
            'total_executions': self.total_executions,
            'successful': self.successful_executions,
            'failed': self.failed_executions,
            'success_rate': round(success_rate, 2),
            'avg_execution_time': round(avg_time, 3),
            'total_time': round(self.total_execution_time, 3)
        }
    

    def reset_metrics(self):
        """Reset performance metrics"""
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.total_execution_time = 0.0
        self.execution_history = []
        self.logger.info("Metrics reset")

        


