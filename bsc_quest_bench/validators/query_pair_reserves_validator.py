"""
Validator for query_pair_reserves

Validates:
1. Query execution success
2. Return format (reserve0, reserve1, blockTimestampLast fields)
3. Reserve values correctness
"""

from typing import Dict, Any


class QueryPairReservesValidator:
    """Validator for PancakeSwap pair reserves query"""
    
    def __init__(
        self,
        pair_address: str,
        token0_address: str,
        token1_address: str,
        token0_symbol: str,
        token1_symbol: str,
        token0_decimals: int = 18,
        token1_decimals: int = 18,
        **kwargs
    ):
        """
        Initialize validator
        
        Args:
            pair_address: Pair contract address
            token0_address: Token0 address
            token1_address: Token1 address
            token0_symbol: Token0 symbol
            token1_symbol: Token1 symbol
            token0_decimals: Token0 decimal places
            token1_decimals: Token1 decimal places
        """
        self.pair_address = pair_address.lower()
        self.token0_address = token0_address.lower()
        self.token1_address = token1_address.lower()
        self.token0_symbol = token0_symbol
        self.token1_symbol = token1_symbol
        self.token0_decimals = token0_decimals
        self.token1_decimals = token1_decimals
        
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate query result
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: State before query (contains actual reserves)
            state_after: State after query (not used for queries)
            
        Returns:
            Validation result dictionary
        """
        result = {
            'passed': False,
            'score': 0,
            'max_score': 100,
            'checks': [],
            'feedback': ''
        }
        
        # Extract query result and actual values
        query_result = tx.get('query_result', {})
        actual_reserve0 = state_before.get('reserve0', 0)
        actual_reserve1 = state_before.get('reserve1', 0)
        actual_timestamp = state_before.get('blockTimestampLast', 0)
        
        # Check 1: Query execution success (30 points)
        if query_result.get('success'):
            result['score'] += 30
            result['checks'].append({
                'name': 'Query Execution Success',
                'passed': True,
                'points': 30,
                'message': 'Query executed successfully'
            })
        else:
            result['checks'].append({
                'name': 'Query Execution Success',
                'passed': False,
                'points': 0,
                'message': f"Query failed: {query_result.get('error', 'Unknown error')}"
            })
            result['feedback'] = '❌ Query execution failed. Please check your code.'
            return result
        
        data = query_result.get('data', {})
        
        # Check 2: Return format (30 points)
        required_fields = ['reserve0', 'reserve1', 'blockTimestampLast']
        missing_fields = [f for f in required_fields if f not in data]
        
        if not missing_fields:
            result['score'] += 30
            result['checks'].append({
                'name': 'Return Format Correct',
                'passed': True,
                'points': 30,
                'message': f"All required fields present: {required_fields}"
            })
        else:
            result['checks'].append({
                'name': 'Return Format Correct',
                'passed': False,
                'points': 0,
                'message': f"Missing fields: {missing_fields}. Got: {list(data.keys())}"
            })
            result['feedback'] = f"❌ Return format incorrect. Missing: {missing_fields}"
            return result
        
        # Check 3: Reserves correctness (40 points)
        returned_reserve0 = data.get('reserve0', '0')
        returned_reserve1 = data.get('reserve1', '0')
        returned_timestamp = data.get('blockTimestampLast', '0')
        
        # Convert to int for comparison (handle both string and int)
        try:
            returned_reserve0 = int(returned_reserve0) if isinstance(returned_reserve0, str) else returned_reserve0
            returned_reserve1 = int(returned_reserve1) if isinstance(returned_reserve1, str) else returned_reserve1
            returned_timestamp = int(returned_timestamp) if isinstance(returned_timestamp, str) else returned_timestamp
        except (ValueError, TypeError) as e:
            result['checks'].append({
                'name': 'Reserves Correctness',
                'passed': False,
                'points': 0,
                'message': f"Failed to parse reserve values: {e}"
            })
            result['feedback'] = "❌ Reserve values must be numbers"
            return result
        
        # Check if reserves match (allow small tolerance for concurrent queries)
        # Since reserves can change between our query and LLM's query, we just check they're reasonable
        reserve0_match = returned_reserve0 == actual_reserve0
        reserve1_match = returned_reserve1 == actual_reserve1
        timestamp_match = returned_timestamp == actual_timestamp
        
        if reserve0_match and reserve1_match and timestamp_match:
            result['score'] += 40
            result['checks'].append({
                'name': 'Reserves Correctness',
                'passed': True,
                'points': 40,
                'message': f"Reserve0: {returned_reserve0}, Reserve1: {returned_reserve1}, Timestamp: {returned_timestamp}"
            })
            result['passed'] = True
            result['feedback'] = '🎉 Congratulations! Pair reserves queried correctly!'
        else:
            # Partial credit: if reserves are close (within 1% tolerance due to potential trades)
            tolerance = 0.01
            reserve0_close = abs(returned_reserve0 - actual_reserve0) / max(actual_reserve0, 1) < tolerance if actual_reserve0 > 0 else returned_reserve0 == 0
            reserve1_close = abs(returned_reserve1 - actual_reserve1) / max(actual_reserve1, 1) < tolerance if actual_reserve1 > 0 else returned_reserve1 == 0
            
            if reserve0_close and reserve1_close:
                # Give partial credit if very close (concurrent trading scenario)
                result['score'] += 35
                result['checks'].append({
                    'name': 'Reserves Correctness',
                    'passed': True,
                    'points': 35,
                    'message': f"Reserves are within tolerance. Expected: ({actual_reserve0}, {actual_reserve1}), Got: ({returned_reserve0}, {returned_reserve1})"
                })
                result['passed'] = True
                result['feedback'] = '✅ Reserves queried correctly (minor difference due to concurrent trades)'
            else:
                result['checks'].append({
                    'name': 'Reserves Correctness',
                    'passed': False,
                    'points': 0,
                    'message': f"Expected: ({actual_reserve0}, {actual_reserve1}, {actual_timestamp}), Got: ({returned_reserve0}, {returned_reserve1}, {returned_timestamp})"
                })
                result['feedback'] = f"❌ Reserve values incorrect. Expected reserve0={actual_reserve0}, reserve1={actual_reserve1}"
        
        return result

