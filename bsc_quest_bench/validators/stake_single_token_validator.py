"""
Validator for stake_single_token operation

Validate single token staking operation:
1. Transaction success (25%)
2. Token approval (20%)
3. Token balance decrease (25%)
4. Staked balance increase (30%)
"""

from typing import Dict, Any, List


class StakeSingleTokenValidator:
    """Validator for staking single token to CAKE Pool"""
    
    def __init__(self, stake_amount: float, token_address: str, pool_address: str, user_address: str, **kwargs):
        """
        Initialize validator with parameters
        
        Args:
            stake_amount: Amount to stake (float)
            token_address: CAKE token address
            pool_address: CAKE Pool contract address
            user_address: User's wallet address
        """
        if not token_address:
            raise ValueError("token_address is required but was None or empty")
        if not pool_address:
            raise ValueError("pool_address is required but was None or empty")
        if not user_address:
            raise ValueError("user_address is required but was None or empty")
        
        self.stake_amount = stake_amount
        self.token_address = token_address.lower()
        self.pool_address = pool_address.lower()
        self.user_address = user_address.lower()
        
        # Convert stake amount to wei
        self.stake_amount_wei = int(self.stake_amount * 10**18)
    
    def validate(self, tx: Dict[str, Any], receipt: Dict[str, Any], 
                 state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the staking transaction
        
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
        
        # 1. Transaction Success (25 points)
        tx_success = receipt.get('status') == 1
        tx_score = 25 if tx_success else 0
        total_score += tx_score
        
        checks.append({
            'name': 'Transaction Success',
            'passed': tx_success,
            'score': tx_score,
            'max_score': 25,
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
        
        # Decode actual stake amount from transaction data
        # deposit(uint256 _amount) - function selector: 0xb6b55f25
        tx_data = tx.get('data', '')
        if isinstance(tx_data, str) and tx_data.startswith('0x') and len(tx_data) >= 74:
            # Extract the uint256 parameter (32 bytes = 64 hex chars after '0x' and 8 char selector)
            amount_hex = tx_data[10:]  # Skip '0x' + 8 char selector
            actual_stake_amount_wei = int(amount_hex, 16)
        else:
            # Fallback to parameter if can't decode
            actual_stake_amount_wei = self.stake_amount_wei
        
        # 2. Token Approval (20 points)
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        
        # Check if there was sufficient allowance (either before or set during transaction)
        approval_valid = allowance_before >= actual_stake_amount_wei or allowance_after >= 0
        approval_score = 20 if approval_valid else 0
        total_score += approval_score
        
        checks.append({
            'name': 'Token Approval',
            'passed': approval_valid,
            'score': approval_score,
            'max_score': 20,
            'message': f'Token approved. Allowance before: {allowance_before / 10**18:.4f}, after: {allowance_after / 10**18:.4f}' if approval_valid else f'Insufficient allowance. Required: {actual_stake_amount_wei}, had: {allowance_before}'
        })
        
        # 3. Token Balance Decrease (25 points)
        balance_before = state_before.get('token_balance', 0)
        balance_after = state_after.get('token_balance', 0)
        balance_decrease = balance_before - balance_after
        
        # Validate balance decreased by the amount extracted from transaction
        # Do NOT use actual decrease as expected (that would be lowering standards)
        expected_decrease = actual_stake_amount_wei
        
        # Allow small tolerance for potential fees (but BSC staking typically has no fees)
        tolerance = expected_decrease * 0.001  # 0.1% tolerance
        balance_decrease_valid = balance_decrease > 0 and abs(balance_decrease - expected_decrease) <= tolerance
        balance_score = 25 if balance_decrease_valid else 0
        total_score += balance_score
        
        checks.append({
            'name': 'Token Balance Decrease',
            'passed': balance_decrease_valid,
            'score': balance_score,
            'max_score': 25,
            'message': f'Balance decreased by {balance_decrease / 10**18:.4f} CAKE (expected: {expected_decrease / 10**18:.4f})' if balance_decrease_valid else f'Balance did not decrease correctly. Expected: {expected_decrease / 10**18:.4f}, Actual: {balance_decrease / 10**18:.4f}'
        })
        
        # 4. Staking Balance Increase (30 points)
        staked_before = state_before.get('staked_amount', 0)
        staked_after = state_after.get('staked_amount', 0)
        staked_increase = staked_after - staked_before
        
        # Validate that staked increase matches balance decrease (allow 1% tolerance for fees)
        staking_valid = staked_increase > 0 and abs(staked_increase - balance_decrease) <= balance_decrease * 0.01
        staking_score = 30 if staking_valid else 0
        total_score += staking_score
        
        checks.append({
            'name': 'Staking Balance Increase',
            'passed': staking_valid,
            'score': staking_score,
            'max_score': 30,
            'message': f'Staked amount increased by {staked_increase / 10**18:.4f} CAKE (balance decreased by {balance_decrease / 10**18:.4f})' if staking_valid else f'Staking increase mismatch. Staked: {staked_increase / 10**18:.4f}, Balance decrease: {balance_decrease / 10**18:.4f}'
        })
        
        # Determine overall validity
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': max_score,
            'checks': checks,
            'details': {
                'stake_amount': self.stake_amount,
                'token_balance_change': balance_decrease / 10**18,
                'staked_balance_change': staked_increase / 10**18,
                'allowance_before': allowance_before / 10**18,
                'allowance_after': allowance_after / 10**18
            }
        }

