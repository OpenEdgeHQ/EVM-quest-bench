"""
PancakeSwap Swap - Exact Output Token to Token Validator

Validates swapTokensForExactTokens transaction on PancakeSwap V2 Router.
"""

from typing import Dict, Any
from decimal import Decimal


class SwapTokensForExactTokensValidator:
    """Validator for PancakeSwap swapTokensForExactTokens operation (exact output)"""
    
    def __init__(
        self,
        router_address: str,
        token_in_address: str,
        token_out_address: str,
        amount_out: float,
        token_in_decimals: int = 18,
        token_out_decimals: int = 18,
        slippage: float = 5.0
    ):
        """
        Initialize validator
        
        Args:
            router_address: PancakeSwap Router contract address
            token_in_address: Input token address (token to spend)
            token_out_address: Output token address (token to receive)
            amount_out: EXACT amount of output tokens to receive
            token_in_decimals: Input token decimals (default: 18)
            token_out_decimals: Output token decimals (default: 18)
            slippage: Slippage tolerance in percent (default: 5.0)
        """
        self.router_address = router_address.lower()
        self.token_in_address = token_in_address.lower()
        self.token_out_address = token_out_address.lower()
        
        # Convert output token amount to smallest unit
        self.amount_out_wei = int(Decimal(str(amount_out)) * Decimal(10**token_out_decimals))
        
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
        4. Function Selector Correct (15%)
        5. Output Token Balance EXACTLY Increased (25%)
        6. Input Token Balance Decreased (reasonable amount) (15%)
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
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        
        # For exact output, we need sufficient allowance to cover potential input
        # Check if there was sufficient allowance or if approval was granted
        approval_sufficient = (allowance_before > 0) or (allowance_after > 0)
        
        if approval_sufficient:
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
                'message': f'No token approval found. Allowance before: {allowance_before}, after: {allowance_after}',
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
        expected_selector = '0x8803dbee'  # swapTokensForExactTokens
        
        selector_correct = function_selector == expected_selector
        
        if selector_correct:
            checks.append({
                'name': 'Function Selector',
                'passed': True,
                'message': f'Correct function: swapTokensForExactTokens ({expected_selector})',
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
        
        # 5. Validate output token balance EXACTLY increased by amount_out
        # This is the KEY check for exact output swaps
        token_out_before = state_before.get('target_token_balance', 0)
        token_out_after = state_after.get('target_token_balance', 0)
        token_out_increase = token_out_after - token_out_before
        
        # Output must match EXACTLY (with tiny tolerance for rounding)
        exact_match_tolerance = 10  # Allow 10 wei tolerance
        output_exact = abs(token_out_increase - self.amount_out_wei) <= exact_match_tolerance
        
        if output_exact:
            checks.append({
                'name': 'Output Token Balance EXACT Match',
                'passed': True,
                'message': f'Output token balance increased by EXACTLY {token_out_increase / 10**self.token_out_decimals:.6f} tokens (expected: {self.amount_out_wei / 10**self.token_out_decimals:.6f})',
                'score': 25
            })
            total_score += 25
        else:
            checks.append({
                'name': 'Output Token Balance EXACT Match',
                'passed': False,
                'message': f'Output mismatch. Expected EXACTLY: {self.amount_out_wei / 10**self.token_out_decimals:.6f}, Got: {token_out_increase / 10**self.token_out_decimals:.6f}',
                'score': 25
            })
        
        # 6. Validate input token balance decreased (within reasonable range)
        token_in_before = state_before.get('token_balance', 0)
        token_in_after = state_after.get('token_balance', 0)
        token_in_decrease = token_in_before - token_in_after
        
        # Input should have decreased (any positive amount is acceptable)
        # We don't check exact amount because it depends on market conditions
        if token_in_decrease > 0:
            checks.append({
                'name': 'Input Token Balance Decrease',
                'passed': True,
                'message': f'Input token balance decreased: {token_in_decrease / 10**self.token_in_decimals:.6f} tokens',
                'score': 10
            })
            total_score += 10
        else:
            checks.append({
                'name': 'Input Token Balance Decrease',
                'passed': False,
                'message': f'Input token balance did not decrease. Change: {token_in_decrease}',
                'score': 10
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
                'amount_out_expected': self.amount_out_wei / 10**self.token_out_decimals,
                'amount_out_expected_wei': self.amount_out_wei,
                'token_in_before': token_in_before,
                'token_in_after': token_in_after,
                'token_in_decrease': token_in_decrease,
                'token_in_decrease_human': token_in_decrease / 10**self.token_in_decimals,
                'token_out_before': token_out_before,
                'token_out_after': token_out_after,
                'token_out_increase': token_out_increase,
                'token_out_increase_human': token_out_increase / 10**self.token_out_decimals,
                'exact_match': output_exact,
                'allowance_before': allowance_before,
                'allowance_after': allowance_after,
                'function_selector': function_selector,
                'expected_selector': expected_selector
            }
        }

