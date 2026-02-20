"""
SQL Generation Agent 
Coverts analysis requirements into validated, safe SQL queries

CRITICAL: Prevenets halluciantonns by grounding in actual database schema
"""

from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from openai import AsyncOpenAI
import asyncpg
import sqlparse
import json
from datetime import datetime, timedelta
from backend.tools.cache_manager import CacheManager

class SQLGenerationAgent(BaseAgent):
    """
    Generates SQL queries with multi-level validation
    
    Validation layers:
    1. Schema grounding (only use real tables/columns)
    2. Syntax validation (sqlparse)
    3. Dry-run (EXPLAIN query)
    4. Result validation (check for anomalies)
    """
    def __init__(
        self,
        openai_api_key: str,
        database_url: str,
        config: Optional[Dict] = None
    ):
        super().__init__("sql_generation", config)
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.database_url = database_url
        self.db_pool = None
        self.schema_cache = None
        self.schema_cache_time = None
        self.cache_ttl = 3600  # 1 hour
        self.cache = CacheManager()
    
    async def initialize(self):
        """Initialize database connection pool"""
        if not self.db_pool:
            self.db_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            self.logger.info("Database pool created")

    async def close(self):
        """Close Database connections"""
        if self.db_pool:
            await self.db_pool.close()
            self.logger.info("Database pool closed")
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input has required fields"""
        return (
            isinstance(input_data, dict) and
            'task' in input_data and
            'params' in input_data
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution - generate and run SQL"""

        # ENsure database is initialized
        await self.initialize()

        task = input_data['task']
        params = input_data['params']

        self.logger.info(f"Executing task: {task}")

        # GEt current database schema
        schema = await self._get_schema()

        # Generate SQL based on task
        if task == 'fetch_data':
            sql = await self._generate_fetch_query(params, schema)
        elif task == 'breakdown_by_dimensions':
            sql = await self._generate_breakdown_query(params, schema)
        elif task == 'fetch_timeseries':
            sql = await self._generate_timeseries_query(params, schema)
        else:
            raise ValueError(f"Unknown task: {task}")
        
        # Validate SQL
        if not self._validate_syntax(sql):
            raise ValueError("Generated SQL has syntax errors")
        
        # Dry-run validation
        if not await self._dry_run_query(sql):
            raise ValueError("SQL failed dry-run validation")
        
        # Execute query
        results = await self._execute_query(sql)
        
        # Validate results
        validated_results = self._validate_results(results)
        
        return {
            'sql': sql,
            'results': validated_results,
            'row_count': len(validated_results),
            'columns': list(validated_results[0].keys()) if validated_results else []
        }
    
    async def _get_schema(self) -> Dict[str, List[Dict]]:
        """Fetch database schema with caching"""

        # Check cache 
        now = datetime.now()
        if (self.schema_cache and self.schema_cache_time and
            (now - self.schema_cache_time).seconds < self.cache_ttl):
            return self.schema_cache
        
        self.logger.info("Fetching database schema...")

        query = """
        SELECT 
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
        """

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query)

            # Organize by table
            schema = {}
            for row in rows:
                table = row['table_name']
                if table not in schema:
                    schema[table] = []

                schema[table].append({
                'column': row['column_name'],
                'type': row['data_type'],
                'nullable': row['is_nullable'] == 'YES'
                })

            # Cache it
            self.schema_cache = schema
            self.schema_cache_time = now

            self.logger.info(f"Schema cached: {len(schema)} tables")
        return schema
    
    async def _generate_fetch_query(
        self,
        params: Dict,
        schema: Dict
    ) -> str:
        """Generate SQL for basic data fetch"""

        metrics = params.get('metrics', [])
        dimensions = params.get('dimensions', [])
        time_period = params.get('time_period', {})
        filters = params.get('filters', {})

        # map metric names to actual columns
        metric_mapping = {
            'revenue': 'order_total',
            'order_count': 'order_id',
            'average_order_value': 'order_total'
        }

        # Build prompt for LLM
        prompt = f"""Generate a PostgreSQL SELECT query.

Avaialble schema:
{json.dumps(schema, indent=2)}

Requirements:
- Metrics to calculate: {metrics}
- Dimensions to group by: {dimensions if dimensions else 'none'}
- Time period: {time_period}
- Filters: {filters if filters else 'none'}

Metric mapping:
- revenue → SUM(order_total)
- order_count → COUNT(order_id)
- average_order_value → AVG(order_total)

Rules:
1. ONLY use tables and columns from the schema above
2. Filter by status = 'completed' for revenue calculations
3. Use proper date filtering for time_period
4. Add appropriate GROUP BY if dimensions specified
5. Order by the main metric DESC
6. Limit to 1000 rows

Time period format:
- If type is "relative" and start is "last_month": 
  WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND order_date < DATE_TRUNC('month', CURRENT_DATE)

Output ONLY the SQL query, no explanations.
"""
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500
        )

        sql = response.choices[0].message.content.strip()

        # Clean up (remove markdown if present)
        sql = sql.replace('```sql', '').replace('```', '').strip()
        
        return sql
    
    async def _generate_breakdown_query(
        self,
        params: Dict,
        schema: Dict
    ) -> str:
        """Generate SQL for dimensional breakdown"""
        
        metrics = params.get('metrics', [])
        dimensions = params.get('dimensions', [])
        time_period = params.get('time_period', {})

        prompt = f"""Generate a PostgreSQL query to break down metrics by dimensions.

Schema:
{json.dumps(schema, indent=2)}

Requirements:
- Metrics: {metrics}
- Group by: {dimensions}
- Time period: {time_period}
- Include counts and percentages

Example output format:
SELECT 
    product_category,
    region,
    SUM(order_total) as revenue,
    COUNT(*) as orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM orders
WHERE ...
GROUP BY product_category, region
ORDER BY revenue DESC;

Output ONLY the SQL query.
"""
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        sql = response.choices[0].message.content.strip()
        sql = sql.replace('```sql', '').replace('```', '').strip()
        
        return sql
    
    async def _generate_timeseries_query(
        self,
        params: Dict,
        schema: Dict,
    ) -> str:
        """Generate SQL for time-series data"""

        metrics = params.get('metrics', [])
        time_period = params.get('time_period', {})
        granularity = params.get('granularity', 'daily')
        
        # Map granularity to SQL
        trunc_map = {
            'daily': 'day',
            'weekly': 'week',
            'monthly': 'month',
            'quarterly': 'quarter',
            'yearly': 'year'
        }
        
        trunc = trunc_map.get(granularity, 'day')
        
        prompt = f"""Generate a time-series query.

Schema:
{json.dumps(schema, indent=2)}

Requirements:        
- Metrics: {metrics}
- Time period: {time_period}
- Granularity: {granularity} (use DATE_TRUNC('{trunc}', order_date))

Example:
SELECT 
    DATE_TRUNC('{trunc}', order_date) as period,
    SUM(order_total) as revenue,
    COUNT(*) as orders
FROM orders
WHERE status = 'completed'
  AND order_date >= ...
GROUP BY DATE_TRUNC('{trunc}', order_date)
ORDER BY period ASC;

Output ONLY the SQL query.and
"""
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        sql = response.choices[0].message.content.strip()
        sql = sql.replace('```sql', '').replace('```', '').strip()
        
        return sql
    
    def _validate_syntax(self, sql: str) -> bool:
        """Validate SQL syntax using sqlparse"""
        try:
            parsed = sqlparse.parse(sql)
            
            if not parsed:
                return False
            
            # Check it's a SELECT statement
            first_token = str(parsed[0].tokens[0]).upper()
            if first_token != 'SELECT':
                self.logger.warning(f"Not a SELECT query: {first_token}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Syntax validation failed: {e}")
            return False
    
    async def _dry_run_query(self, sql: str) -> bool:
        """Run EXPLAIN to validate without executing"""
        try:
            explain_query = f"EXPLAIN {sql}"

            async with self.db_pool.acquire() as conn:
                await conn.fetch(explain_query)

            return True
        
        except Exception as e:
            self.logger.error(f"Dry-run failed: {e}")
            return False
        
    async def _execute_query(self, sql: str) -> List[Dict]:
        """Execute with caching"""
        
        # Check cache first
        cached = self.cache.get_cached_query(sql)
        if cached:
            self.logger.info(f"✨ Cache hit! Returning cached results")
            return cached
        
        # Cache miss - execute query
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(sql)
            
            results = [dict(row) for row in rows]
            
            # Cache results (10 min TTL)
            self.cache.cache_query_result(sql, results, ttl=600)
            
            self.logger.info(f"Query executed and cached ({len(results)} rows)")
            return results
            
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise

    def _validate_results(self, results: List[Dict]) -> List[Dict]:
        """Validate query results for anomalies"""
        
        if not results:
            self.logger.warning("Query returned no results")
            return results
        
        # Check for all NULL values (suspicious)
        if all(all(v is None for v in row.values()) for row in results):
            self.logger.warning("All results are NULL - may indicate issue")
        
        # Check for extreme outliers in numeric columns
        for key in results[0].keys():
            values = [row[key] for row in results if row[key] is not None]
            
            if values and isinstance(values[0], (int, float)):
                max_val = max(values)
                if max_val > 1e10:  # Suspiciously large number
                    self.logger.warning(f"Column {key} has extreme value: {max_val}")
        
        return results