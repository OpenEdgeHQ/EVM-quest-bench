"""
Validator for remove_liquidity_tokens atomic problem.

Validates:
1. Transaction success
2. LP token approved for Router
3. Correct PancakeSwap Router called
4. Correct function (removeLiquidity)
5. LP token balance decreased
6. Token A balance increased
7. Token B balance increased
"""

from decimal import Decimal
from typing import Dict, Any, List
from eth_utils import to_checksum_address


class RemoveLiquidityTokensValidator:
    """Validator for removing liquidity from Token-Token pool"""
    
    def __init__(self, **params):
        """
        Initialize validator with parameters
        
        Args:
            router_address: PancakeSwap Router address
            token_a_address: Token A address
            token_b_address: Token B address
            liquidity_percentage: Percentage of LP tokens to remove
            **params: Additional parameters
        """
        router_address = params.get('router_address')
        token_a_address = params.get('token_a_address')
        token_b_address = params.get('token_b_address')
        
        if not router_address:
            raise ValueError("router_address is required but was None or empty")
        if not token_a_address:
            raise ValueError("token_a_address is required but was None or empty")
        if not token_b_address:
            raise ValueError("token_b_address is required but was None or empty")
        
        self.router_address = to_checksum_address(router_address)
        self.token_a_address = to_checksum_address(token_a_address)
        self.token_b_address = to_checksum_address(token_b_address)
        self.liquidity_percentage = Decimal(str(params.get('liquidity_percentage', 50)))
        
        # Expected function selector for removeLiquidity
        self.expected_selector = '0xbaa2abde'
    
    def validate(self, tx: Dict[str, Any], receipt: Dict[str, Any],
                 state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the remove liquidity transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result with pass/fail status and details
        """
        checks = []
        
        # 1. Check transaction success
        status = receipt.get('status', 0)
        tx_success = status == 1
        checks.append({
            'name': 'Transaction Success',
            'passed': tx_success,
            'message': 'Transaction executed successfully' if tx_success else f'Transaction failed with status: {status}'
        })
        
        if not tx_success:
            return {
                'passed': False,
                'score': 0,
                'checks': checks
            }
        
        # 2. Check LP token approval (allowance should have decreased or been set)
        lp_allowance_before = Decimal(str(state_before.get('lp_allowance', 0)))
        lp_allowance_after = Decimal(str(state_after.get('lp_allowance', 0)))
        
        # If allowance decreased or was already sufficient, it's good
        lp_approved = lp_allowance_before > 0 or lp_allowance_after > 0
        checks.append({
            'name': 'LP Token Approval',
            'passed': lp_approved,
            'message': f'LP token {"approved" if lp_approved else "not approved"}. Allowance before: {lp_allowance_before}, after: {lp_allowance_after}'
        })
        
        # 3. Check correct Router called
        to_address = to_checksum_address(tx.get('to', ''))
        router_correct = to_address == self.router_address
        checks.append({
            'name': 'Correct Router',
            'passed': router_correct,
            'message': f'Correct PancakeSwap Router: {to_address.lower()}' if router_correct else f'Wrong router: {to_address} (expected: {self.router_address})'
        })
        
        # 4. Check correct function called
        tx_data = tx.get('data', '0x')
        if isinstance(tx_data, str) and len(tx_data) >= 10:
            function_selector = tx_data[:10].lower()
        else:
            function_selector = '0x00000000'
        
        selector_correct = function_selector == self.expected_selector
        checks.append({
            'name': 'Correct Function',
            'passed': selector_correct,
            'message': f'Correct function: removeLiquidity ({function_selector})' if selector_correct else f'Wrong function: {function_selector} (expected: {self.expected_selector})'
        })
        
        # 5. Check LP token balance decreased
        lp_balance_before = Decimal(str(state_before.get('lp_token_balance', 0)))
        lp_balance_after = Decimal(str(state_after.get('lp_token_balance', 0)))
        lp_decrease = lp_balance_before - lp_balance_after
        
        lp_decreased = lp_decrease > 0
        checks.append({
            'name': 'LP Token Decrease',
            'passed': lp_decreased,
            'message': f'LP tokens decreased by {lp_decrease / Decimal(10**18):.6f}' if lp_decreased else f'LP tokens did not decrease. Before: {lp_balance_before}, After: {lp_balance_after}'
        })
        
        # 6. Check Token A balance increased
        token_a_balance_before = Decimal(str(state_before.get('token_balance', 0)))
        token_a_balance_after = Decimal(str(state_after.get('token_balance', 0)))
        token_a_increase = token_a_balance_after - token_a_balance_before
        
        token_a_increased = token_a_increase > 0
        checks.append({
            'name': 'Token A Increase',
            'passed': token_a_increased,
            'message': f'Token A increased by {token_a_increase / Decimal(10**18):.6f} tokens' if token_a_increased else f'Token A did not increase. Before: {token_a_balance_before}, After: {token_a_balance_after}'
        })
        
        # 7. Check Token B balance increased
        # Use target_token_balance or token_b_balance for Token B
        token_b_balance_before = Decimal(str(state_before.get('target_token_balance', 0)))
        token_b_balance_after = Decimal(str(state_after.get('target_token_balance', 0)))
        token_b_increase = token_b_balance_after - token_b_balance_before
        
        token_b_increased = token_b_increase > 0
        checks.append({
            'name': 'Token B Increase',
            'passed': token_b_increased,
            'message': f'Token B increased by {token_b_increase / Decimal(10**18):.6f} tokens' if token_b_increased else f'Token B did not increase. Before: {token_b_balance_before}, After: {token_b_balance_after}'
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
RemoveLiquidityTokensValidator = RemoveLiquidityTokensValidator

