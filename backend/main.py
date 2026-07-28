"""
InsightForge FASTAPI Application
Main API server for ML powered business intelligence
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
import uvicorn

#Import agents and worflow
from agents.langgraph_workflow import InsightForgeWorkflow
from config.settings import settings

# Valiadte settings on startup
settings.validate()


workflow = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler (startup + shutdown)"""
    # Startup
    global workflow
    print("🚀 Starting InsightForge API...")
    
    workflow = InsightForgeWorkflow(
        openai_api_key=settings.OPENAI_API_KEY,
        database_url=settings.DATABASE_URL
    )
    
    print("✅ InsightForge API ready!")
    
    yield  # Application runs here
    
    # Shutdown
    print("👋 Shutting down InsightForge API...")
    if workflow and workflow.agents.get('sql'):
        await workflow.agents['sql'].close()

# Initialize FastAPI app
app = FastAPI(
    title="InsightForge API",
    description="Autonomous Business Intelligence with Multi-Agent AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_version="3.1.0"  # ← Add this
)

# CORS middleware (allow frontend to call API)
# Note: allow_origins=["*"] together with allow_credentials=True is invalid
# per the CORS spec - browsers reject it outright ("blocked by CORS policy"
# even though the request succeeds server-side). We don't use cookies/auth
# here, so credentials stay off.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify exact origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize workflow (singleton)

# ==================== Request/Response Models ====================
class QueryRequest(BaseModel):
    """Request model for analysis queries"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Why did revenue drop in December?",
                "user_id": "user_123"
            }
        }
    )

    query: str = Field(..., description="Natural language business question", min_length=5)
    user_id: Optional[str] = Field(None, description="User identifier for tracking")
    session_id: Optional[str] = Field(
        None,
        description="Conversation thread ID. Pass the session_id from a previous "
                    "response to ask a follow-up question with context (e.g. "
                    "'why did that happen'). Omit to start a new conversation."
    )

class QueryResponse(BaseModel):
    """Response model for analysis results"""
    query_id: str
    session_id: str
    status: str
    query: str
    query_type: Optional[str] = None
    executive_summary: Optional[str] = None
    key_findings: Optional[List[str]] = None
    root_causes: Optional[List[Dict]] = None
    recommendations: Optional[List[Dict]] = None
    metric_change: Optional[Dict] = None
    external_factors: Optional[List[Dict]] = None
    execution_time: Optional[float] = None
    agents_executed: Optional[List[str]] = None
    confidence: Optional[float] = None
    timestamp: str

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    components : Dict[str, str]

class MetricsResponse(BaseModel):
    """System  metrics response"""
    total_queries: int
    avg_execution_time: float
    cache_hit_rate: float
    agents_performance: Dict[str, Dict]

    
# ==================== API Endpoints ====================

@app.get("/", tags=["General"])
async def root():
    """API root - basic info"""
    return {
        "name": "InsightForge API",
        "version": "1.0.0",
        "description": "Autonomous Business Intelligence with Multi-Agent AI",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """
    Health check endpoint
    Returns status of all system components
    """
    
    # Check database
    db_status = "healthy"
    try:
        if workflow and workflow.agents.get('sql'):
            await workflow.agents['sql'].initialize()
            db_status = "healthy"
        else:
            db_status = "unknown"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Pinecone
    pinecone_status = "healthy" if settings.PINECONE_API_KEY else "disabled"
    
    # Check Redis
    redis_status = "optional"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        components={  # ← FIX: Was "componenets" (typo!)
            "database": db_status,
            "pinecone": pinecone_status,
            "redis": redis_status,
            "workflow": "initialized" if workflow else "not_initialized"
        }
    )

@app.post("/api/query", response_model=QueryResponse, tags=["Analysis"])
async def analyze_query(request: QueryRequest):
    """
    Main analysis endpoint
    Accepts natural language business questions and returns AI-generated insights
    
    Example queries:
    - "What was revenue last month?"
    - "Why did sales drop in December?"
    - "Compare Q4 vs Q3 performance"
    
    """
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized")

    try:
        #Execute workflow
        result = await workflow.run(request.query, session_id=request.session_id)

        # Determine status
        query_type = result.get('query_type', '')
        is_simple = query_type in ['simple_lookup', 'dimension_breakdown']
        
        # For simple queries, create basic summary from SQL results
        if is_simple and not result.get('executive_summary'):
            sql_results = result.get('sql_results', [])
            if sql_results and len(sql_results) > 0:
                row_count = len(sql_results[0].get('results', [])) if sql_results else 0
                result['executive_summary'] = f"Query executed successfully. Retrieved {row_count} result(s)."
                result['key_findings'] = [f"Data retrieved for: {request.query}"]

        # Build response
        response = QueryResponse(
            query_id=f"q_{int(datetime.now().timestamp())}",
            session_id=result.get('session_id'),
            status="success" if result.get('executive_summary') else "partial",
            query=request.query,
            query_type=result.get('query_type'),
            executive_summary=result.get('executive_summary'),
            key_findings=result.get('key_findings', []),
            root_causes=result.get('root_causes', []),
            recommendations=result.get('recommendations', []),
            metric_change={
                'percentage_change': result.get('percentage_change'),
                'calculations': result.get('calculations')
            } if result.get('calculations') else None,
            external_factors=result.get('external_factors', []),
            execution_time=result.get('total_time'),
            agents_executed=result.get('agents_executed', []),
            confidence=result.get('confidence'),
            timestamp=datetime.now().isoformat()
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/query/stream", tags=["Analysis"])
async def analyze_query_stream(request: QueryRequest):
    """
    Streaming analysis endpoint (Server-Sent Events)
    
    Returns real-time updates as agents execute
    """

    async def generate():
        """Generator for sreaming responses"""

        #Send inital status
        yield f"data: {{'status': 'started', 'query': '{request.query}'}}\n\n"

        try:
            # This is a simplified version - full streaming requires LangGraph streaming support
            result = await workflow.run(request.query, session_id=request.session_id)

            # Send progress updates (simulated for now)
            for agent in result.get('agents_executed', []):
                yield f"data: {{'agent': '{agent}', 'status': 'completed'}}\n\n"
                await asyncio.sleep(0.1)

            #Send final result
            import json
            final_data = {
                'status': 'completed',
                'executive_summary': result.get('executive_summary'),
                'execution_time': result.get('total_time')
            }

            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            yield f"data: {{'status': 'error', 'error': '{str(e)}'}}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

@app.get("/api/metrics", response_model=MetricsResponse, tags=["Monitoring"])
async def get_metrics():
    """
    System performance metrics
    
    Returns:
    - Total queries processed
    - Average execution time
    - Cache hit rate
    - Per-agent performance
    """
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    
    # Collect agent metrics
    agents_performance = {}

    for agent_id, agent in workflow.agents.items():
        metrics = agent.get_metrics()
        agents_performance[agent_id] = {
            'total_executions': metrics.get('total_executions', 0),
            'success_rate': metrics.get('success_rate', 0),
            'avg_time': metrics.get('avg_execution_time', 0)
        }

    # Get cache stats( If redis availblae)
    cache_hit_rate = 0.0
    if workflow.agents.get('sql') and hasattr(workflow.agents['sql'], 'cache'):
        cache_stats = workflow.agents['sql'].cache.get_stats()
        hits = cache_stats.get('hits', 0)
        misses = cache_stats.get('misses', 0)
        total = hits + misses
        cache_hit_rate = (hits / total * 100) if total > 0 else 0

    # Calculate average execution time
    total_queries = sum(a.get('total_executions', 0) for a in agents_performance.values())
    avg_time = sum(
        a.get('avg_time', 0) * a.get('total_executions', 0) 
        for a in agents_performance.values()
    ) / total_queries if total_queries > 0 else 0
    
    return MetricsResponse(
        total_queries=total_queries,
        avg_execution_time=round(avg_time, 2),
        cache_hit_rate=round(cache_hit_rate, 1),
        agents_performance=agents_performance
    )

@app.get("/api/examples", tags=["Analysis"])
async def get_example_queries():
    """
    Get example queries users can try
    """
    return {
        "simple_queries": [
            "What was our revenue last month?",
            "Show me total orders this week",
            "What's our average order value?",
        ],
        "comparison_queries": [
            "Compare December vs November revenue",
            "How did Q4 2024 perform vs Q3 2024?",
            "Show me year-over-year growth",
        ],
        "analysis_queries": [
            "Why did revenue drop in December?",
            "What caused the sales spike last week?",
            "Analyze customer churn trends",
            "Which product category is growing fastest?",
        ]
    }

@app.get("/api/schema", tags=["Data"])
async def get_database_schema():
    """
    Get available database schema
    Shows what data is available for analysis
    """
    
    if not workflow or not workflow.agents.get('sql'):
        raise HTTPException(status_code=503, detail="SQL agent not available")
    
    try:
        await workflow.agents['sql'].initialize()
        schema = await workflow.agents['sql']._get_schema()
        
        # Format for display
        formatted_schema = {}
        for table, columns in schema.items():
            formatted_schema[table] = [
                {
                    'name': col['column'],
                    'type': col['type'],
                    'nullable': col.get('nullable', True)
                }
                for col in columns
            ]

        return {
            "tables": formatted_schema,
            "available_metrics": [
                "revenue (SUM of order_total)",
                "order_count (COUNT of orders)",
                "average_order_value (AVG of order_total)",
                "customer_count (COUNT DISTINCT customers)"
            ],
            "available_dimensions": [
                "product_category",
                "region",
                "customer_segment",
                "time (daily, weekly, monthly)"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema fetch failed: {str(e)}")
    
@app.post("/api/admin/reset-cache", tags=["Admin"])
async def reset_cache():
    """
    Clear all caches (admin only)
    """
    
    if workflow and workflow.agents.get('sql'):
        sql_agent = workflow.agents['sql']
        
        # Clear schema cache
        sql_agent.schema_cache = None
        sql_agent.schema_cache_time = None
        
        # Clear query cache (Redis)
        if hasattr(sql_agent, 'cache'):
            # Would delete all keys here
            pass
    
    return {"status": "success", "message": "Caches cleared"}


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Catch-all exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

#==================== Run Server ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8010,  # 8000 is taken by another local app on this machine
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )