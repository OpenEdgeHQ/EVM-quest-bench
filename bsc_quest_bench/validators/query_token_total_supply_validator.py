"""
Validator for query_token_total_supply atomic problem.
Validates that the LLM correctly queries ERC20 token total supply.
"""

from typing import Dict, Any


class QueryTokenTotalSupplyValidator:
    """Validator for ERC20 token total supply query operations"""
    
    def __init__(
        self,
        token_address: str,
        token_decimals: int,
        token_symbol: str = "TOKEN"
    ):
        """
        Initialize validator with token parameters.
        
        Args:
            token_address: ERC20 token contract address
            token_decimals: Token decimals for formatting
            token_symbol: Token symbol for display
        """
        self.token_address = token_address.lower()
        self.token_decimals = token_decimals
        self.token_symbol = token_symbol
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the token total supply query result.
        
        Scoring:
        - Query execution success: 40 points
        - Return format correctness: 30 points
        - Total supply correctness: 30 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains actual total supply if available)
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
        
        # Get expected total supply from state_before if set by quest_executor
        expected_total_supply = state_before.get('token_total_supply')
        
        # Check 1: Query execution success (40 points)
        query_success = query_result.get('success', False)
        error_msg = query_result.get('error', '')
        
        if query_success:
            score += 40
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
        
        # Check 2: Return format correctness (30 points)
        required_fields = ['totalSupply']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            score += 30
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
        
        # Check 3: Total supply correctness (30 points)
        # NOTE: Use 0.1% tolerance because supply may change due to minting/burning
        if expected_total_supply is not None:
            try:
                # Parse total supply from query result
                returned_total_supply = data.get('totalSupply', '0')
                if isinstance(returned_total_supply, str):
                    returned_total_supply_wei = int(returned_total_supply)
                else:
                    returned_total_supply_wei = int(returned_total_supply)
                
                # Check if amounts match (with 0.1% tolerance for potential minting/burning)
                if expected_total_supply > 0:
                    amount_diff_percent = abs(returned_total_supply_wei - expected_total_supply) / expected_total_supply * 100
                else:
                    # If expected is 0, check if returned is also 0
                    amount_diff_percent = 0 if returned_total_supply_wei == 0 else 100
                
                if amount_diff_percent <= 0.1:  # 0.1% tolerance
                    score += 30
                    checks.append({
                        'name': 'Total Supply Correctness',
                        'passed': True,
                        'message': f'Total supply: {returned_total_supply_wei} wei ({returned_total_supply_wei / 10**self.token_decimals:.6f} {self.token_symbol})'
                    })
                    feedback_parts.append("✅ Total supply queried correctly!")
                else:
                    # Partial score based on difference
                    partial_score = max(0, int(30 * (1 - amount_diff_percent / 10)))
                    score += partial_score
                    checks.append({
                        'name': 'Total Supply Correctness',
                        'passed': False,
                        'message': f'Supply mismatch - Expected: {expected_total_supply} wei, Got: {returned_total_supply_wei} wei (diff: {amount_diff_percent:.2f}%)'
                    })
                    feedback_parts.append(f"⚠️  Total supply difference: {amount_diff_percent:.2f}% (tolerance: 0.1%)")
            except (ValueError, KeyError, TypeError) as e:
                checks.append({
                    'name': 'Total Supply Correctness',
                    'passed': False,
                    'message': f'Failed to parse total supply: {str(e)}'
                })
                feedback_parts.append(f"❌ Failed to parse total supply: {str(e)}")
        else:
            # No expected value to compare against
            checks.append({
                'name': 'Total Supply Correctness',
                'passed': False,
                'message': 'No expected total supply available for comparison'
            })
            feedback_parts.append("⚠️  Cannot verify total supply: no expected value")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! Token total supply queried correctly!"
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

