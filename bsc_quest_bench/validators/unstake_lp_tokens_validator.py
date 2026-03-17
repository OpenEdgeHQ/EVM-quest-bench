"""
Unstake LP Tokens Validator

Validates the withdrawal of staked LP tokens from a farming pool.
"""

from typing import Dict, Any
from decimal import Decimal


class UnstakeLPTokensValidator:
    """Validator for unstake LP tokens operation"""
    
    def __init__(
        self,
        pool_address: str,
        unstake_amount: float,
        lp_token_address: str,
        user_address: str
    ):
        self.pool_address = pool_address.lower()
        self.lp_token_address = lp_token_address.lower()
        self.user_address = user_address.lower()
        
        # Use Decimal for precise calculation
        self.expected_unstake_amount = int(Decimal(str(unstake_amount)) * Decimal(10 ** 18))
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate unstake LP tokens operation
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result dictionary
            
        Checks:
        1. Transaction success (30%)
        2. LP token balance increased correctly (40%)
        3. Staked amount decreased correctly (30%)
        """
        
        checks = []
        score = 0
        details = {
            'pool_address': self.pool_address,
            'lp_token_address': self.lp_token_address,
            'user_address': self.user_address,
            'expected_unstake_amount': self.expected_unstake_amount
        }
        
        # Check 1: Transaction success (30 points)
        tx_success = receipt.get('status') == 1
        if tx_success:
            score += 30
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'points': 30,
                'message': 'Withdraw transaction executed successfully'
            })
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'points': 0,
                'message': f"Transaction failed with status: {receipt.get('status')}"
            })
            # Early return on transaction failure
            return {
                'score': score,
                'max_score': self.max_score,
                'passed': False,
                'checks': checks,
                'details': details
            }
        
        # Decode actual unstake amount from transaction data
        tx_data = tx.get('data', '')
        actual_unstake_amount_wei = self.expected_unstake_amount
        
        if isinstance(tx_data, str) and tx_data.startswith('0x') and len(tx_data) >= 74:
            # withdraw(uint256 _amount) function
            # Skip function selector (first 10 chars: 0x + 8 hex chars)
            amount_hex = tx_data[10:74]  # 64 hex chars = 32 bytes
            try:
                actual_unstake_amount_wei = int(amount_hex, 16)
            except ValueError:
                pass
        
        details['actual_unstake_amount'] = actual_unstake_amount_wei
        
        # Check 2: LP token balance increased (40 points)
        lp_balance_before = state_before.get('lp_token_balance', 0)
        lp_balance_after = state_after.get('lp_token_balance', 0)
        lp_balance_increase = lp_balance_after - lp_balance_before
        
        details['lp_balance_before'] = lp_balance_before
        details['lp_balance_after'] = lp_balance_after
        details['lp_balance_increase'] = lp_balance_increase
        
        # Allow 1% tolerance for potential fees or rounding
        tolerance = Decimal(str(actual_unstake_amount_wei)) * Decimal('0.01')
        balance_increase_valid = (
            lp_balance_increase > 0 and 
            abs(Decimal(str(lp_balance_increase)) - Decimal(str(actual_unstake_amount_wei))) <= tolerance
        )
        
        if balance_increase_valid:
            score += 40
            checks.append({
                'name': 'LP Token Balance Increase',
                'passed': True,
                'points': 40,
                'message': f'LP token balance correctly increased by {lp_balance_increase / 10**18:.4f} tokens',
                'details': {
                    'expected': actual_unstake_amount_wei / 10**18,
                    'actual': lp_balance_increase / 10**18
                }
            })
        else:
            checks.append({
                'name': 'LP Token Balance Increase',
                'passed': False,
                'points': 0,
                'message': f'LP balance increase mismatch. Expected: ~{actual_unstake_amount_wei / 10**18:.4f}, Got: {lp_balance_increase / 10**18:.4f}',
                'details': {
                    'expected': actual_unstake_amount_wei / 10**18,
                    'actual': lp_balance_increase / 10**18
                }
            })
        
        # Check 3: Staked amount decreased (30 points)
        staked_before = state_before.get('staked_amount', 0)
        staked_after = state_after.get('staked_amount', 0)
        staked_decrease = staked_before - staked_after
        
        details['staked_before'] = staked_before
        details['staked_after'] = staked_after
        details['staked_decrease'] = staked_decrease
        
        staked_decrease_valid = (
            staked_decrease > 0 and 
            abs(Decimal(str(staked_decrease)) - Decimal(str(actual_unstake_amount_wei))) <= tolerance
        )
        
        if staked_decrease_valid:
            score += 30
            checks.append({
                'name': 'Staked Amount Decrease',
                'passed': True,
                'points': 30,
                'message': f'Staked amount correctly decreased by {staked_decrease / 10**18:.4f} tokens',
                'details': {
                    'expected': actual_unstake_amount_wei / 10**18,
                    'actual': staked_decrease / 10**18
                }
            })
        else:
            checks.append({
                'name': 'Staked Amount Decrease',
                'passed': False,
                'points': 0,
                'message': f'Staked decrease mismatch. Expected: ~{actual_unstake_amount_wei / 10**18:.4f}, Got: {staked_decrease / 10**18:.4f}',
                'details': {
                    'expected': actual_unstake_amount_wei / 10**18,
                    'actual': staked_decrease / 10**18
                }
            })
        
        # Determine overall pass/fail
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': all_passed,
            'checks': checks,
            'details': details
        }

