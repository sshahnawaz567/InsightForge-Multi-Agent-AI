"""
Query Understanding Agent
Converts natural language queries into structrure analysis requirements
"""

from typing import Dict, Any, Optional, Any
import json
from tools.llm_client import get_openai_client
from .base_agent import BaseAgent

class QueryUnderstandingAgent(BaseAgent):
    """
    Parses natural language business questions into structured requirements
    
    Input: 
        {"query": "Why did revenue drop last month?"}
    
    Output:
        {
            "query_type": "root_cause_analysis",
            "metrics": ["revenue"],
            "time_period": {...},
            "analysis_required": [...],
            "confidence": 0.95
        }
    """
    
    def __init__(self, openai_api_key: str, config: Optional[Dict] = None):
        super().__init__("query_understanding", config)
        self.client = get_openai_client(openai_api_key)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Create system prompt for query parsing"""
        return """You are a business intelligence query parser for InsightForge.
Your job is to convert natural language business questions into structured JSON.

Available metrics in our database:
- revenue (order_total)
- order_count
- average_order_value
- customer_count
- churn_rate

Available dimensions:
- product_category (Electronics, Clothing, Home & Garden, Books)
- region (North America, Europe, Asia, South America, Australia)
- customer_segment (Individual, SMB, Enterprise)
- time (daily, weekly, monthly, quarterly, yearly)

Query types:
- simple_lookup: "What was revenue last month?"
- trend_analysis: "Show me revenue over time"
- comparison: "Compare Q1 vs Q2 revenue"
- root_cause_analysis: "Why did X happen?"
- forecast: "Predict next month's revenue"
- correlation: "Is X related to Y?"
- breakdown: "Revenue by product category"

Output JSON schema:
{
  "query_type": "<type>",
  "metrics": ["<metric_name>"],
  "dimensions": ["<dimension>"] or [],
  "time_period": {
    "type": "absolute|relative",
    "start": "YYYY-MM-DD" or "last_month",
    "end": "YYYY-MM-DD" or "today"
  },
  "comparison_period": {<same as time_period>} or null,
  "filters": {<column>: <value>} or {},
  "analysis_required": ["<analysis_type>"],
  "confidence": 0.0-1.0,
  "ambiguities": ["<unclear aspect>"] or []
}

Examples:

Q: "What was our revenue last month?"
A: {
  "query_type": "simple_lookup",
  "metrics": ["revenue"],
  "dimensions": [],
  "time_period": {"type": "relative", "start": "last_month", "end": "last_month"},
  "comparison_period": null,
  "filters": {},
  "analysis_required": [],
  "confidence": 0.98,
  "ambiguities": []
}

Q: "Why did sales drop in December compared to November?"
A: {
  "query_type": "root_cause_analysis",
  "metrics": ["revenue", "order_count"],
  "dimensions": ["product_category", "region"],
  "time_period": {"type": "absolute", "start": "2024-12-01", "end": "2024-12-31"},
  "comparison_period": {"type": "absolute", "start": "2024-11-01", "end": "2024-11-30"},
  "filters": {},
  "analysis_required": ["trend_analysis", "dimension_breakdown", "external_factors"],
  "confidence": 0.95,
  "ambiguities": []
}

Q: "Show me revenue"
A: {
  "query_type": "simple_lookup",
  "metrics": ["revenue"],
  "dimensions": [],
  "time_period": {"type": "relative", "start": "last_month", "end": "today"},
  "comparison_period": null,
  "filters": {},
  "analysis_required": [],
  "confidence": 0.65,
  "ambiguities": ["time_period_not_specified"]
}

Rules:
1. If time period unclear, use last 30 days
2. If comparing, create comparison_period
3. For "why" questions, set query_type to root_cause_analysis
4. Confidence < 0.7 if query is vague
5. List ambiguities if anything unclear
6. ONLY output valid JSON, no explanations
7. If a "Recent conversation" section is provided, use it to resolve
   follow-up references (e.g. "why did that happen", "what about Europe")
   to concrete metrics/dimensions/time periods from the earlier turns.
   Do not lower confidence just because the query relies on prior context.

Current date: {current_date}
"""

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that we have a query string"""
        return (
            isinstance(input_data, dict) and
            'query' in input_data and
            isinstance(input_data['query'], str) and
            len(input_data['query'].strip()) > 0
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse natural language query into structrured format"""

        user_query = input_data['query'].strip()
        conversation_history = input_data.get('conversation_history', [])
        self.logger.info(f"Parsing query: '{user_query}' (history: {len(conversation_history)} turns)")

        # Get current date for context
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt = self.system_prompt.replace("{current_date}", current_date)

        user_content = user_query
        if conversation_history:
            history_lines = []
            for turn in conversation_history[-3:]:
                history_lines.append(f"Q: {turn.get('query', '')}")
                if turn.get('executive_summary'):
                    history_lines.append(f"A: {turn['executive_summary']}")
            user_content = (
                "Recent conversation:\n" + "\n".join(history_lines) +
                f"\n\nCurrent question: {user_query}"
            )

        try:
            # Call openAI with JSON mode
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=500
            )

            # Parse response
            parsed = json.loads(response.choices[0].message.content)

            # Add original query for reference
            parsed['original_query'] = user_query

            #check confidence
            confidence = parsed.get('confidence', 0)

            if confidence < 0.7:
                self.logger.warning(f"Low confidence parse: {confidence}")
                return {
                    'status': 'needs_clarification',
                    'parsed_query': parsed,
                    'clarification_questions': self._generate_clarifying_questions(parsed)
                }
            
            self.logger.info(f"Successfully parsed as: {parsed.get('query_type')}")
            
            return {
                'status': 'success',
                'parsed_query': parsed
            }
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError("LLM returned invalid JSON")
        
        except Exception as e:
            self.logger.error(f"Query parsing failed: {e}")
            raise

    def _generate_clarifying_questions(self, parsed: Dict) -> list:
        """Generate questions when confidence is low"""
        questions = []
        
        ambiguities = parsed.get('ambiguities', [])
        
        if 'time_period_not_specified' in ambiguities:
            questions.append("What time period are you interested in? (e.g., last month, Q4 2024)")
        
        if 'metric_unclear' in ambiguities:
            questions.append("Which metric would you like to analyze? (revenue, orders, customers)")
        
        if not parsed.get('metrics'):
            questions.append("What would you like to measure? (revenue, customer count, etc.)")
        
        if not questions:
            questions.append("Could you provide more details about what you'd like to analyze?")
        
        return questions
    