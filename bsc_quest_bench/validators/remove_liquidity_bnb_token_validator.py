"""
Validator for PancakeSwap Remove Liquidity - BNB + Token

This validator checks:
1. Transaction success
2. LP token approval for Router
3. Correct Router contract interaction
4. Correct function call (removeLiquidityETH)
5. LP token balance decrease
6. Token balance increase (receive tokens from pool)
7. BNB balance increase (receive BNB from pool, after gas)
"""

from decimal import Decimal
from typing import Dict, Any


class RemoveLiquidityBNBTokenValidator:
    """Validator for PancakeSwap removeLiquidityETH operation"""
    
    def __init__(
        self,
        router_address: str,
        token_address: str,
        liquidity_percentage: float,
        token_decimals: int = 18,
        slippage: float = 5.0
    ):
        """
        Initialize validator
        
        Args:
            router_address: PancakeSwap Router V2 address
            token_address: Token address paired with BNB
            liquidity_percentage: Percentage of LP tokens to remove
            token_decimals: Token decimals
            slippage: Slippage tolerance percentage
        """
        self.router_address = router_address.lower()
        self.token_address = token_address.lower()
        self.liquidity_percentage = Decimal(str(liquidity_percentage))
        self.token_decimals = token_decimals
        self.slippage = Decimal(str(slippage))
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate remove liquidity transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result with score and checks
        """
        checks = []
        
        # 1. Check transaction success (20 points)
        tx_success = receipt.get('status') == 1
        checks.append({
            'name': 'Transaction Success',
            'passed': tx_success,
            'message': 'Transaction executed successfully' if tx_success else f"Transaction failed with status: {receipt.get('status')}"
        })
        
        if not tx_success:
            # If transaction failed, return early
            return {
                'passed': False,
                'score': 0,
                'max_score': self.max_score,
                'checks': checks
            }
        
        # 2. Check LP token approval (10 points)
        lp_allowance_before = state_before.get('lp_allowance', 0)
        lp_allowance_after = state_after.get('lp_allowance', 0)
        
        lp_approved = lp_allowance_before > 0 or lp_allowance_after > 0
        checks.append({
            'name': 'LP Token Approval',
            'passed': lp_approved,
            'message': f'LP token approved. Allowance before: {lp_allowance_before}, after: {lp_allowance_after}' if lp_approved else f'LP token not approved. Allowance before: {lp_allowance_before}, after: {lp_allowance_after}'
        })
        
        # 3. Check correct Router contract (10 points)
        tx_to = tx.get('to', '').lower()
        router_correct = tx_to == self.router_address
        checks.append({
            'name': 'Correct Router',
            'passed': router_correct,
            'message': f'Correct PancakeSwap Router: {tx_to}' if router_correct else f'Wrong router. Expected: {self.router_address}, Got: {tx_to}'
        })
        
        # 4. Check correct function call (10 points)
        # removeLiquidityETH function selector: 0x02751cec
        tx_data = tx.get('data', '')
        expected_selector = '0x02751cec'
        actual_selector = tx_data[:10] if tx_data else ''
        
        function_correct = actual_selector == expected_selector
        checks.append({
            'name': 'Correct Function',
            'passed': function_correct,
            'message': f'Correct function: removeLiquidityETH ({actual_selector})' if function_correct else f'Wrong function. Expected: {expected_selector}, Got: {actual_selector}'
        })
        
        # 5. Check LP token balance decrease (20 points)
        lp_balance_before = state_before.get('lp_token_balance', 0)
        lp_balance_after = state_after.get('lp_token_balance', 0)
        lp_decrease = lp_balance_before - lp_balance_after
        
        # Calculate expected liquidity to remove
        expected_liquidity = (Decimal(str(lp_balance_before)) * self.liquidity_percentage) / Decimal('100')
        
        # Allow some tolerance (within 1%)
        min_expected = int(expected_liquidity * Decimal('0.99'))
        max_expected = int(expected_liquidity * Decimal('1.01'))
        
        lp_decreased = min_expected <= lp_decrease <= max_expected
        lp_decrease_human = float(Decimal(str(lp_decrease)) / Decimal(10**18))
        checks.append({
            'name': 'LP Token Decrease',
            'passed': lp_decreased,
            'message': f'LP tokens decreased by {lp_decrease_human:.6f}' if lp_decreased else f'LP token decrease incorrect. Expected ~{float(expected_liquidity / Decimal(10**18)):.6f}, Got: {lp_decrease_human:.6f}'
        })
        
        # 6. Check token balance increase (15 points)
        token_balance_before = state_before.get('token_balance', 0)
        token_balance_after = state_after.get('token_balance', 0)
        token_increase = token_balance_after - token_balance_before
        
        token_increased = token_increase > 0
        token_increase_human = float(Decimal(str(token_increase)) / Decimal(10**self.token_decimals))
        checks.append({
            'name': 'Token Increase',
            'passed': token_increased,
            'message': f'Token increased by {token_increase_human:.6f} tokens' if token_increased else f'Token did not increase. Before: {token_balance_before}, After: {token_balance_after}'
        })
        
        # 7. Check BNB balance increase (15 points)
        # Note: BNB balance should increase (receive BNB from pool), but gas is also deducted
        # So we check if there's a net increase after accounting for gas
        bnb_balance_before = state_before.get('balance', 0)
        bnb_balance_after = state_after.get('balance', 0)
        bnb_change = bnb_balance_after - bnb_balance_before
        
        # Calculate gas cost
        gas_used = receipt.get('gasUsed', 0)
        effective_gas_price = receipt.get('effectiveGasPrice', 0)
        gas_cost = gas_used * effective_gas_price
        
        # Net BNB increase (after adding back gas cost)
        bnb_received = bnb_change + gas_cost
        
        bnb_increased = bnb_received > 0
        bnb_received_human = float(Decimal(str(bnb_received)) / Decimal(10**18))
        gas_cost_human = float(Decimal(str(gas_cost)) / Decimal(10**18))
        checks.append({
            'name': 'BNB Increase',
            'passed': bnb_increased,
            'message': f'BNB increased by {bnb_received_human:.6f} BNB (gas: {gas_cost_human:.6f} BNB)' if bnb_increased else f'BNB did not increase. Received: {bnb_received_human:.6f}, Gas: {gas_cost_human:.6f}'
        })
        
        # Calculate score
        passed_checks = sum(1 for check in checks if check['passed'])
        total_checks = len(checks)
        max_score = 100
        score = int((passed_checks / total_checks) * max_score)
        
        # Overall pass: all critical checks must pass
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': score,
            'max_score': max_score,
            'checks': checks
        }


# Alias for backwards compatibility
RemoveLiquidityBNBTokenValidator = RemoveLiquidityBNBTokenValidator
