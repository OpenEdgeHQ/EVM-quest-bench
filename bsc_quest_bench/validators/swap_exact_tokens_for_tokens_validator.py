"""
PancakeSwap Swap - Token to Token Validator

Validates swapExactTokensForTokens transaction on PancakeSwap V2 Router.
"""

from typing import Dict, Any
from decimal import Decimal


class SwapExactTokensForTokensValidator:
    """Validator for PancakeSwap swapExactTokensForTokens operation"""
    
    def __init__(
        self,
        router_address: str,
        token_in_address: str,
        token_out_address: str,
        amount_in: float,
        token_in_decimals: int = 18,
        token_out_decimals: int = 18,
        slippage: float = 5.0,
        **kwargs  # Accept extra params
    ):
        """
        Initialize validator
        
        Args:
            router_address: PancakeSwap Router contract address
            token_in_address: Input token address (token to swap)
            token_out_address: Output token address (token to receive)
            amount_in: Amount of input tokens to swap
            token_in_decimals: Input token decimals (default: 18)
            token_out_decimals: Output token decimals (default: 18)
            slippage: Slippage tolerance in percent (default: 5.0)
        """
        if not router_address:
            raise ValueError("router_address is required but was None or empty")
        if not token_in_address:
            raise ValueError("token_in_address is required but was None or empty")
        if not token_out_address:
            raise ValueError("token_out_address is required but was None or empty")
        
        self.router_address = router_address.lower()
        self.token_in_address = token_in_address.lower()
        self.token_out_address = token_out_address.lower()
        
        # Convert token amount to smallest unit
        self.amount_in_wei = int(Decimal(str(amount_in)) * Decimal(10**token_in_decimals))
        
        self.token_in_decimals = token_in_decimals
        self.token_out_decimals = token_out_decimals
        self.slippage = slippage
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the swap transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result dictionary
        
        Checks:
        1. Transaction Success (20%)
        2. Token Approval (15%)
        3. Router Contract Called (10%)
        4. Function Selector Correct (10%)
        5. Input Token Balance Decreased (20%)
        6. Output Token Balance Increased (25%)
        """
        checks = []
        total_score = 0
        
        # 1. Validate transaction success
        tx_status = receipt.get('status', 0)
        if tx_status == 1:
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'message': 'Transaction executed successfully',
                'score': 30
            })
            total_score += 30
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'message': f'Transaction failed with status: {tx_status}',
                'score': 20
            })
            # Transaction failed, return early
            return {
                'passed': False,
                'score': 0,
                'max_score': self.max_score,
                'checks': checks,
                'details': {
                    'tx_status': tx_status
                }
            }
        
        # 2. Validate token approval
        # Check if there was sufficient allowance before or if approval was granted
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        
        # Approval is considered correct if:
        # - Allowance before >= amount_in, OR
        # - Allowance after >= amount_in, OR
        # - Allowance was consumed (decreased by amount_in)
        approval_sufficient_before = allowance_before >= self.amount_in_wei
        approval_sufficient_after = allowance_after >= self.amount_in_wei
        allowance_consumed = (allowance_before - allowance_after) >= self.amount_in_wei * 0.99  # Allow 1% tolerance
        
        approval_correct = approval_sufficient_before or approval_sufficient_after or allowance_consumed
        
        if approval_correct:
            checks.append({
                'name': 'Token Approval',
                'passed': True,
                'message': f'Input token approval handled correctly',
                'score': 15
            })
            total_score += 15
        else:
            checks.append({
                'name': 'Token Approval',
                'passed': False,
                'message': f'Insufficient token approval. Allowance before: {allowance_before}, after: {allowance_after}, required: {self.amount_in_wei}',
                'score': 15
            })
        
        # 3. Validate router contract called
        actual_to = tx.get('to', '').lower()
        router_correct = actual_to == self.router_address
        
        if router_correct:
            checks.append({
                'name': 'Router Contract',
                'passed': True,
                'message': f'Correct PancakeSwap Router called: {self.router_address}',
                'score': 10
            })
            total_score += 10
        else:
            checks.append({
                'name': 'Router Contract',
                'passed': False,
                'message': f'Expected Router: {self.router_address}, Got: {actual_to}',
                'score': 10
            })
        
        # 4. Validate function selector
        tx_data = tx.get('data', '0x')
        function_selector = tx_data[:10].lower() if tx_data and len(tx_data) >= 10 else ''
        expected_selector = '0x38ed1739'  # swapExactTokensForTokens
        
        selector_correct = function_selector == expected_selector
        
        if selector_correct:
            checks.append({
                'name': 'Function Selector',
                'passed': True,
                'message': f'Correct function: swapExactTokensForTokens ({expected_selector})',
                'score': 10
            })
            total_score += 10
        else:
            checks.append({
                'name': 'Function Selector',
                'passed': False,
                'message': f'Expected: {expected_selector}, Got: {function_selector}',
                'score': 10
            })
        
        # 5. Validate input token balance decreased
        token_in_before = state_before.get('token_balance', 0)
        token_in_after = state_after.get('token_balance', 0)
        token_in_decrease = token_in_before - token_in_after
        
        # Input token balance should have decreased by exactly amount_in
        # Allow small tolerance for rounding
        token_in_decrease_correct = abs(token_in_decrease - self.amount_in_wei) < 10
        
        if token_in_decrease_correct:
            checks.append({
                'name': 'Input Token Balance Decrease',
                'passed': True,
                'message': f'Input token balance decreased correctly: {token_in_decrease / 10**self.token_in_decimals:.6f} tokens',
                'score': 20
            })
            total_score += 20
        else:
            checks.append({
                'name': 'Input Token Balance Decrease',
                'passed': False,
                'message': f'Expected decrease: {self.amount_in_wei / 10**self.token_in_decimals:.6f}, Actual: {token_in_decrease / 10**self.token_in_decimals:.6f}',
                'score': 20
            })
        
        # 6. Validate output token balance increased
        # Output token balance is tracked in target_token_balance
        token_out_before = state_before.get('target_token_balance', 0)
        token_out_after = state_after.get('target_token_balance', 0)
        token_out_increase = token_out_after - token_out_before
        
        # Output token balance should have increased (any positive amount is acceptable)
        if token_out_increase > 0:
            checks.append({
                'name': 'Output Token Balance Increase',
                'passed': True,
                'message': f'Output token balance increased: {token_out_increase / 10**self.token_out_decimals:.6f} tokens',
                'score': 15
            })
            total_score += 15
        else:
            checks.append({
                'name': 'Output Token Balance Increase',
                'passed': False,
                'message': f'Output token balance did not increase. Change: {token_out_increase}',
                'score': 15
            })
        
        # Determine overall pass/fail
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': self.max_score,
            'checks': checks,
            'details': {
                'router_address': self.router_address,
                'token_in_address': self.token_in_address,
                'token_out_address': self.token_out_address,
                'amount_in_tokens': self.amount_in_wei / 10**self.token_in_decimals,
                'amount_in_wei': self.amount_in_wei,
                'token_in_before': token_in_before,
                'token_in_after': token_in_after,
                'token_in_decrease': token_in_decrease,
                'token_out_before': token_out_before,
                'token_out_after': token_out_after,
                'token_out_increase': token_out_increase,
                'token_out_increase_human': token_out_increase / 10**self.token_out_decimals,
                'allowance_before': allowance_before,
                'allowance_after': allowance_after,
                'function_selector': function_selector,
                'expected_selector': expected_selector
            }
        }

