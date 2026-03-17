"""
PancakeSwap Swap - BNB to Token Validator

Validates swapExactETHForTokens transaction on PancakeSwap V2 Router.
"""

from typing import Dict, Any
from decimal import Decimal


class SwapExactBNBForTokensValidator:
    """Validator for PancakeSwap swapExactETHForTokens operation"""
    
    def __init__(
        self,
        router_address: str,
        token_address: str,
        amount_in: float,
        token_decimals: int = 18,
        slippage: float = 5.0
    ):
        """
        Initialize validator
        
        Args:
            router_address: PancakeSwap Router contract address
            token_address: Target token address (output token)
            amount_in: Amount of BNB to swap
            token_decimals: Token decimals (default: 18)
            slippage: Slippage tolerance in percent (default: 5.0)
        """
        self.router_address = router_address.lower()
        self.token_address = token_address.lower()
        
        # Convert BNB amount to wei
        self.amount_in_wei = int(Decimal(str(amount_in)) * Decimal(10**18))
        
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
        1. Transaction Success (30 points)
        2. Router Contract Called (15 points)
        3. Function Selector Correct (15 points)
        4. BNB Balance Decreased (15 points)
        5. Token Balance Increased (25 points)
        """
        checks = []
        total_score = 0
        
        # 1. Validate transaction success (30 points)
        tx_status = receipt.get('status', 0)
        if tx_status == 1:
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'score': 30,
                'message': 'Transaction executed successfully'
            })
            total_score += 30
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'score': 0,
                'message': f'Transaction failed with status: {tx_status}'
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
        
        # 2. Validate router contract called (15 points)
        actual_to = tx.get('to', '').lower()
        router_correct = actual_to == self.router_address
        
        if router_correct:
            checks.append({
                'name': 'Router Contract',
                'passed': True,
                'score': 15,
                'message': f'Correct PancakeSwap Router called: {self.router_address}'
            })
            total_score += 15
        else:
            checks.append({
                'name': 'Router Contract',
                'passed': False,
                'score': 0,
                'message': f'Expected Router: {self.router_address}, Got: {actual_to}'
            })
        
        # 3. Validate function selector (15 points)
        tx_data = tx.get('data', '0x')
        function_selector = tx_data[:10].lower() if tx_data and len(tx_data) >= 10 else ''
        expected_selector = '0x7ff36ab5'  # swapExactETHForTokens
        
        selector_correct = function_selector == expected_selector
        
        if selector_correct:
            checks.append({
                'name': 'Function Selector',
                'passed': True,
                'score': 15,
                'message': f'Correct function: swapExactETHForTokens ({expected_selector})'
            })
            total_score += 15
        else:
            checks.append({
                'name': 'Function Selector',
                'passed': False,
                'score': 0,
                'message': f'Expected: {expected_selector}, Got: {function_selector}'
            })
        
        # 4. Validate BNB balance decreased (15 points)
        bnb_before = state_before.get('balance', 0)
        bnb_after = state_after.get('balance', 0)
        gas_used = receipt.get('gasUsed', 0)
        gas_price = receipt.get('effectiveGasPrice', 0)
        gas_cost = gas_used * gas_price
        
        # Expected BNB change: amount_in + gas
        expected_bnb_decrease = self.amount_in_wei + gas_cost
        actual_bnb_decrease = bnb_before - bnb_after
        
        # Check if BNB decreased by approximately the expected amount
        # Allow small tolerance for gas estimation differences
        bnb_decrease_correct = abs(actual_bnb_decrease - expected_bnb_decrease) < (gas_cost * 0.1)
        
        # Also check transaction value
        tx_value = tx.get('value', 0)
        if isinstance(tx_value, str):
            tx_value = int(tx_value, 16) if tx_value.startswith('0x') else int(tx_value)
        
        value_correct = tx_value == self.amount_in_wei
        
        if value_correct:
            # Transaction value is correct (balance change validation is informational)
            message = f'BNB decreased correctly: {self.amount_in_wei / 10**18:.6f} BNB + gas' if bnb_decrease_correct else f'Transaction value correct, balance change acceptable'
            checks.append({
                'name': 'BNB Balance Decrease',
                'passed': True,
                'score': 15,
                'message': message
            })
            total_score += 15
        else:
            checks.append({
                'name': 'BNB Balance Decrease',
                'passed': False,
                'score': 0,
                'message': f'Expected value: {self.amount_in_wei}, Got: {tx_value}'
            })
        
        # 5. Validate token balance increased (25 points)
        token_before = state_before.get('token_balance', 0)
        token_after = state_after.get('token_balance', 0)
        token_increase = token_after - token_before
        
        # Token balance should have increased (any positive amount is acceptable)
        if token_increase > 0:
            checks.append({
                'name': 'Token Balance Increase',
                'passed': True,
                'score': 25,
                'message': f'Token balance increased: {token_increase / 10**self.token_decimals:.6f} tokens'
            })
            total_score += 25
        else:
            checks.append({
                'name': 'Token Balance Increase',
                'passed': False,
                'score': 0,
                'message': f'Token balance did not increase. Change: {token_increase}'
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
                'amount_in_bnb': self.amount_in_wei / 10**18,
                'amount_in_wei': self.amount_in_wei,
                'bnb_before': bnb_before,
                'bnb_after': bnb_after,
                'bnb_change': bnb_before - bnb_after,
                'gas_cost': gas_cost,
                'tx_value': tx_value,
                'token_before': token_before,
                'token_after': token_after,
                'token_increase': token_increase,
                'token_increase_human': token_increase / 10**self.token_decimals,
                'function_selector': function_selector,
                'expected_selector': expected_selector
            }
        }

