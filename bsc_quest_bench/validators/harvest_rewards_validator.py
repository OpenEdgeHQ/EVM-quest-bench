"""
Validator for harvest_rewards operation

Validate harvest rewards operation:
1. Transaction success (30%)
2. Reward token balance increase (70%)
"""

from typing import Dict, Any, List


class HarvestRewardsValidator:
    """Validator for harvesting farming rewards"""
    
    def __init__(self, reward_token_address: str, pool_address: str, user_address: str, **kwargs):
        """
        Initialize validator with parameters
        
        Args:
            reward_token_address: Reward token (CAKE) address
            pool_address: Reward pool contract address
            user_address: User's wallet address
        """
        if not reward_token_address:
            raise ValueError("reward_token_address is required but was None or empty")
        if not pool_address:
            raise ValueError("pool_address is required but was None or empty")
        if not user_address:
            raise ValueError("user_address is required but was None or empty")
        
        self.reward_token_address = reward_token_address.lower()
        self.pool_address = pool_address.lower()
        self.user_address = user_address.lower()
    
    def validate(self, tx: Dict[str, Any], receipt: Dict[str, Any], 
                 state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the harvest transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: Chain state before transaction
            state_after: Chain state after transaction
            
        Returns:
            Dictionary with validation results
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
        
        # 2. Reward Token Balance Increase (70 points)
        reward_balance_before = state_before.get('token_balance', 0)
        reward_balance_after = state_after.get('token_balance', 0)
        reward_increase = reward_balance_after - reward_balance_before
        
        # Validate that reward balance increased (any positive amount)
        reward_valid = reward_increase > 0
        reward_score = 70 if reward_valid else 0
        total_score += reward_score
        
        checks.append({
            'name': 'Reward Token Balance Increase',
            'passed': reward_valid,
            'score': reward_score,
            'max_score': 70,
            'message': f'Reward balance increased by {reward_increase / 10**18:.6f} CAKE' if reward_valid else f'Reward balance did not increase. Before: {reward_balance_before / 10**18:.6f}, After: {reward_balance_after / 10**18:.6f}'
        })
        
        # Determine overall validity
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': max_score,
            'checks': checks,
            'details': {
                'reward_increase': reward_increase / 10**18,
                'reward_balance_before': reward_balance_before / 10**18,
                'reward_balance_after': reward_balance_after / 10**18
            }
        }

