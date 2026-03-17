"""
Validator for query_pending_rewards atomic problem.
Validates that the LLM correctly queries pending rewards using the SimpleRewardPool contract's pendingReward function.
"""

from typing import Dict, Any


class QueryPendingRewardsValidator:
    """Validator for staking pool pending rewards query operations"""
    
    def __init__(
        self,
        pool_address: str,
        query_address: str,
        expected_pending_rewards: float,
        reward_token_decimals: int = 18
    ):
        """
        Initialize validator with pending rewards query parameters.
        
        Args:
            pool_address: SimpleRewardPool contract address
            query_address: User address to query pending rewards for
            expected_pending_rewards: Expected pending rewards amount (in token units)
            reward_token_decimals: Reward token decimals (default: 18 for CAKE)
        """
        self.pool_address = pool_address.lower()
        self.query_address = query_address.lower()
        self.expected_pending_rewards = expected_pending_rewards
        self.reward_token_decimals = reward_token_decimals
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the pending rewards query result.
        
        Scoring:
        - Query execution success: 30 points
        - Return format correctness: 30 points
        - Pending rewards correctness: 40 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains actual pending rewards if available)
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
        
        # Get expected pending rewards from state_before if set by quest_executor
        expected_pending_rewards_wei = state_before.get('pending_rewards')
        if expected_pending_rewards_wei is None:
            # Calculate from expected_pending_rewards parameter
            from decimal import Decimal
            expected_pending_rewards_wei = int(Decimal(str(self.expected_pending_rewards)) * Decimal(10**self.reward_token_decimals))
        
        # Check 1: Query execution success (30 points)
        query_success = query_result.get('success', False)
        error_msg = query_result.get('error', '')
        
        if query_success:
            score += 30
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
        required_fields = ['pending_rewards']
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
        
        # Check 3: Pending rewards correctness (40 points)
        # NOTE: Use 5% tolerance because rewards accumulate over time
        try:
            # Parse pending rewards from query result
            returned_pending_rewards = data.get('pending_rewards', '0')
            if isinstance(returned_pending_rewards, str):
                returned_pending_rewards_wei = int(returned_pending_rewards)
            else:
                returned_pending_rewards_wei = int(returned_pending_rewards)
            
            # Check if amounts match (with 5% tolerance for time-based accumulation)
            if expected_pending_rewards_wei > 0:
                amount_diff_percent = abs(returned_pending_rewards_wei - expected_pending_rewards_wei) / expected_pending_rewards_wei * 100
            else:
                # If expected is 0, check if returned is also 0
                amount_diff_percent = 0 if returned_pending_rewards_wei == 0 else 100
            
            if amount_diff_percent <= 5:  # 5% tolerance for time-based accumulation
                score += 40
                checks.append({
                    'name': 'Pending Rewards Correctness',
                    'passed': True,
                    'message': f'Pending rewards: {returned_pending_rewards_wei} wei ({returned_pending_rewards_wei / 10**self.reward_token_decimals:.6f} tokens)'
                })
                feedback_parts.append("✅ Pending rewards queried correctly!")
            else:
                # Partial score based on difference
                partial_score = max(0, int(40 * (1 - amount_diff_percent / 20)))
                score += partial_score
                checks.append({
                    'name': 'Pending Rewards Correctness',
                    'passed': False,
                    'message': f'Amount mismatch - Expected: {expected_pending_rewards_wei} wei, Got: {returned_pending_rewards_wei} wei (diff: {amount_diff_percent:.2f}%)'
                })
                feedback_parts.append(f"⚠️  Pending rewards difference: {amount_diff_percent:.2f}% (tolerance: 5%)")
        except (ValueError, KeyError, TypeError) as e:
            checks.append({
                'name': 'Pending Rewards Correctness',
                'passed': False,
                'message': f'Failed to parse pending rewards: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse pending rewards: {str(e)}")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! Pending rewards queried correctly!"
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

