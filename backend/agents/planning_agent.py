"""
Planning Agent - The orchestrator
Creates multi step execution plans for complex queries
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from openai import AsyncOpenAI
import json

class PlanningAgent(BaseAgent):
    """
    THe brain of InsightForge - decides what need to be done and in what order
    
    Responsibilietis:
    1. Analyzed parsed query requirements
    2. Determine which agents are needed
    3. Create step-by-step execution plan
    4. Identify dependencies betweens steps
    5. Find parallel execution opportunities
    """

    def __init__(self, openai_api_key: str, config: Optional[Dict] = None):
        super().__init__("planning", config)
        self.client = AsyncOpenAI(api_key=openai_api_key)

        # Available agents this orchestrator can call
        self.available_agents = {
            'sql_generation': {
                'description': 'Generates and executes SQL queries on the database',
                'capabilities': ['fetch_data', 'aggregate', 'filter', 'join'],
                'input': 'metrics, dimensions, filters, time_period',
                'output': 'query resu;ts (rows of data)'
            },
            'calculation':{
                'description': 'Performs mathematical and statistical analysis',
                'capabilities': ['compare', 'trend_analysis', 'correlation', 'forecast'],
                'input': 'numerical data, comparison_type',
                'output': 'calculated results, statistical significance'
            },
            'context': {
                'description': 'Searches for external factors and historical context',
                'capabilities': ['web_search', 'knowledge_base_search', 'event_lookup'],
                'input': 'keywords, time_range',
                'output': 'relevant context, external factors'
            },
            'synthesis': {
                'description': 'Combines results into executive insights',
                'capabilities': ['summarize', 'generate_report', 'create_recommendations'],
                'input': 'all_results',
                'output': 'executive summary, visualizations'
            }
        }
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate we have a parsed query"""
        return (
            isinstance(input_data, dict) and
            'parsed_query' in input_data and
            isinstance(input_data['parsed_query'], dict)
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution plan based on query requirements"""

        parsed_query = input_data['parsed_query']
        query_type = parsed_query.get('query_type')

        self.logger.info(f"Creating plan for query_type: {query_type}")

        # For Week 2, we'll create simple plans
        # Week 3+ will use LLM for complex planning

        if query_type == 'simple_lookup':
            plan = self._create_simple_lookup_plan(parsed_query)
        elif query_type == 'comparison':
            plan = self._create_comparison_plan(parsed_query)
        elif query_type == 'root_cause_analysis':
            plan = self._create_root_cause_plan(parsed_query)
        elif query_type == 'trend_analysis':
            plan = self._create_trend_plan(parsed_query)
        else:
            # Fallback: use LLM for complex cases
            plan = await self._create_llm_plan(parsed_query)

        # Validate plan
        validated_plan = self._validate_plan(plan)
        
        self.logger.info(f"Created plan with {len(validated_plan['steps'])} steps")
        
        return {
            'plan': validated_plan,
            'estimated_time': self._estimate_execution_time(validated_plan)
        }
    
    def _create_simple_lookup_plan(self, query: Dict) -> Dict:
        """Plan for simple data lookup"""
        return {
            'plan_id': self._generate_plan_id(),
            'query_type': 'simple_lookup',
            'steps': [
                {
                    'step': 1,
                    'agent': 'sql_generation',
                    'task': 'fetch_data',
                    'params': {
                        'metrics': query.get('metrics', []),
                        'dimensions': query.get('dimensions', []),
                        'time_period': query.get('time_period'),
                        'filters': query.get('filters', {})
                    },
                    'dependencies': [],
                    'critical': True
                }
            ],
            'parallel_groups': []
        }
    
    def _create_comparison_plan(self, query: Dict) -> Dict:
        """Plan for comparing two periods"""
        return {
            'plan_id': self._generate_plan_id(),
            'query_type': 'comparison',
            'steps': [
                {
                    'step': 1,
                    'agent': 'sql_generation',
                    'task': 'fetch_data',
                    'params': {
                        'metrics': query.get('metrics', []),
                        'time_period': query.get('time_period'),
                        'label': 'current_period'
                    },
                    'dependencies': []
                },
                {
                    'step': 2,
                    'agent': 'sql_generation',
                    'task': 'fetch_data',
                    'params': {
                        'metrics': query.get('metrics', []),
                        'time_period': query.get('comparison_period'),
                        'label': 'comparison_period'
                    },
                    'dependencies': []
                },
                {
                    'step': 3,
                    'agent': 'calculation',
                    'task': 'compare_periods',
                    'params': {
                        'comparison_type': 'percentage_change'
                    },
                    'dependencies': [1, 2],
                    'critical': True
                }
            ],
            'parallel_groups': [[1, 2]]  # Steps 1 and 2 can run in parallel
        }

    def _create_root_cause_plan(self, query: Dict) -> Dict:
        """Plan for root cause analysis"""
        return {
            'plan_id': self._generate_plan_id(),
            'query_type': 'root_cause_analysis',
            'steps': [
                {
                    'step': 1,
                    'agent': 'sql_generation',
                    'task': 'fetch_data',
                    'params': {
                        'metrics': query.get('metrics', []),
                        'time_period': query.get('time_period')
                    },
                    'dependencies': []
                },
                {
                    'step': 2,
                    'agent': 'sql_generation',
                    'task': 'fetch_data',
                    'params': {
                        'metrics': query.get('metrics', []),
                        'time_period': query.get('comparison_period')
                    },
                    'dependencies': []
                },
                {
                    'step': 3,
                    'agent': 'sql_generation',
                    'task': 'breakdown_by_dimensions',
                    'params': {
                        'metrics': query.get('metrics', []),
                        'dimensions': query.get('dimensions', ['product_category', 'region']),
                        'time_period': query.get('time_period')
                    },
                    'dependencies': [1]
                },
                {
                    'step': 4,
                    'agent': 'calculation',
                    'task': 'identify_biggest_changes',
                    'params': {},
                    'dependencies': [1, 2, 3],
                    'critical': True
                }
            ],
            'parallel_groups': [[1, 2]]
        }
    
    async def _create_llm_plan(self, query: Dict) -> Dict:
        """Use LLM to create plan for complex queries"""
        
        prompt = f"""You are a workflow planner for business intelligence analysis.

Available agents:
{json.dumps(self.available_agents, indent=2)}

Query requirements:
{json.dumps(query, indent=2)}

Create a step-by-step execution plan. Output JSON:
{{
  "plan_id": "unique_id",
  "query_type": "{query.get('query_type')}",
  "steps": [
    {{
      "step": 1,
      "agent": "agent_name",
      "task": "task_description",
      "params": {{}},
      "dependencies": []
    }}
  ],
  "parallel_groups": [[step_numbers_that_can_run_together]]
}}

Rules:
1. Each step uses ONE agent
2. Dependencies = list of step numbers that must complete first
3. Identify parallel opportunities
4. Mark critical steps (must succeed)
"""
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        plan = json.loads(response.choices[0].message.content)
        return plan
    
    def _validate_plan(self, plan: Dict) -> Dict:
        """Validate plan structure and dependencies"""
        
        steps = plan.get('steps', [])
        
        # Check each step has required fields
        for step in steps:
            if 'step' not in step or 'agent' not in step or 'task' not in step:
                raise ValueError(f"Invalid step structure: {step}")
            
            # Check agent exists
            if step['agent'] not in self.available_agents:
                raise ValueError(f"Unknown agent: {step['agent']}")
            
            # Check dependencies are valid
            for dep in step.get('dependencies', []):
                if dep >= step['step']:
                    raise ValueError(f"Step {step['step']} cannot depend on future step {dep}")
        
        # Check for circular dependencies (simple check)
        if self._has_circular_dependencies(steps):
            raise ValueError("Circular dependencies detected in plan")
        
        return plan
    
    def _has_circular_dependencies(self, steps: List[Dict]) -> bool:
        """Simple cycle detection"""
        # For Week 2, simple check
        # Week 3+ will implement proper DFS
        
        for step in steps:
            deps = step.get('dependencies', [])
            if step['step'] in deps:
                return True  # Self-dependency
        
        return False
    
    def _estimate_execution_time(self, plan: Dict) -> float:
        """Estimate total execution time"""
        
        # Simple estimation (Week 2)
        # Week 3+ will use actual agent metrics
        
        time_estimates = {
            'sql_generation': 2.0,  # seconds
            'calculation': 0.5,
            'context': 3.0,
            'synthesis': 2.0
        }

        total_time = 0
        for step in plan.get('steps', []):
            agent = step['agent']
            total_time += time_estimates.get(agent, 1.0)
        
        # Account for parallel execution
        parallel_groups = plan.get('parallel_groups', [])
        if parallel_groups:
            # Rough reduction for parallelism
            total_time *= 0.7
        
        return round(total_time, 1)
    
    def _generate_plan_id(self) -> str:
        """Generate unique plan ID"""
        import uuid
        return f"plan_{uuid.uuid4().hex[:8]}"