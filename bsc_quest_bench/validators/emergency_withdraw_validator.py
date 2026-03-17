from typing import Dict, Any, List

class EmergencyWithdrawValidator:
    """Validator for emergency_withdraw operation"""
    
    def __init__(self, lp_token_address: str, reward_token_address: str, 
                 pool_address: str, user_address: str, **kwargs):
        if not lp_token_address:
            raise ValueError("lp_token_address is required but was None or empty")
        if not reward_token_address:
            raise ValueError("reward_token_address is required but was None or empty")
        if not pool_address:
            raise ValueError("pool_address is required but was None or empty")
        if not user_address:
            raise ValueError("user_address is required but was None or empty")
        
        self.lp_token_address = lp_token_address.lower()
        self.reward_token_address = reward_token_address.lower()
        self.pool_address = pool_address.lower()
        self.user_address = user_address.lower()
    
    def validate(self, tx: Dict[str, Any], receipt: Dict[str, Any], 
                 state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate emergency withdraw operation
        
        Checks:
        1. Transaction success (30 points)
        2. LP token full return (40 points) - ALL staked tokens returned
        3. Staking record cleared (20 points) - staked_amount becomes 0
        4. Rewards not claimed (10 points) - CAKE balance unchanged
        """
        checks = []
        total_score = 0
        max_score = 100
        
        # 1. Transaction Success (30 points)
        tx_success = receipt.get('status') == 1
        tx_score = 30 if tx_success else 0
        total_score += tx_score
        
        checks.append({
            'name': 'Transaction Success',
            'passed': tx_success,
            'score': tx_score,
            'max_score': 30,
            'message': 'Transaction executed successfully' if tx_success else f'Transaction failed with status: {receipt.get("status")}'
        })
        
        if not tx_success:
            return {
                'passed': False,
                'score': total_score,
                'max_score': max_score,
                'checks': checks,
                'error': 'Transaction failed'
            }
        
        # Get state changes
        staked_before = state_before.get('staked_amount', 0)
        staked_after = state_after.get('staked_amount', 0)
        
        lp_balance_before = state_before.get('lp_token_balance', 0)
        lp_balance_after = state_after.get('lp_token_balance', 0)
        lp_balance_increase = lp_balance_after - lp_balance_before
        
        reward_balance_before = state_before.get('token_balance', 0)  # CAKE
        reward_balance_after = state_after.get('token_balance', 0)
        reward_increase = reward_balance_after - reward_balance_before
        
        # 2. LP Token Full Return (40 points)
        # All staked tokens should be returned
        lp_return_valid = abs(lp_balance_increase - staked_before) <= staked_before * 0.01
        lp_score = 40 if lp_return_valid else 0
        total_score += lp_score
        
        checks.append({
            'name': 'LP Token Full Return',
            'passed': lp_return_valid,
            'score': lp_score,
            'max_score': 40,
            'message': f'All LP tokens returned: {lp_balance_increase / 10**18:.4f} (expected: {staked_before / 10**18:.4f})' if lp_return_valid else f'LP return mismatch. Expected: {staked_before / 10**18:.4f}, actual: {lp_balance_increase / 10**18:.4f}'
        })
        
        # 3. Staking Record Cleared (20 points)
        # Staked amount should be 0
        record_cleared = staked_after == 0
        record_score = 20 if record_cleared else 0
        total_score += record_score
        
        checks.append({
            'name': 'Staking Record Cleared',
            'passed': record_cleared,
            'score': record_score,
            'max_score': 20,
            'message': f'Staking record cleared (amount = 0)' if record_cleared else f'Staking record not cleared. Remaining: {staked_after / 10**18:.4f}'
        })
        
        # 4. Rewards Not Claimed (10 points)
        # CAKE balance should not increase significantly (allow tiny rounding)
        rewards_forfeited = abs(reward_increase) < (1 * 10**15)  # Less than 0.001 CAKE
        rewards_score = 10 if rewards_forfeited else 0
        total_score += rewards_score
        
        checks.append({
            'name': 'Rewards Not Claimed',
            'passed': rewards_forfeited,
            'score': rewards_score,
            'max_score': 10,
            'message': f'Rewards correctly forfeited (CAKE balance unchanged)' if rewards_forfeited else f'Rewards were claimed! CAKE increased by {reward_increase / 10**18:.4f} (should be ~0)'
        })
        
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': max_score,
            'checks': checks,
            'details': {
                'staked_before': staked_before / 10**18,
                'staked_after': staked_after / 10**18,
                'lp_balance_change': lp_balance_increase / 10**18,
                'reward_balance_change': reward_increase / 10**18,
                'all_tokens_returned': lp_return_valid,
                'record_cleared': record_cleared,
                'rewards_forfeited': rewards_forfeited
            }
        }

