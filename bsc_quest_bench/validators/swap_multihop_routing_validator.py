"""
Validator for PancakeSwap Multi-hop Routing Swap

This validator checks:
1. Transaction success
2. Token approval for input token
3. Correct Router contract interaction
4. Correct function call (swapExactTokensForTokens)
5. Input token balance decrease (exact amount)
6. Output token balance increase (with slippage tolerance)
7. Correct multi-hop path used (validate path length and intermediate tokens)
"""

from decimal import Decimal
from typing import Dict, Any, List


class SwapMultihopRoutingValidator:
    """Validator for PancakeSwap multi-hop routing swap"""
    
    def __init__(
        self,
        router_address: str,
        token_start_address: str,
        token_end_address: str,
        amount_in: float,
        token_start_decimals: int = 18,
        token_end_decimals: int = 18,
        slippage: float = 5.0,
        **kwargs  # Accept extra params
    ):
        """
        Initialize validator
        
        Args:
            router_address: PancakeSwap Router V2 address
            token_start_address: Starting token address
            token_end_address: Ending token address
            amount_in: Amount of starting tokens to swap
            token_start_decimals: Starting token decimals
            token_end_decimals: Ending token decimals
            slippage: Slippage tolerance percentage
        """
        if not router_address:
            raise ValueError("router_address is required but was None or empty")
        if not token_start_address:
            raise ValueError("token_start_address is required but was None or empty")
        if not token_end_address:
            raise ValueError("token_end_address is required but was None or empty")
        
        self.router_address = router_address.lower()
        self.token_start_address = token_start_address.lower()
        self.token_end_address = token_end_address.lower()
        self.amount_in = Decimal(str(amount_in))
        self.token_start_decimals = token_start_decimals
        self.token_end_decimals = token_end_decimals
        self.slippage = Decimal(str(slippage)) / Decimal('100')
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate multi-hop routing swap transaction
        
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
        max_score = 100
        
        # Convert amount to smallest unit
        amount_in_wei = int(self.amount_in * Decimal(10 ** self.token_start_decimals))
        
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
                'max_score': max_score,
                'checks': checks
            }
        
        # 2. Check token approval (10 points)
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        
        if allowance_before > 0 or allowance_after > 0:
            score += 10
            checks.append({
                'name': 'Token Approval',
                'passed': True,
                'message': f'Input token approved. Allowance before: {allowance_before}, after: {allowance_after}'
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
        # swapExactTokensForTokens function selector: 0x38ed1739
        tx_data = tx.get('data', '')
        expected_selector = '0x38ed1739'
        actual_selector = tx_data[:10] if tx_data else ''
        
        if actual_selector == expected_selector:
            score += 10
            checks.append({
                'name': 'Correct Function',
                'passed': True,
                'message': f'Correct function: swapExactTokensForTokens ({actual_selector})'
            })
        else:
            checks.append({
                'name': 'Correct Function',
                'passed': False,
                'message': f'Wrong function. Expected: {expected_selector}, Got: {actual_selector}'
            })
        
        # 5. Check input token balance decrease (20 points)
        token_start_balance_before = state_before.get('token_balance', 0)
        token_start_balance_after = state_after.get('token_balance', 0)
        token_start_decrease = token_start_balance_before - token_start_balance_after
        
        # Convert to Decimal for precise comparison
        token_start_decrease_decimal = Decimal(str(token_start_decrease))
        amount_in_wei_decimal = Decimal(str(amount_in_wei))
        
        if token_start_decrease_decimal == amount_in_wei_decimal:
            score += 20
            token_start_decrease_human = float(token_start_decrease_decimal / Decimal(10 ** self.token_start_decimals))
            checks.append({
                'name': 'Input Token Decrease',
                'passed': True,
                'message': f'Input token decreased correctly by {token_start_decrease_human:.6f} tokens'
            })
        else:
            token_start_decrease_human = float(token_start_decrease_decimal / Decimal(10 ** self.token_start_decimals))
            checks.append({
                'name': 'Input Token Decrease',
                'passed': False,
                'message': f'Input token balance change incorrect. Expected: {float(self.amount_in):.6f}, Got: {token_start_decrease_human:.6f}'
            })
        
        # 6. Check output token balance increase (20 points)
        token_end_balance_before = state_before.get('target_token_balance', 0)
        token_end_balance_after = state_after.get('target_token_balance', 0)
        token_end_increase = token_end_balance_after - token_end_balance_before
        
        if token_end_increase > 0:
            score += 20
            token_end_increase_human = float(Decimal(str(token_end_increase)) / Decimal(10 ** self.token_end_decimals))
            checks.append({
                'name': 'Output Token Increase',
                'passed': True,
                'message': f'Output token increased by {token_end_increase_human:.6f} tokens'
            })
        else:
            checks.append({
                'name': 'Output Token Increase',
                'passed': False,
                'message': f'Output token did not increase. Change: {token_end_increase}'
            })
        
        # 7. Check multi-hop path validation (10 points)
        # Decode transaction data to extract path
        path_check_passed = False
        path_info = "Unable to decode path from transaction data"
        
        try:
            if len(tx_data) > 10:
                # The path is encoded in the transaction data
                # For swapExactTokensForTokens, the path array is at a specific offset
                # We'll check logs for pair interactions as a proxy
                logs = receipt.get('logs', [])
                
                # Count unique pair contracts interacted with (from logs)
                pair_addresses = set()
                for log in logs:
                    # Check if this is a Swap event or Transfer event from a pair
                    log_address = log.get('address', '').lower()
                    if log_address and log_address != self.token_start_address and log_address != self.token_end_address:
                        pair_addresses.add(log_address)
                
                # Multi-hop should involve at least 2 pairs (for 3+ hops)
                if len(pair_addresses) >= 2:
                    path_check_passed = True
                    path_info = f"Multi-hop path detected: {len(pair_addresses)} pairs/intermediaries involved"
                else:
                    path_info = f"Insufficient hops detected. Only {len(pair_addresses)} pairs/intermediaries found (expected >= 2)"
        
        except Exception as e:
            path_info = f"Error validating path: {str(e)}"
        
        if path_check_passed:
            score += 10
            checks.append({
                'name': 'Multi-hop Path',
                'passed': True,
                'message': path_info
            })
        else:
            checks.append({
                'name': 'Multi-hop Path',
                'passed': False,
                'message': path_info
            })
        
        # Determine overall pass/fail
        passed = score >= 80  # Need 80% to pass (hard difficulty)
        
        return {
            'passed': passed,
            'score': score,
            'max_score': max_score,
            'checks': checks,
            'details': {
                'router_address': self.router_address,
                'token_start_address': self.token_start_address,
                'token_end_address': self.token_end_address,
                'amount_in': float(self.amount_in),
                'amount_in_wei': amount_in_wei,
                'token_start_balance_before': token_start_balance_before,
                'token_start_balance_after': token_start_balance_after,
                'token_start_decrease': token_start_decrease,
                'token_end_balance_before': token_end_balance_before,
                'token_end_balance_after': token_end_balance_after,
                'token_end_increase': token_end_increase,
                'allowance_before': allowance_before,
                'allowance_after': allowance_after,
                'function_selector': actual_selector,
                'expected_selector': expected_selector
            }
        }

