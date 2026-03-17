"""
Validator for query_token_metadata atomic problem.
Validates that the LLM correctly queries ERC20 token metadata including name, symbol, decimals, and totalSupply.
"""

from typing import Dict, Any


class QueryTokenMetadataValidator:
    """Validator for ERC20 token metadata query operations"""
    
    def __init__(
        self,
        token_address: str,
        expected_name: str,
        expected_symbol: str,
        expected_decimals: int
    ):
        """
        Initialize validator with token metadata parameters.
        
        Args:
            token_address: ERC20 token contract address
            expected_name: Expected token name
            expected_symbol: Expected token symbol
            expected_decimals: Expected token decimals
        """
        self.token_address = token_address.lower()
        self.expected_name = expected_name
        self.expected_symbol = expected_symbol
        self.expected_decimals = expected_decimals
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the token metadata query result.
        
        Scoring:
        - Query execution success: 25 points
        - Return format correctness: 25 points
        - Name correctness: 15 points
        - Symbol correctness: 15 points
        - Decimals correctness: 20 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains actual metadata if available)
            state_after: Not used for query operations
            
        Returns:
            Validation result with score and feedback
        """
        # For query operations, the query result is in 'tx'
        query_result = tx.get('query_result', {})
        score = 0
        max_score = 100
        checks = []
        feedback_parts = []
        
        # Get expected values from state_before if set by quest_executor
        expected_name = state_before.get('token_name', self.expected_name)
        expected_symbol = state_before.get('token_symbol', self.expected_symbol)
        expected_decimals = state_before.get('token_decimals', self.expected_decimals)
        expected_total_supply = state_before.get('token_total_supply')
        
        # Check 1: Query execution success (25 points)
        query_success = query_result.get('success', False)
        error_msg = query_result.get('error', '')
        
        if query_success:
            score += 25
            checks.append({
                'name': 'Query Execution Success',
                'passed': True,
                'message': 'Query executed successfully'
            })
        else:
            checks.append({
                'name': 'Query Execution Success',
                'passed': False,
                'message': f"Query execution failed: {error_msg}"
            })
            return {
                'passed': False,
                'score': score,
                'max_score': max_score,
                'checks': checks,
                'feedback': '❌ Query execution failed'
            }
        
        # Extract data from query result
        data = query_result.get('data', {})
        
        # Check 2: Return format correctness (25 points)
        required_fields = ['name', 'symbol', 'decimals', 'totalSupply']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            score += 25
            checks.append({
                'name': 'Return Format Correct',
                'passed': True,
                'message': f'All required fields present: {required_fields}'
            })
        else:
            checks.append({
                'name': 'Return Format Correct',
                'passed': False,
                'message': f'Missing required fields: {missing_fields}'
            })
            feedback_parts.append(f"⚠️  Missing fields: {', '.join(missing_fields)}")
        
        # Check 3: Name correctness (15 points)
        returned_name = data.get('name', '')
        if returned_name == expected_name:
            score += 15
            checks.append({
                'name': 'Name Correctness',
                'passed': True,
                'message': f'Token name correct: {returned_name}'
            })
        else:
            checks.append({
                'name': 'Name Correctness',
                'passed': False,
                'message': f'Name mismatch - Expected: {expected_name}, Got: {returned_name}'
            })
            feedback_parts.append(f"⚠️  Name mismatch")
        
        # Check 4: Symbol correctness (15 points)
        returned_symbol = data.get('symbol', '')
        if returned_symbol == expected_symbol:
            score += 15
            checks.append({
                'name': 'Symbol Correctness',
                'passed': True,
                'message': f'Token symbol correct: {returned_symbol}'
            })
        else:
            checks.append({
                'name': 'Symbol Correctness',
                'passed': False,
                'message': f'Symbol mismatch - Expected: {expected_symbol}, Got: {returned_symbol}'
            })
            feedback_parts.append(f"⚠️  Symbol mismatch")
        
        # Check 5: Decimals correctness (20 points)
        try:
            returned_decimals = int(data.get('decimals', 0))
            if returned_decimals == expected_decimals:
                score += 20
                checks.append({
                    'name': 'Decimals Correctness',
                    'passed': True,
                    'message': f'Token decimals correct: {returned_decimals}'
                })
            else:
                checks.append({
                    'name': 'Decimals Correctness',
                    'passed': False,
                    'message': f'Decimals mismatch - Expected: {expected_decimals}, Got: {returned_decimals}'
                })
                feedback_parts.append(f"⚠️  Decimals mismatch")
        except (ValueError, TypeError) as e:
            checks.append({
                'name': 'Decimals Correctness',
                'passed': False,
                'message': f'Failed to parse decimals: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse decimals")
        
        # Bonus: Verify totalSupply is present and is a valid number (no points, just feedback)
        try:
            returned_total_supply = data.get('totalSupply', '0')
            if isinstance(returned_total_supply, str):
                total_supply_value = int(returned_total_supply)
            else:
                total_supply_value = int(returned_total_supply)
            
            # If we have expected total supply from chain, verify it matches
            if expected_total_supply is not None:
                if total_supply_value == expected_total_supply:
                    feedback_parts.append(f"✅ Total supply verified: {total_supply_value}")
                else:
                    feedback_parts.append(f"ℹ️  Total supply: {total_supply_value} (expected: {expected_total_supply})")
        except (ValueError, TypeError):
            pass
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! Token metadata queried correctly!"
        elif score >= 60:
            feedback = "✅ Query mostly correct. " + " ".join(feedback_parts)
        else:
            feedback = "❌ Query needs improvement. " + " ".join(feedback_parts)
        
        return {
            'passed': score >= 60,  # Pass threshold: 60%
            'score': score,
            'max_score': max_score,
            'checks': checks,
            'feedback': feedback
        }

