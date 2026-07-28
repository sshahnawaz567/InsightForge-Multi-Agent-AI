"""
LangGraph Workflow
Orchestrates all agents using graph-based state machine

Visual workflow:
    User Query
        ↓
    Query Understanding
        ↓
    Planning
        ↓
    ┌─────┴─────┐
    SQL      Context (parallel)
    └─────┬─────┘
        ↓
    Calculation
        ↓
    Synthesis
        ↓
    Final Answer
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any, Optional
import asyncio
import time
import uuid
from datetime import datetime

#Import agents
from .query_understanding_agent import QueryUnderstandingAgent
from .planning_agent import PlanningAgent
from .sql_generation_agent import SQLGenerationAgent
from .calculation_agent import CalculationAgent
from .context_agent import ContextAgent
from .synthesis_agent import SynthesisAgent
from .state_schema import AgentState

class InsightForgeWorkflow:
    """
    LangGraph-powered autonomous workflow
    
    Benefits over manual executor:
    - Visual graph representation
    - Built-in state management
    - Conditional routing
    - Error recovery
    - Streaming support
    """

    def __init__(
        self,
        openai_api_key: str,
        database_url: str
    ):
        self.openai_api_key= openai_api_key
        self.database_url = database_url

        #Intialize all agents
        self.agents = self._initialize_agents()

        # Bui;d graph
        self.workflow = self._build_graph()

        # In-memory checkpointer: keeps per-session state (conversation_history)
        # alive between calls to run() that share the same session_id, so
        # follow-up questions like "why did that happen" have context.
        # Process-lifetime only - swap for a SqliteSaver/PostgresSaver to
        # survive restarts.
        self.checkpointer = MemorySaver()

        # Compile into runnable app
        self.app = self.workflow.compile(checkpointer=self.checkpointer)

    def _initialize_agents(self) -> Dict:
        """Initialize all agent instances"""

        query_agent = QueryUnderstandingAgent(self.openai_api_key)
        planning_agent = PlanningAgent(self.openai_api_key)
        sql_agent = SQLGenerationAgent(self.openai_api_key, self.database_url)
        calc_agent = CalculationAgent()
        context_agent = ContextAgent()
        synthesis_agent  = SynthesisAgent(self.openai_api_key)

        return {
            'query': query_agent,
            'planning': planning_agent,
            'sql': sql_agent,
            'calculation': calc_agent,
            'context': context_agent,
            'synthesis': synthesis_agent
        }
    
    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow
        
        Graph structure:
            start → query_understanding → planning → routing
                                                      ↓
                                            [simple vs complex]
                                                      ↓
            Simple: sql → END
            Complex: sql → calculation → context → synthesis → END
        """

        #Create graph with state schema
        workflow = StateGraph(AgentState)

        # Add nodes (agents)
        workflow.add_node("query_understanding", self._query_understanding_node)
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("sql_execution", self._sql_execution_node)
        workflow.add_node("calculation", self._calculation_node)
        workflow.add_node("context_search", self._context_search_node)
        workflow.add_node("synthesis", self._synthesis_node)

        # Set entry point
        workflow.set_entry_point("query_understanding")

        # Add edged(workflow flow)
        workflow.add_edge("query_understanding", "planning")
        workflow.add_edge("planning", "sql_execution")

        #Conditional routing based on query type
        workflow.add_conditional_edges(
            "sql_execution",
            self._route_after_sql,
            {
                "simple": END,           # Simple queries end here
                "calculation": "calculation",  # Complex queries continue
            }
        )

        workflow.add_edge("calculation", "context_search")
        workflow.add_edge("context_search", "synthesis")
        workflow.add_edge("synthesis", END)
        
        return workflow
    
    # ==================== Node Functions ====================

    async def _query_understanding_node(self, state: AgentState) -> AgentState:
        """Node 1: Parse user query"""

        print("\n🔍 Step 1: Query Understanding")
        start_time = time.time()

        result = await self.agents['query'].run({
            'query': state['query'],
            'conversation_history': state.get('conversation_history', [])
        })

        if result['status'] == 'success':
            parsed = result['result']['parsed_query']
            state['parsed_query'] = parsed
            state['query_type'] = parsed.get('query_type')
            state['confidence'] = parsed.get('confidence', 0)
            print(f"   ✅ Parsed as: {state['query_type']} (confidence: {state['confidence']:.0%})")
        else:
            state['errors'].append(f"Query understanding failed: {result.get('error')}")
            print(f"   ❌ Failed: {result.get('error')}")

        exec_time = time.time() - start_time
        state['execution_times']['query_understanding'] = exec_time
        state['agents_executed'].append('query_understanding')

        return state
    
    async def _planning_node(self, state: AgentState) -> AgentState:
        """Node 2: Create execution plan"""

        print("\n📋 Step 2: Planning")
        start_time = time.time()

        result = await self.agents['planning'].run({
            'parsed_query': state['parsed_query']
        })

        if result['status'] == 'success':
            state['execution_plan'] = result['result']['plan']
            state['estimated_time'] = result['result']['estimated_time']
            print(f"   ✅ Created {len(state['execution_plan']['steps'])}-step plan")
        else:
            state['errors'].append(f"Planning failed: {result.get('error')}")
            print(f"   ❌ Failed")
        
        exec_time = time.time() - start_time
        state['execution_times']['planning'] = exec_time
        state['agents_executed'].append('planning')
        
        return state
    
    async def _sql_execution_node(self, state: AgentState) -> AgentState:
        """Node 3: Execute SQL queries"""

        print("\n💾 Step 3: SQL Execution")
        start_time = time.time()
        
        # Initialize SQL agent pool
        await self.agents['sql'].initialize()

        # Execute all SQL steps from the plan concurrently - they're
        # independent queries (e.g. current period vs. comparison period),
        # so there's no reason to pay each one's LLM + DB latency in sequence.
        plan = state['execution_plan']
        sql_steps = [step for step in plan['steps'] if step['agent'] == 'sql_generation']

        async def run_sql_step(step):
            print(f"   Executing: {step['task']}")
            result = await self.agents['sql'].run({
                'task': step['task'],
                'params': step['params']
            })
            if result['status'] == 'success':
                print(f"   ✅ {result['result']['row_count']} rows")
            else:
                print(f"   ❌ Failed")
            return result

        step_results = await asyncio.gather(*(run_sql_step(step) for step in sql_steps))

        sql_queries = [r['result']['sql'] for r in step_results if r['status'] == 'success']
        sql_results = [r['result'] for r in step_results if r['status'] == 'success']

        state['sql_queries'] = sql_queries
        state['sql_results'] = sql_results

        exec_time = time.time() - start_time
        state['execution_times']['sql_execution'] = exec_time
        state['agents_executed'].append('sql_execution')

        # Note: the SQL agent's connection pool is intentionally NOT closed
        # here - self.agents['sql'] is a singleton shared across every
        # request. Closing it per-request left it permanently dead after the
        # first query, since initialize()'s `if not self.db_pool` guard
        # treats a closed-but-non-None pool as already initialized. The pool
        # is closed once, at actual app shutdown, in main.py's lifespan handler.

        return state

    async def _calculation_node(self, state: AgentState) -> AgentState:
        """Node 4: Statistical calculations"""
    
        print("\n🧮 Step 4: Calculation")
        start_time = time.time()
    
        # Find calculation steps in plan
        plan = state['execution_plan']
    
        for step in plan['steps']:
            # ✅ FIX: Only run calculation tasks!
            if step['agent'] == 'calculation' and step['task'] in ['compare_periods', 'analyze_trend', 'statistical_significance']:
                print(f"   Calculating: {step['task']}")
    
                # Prepare dependency results
                dependency_results = {}
                for dep_num in step.get('dependencies', []):
                    # Map to SQL results
                    if dep_num <= len(state['sql_results']):
                        dependency_results[dep_num] = {
                            'status': 'success',
                            'result': state['sql_results'][dep_num - 1]
                        }
                
                # ✅ FIX: This was indented wrong - moved inside the if block
                result = await self.agents['calculation'].run({
                    'task': step['task'],
                    'params': step.get('params', {}),
                    'dependency_results': dependency_results
                })
                
                if result['status'] == 'success':
                    state['calculations'] = result['result']
                    state['percentage_change'] = result['result'].get('percentage_change')
                    print(f"   ✅ Change: {state['percentage_change']:+.1f}%")
                else:
                    print(f"   ❌ Failed: {result.get('error')}")
            
            else:
                # Skip non-calculation tasks
                print(f"   ⏭️  Skipping non-calculation task: {step['task']}")
        
        # ✅ FIX: These were inside the loop - moved outside
        exec_time = time.time() - start_time
        state['execution_times']['calculation'] = exec_time
        state['agents_executed'].append('calculation')
        
        return state
    
    async def _context_search_node(self, state: AgentState) -> AgentState:
        """Node 5: Search for external context"""

        print("\n🔍 Step 5: Context Search")
        start_time = time.time()

        result = await self.agents['context'].run({
            'task': 'search_external_factors',
            'params': {
                'time_period': state['parsed_query'].get('time_period')

            },
            'dependency_results':{
                1: {
                    'status': 'success',
                    'result': state['calculations']
                }
            }
        })

        if result['status'] == 'success':
            state['external_factors'] = result['result'].get('factors', [])
            print(f"   ✅ Found {len(state['external_factors'])} factors")
        else:
            state['external_factors'] = []
            print(f"   ⚠️  No factors found")

        exec_time = time.time() - start_time
        state['execution_times']['context_search'] = exec_time
        state['agents_executed'].append('context_search')

        return state
    
    async def _synthesis_node(self, state: AgentState) -> AgentState:
        """Node 6: Generate final insights"""
        
        print("\n📊 Step 6: Synthesis")
        start_time = time.time()
        
        # Skip synthesis for simple queries (just return SQL results)
        query_type = state.get('query_type', '')
        if query_type in ['simple_lookup', 'dimension_breakdown']:
            print("   ⏭️  Skipping synthesis for simple query")
            
            # Just format SQL results nicely
            if state['sql_results']:
                state['executive_summary'] = f"Query returned {state['sql_results'][0].get('row_count', 0)} results"
                state['key_findings'] = ["Data retrieved successfully"]

            exec_time = time.time() - start_time
            state['execution_times']['synthesis'] = exec_time
            state['agents_executed'].append('synthesis')

            self._remember_turn(state)

            return state
        
        # Prepare all results for synthesis
        dependency_results = {
            1: {
                'agent_id': 'sql_generation',
                'status': 'success',
                'result': state['sql_results'][0] if state['sql_results'] else {}
            },
            2: {
                'agent_id': 'calculation',
                'status': 'success',
                'result': state['calculations']
            },
            3: {
                'agent_id': 'context',
                'status': 'success',
                'result': {'factors': state['external_factors']}
            }
        }

        result = await self.agents['synthesis'].run({
            'task':'generate_insights',
            'params': {},
            'dependency_results': dependency_results
        })

        if result['status'] == 'success':
            insights = result['result']
            state['executive_summary'] = insights.get('executive_summary')
            state['key_findings'] = insights.get('key_findings', [])
            state['root_causes'] = insights.get('root_causes', [])
            state['recommendations'] = insights.get('recommendations', [])
            print(f"   ✅ Report generated")
        else:
            print(f"   ❌ Failed")

        exec_time = time.time() - start_time
        state['execution_times']['synthesis'] = exec_time
        state['agents_executed'].append('synthesis')

        self._remember_turn(state)

        return state

    def _remember_turn(self, state: AgentState) -> None:
        """Append this turn to conversation_history for the next call in this session"""
        history = state.get('conversation_history', [])
        history.append({
            'query': state['query'],
            'executive_summary': state.get('executive_summary'),
            'timestamp': state['timestamp']
        })
        # Keep only the last 5 turns so the prompt doesn't grow unbounded
        state['conversation_history'] = history[-5:]

    # ==================== Routing Functions ====================

    def _route_after_sql(self, state: AgentState) -> str:
        """
        Decide next step after SQL execution

        Simple queries (simple_lookup, dimension_breakdown) → END
        Complex queries (root_cause, comparison) → calculation
        """

        query_type = state.get('query_type', '')

        # Simple queries that don't need calculation/context
        simple_types = ['simple_lookup', 'dimension_breakdown', 'aggregation']

        if query_type in simple_types:
            print(f"\n   → Simple query ({query_type}), ending here")
            return "simple"
        else:
            print(f"\n   → Complex query ({query_type}), continuing analysis")
            return "calculation"

    # ==================== Main Execution ====================

    async def run(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute complete workflow

        Args:
            query: Natural language question
            session_id: Conversation thread ID. Pass the same ID back on a
                follow-up question to give the workflow access to prior
                turns (conversation_history) in this session. Omit to start
                a new session - a fresh ID is generated and returned.

        Returns:
            Complete analysis with insights, including 'session_id' so the
            caller can continue the conversation.
        """

        print("="*70)
        print("🚀 INSIGHTFORGE - LANGGRAPH EXECUTION")
        print("="*70)
        print(f"\nQuery: '{query}'\n")

        overall_start = time.time()

        session_id = session_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": session_id}}

        # Carry forward conversation_history from prior turns in this session
        conversation_history = []
        try:
            snapshot = await self.app.aget_state(config)
            if snapshot and snapshot.values:
                conversation_history = snapshot.values.get('conversation_history', [])
        except Exception as e:
            print(f"   ⚠️  Could not load prior session state: {e}")

        #Initialize state

        initial_state: AgentState = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'conversation_history': conversation_history,
            'parsed_query': None,
            'query_type': None,
            'confidence': None,
            'execution_plan': None,
            'estimated_time': None,
            'sql_queries': [],
            'sql_results': [],
            'calculations': None,
            'percentage_change': None,
            'external_factors': [],
            'context_summary': None,
            'executive_summary': None,
            'key_findings': [],
            'root_causes': [],
            'recommendations': [],
            'agents_executed': [],
            'execution_times': {},
            'errors': [],
            'total_time': None
        }

        # Execute workflow

        final_state = await self.app.ainvoke(initial_state, config)

        # Caclulation total time
        total_time = time.time() - overall_start
        final_state['total_time'] = round(total_time, 2)
        final_state['session_id'] = session_id

        print("\n" + "="*70)
        print("✅ WORKFLOW COMPLETE")
        print("="*70)
        print(f"Total time: {total_time:.1f}s")
        print(f"Agents executed: {len(final_state['agents_executed'])}")
        
        return final_state
    
    def visualize(self):
        """
        Generate Mermaid diagram of workflow
        
        Can be rendered in documentation
        """

        mermaid = """
graph TD
    start([User Query]) --> A[Query Understanding]
    A --> B[Planning]
    B --> C[SQL Execution]
    C --> D{Query Type?}
    D -->|Simple| End([Return Results])
    D -->|Complex| E[Calculation]
    E --> F[Context Search]
    F --> G[Synthesis]
    G --> End
"""

        return mermaid
        
    