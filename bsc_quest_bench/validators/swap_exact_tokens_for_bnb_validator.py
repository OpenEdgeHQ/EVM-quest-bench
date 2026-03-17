"""
PancakeSwap Swap - Token to BNB Validator

Validates swapExactTokensForETH transaction on PancakeSwap V2 Router.
"""

from typing import Dict, Any
from decimal import Decimal


class SwapExactTokensForBNBValidator:
    """Validator for PancakeSwap swapExactTokensForETH operation"""
    
    def __init__(
        self,
        router_address: str,
        token_address: str,
        amount_in: float,
        token_decimals: int = 18,
        slippage: float = 5.0,
        **kwargs  # Accept extra params
    ):
        """
        Initialize validator
        
        Args:
            router_address: PancakeSwap Router contract address
            token_address: Input token address (token to swap)
            amount_in: Amount of tokens to swap
            token_decimals: Token decimals (default: 18)
            slippage: Slippage tolerance in percent (default: 5.0)
        """
        if not router_address:
            raise ValueError("router_address is required but was None or empty")
        if not token_address:
            raise ValueError("token_address is required but was None or empty")
        
        self.router_address = router_address.lower()
        self.token_address = token_address.lower()
        
        # Convert token amount to smallest unit
        self.amount_in_wei = int(Decimal(str(amount_in)) * Decimal(10**token_decimals))
        
        self.token_decimals = token_decimals
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
        1. Transaction Success (25%)
        2. Token Approval (20%)
        3. Router Contract Called (10%)
        4. Function Selector Correct (10%)
        5. Token Balance Decreased (20%)
        6. BNB Balance Increased (15%)
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
                'score': 25
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
                'message': f'Token approval handled correctly',
                'score': 20
            })
            total_score += 20
        else:
            checks.append({
                'name': 'Token Approval',
                'passed': False,
                'message': f'Insufficient token approval. Allowance before: {allowance_before}, after: {allowance_after}, required: {self.amount_in_wei}',
                'score': 20
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
        expected_selector = '0x18cbafe5'  # swapExactTokensForETH
        
        selector_correct = function_selector == expected_selector
        
        if selector_correct:
            checks.append({
                'name': 'Function Selector',
                'passed': True,
                'message': f'Correct function: swapExactTokensForETH ({expected_selector})',
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
        
        # 5. Validate token balance decreased
        token_before = state_before.get('token_balance', 0)
        token_after = state_after.get('token_balance', 0)
        token_decrease = token_before - token_after
        
        # Token balance should have decreased by exactly amount_in
        # Allow small tolerance for rounding
        token_decrease_correct = abs(token_decrease - self.amount_in_wei) < 10
        
        if token_decrease_correct:
            checks.append({
                'name': 'Token Balance Decrease',
                'passed': True,
                'message': f'Token balance decreased correctly: {token_decrease / 10**self.token_decimals:.6f} tokens',
                'score': 20
            })
            total_score += 20
        else:
            checks.append({
                'name': 'Token Balance Decrease',
                'passed': False,
                'message': f'Expected decrease: {self.amount_in_wei / 10**self.token_decimals:.6f}, Actual: {token_decrease / 10**self.token_decimals:.6f}',
                'score': 20
            })
        
        # 6. Validate BNB balance increased
        bnb_before = state_before.get('balance', 0)
        bnb_after = state_after.get('balance', 0)
        gas_used = receipt.get('gasUsed', 0)
        gas_price = receipt.get('effectiveGasPrice', 0)
        gas_cost = gas_used * gas_price
        
        # BNB change = after - before (should be positive after receiving BNB, minus gas)
        # Net change = BNB received from swap - gas cost
        bnb_change = bnb_after - bnb_before
        
        # BNB should have increased (even after gas cost)
        # We expect: bnb_change = swap_output - gas_cost > 0
        # Or at least: bnb_change + gas_cost > 0 (meaning we got some BNB from swap)
        bnb_received = bnb_change + gas_cost
        
        if bnb_received > 0:
            checks.append({
                'name': 'BNB Balance Increase',
                'passed': True,
                'message': f'BNB balance increased: received ~{bnb_received / 10**18:.6f} BNB (net change after gas: {bnb_change / 10**18:.6f} BNB)',
                'score': 10
            })
            total_score += 10
        else:
            checks.append({
                'name': 'BNB Balance Increase',
                'passed': False,
                'message': f'BNB balance did not increase. Change: {bnb_change / 10**18:.6f} BNB, Gas: {gas_cost / 10**18:.6f} BNB',
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
                'token_address': self.token_address,
                'amount_in_tokens': self.amount_in_wei / 10**self.token_decimals,
                'amount_in_wei': self.amount_in_wei,
                'token_before': token_before,
                'token_after': token_after,
                'token_decrease': token_decrease,
                'allowance_before': allowance_before,
                'allowance_after': allowance_after,
                'bnb_before': bnb_before,
                'bnb_after': bnb_after,
                'bnb_change': bnb_change,
                'gas_cost': gas_cost,
                'bnb_received_estimate': bnb_received,
                'function_selector': function_selector,
                'expected_selector': expected_selector
            }
        }

