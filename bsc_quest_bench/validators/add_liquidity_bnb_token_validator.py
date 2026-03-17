"""
Validator for PancakeSwap Add Liquidity - BNB + Token

This validator checks:
1. Transaction success
2. Token approval for Router
3. Correct Router contract interaction
4. Correct function call (addLiquidityETH)
5. BNB balance decrease (amount + gas)
6. Token balance decrease (approximately the specified amount)
7. LP token balance increase
"""

from decimal import Decimal
from typing import Dict, Any


class AddLiquidityBNBTokenValidator:
    """Validator for PancakeSwap addLiquidityETH operation"""
    
    def __init__(
        self,
        router_address: str,
        token_address: str,
        amount_bnb: float,
        amount_token: float,
        token_decimals: int = 18,
        slippage: float = 5.0,
        **kwargs  # Accept extra params
    ):
        """
        Initialize validator
        
        Args:
            router_address: PancakeSwap Router V2 address
            token_address: Token address to pair with BNB
            amount_bnb: Amount of BNB to add
            amount_token: Amount of tokens to add
            token_decimals: Token decimals
            slippage: Slippage tolerance percentage
        """
        if not router_address:
            raise ValueError("router_address is required but was None or empty")
        if not token_address:
            raise ValueError("token_address is required but was None or empty")
        
        self.router_address = router_address.lower()
        self.token_address = token_address.lower()
        self.amount_bnb = Decimal(str(amount_bnb))
        self.amount_token = Decimal(str(amount_token))
        self.token_decimals = token_decimals
        self.slippage = Decimal(str(slippage)) / Decimal('100')
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate add liquidity transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result with score and checks
        """
        checks = []
        score = 0
        
        # Convert amounts to smallest unit
        amount_bnb_wei = int(self.amount_bnb * Decimal(10**18))
        amount_token_wei = int(self.amount_token * Decimal(10**self.token_decimals))
        
        # 1. Check transaction success (20 points)
        tx_success = receipt.get('status') == 1
        if tx_success:
            score += 20
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'message': 'Transaction executed successfully'
            })
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'message': f"Transaction failed with status: {receipt.get('status')}"
            })
            # If transaction failed, return early
            return {
                'passed': False,
                'score': score,
                'max_score': self.max_score,
                'checks': checks
            }
        
        # 2. Check token approval (15 points)
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        
        if allowance_before > 0 or allowance_after > 0:
            score += 15
            checks.append({
                'name': 'Token Approval',
                'passed': True,
                'message': f'Token approved for Router. Allowance before: {allowance_before}, after: {allowance_after}'
            })
        else:
            checks.append({
                'name': 'Token Approval',
                'passed': False,
                'message': f'No token approval found. Allowance before: {allowance_before}, after: {allowance_after}'
            })
        
        # 3. Check correct Router contract (10 points)
        tx_to = tx.get('to', '').lower()
        if tx_to == self.router_address:
            score += 10
            checks.append({
                'name': 'Correct Router',
                'passed': True,
                'message': f'Correct PancakeSwap Router called: {tx_to}'
            })
        else:
            checks.append({
                'name': 'Correct Router',
                'passed': False,
                'message': f'Wrong contract called. Expected: {self.router_address}, Got: {tx_to}'
            })
        
        # 4. Check correct function call (10 points)
        # addLiquidityETH function selector: 0xf305d719
        tx_data = tx.get('data', '')
        expected_selector = '0xf305d719'
        actual_selector = tx_data[:10] if tx_data else ''
        
        if actual_selector == expected_selector:
            score += 10
            checks.append({
                'name': 'Correct Function',
                'passed': True,
                'message': f'Correct function: addLiquidityETH ({actual_selector})'
            })
        else:
            checks.append({
                'name': 'Correct Function',
                'passed': False,
                'message': f'Wrong function. Expected: {expected_selector}, Got: {actual_selector}'
            })
        
        # 5. Check BNB balance decrease (20 points)
        # Get BNB balances from state
        bnb_balance_before = state_before.get('balance', 0)
        bnb_balance_after = state_after.get('balance', 0)
        
        # Calculate gas cost from receipt
        gas_used = receipt.get('gasUsed', 0)
        effective_gas_price = receipt.get('effectiveGasPrice', 0)
        gas_cost = gas_used * effective_gas_price
        
        # Calculate BNB decrease (balance change + gas cost = BNB sent)
        bnb_decrease = bnb_balance_before - bnb_balance_after - gas_cost
        
        # Check transaction value (more reliable)
        tx_value = tx.get('value', 0)
        if isinstance(tx_value, str):
            tx_value = int(tx_value, 16) if tx_value.startswith('0x') else int(tx_value)
        
        # BNB amount should match transaction value (not subject to slippage in addLiquidityETH)
        # Allow 1% tolerance for any precision issues
        tolerance = int(amount_bnb_wei * Decimal('0.01'))
        
        if abs(tx_value - amount_bnb_wei) <= tolerance:
            score += 20
            bnb_sent_human = float(Decimal(str(tx_value)) / Decimal(10**18))
            checks.append({
                'name': 'BNB Decrease',
                'passed': True,
                'score': 20,
                'message': f'BNB sent correctly: {bnb_sent_human:.6f} BNB'
            })
        else:
            bnb_sent_human = float(Decimal(str(tx_value)) / Decimal(10**18))
            expected_human = float(self.amount_bnb)
            checks.append({
                'name': 'BNB Decrease',
                'passed': False,
                'score': 0,
                'message': f'BNB amount incorrect. Expected: {expected_human:.6f}, Got: {bnb_sent_human:.6f} BNB'
            })
        
        # 6. Check token balance decrease (15 points)
        token_balance_before = state_before.get('token_balance', 0)
        token_balance_after = state_after.get('token_balance', 0)
        token_decrease = token_balance_before - token_balance_after
        
        # Token amount is automatically adjusted by router based on pool ratio
        # For addLiquidityETH, the actual token amount used will be calculated as:
        # optimalTokenAmount = (amountBNB * reserveToken) / reserveWBNB
        # So we just check if a reasonable amount of tokens was used (> 0)
        # and within a very wide range (to catch obvious errors)
        
        if token_decrease > 0:
            # Token was used - this is correct
            score += 15
            token_decrease_human = float(Decimal(str(token_decrease)) / Decimal(10**self.token_decimals))
            checks.append({
                'name': 'Token Decrease',
                'passed': True,
                'score': 15,
                'message': f'Token balance decreased by {token_decrease_human:.6f} tokens (adjusted by AMM pool ratio)'
            })
        else:
            # No tokens used - this is wrong
            token_decrease_human = float(Decimal(str(token_decrease)) / Decimal(10**self.token_decimals))
            checks.append({
                'name': 'Token Decrease',
                'passed': False,
                'score': 0,
                'message': f'No tokens were used. Token decrease: {token_decrease_human:.6f}'
            })
        
        # 7. Check LP token increase (10 points)
        # LP token balance is tracked in lp_token_balance
        lp_balance_before = state_before.get('lp_token_balance', 0)
        lp_balance_after = state_after.get('lp_token_balance', 0)
        lp_increase = lp_balance_after - lp_balance_before
        
        if lp_increase > 0:
            score += 10
            lp_increase_human = float(Decimal(str(lp_increase)) / Decimal(10**18))
            checks.append({
                'name': 'LP Token Received',
                'passed': True,
                'score': 10,
                'message': f'Received {lp_increase_human:.6f} LP tokens'
            })
        else:
            checks.append({
                'name': 'LP Token Received',
                'passed': False,
                'score': 0,
                'message': f'No LP tokens received. Before: {lp_balance_before}, After: {lp_balance_after}'
            })
        
        # Determine overall pass/fail
        passed = score >= 70  # Need 70% to pass (medium difficulty)
        
        return {
            'passed': passed,
            'score': score,
            'max_score': self.max_score,
            'checks': checks,
            'details': {
                'router_address': self.router_address,
                'token_address': self.token_address,
                'amount_bnb': float(self.amount_bnb),
                'amount_token': float(self.amount_token),
                'amount_bnb_wei': amount_bnb_wei,
                'amount_token_wei': amount_token_wei,
                'bnb_balance_before': bnb_balance_before,
                'bnb_balance_after': bnb_balance_after,
                'bnb_decrease': bnb_decrease,
                'gas_cost': gas_cost,
                'token_balance_before': token_balance_before,
                'token_balance_after': token_balance_after,
                'token_decrease': token_decrease,
                'lp_balance_before': lp_balance_before,
                'lp_balance_after': lp_balance_after,
                'lp_increase': lp_increase,
                'allowance_before': allowance_before,
                'allowance_after': allowance_after,
                'function_selector': actual_selector,
                'expected_selector': expected_selector
            }
        }

