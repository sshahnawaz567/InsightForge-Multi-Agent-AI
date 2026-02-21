"""
LangGraph State Schema
Defines what information flows between agents
"""
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

class AgentState(TypedDict):
    """
    Shared state that flows through all agents
    
    Each agent:
    1. Reads relevant fields
    2. Adds its results
    3. Passes state to next agent
    """
    
    # User Input
    query: str                          # Original user question
    timestamp: str                      # When query was asked
    
    # Query Understanding Output
    parsed_query: Optional[Dict]        # Structured query requirements
    query_type: Optional[str]           # simple_lookup, comparison, root_cause, etc.
    confidence: Optional[float]         # Parse confidence (0-1)
    
    # Planning Output
    execution_plan: Optional[Dict]      # Multi-step workflow
    estimated_time: Optional[float]     # Expected execution time
    
    # SQL Generation Output
    sql_queries: List[str]              # Generated SQL queries
    sql_results: List[Dict]             # Query results
    
    # Calculation Output
    calculations: Optional[Dict]        # Statistical analysis results
    percentage_change: Optional[float]  # Main metric change
    
    # Context Output
    external_factors: List[Dict]        # External factors found
    context_summary: Optional[str]      # Context narrative
    
    # Synthesis Output
    executive_summary: Optional[str]    # Final summary
    key_findings: List[str]             # Bullet points
    root_causes: List[Dict]             # Ranked causes
    recommendations: List[Dict]         # Action items
    
    # Metadata
    agents_executed: List[str]          # Which agents ran
    execution_times: Dict[str, float]   # Time per agent
    errors: List[str]                   # Any errors encountered
    total_time: Optional[float]         # End-to-end time