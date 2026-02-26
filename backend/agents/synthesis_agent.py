"""
Synthesis Agent
Combines all analysis results into executive-ready insights

Takes results from:
- Query Understanding (what user asked)
- SQL Generation (data)
- Calculation (statistics)
- Context (external factors)

Produces:
- Executive summary
- Root cause analysis
- Recommendations
- Visualizations (data for charts)
"""
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from openai import AsyncOpenAI
import json
from datetime import datetime

class SynthesisAgent(BaseAgent):
    """
    The storyteller - creates final narrative
    
    Input: All agent results
    Output: Executive report with insights + recommendations
    """
    def __init__(self, open_api_key: str, config: Optional[Dict] = None):
        super().__init__("synthesis", config)
        self.client = AsyncOpenAI(api_key=open_api_key)

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate we have results to synthesize"""
        return (
            isinstance(input_data, dict) and
            'task' in input_data
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        
        task = input_data['task']
        dependency_results = input_data.get('dependency_results', {})
        
        self.logger.info(f"Synthesizing results for task: {task}")
        
        if task == 'generate_insights':
            return await self._generate_insights(dependency_results)
        elif task == 'create_report':
            return await self._create_report(dependency_results)
        else:
            raise ValueError(f"Unknown synthesis task: {task}")
        

    async def _generate_insights(self, dependency_results: Dict) -> Dict[str, Any]:
        """
        Generate executive insights from all agent results
        
        Creates:
        1. Executive summary (2-3 sentences)
        2. key findings (bullet points)
        3. root causes (ranked by impace
        4. recommendations (actionable next steps)
        
        """
        self.logger.info("Generating executive insights...")
        
        # Extract data from each agent
        analysis_data = self._extract_analysis_data(dependency_results)
        
        # Build prompt for LLM
        prompt = self._build_synthesis_prompt(analysis_data)
        
        # Generate insights using LLM
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a senior business analyst creating executive summaries.

Your goal: Transform technical analysis into clear business insights.

Style:
- Executive summary: 2-3 sentences, bottom line first
- Key findings: 3-5 bullet points, specific numbers
- Root causes: Ranked by impact, explain reasoning
- Recommendations: Actionable, prioritized (urgent/short-term/long-term)

Tone: Professional but conversational, confident but not overconfident.

Output JSON format:
{
  "executive_summary": "...",
  "key_findings": ["...", "..."],
  "root_causes": [
    {"cause": "...", "impact": "high|medium|low", "explanation": "..."}
  ],
  "recommendations": [
    {"action": "...", "priority": "urgent|short-term|long-term", "rationale": "..."}
  ],
  "confidence": 0.0-1.0
}"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500
        )

        insights = json.loads(response.choices[0].message.content)

        # Add metadata
        insights['generated_at'] = analysis_data.get('timestamp')
        insights['data_sources'] = self._identify_data_sources(dependency_results)
        
        self.logger.info("Insights generated successfully")
        
        return insights
    
    def _extract_analysis_data(self, dependency_results: Dict) -> Dict:
        """Extract relevant data from all previous agents"""

        data = {
            'timestamp': datetime.now().isoformat(),
            'metric_changes': [],
            'external_factors': [],
            'data_breakdown': [],
            'statistical_tests': [],
            'sql_results': []
        }

        for step_num, result in dependency_results.items():
            if result.get('status') != 'success':
                continue
            
            agent_id = result.get('agent_id', '')
            agent_result = result.get('result')

            # Skip if result is None
            if agent_result is None:
                continue
            
            # Check if it's a dict
            if not isinstance(agent_result, dict):
                continue
            
            # From calculation agent
            if agent_id == 'calculation':
                if 'percentage_change' in agent_result:
                    data['metric_changes'].append({
                        'metric': 'revenue',
                        'current': agent_result.get('current_value'),
                        'previous': agent_result.get('comparison_value'),
                        'change_pct': agent_result.get('percentage_change'),
                        'change_abs': agent_result.get('absolute_change'),
                        'direction': agent_result.get('direction'),
                        'interpretation': agent_result.get('interpretation')
                    })

                if 'top_changes' in agent_result:
                    data['data_breakdown'] = agent_result['top_changes']

            # From context agent
            elif agent_id == 'context':
                if 'factors' in agent_result:
                    data['external_factors'] = agent_result['factors']

            # From SQL agent (for simple queries without calculation)
            elif agent_id == 'sql_generation':
                if 'results' in agent_result:
                    data['sql_results'].extend(agent_result['results'])

        return data

    def _build_synthesis_prompt(self, analysis_data: Dict) -> str:
        """Build prompt for LLM synthesis"""

        prompt_parts = ["Analyze this business data and provide insights:\n"]

        # Check if we have metric changes (comparison/root cause queries)
        has_comparison = bool(analysis_data['metric_changes'])

        # Metric changes (for comparison queries)
        if analysis_data['metric_changes']:
            prompt_parts.append("\n## Metric Changes:")
            for change in analysis_data['metric_changes']:
                prompt_parts.append(
                    f"- {change['metric'].title()}: "
                    f"${change['current']:,.0f} (current) vs "
                    f"${change['previous']:,.0f} (previous) = "
                    f"{change['change_pct']:+.1f}% change"
                )
                prompt_parts.append(f"  Status: {change['interpretation']}")

        # SQL Results (for simple queries without comparison)
        elif analysis_data['sql_results']:
            prompt_parts.append("\n## Query Results:")
            prompt_parts.append(f"Retrieved {len(analysis_data['sql_results'])} data points:")

            # Show first few results
            for i, row in enumerate(analysis_data['sql_results'][:5], 1):
                row_summary = ", ".join([f"{k}: {v}" for k, v in row.items()])
                prompt_parts.append(f"{i}. {row_summary}")

            if len(analysis_data['sql_results']) > 5:
                prompt_parts.append(f"... and {len(analysis_data['sql_results']) - 5} more rows")

            # Provide context for synthesis
            prompt_parts.append("\nTask: Provide a brief executive summary of these results.")
            prompt_parts.append("Focus on: Key patterns, top performers, notable insights.")

        # External factors
        if analysis_data['external_factors']:
            prompt_parts.append("\n## External Factors Found:")
            for factor in analysis_data['external_factors'][:5]:
                prompt_parts.append(
                    f"- [{factor['impact'].upper()}] {factor['content']}"
                )
                prompt_parts.append(f"  Source: {factor['source']}")

        # Data breakdown
        if analysis_data['data_breakdown']:
            prompt_parts.append("\n## Dimensional Breakdown:")
            for item in analysis_data['data_breakdown'][:3]:
                prompt_parts.append(
                    f"- {item['dimension']}: {item['percentage_change']:+.1f}% change"
                )

        # Adjust instructions based on query type
        if has_comparison:
            prompt_parts.append("\n\nProvide executive insights with root causes and recommendations in JSON format.")
        else:
            prompt_parts.append("\n\nProvide a concise executive summary highlighting key insights in JSON format.")

        return "\n".join(prompt_parts)
    
    def _identify_data_sources(self, dependency_results: Dict) -> List[str]:

        """Identify which data sources were used"""
        sources = set()

        for result in dependency_results.values():
            agent_id = result.get('agent_id', '')
            if agent_id == 'sql_generation':
                sources.add('Internal Database')
            elif agent_id == 'context':
                sources.add('Knowledge Base')
            elif agent_id == 'calculation':
                sources.add('Statistical Analysis')
        
        return list(sources)
    
    async def _create_report(self, dependency_results: Dict) -> Dict[str, Any]:
        """
        Create full formatted report (markdown)
        
        Used for: Email summaries, PDF exports, documentation
        """
        insights = await self._generate_insights(dependency_results)

        # GEenrate markdown report
        markdown = self._format_as_markdown(insights)

        return {
            'insights': insights,
            'markdown': markdown,
            'format': 'markdown'
        }
    
    def _format_as_markdown(self, insights: Dict) -> str:

        """Format insights as markdown"""

        lines = [
            "# Business Intelligence Report",
            f"\n**Generated:** {insights.get('generated_at', 'N/A')}",
            f"**Confidence:** {insights.get('confidence', 0)*100:.0f}%",
            "\n---\n",
            "\n## Executive Summary\n",
            insights['executive_summary'],
            "\n## Key Findings\n"
        ]

        for finding in insights['key_findings']:
            lines.append(f"- {finding}")
        
        lines.append("\n## Root Causes\n")
        for cause in insights['root_causes']:
            impact_emoji = "🔴" if cause['impact'] == 'high' else "🟡" if cause['impact'] == 'medium' else "🟢"
            lines.append(f"\n### {impact_emoji} {cause['cause']}")
            lines.append(f"**Impact:** {cause['impact'].title()}")
            lines.append(f"\n{cause['explanation']}")
        
        lines.append("\n## Recommended Actions\n")
        for rec in insights['recommendations']:
            priority_emoji = "🚨" if rec['priority'] == 'urgent' else "📅" if rec['priority'] == 'short-term' else "📊"
            lines.append(f"\n### {priority_emoji} {rec['action']}")
            lines.append(f"**Priority:** {rec['priority'].title()}")
            lines.append(f"\n{rec['rationale']}")
        
        lines.append("\n---")
        lines.append(f"\n**Data Sources:** {', '.join(insights.get('data_sources', []))}")
        
        return "\n".join(lines)




