"""
Validator for query_swap_output_amount

Validates:
1. Query execution success
2. Return format (amounts array)
3. Output amount correctness
"""

from typing import Dict, Any


class QuerySwapOutputAmountValidator:
    """Validator for PancakeSwap swap output amount query"""
    
    def __init__(
        self,
        router_address: str,
        token_in_address: str,
        token_out_address: str,
        token_in_symbol: str,
        token_out_symbol: str,
        amount_in: float,
        token_in_decimals: int = 18,
        token_out_decimals: int = 18,
        **kwargs
    ):
        """
        Initialize validator
        
        Args:
            router_address: Router contract address
            token_in_address: Input token address
            token_out_address: Output token address
            token_in_symbol: Input token symbol
            token_out_symbol: Output token symbol
            amount_in: Input amount
            token_in_decimals: Input token decimals
            token_out_decimals: Output token decimals
        """
        self.router_address = router_address.lower()
        self.token_in_address = token_in_address.lower()
        self.token_out_address = token_out_address.lower()
        self.token_in_symbol = token_in_symbol
        self.token_out_symbol = token_out_symbol
        self.amount_in = amount_in
        self.token_in_decimals = token_in_decimals
        self.token_out_decimals = token_out_decimals
        
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
            state_before: State before query (contains actual amounts from router)
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
        actual_amounts = state_before.get('expected_amounts', [])
        
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
        if 'amounts' in data:
            result['score'] += 30
            result['checks'].append({
                'name': 'Return Format Correct',
                'passed': True,
                'points': 30,
                'message': f"Expected 'amounts' array in result. Got: {list(data.keys())}"
            })
        else:
            result['checks'].append({
                'name': 'Return Format Correct',
                'passed': False,
                'points': 0,
                'message': f"Missing 'amounts' field. Got: {list(data.keys())}"
            })
            result['feedback'] = "❌ Return format incorrect. Expected 'amounts' array."
            return result
        
        # Check 3: Output amount correctness (40 points)
        returned_amounts = data.get('amounts', [])
        
        # Convert to list of ints for comparison
        try:
            if isinstance(returned_amounts, str):
                # If it's a string, try to parse as JSON array
                import json
                returned_amounts = json.loads(returned_amounts)
            
            returned_amounts = [int(amt) if isinstance(amt, str) else amt for amt in returned_amounts]
        except (ValueError, TypeError, AttributeError) as e:
            result['checks'].append({
                'name': 'Output Amount Correctness',
                'passed': False,
                'points': 0,
                'message': f"Failed to parse amounts array: {e}"
            })
            result['feedback'] = "❌ Amounts array must be valid array of numbers"
            return result
        
        # Check if amounts array has correct length (should be 2 for direct swap: [amountIn, amountOut])
        if len(returned_amounts) != len(actual_amounts):
            result['checks'].append({
                'name': 'Output Amount Correctness',
                'passed': False,
                'points': 0,
                'message': f"Amounts array length mismatch. Expected {len(actual_amounts)}, got {len(returned_amounts)}"
            })
            result['feedback'] = f"❌ Amounts array should have {len(actual_amounts)} elements"
            return result
        
        # Check if output amount matches (last element in array)
        # Allow small tolerance due to potential price changes between queries
        if len(actual_amounts) > 0:
            actual_output = actual_amounts[-1]
            returned_output = returned_amounts[-1]
            
            # Check exact match first
            if returned_output == actual_output:
                result['score'] += 40
                result['checks'].append({
                    'name': 'Output Amount Correctness',
                    'passed': True,
                    'points': 40,
                    'message': f"Output amount: {returned_output} (matches expected)"
                })
                result['passed'] = True
                result['feedback'] = '🎉 Congratulations! Swap output amount queried correctly!'
            else:
                # Allow 1% tolerance for concurrent trading
                tolerance = 0.01
                if abs(returned_output - actual_output) / max(actual_output, 1) < tolerance:
                    result['score'] += 35
                    result['checks'].append({
                        'name': 'Output Amount Correctness',
                        'passed': True,
                        'points': 35,
                        'message': f"Output amount within tolerance. Expected: {actual_output}, Got: {returned_output}"
                    })
                    result['passed'] = True
                    result['feedback'] = '✅ Output amount correct (minor difference due to concurrent trades)'
                else:
                    result['checks'].append({
                        'name': 'Output Amount Correctness',
                        'passed': False,
                        'points': 0,
                        'message': f"Expected amounts: {actual_amounts}, Got: {returned_amounts}"
                    })
                    result['feedback'] = f"❌ Output amount incorrect. Expected {actual_output}, got {returned_output}"
        else:
            result['checks'].append({
                'name': 'Output Amount Correctness',
                'passed': False,
                'points': 0,
                'message': "Could not verify output amount (no actual amounts available)"
            })
            result['feedback'] = "❌ Could not verify output amount"
        
        return result

