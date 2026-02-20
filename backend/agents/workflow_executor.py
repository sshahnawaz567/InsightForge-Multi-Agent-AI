"""
Workflow Executor
Executes multi-step plans created by Planning Agent

Handles:
- Sequential execution (step dependencies)
- Parallel execution (independent steps)
- Error recovery (retry, skip, fallback)
- State tracking (what's done, what failed)
"""
from typing import Dict, Any, List, Optional
import asyncio
import time
from datetime import datetime
from collections import defaultdict

class WorkflowExecutor:
    """
    Execture agent workflow with dependency management
    
    Example wrofklow:
    Step 1: Fetch current data    }
    Step 2: Fetch comparison data  } → Run in parallel
    Step 3: Calculate change (depends on 1,2)
    Step 4: Generate report (depends on 3)
    """

    def __init__(self, agent_registry: Dict):
        """
        Args:
            agent_registry: Dict mapping agent_id → agent instance
                           e.g., {'sql_generation': sql_agent, ...}
        """
        self.agents = agent_registry
        self.execution_history = []

    async def execute(self, plan: Dict) -> Dict[str, Any]:
        """
        Execute entire workflow
        
        Args:
            plan: Execution plan from planning Agent
            
        Returns:
            Dict with step results and final output
        """
        plan_id = plan.get('plan_id')
        steps = plan.get('steps', [])
        
        print(f"\n🚀 Executing workflow: {plan_id}")
        print(f"   Total steps: {len(steps)}")
        
        start_time = time.time()
        
        # Track results by step number
        step_results = {}
        
        # Sort steps by dependencie (topological sort)
        sorted_steps = self._topological_sort(steps)

        # Execute in order
        for step in sorted_steps:
            step_num = step['step']
            
            print(f"\n   Step {step_num}/{len(steps)}: {step['agent']} → {step['task']}")
            
            # Check dependencies completed successfully
            deps_ok = self._check_dependencies(step, step_results)
            
            if not deps_ok:
                print(f"   ⏭️  Skipped (dependency failed)")
                step_results[step_num] = {
                    'status': 'skipped',
                    'reason': 'dependency_failed'
                }
                continue

            # Execute step
            try:
                result = await self._execute_step(step, step_results)
                step_results[step_num] = result

                if result['status'] == 'success':
                     print(f"   ✅ Completed in {result['execution_time']}s")
                else:
                    print(f"   ❌ Failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
                step_results[step_num] = {
                    'status': 'failed',
                    'error': str(e)
                }

        # Calculate total time
        total_time = time.time() - start_time

        # check if workflow succeeded
        success = all(
            r.get('status') == 'success' 
            for r in step_results.values()
            if r.get('status') != 'skipped'
        )
        
        result = {
            'plan_id': plan_id,
            'success': success,
            'step_results': step_results,
            'total_steps': len(steps),
            'completed_steps': sum(1 for r in step_results.values() if r.get('status') == 'success'),
            'failed_steps': sum(1 for r in step_results.values() if r.get('status') == 'failed'),
            'skipped_steps': sum(1 for r in step_results.values() if r.get('status') == 'skipped'),
            'execution_time': round(total_time, 2)
        }
        
        print(f"\n{'='*60}")
        print(f"✅ Workflow completed in {total_time:.1f}s")
        print(f"   Success: {result['completed_steps']}/{len(steps)} steps")
        print(f"{'='*60}\n")
        
        return result
    
    def _check_dependencies(
        self,
        step: Dict,
        step_results: Dict
    ) -> bool:
        """Check if all dependencies completed successfully"""
        dependencies = step.get('dependencies', [])

        for dep_num in dependencies:
            if dep_num not in step_results:
                return False
            
            dep_result = step_results[dep_num]
            if dep_result.get('status') != 'success':
                return False
        
        return True
    
    async def _execute_step(
        self,
        step: Dict,
        step_results: Dict
    ) -> Dict[str, Any]:
        """Execute a single step"""

        agent_id = step['agent']
        task = step['task']
        params = step.get('params', {})

        # GEt agent instance
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        
        # Prepare input (include dependency results)
        dependency_results = {}
        for dep_num in step.get('dependencies', []):
            dependency_results[dep_num] = step_results[dep_num]
        
        agent_input = {
            'task': task,
            'params': params,
            'dependency_results': dependency_results
        }
        
        # Execute agent
        result = await agent.run(agent_input)
        
        return result
    

    def _topological_sort(self, steps: List[Dict]) -> List[Dict]:
        """
        Sort steps by dependencie (Kahn's algorithm)
        
        Ensures steps run in correct order
        """

        # Build adjacency list
        in_degree = {s['step']: 0 for s in steps}
        graph = defaultdict(list)
        
        for step in steps:
            for dep in step.get('dependencies', []):
                graph[dep].append(step['step'])
                in_degree[step['step']] += 1
        
        # Find steps with no dependencies
        queue = [s for s in in_degree if in_degree[s] == 0]
        sorted_steps = []

        while queue:
            # Process step with no remaining dependencies
            step_num = queue.pop(0)
            step = next(s for s in steps if s['step'] == step_num)
            sorted_steps.append(step)
            
            # Reduce in-degree for dependent steps
            for neighbor in graph[step_num]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(sorted_steps) != len(steps):
            raise ValueError("Circular dependency detected in workflow")
        
        return sorted_steps


