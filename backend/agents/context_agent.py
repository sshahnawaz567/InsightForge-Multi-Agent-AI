"""
Context Agent
Searches for external factors explaining data patterns

Data Sources:
1. Internal knowledge base (vector DB - RAG)
2. External events (holidays, competitot launches)
3. Web search simulation (week 4: simplified, week 5: real API)
"""
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
import json
from datetime import datetime
from sentence_transformers import SentenceTransformer


class ContextAgent(BaseAgent):
    """
    Finds context explaining why metrics changed
    
    Example:
    Input: "Revenue dropped 79% in December"
    Output: 
        - Holiday season (expected impact: -15%)
        - Competitor launched Dec 1st (news article found)
        - Shipping delays in Europe (industry report)
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__("context", config)
        
        # Initialize embedding model (for RAG)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Simulated knowledge base (Week 4)
        # Week 5: Replace with real Pinecone + web search
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> List[Dict]:
        """
        Simulated internal knowledge base
        (In production: Load from Pinecone vector DB)
        """
        return [
            {
                'id': 'kb_001',
                'content': 'December retail sales typically drop 10-15% due to holiday store closures and reduced business days',
                'category': 'seasonal',
                'date': '2024-12-01',
                'impact': 'expected',
                'source': 'Historical Analysis'
            },
            {
                'id': 'kb_002',
                'content': 'Major competitor TechCorp launched aggressive pricing campaign on December 1st, offering 40% discounts on enterprise plans',
                'category': 'competition',
                'date': '2024-12-01',
                'impact': 'high',
                'source': 'Market Intelligence'
            },
            {
                'id': 'kb_003',
                'content': 'Shipping carriers (FedEx, UPS) experienced delays in Europe during December due to winter weather',
                'category': 'logistics',
                'date': '2024-12-15',
                'impact': 'medium',
                'source': 'Industry Report'
            },
            {
                'id': 'kb_004',
                'content': 'Black Friday (November 29th) drove 200% revenue spike in late November, creating tough comparison',
                'category': 'seasonal',
                'date': '2024-11-29',
                'impact': 'medium',
                'source': 'Internal Data'
            },
            {
                'id': 'kb_005',
                'content': 'New data privacy regulations in EU effective December 1st impacted tracking and retargeting campaigns',
                'category': 'regulatory',
                'date': '2024-12-01',
                'impact': 'low',
                'source': 'Legal Team'
            }
        ]
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate we have search parameters"""
        return (
            isinstance(input_data, dict) and
            'task' in input_data
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for contextual factors"""
        task = input_data['task']
        params = input_data.get('params', {})
        dependency_results = input_data.get('dependency_results', {})

        self.logger.info(f"Searching context for task: {task}")

        if task == 'search_external_factors':
            return self._search_external_factors(params, dependency_results)
        elif task == 'find_similar_incidents':
            return self._find_similar_incidents(params)
        else:
            raise ValueError(f"Unknown context task: {task}")
        
    
    def _search_external_factors(
        self,
        params: Dict,
        dependency_results: Dict
    ) -> Dict[str, Any]:
        """
        Search for external factors explaining the change
        
        Process:
        1. Analyze what changed(from dependency results)
        2. Generate search query
        3. Search knowledge base (vector similarity)
        4. Rank by relevance
        """

        self.logger.info("Searching for external factors...")
    
        #Extract information from previous step
        change_description = self._build_change_description(dependency_results)
        time_period = params.get('time_period', {})
        
        self.logger.info(f"Change description: {change_description}")

        # Search knowledge base using semantic similarity
        relevant_factors = self._semantic_search(change_description, time_period)
        
        # Categorize factors
        categorized = self._categorize_factors(relevant_factors)
        
        result = {
            'factors_found': len(relevant_factors),
            'factors': relevant_factors,
            'by_category': categorized,
            'high_impact_factors': [f for f in relevant_factors if f['impact'] == 'high'],
            'search_query': change_description
        }
        
        self.logger.info(f"Found {len(relevant_factors)} relevant factors")
        
        return result
    
    def _build_change_description(self, dependency_results: Dict) -> str:
        """
        Build search query from previous agent results
        Example: "REvenue dropped 79% in December 2024
        """
        description_parts = []

        for step_num, result in dependency_results.items():
            if result.get('status') != 'success':
                continue

            agent_result = result.get('result', {})

            # From calculation agent
            if 'percentage_change' in agent_result:
                pct = agent_result['percentage_change']
                direction = agent_result['direction']
                description_parts.append(f"revenue {direction} {abs(pct):.0f}%")
            
            # From SQL agent (extract time period)
            if 'sql' in agent_result:
                sql = agent_result['sql']
                if 'December' in sql or '2024-12' in sql:
                    description_parts.append("in December 2024")
        
        return " ".join(description_parts) if description_parts else "revenue change"
        
    def _semantic_search(
        self,
        query: str,
        time_period: Dict,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search knowledge base using semantic similarity
        
        In In production: Query Pinecone vector DB
        Week 4: Simple keyword matching + date filtering
        """

        #GEenaete embedding for query
        query_embedding = self.embedding_model.encode(query)

        # calculate similarty with each knwoledge abse entry
        scored_items = []

        for item in self.knowledge_base:
            # Simple keyword matching (Week 4 simplification)
            content_lower = item['content'].lower()
            query_lower = query.lower()
            
            # Calculate relevance score
            score = 0.0
            
            # Keyword matching
            keywords = ['revenue', 'drop', 'decrease', 'sales', 'december']
            for keyword in keywords:
                if keyword in query_lower and keyword in content_lower:
                    score += 0.2

            # Date relevance
            if time_period:
                item_date = item.get('date', '')
                if item_date and self._is_date_relevant(item_date, time_period):
                    score += 0.3
            
            # Impact weighting
            impact_weights = {'high': 0.4, 'medium': 0.2, 'expected': 0.1, 'low': 0.05}
            score += impact_weights.get(item['impact'], 0)
            
            if score > 0.2:  # Threshold
                scored_items.append({
                    **item,
                    'relevance_score': round(score, 2)
                })
        
        # Sort by relevance
        scored_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return scored_items[:top_k]
    
    def _is_date_relevant(self, item_date: str, time_period: Dict) -> bool:
        """Check if date falls within relevant time period"""
        try:
            item_dt = datetime.strptime(item_date, '%Y-%m-%d')
            
            # Simple check: within 30 days of period
            # More sophisticated in production
            return '2024-12' in item_date or '2024-11' in item_date
        except:
            return False
    
    def _categorize_factors(self, factors: List[Dict]) -> Dict[str, List[Dict]]:
        """Group factors by category"""
        categories = {}
        
        for factor in factors:
            category = factor.get('category', 'other')
            if category not in categories:
                categories[category] = []
            categories[category].append(factor)
        
        return categories
    
    def _find_similar_incidents(self, params: Dict) -> Dict[str, Any]:
        """
        Find similar past incidents (RAG)
        
        Example: "Has revenue dropped like this before?"
        """
        
        self.logger.info("Searching for similar past incidents...")
        
        # Simulated: In production, query vector DB for past analyses
        similar_incidents = [
            {
                'date': '2023-12-01',
                'description': 'Revenue dropped 45% in December 2023',
                'root_cause': 'Holiday season + supply chain issues',
                'resolution': 'Recovered in January with promotional campaign',
                'similarity_score': 0.78
            }
        ]
        
        return {
            'similar_incidents_found': len(similar_incidents),
            'incidents': similar_incidents
        }



