"""
Validator for add_liquidity_tokens atomic problem

Validates that:
1. Transaction succeeded
2. Both tokens were approved for Router
3. Correct PancakeSwap Router was called
4. addLiquidity function was called
5. Token A balance decreased correctly
6. Token B balance decreased correctly
7. LP tokens were received
"""

from decimal import Decimal
from typing import Dict, Any


class AddLiquidityTokensValidator:
    """Validator for PancakeSwap add liquidity (Token + Token) operations"""
    
    def __init__(self, **params):
        """
        Initialize validator with parameters
        
        Args:
            router_address: PancakeSwap Router address
            token_a_address: First token address
            token_b_address: Second token address
            amount_token_a: Desired amount of token A
            amount_token_b: Desired amount of token B
            token_a_decimals: Token A decimals
            token_b_decimals: Token B decimals
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
        
        self.router_address = router_address.lower()
        self.token_a_address = token_a_address.lower()
        self.token_b_address = token_b_address.lower()
        self.amount_token_a = Decimal(str(params.get('amount_token_a', 0)))
        self.amount_token_b = Decimal(str(params.get('amount_token_b', 0)))
        self.token_a_decimals = params.get('token_a_decimals', 18)
        self.token_b_decimals = params.get('token_b_decimals', 18)
        
        # Convert to smallest unit
        self.amount_token_a_wei = int(self.amount_token_a * Decimal(10 ** self.token_a_decimals))
        self.amount_token_b_wei = int(self.amount_token_b * Decimal(10 ** self.token_b_decimals))
        
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the add liquidity transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result with passed status and details
        """
        checks = []
        score = 0
        details = {}
        
        # 1. Transaction success check (30 points)
        tx_success = receipt.get('status') == 1
        if tx_success:
            score += 30
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'score': 30,
                'message': 'Transaction executed successfully'
            })
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'score': 0,
                'message': f'Transaction failed with status: {receipt.get("status")}'
            })
        
        # 2. Token A approval check (10 points)
        token_a_allowance_before = state_before.get('allowance', 0)
        token_a_allowance_after = state_after.get('allowance', 0)
        
        token_a_approved = token_a_allowance_before > 0
        if token_a_approved:
            score += 10
            checks.append({
                'name': 'Token A Approval',
                'passed': True,
                'score': 10,
                'message': f'Token A approved. Allowance before: {token_a_allowance_before}, after: {token_a_allowance_after}'
            })
        else:
            checks.append({
                'name': 'Token A Approval',
                'passed': False,
                'score': 0,
                'message': f'Token A not approved. Allowance: {token_a_allowance_before}'
            })
        
        # 3. Token B approval check (10 points)
        token_b_allowance_before = state_before.get('token_b_allowance', 0)
        token_b_allowance_after = state_after.get('token_b_allowance', 0)
        
        token_b_approved = token_b_allowance_before > 0
        if token_b_approved:
            score += 10
            checks.append({
                'name': 'Token B Approval',
                'passed': True,
                'score': 10,
                'message': f'Token B approved. Allowance before: {token_b_allowance_before}, after: {token_b_allowance_after}'
            })
        else:
            checks.append({
                'name': 'Token B Approval',
                'passed': False,
                'score': 0,
                'message': f'Token B not approved. Allowance: {token_b_allowance_before}'
            })
        
        # 4. Router address check (10 points)
        to_address = tx.get('to', '').lower()
        router_correct = to_address == self.router_address
        if router_correct:
            score += 10
            checks.append({
                'name': 'Correct Router',
                'passed': True,
                'score': 10,
                'message': f'Correct PancakeSwap Router: {to_address}'
            })
        else:
            checks.append({
                'name': 'Correct Router',
                'passed': False,
                'score': 0,
                'message': f'Wrong router. Expected: {self.router_address}, Got: {to_address}'
            })
        
        # 5. Function selector check (5 points)
        data = tx.get('data', '')
        if data and len(data) >= 10:
            function_selector = data[:10].lower()
            expected_selector = '0xe8e33700'
            selector_correct = function_selector == expected_selector
            if selector_correct:
                score += 5
                checks.append({
                    'name': 'Correct Function',
                    'passed': True,
                    'score': 5,
                    'message': f'Correct function: addLiquidity ({function_selector})'
                })
            else:
                checks.append({
                    'name': 'Correct Function',
                    'passed': False,
                    'score': 0,
                    'message': f'Wrong function. Expected: {expected_selector}, Got: {function_selector}'
                })
        else:
            checks.append({
                'name': 'Correct Function',
                'passed': False,
                'score': 0,
                'message': 'No function data found'
            })
        
        # 6. Token A balance decrease check (15 points)
        token_a_balance_before = state_before.get('token_balance', 0)
        token_a_balance_after = state_after.get('token_balance', 0)
        token_a_decrease = token_a_balance_before - token_a_balance_after
        
        # Allow for some fluctuation (pool ratio adjustment) - up to 50%
        expected_min = int(self.amount_token_a_wei * 0.5)
        expected_max = int(self.amount_token_a_wei * 1.5)
        
        token_a_decrease_valid = expected_min <= token_a_decrease <= expected_max
        token_a_decrease_human = Decimal(token_a_decrease) / Decimal(10 ** self.token_a_decimals)
        
        if token_a_decrease_valid:
            score += 15
            checks.append({
                'name': 'Token A Decrease',
                'passed': True,
                'score': 15,
                'message': f'Token A decreased by {token_a_decrease_human:.6f} tokens'
            })
        else:
            checks.append({
                'name': 'Token A Decrease',
                'passed': False,
                'score': 0,
                'message': f'Token A change incorrect. Expected ~{self.amount_token_a:.6f}, Got: {token_a_decrease_human:.6f}'
            })
        
        # 7. Token B balance decrease check (15 points)
        token_b_balance_before = state_before.get('token_b_balance', 0)
        token_b_balance_after = state_after.get('token_b_balance', 0)
        token_b_decrease = token_b_balance_before - token_b_balance_after
        
        # Allow for some fluctuation (pool ratio adjustment) - up to 50%
        expected_min_b = int(self.amount_token_b_wei * 0.5)
        expected_max_b = int(self.amount_token_b_wei * 1.5)
        
        token_b_decrease_valid = expected_min_b <= token_b_decrease <= expected_max_b
        token_b_decrease_human = Decimal(token_b_decrease) / Decimal(10 ** self.token_b_decimals)
        
        if token_b_decrease_valid:
            score += 15
            checks.append({
                'name': 'Token B Decrease',
                'passed': True,
                'score': 15,
                'message': f'Token B decreased by {token_b_decrease_human:.6f} tokens'
            })
        else:
            checks.append({
                'name': 'Token B Decrease',
                'passed': False,
                'score': 0,
                'message': f'Token B change incorrect. Expected ~{self.amount_token_b:.6f}, Got: {token_b_decrease_human:.6f}'
            })
        
        # 8. LP token increase check (5 points)
        lp_balance_before = state_before.get('lp_token_balance', 0)
        lp_balance_after = state_after.get('lp_token_balance', 0)
        lp_increase = lp_balance_after - lp_balance_before
        
        lp_received = lp_increase > 0
        if lp_received:
            score += 5
            lp_increase_human = Decimal(lp_increase) / Decimal(10 ** 18)
            checks.append({
                'name': 'LP Token Received',
                'passed': True,
                'score': 5,
                'message': f'Received {lp_increase_human:.6f} LP tokens'
            })
        else:
            checks.append({
                'name': 'LP Token Received',
                'passed': False,
                'score': 0,
                'message': f'No LP tokens received. Before: {lp_balance_before}, After: {lp_balance_after}'
            })
        
        # Determine overall pass/fail (need 70% to pass for medium difficulty)
        passed = score >= 70
        
        # Detailed information for debugging
        details['router_address'] = self.router_address
        details['token_a_address'] = self.token_a_address
        details['token_b_address'] = self.token_b_address
        details['amount_token_a'] = float(self.amount_token_a)
        details['amount_token_b'] = float(self.amount_token_b)
        details['amount_token_a_wei'] = self.amount_token_a_wei
        details['amount_token_b_wei'] = self.amount_token_b_wei
        details['token_a_balance_before'] = token_a_balance_before
        details['token_a_balance_after'] = token_a_balance_after
        details['token_a_decrease'] = token_a_decrease
        details['token_a_decrease_human'] = float(token_a_decrease_human)
        details['token_b_balance_before'] = token_b_balance_before
        details['token_b_balance_after'] = token_b_balance_after
        details['token_b_decrease'] = token_b_decrease
        details['token_b_decrease_human'] = float(token_b_decrease_human)
        details['lp_balance_before'] = lp_balance_before
        details['lp_balance_after'] = lp_balance_after
        details['lp_increase'] = lp_increase
        details['token_a_allowance_before'] = token_a_allowance_before
        details['token_a_allowance_after'] = token_a_allowance_after
        details['token_b_allowance_before'] = token_b_allowance_before
        details['token_b_allowance_after'] = token_b_allowance_after
        details['function_selector'] = data[:10].lower() if data and len(data) >= 10 else 'N/A'
        details['expected_selector'] = '0xe8e33700'
        
        return {
            'passed': passed,
            'score': score,
            'max_score': 100,
            'checks': checks,
            'details': details
        }

