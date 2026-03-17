"""Validator for erc20_approve operation"""

from typing import Dict, Any


class ERC20ApproveValidator:
    """Validator for erc20_approve operation"""
    
    def __init__(self, token_address: str, spender_address: str, 
                 amount: float, agent_address: str, token_decimals: int = 18):
        self.token_address = token_address.lower()
        self.spender_address = spender_address.lower()
        self.amount = amount
        self.agent_address = agent_address.lower()
        self.token_decimals = token_decimals
        self.amount_wei = int(self.amount * 10**self.token_decimals)
    
    def validate(self, tx: Dict[str, Any], receipt: Dict[str, Any], 
                 state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, Any]:
        checks = []
        total_score = 0
        max_score = 100
        
        # 1. Transaction Success (30 points)
        tx_success = receipt.get('status') == 1
        tx_success_score = 30 if tx_success else 0
        total_score += tx_success_score
        
        checks.append({
            'name': 'Transaction Success',
            'passed': tx_success,
            'score': tx_success_score,
            'max_score': 30,
            'message': 'Transaction executed successfully' if tx_success else 'Transaction failed'
        })
        
        if not tx_success:
            # If transaction failed, skip other checks
            return {
                'passed': False,
                'score': total_score,
                'max_score': max_score,
                'checks': checks,
                'details': {
                    'transaction_failed': True
                }
            }
        
        # 2. Correct Function Called (20 points)
        tx_data = tx.get('data', '') if isinstance(tx, dict) else tx.data if hasattr(tx, 'data') else ''
        correct_function = False
        
        if isinstance(tx_data, str) and tx_data.startswith('0x095ea7b3'):
            correct_function = True
        elif hasattr(tx_data, 'hex') and tx_data.hex().startswith('095ea7b3'):
            correct_function = True
        
        function_score = 20 if correct_function else 0
        total_score += function_score
        
        checks.append({
            'name': 'Correct Function Called',
            'passed': correct_function,
            'score': function_score,
            'max_score': 20,
            'message': 'Called approve(address,uint256)' if correct_function else f'Wrong function called. Expected approve (0x095ea7b3), got {tx_data[:10] if tx_data else "none"}'
        })
        
        # Decode actual parameters from transaction data
        actual_amount_wei = self.amount_wei  # Default to generated parameter
        actual_spender = None
        params_match = True
        param_mismatch_details = []
        
        if correct_function and len(tx_data) >= 138:
            try:
                # approve(address spender, uint256 amount)
                # Data layout: 0x + 8 (selector) + 64 (spender) + 64 (amount)
                spender_hex = tx_data[10:74]  # Skip '0x095ea7b3', take next 64 chars
                actual_spender = '0x' + spender_hex[-40:]  # Last 40 chars = 20 bytes = address
                
                amount_hex = tx_data[74:138]  # Next 64 chars
                actual_amount_wei = int(amount_hex, 16)
                
                print(f"🔍 Decoded transaction parameters:")
                print(f"   Spender: {actual_spender}")
                print(f"   Amount: {actual_amount_wei / 10**self.token_decimals:.2f}")
                
                # Compare with generated parameters
                if actual_spender.lower() != self.spender_address.lower():
                    params_match = False
                    param_mismatch_details.append(f"spender mismatch: expected {self.spender_address}, got {actual_spender}")
                
                # No tolerance for amount (exact match required)
                if abs(actual_amount_wei - self.amount_wei) > 0:
                    params_match = False
                    param_mismatch_details.append(f"amount mismatch: expected {self.amount:.2f}, got {actual_amount_wei / 10**self.token_decimals:.2f}")
                
                if not params_match:
                    print(f"⚠️  Parameter mismatches detected:")
                    for detail in param_mismatch_details:
                        print(f"     - {detail}")
                else:
                    print(f"✅ All parameters match generated values")
                    
            except Exception as e:
                print(f"⚠️  Failed to decode parameters from tx data: {e}, using generated parameters")
        
        # Get state changes
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        allowance_change = allowance_after - allowance_before
        
        # Use actual amount for validation
        expected_amount = actual_amount_wei / 10**self.token_decimals
        
        # 3. Allowance Set Correctly (40 points)
        # approve() SETS the allowance to the specified amount (not increases it)
        # So we check if allowance_after equals the approved amount (exact match)
        allowance_valid = allowance_after == actual_amount_wei
        allowance_score = 40 if allowance_valid else 0
        total_score += allowance_score
        
        allowance_message = f'Allowance set to {allowance_after / 10**self.token_decimals:.2f} (expected: {expected_amount:.2f})' if allowance_valid else f'Allowance mismatch. Expected: {expected_amount:.2f}, actual: {allowance_after / 10**self.token_decimals:.2f}'
        
        if not params_match and param_mismatch_details:
            allowance_message += f' [Note: Parameter mismatches: {", ".join(param_mismatch_details)}]'
        
        checks.append({
            'name': 'Allowance Set Correctly',
            'passed': allowance_valid,
            'score': allowance_score,
            'max_score': 40,
            'message': allowance_message
        })
        
        # 4. No Token Transfer (10 points)
        # Token balance should not change for approve
        balance_before = state_before.get('token_balance', 0)
        balance_after = state_after.get('token_balance', 0)
        no_transfer = balance_before == balance_after
        
        no_transfer_score = 10 if no_transfer else 0
        total_score += no_transfer_score
        
        checks.append({
            'name': 'No Token Transfer',
            'passed': no_transfer,
            'score': no_transfer_score,
            'max_score': 10,
            'message': 'Token balance unchanged (approve does not transfer)' if no_transfer else f'Token balance changed unexpectedly. Before: {balance_before / 10**self.token_decimals:.4f}, After: {balance_after / 10**self.token_decimals:.4f}'
        })
        
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': max_score,
            'checks': checks,
            'details': {
                'approved_amount': expected_amount,
                'allowance_before': allowance_before / 10**self.token_decimals,
                'allowance_after': allowance_after / 10**self.token_decimals,
                'allowance_change': allowance_change / 10**self.token_decimals,
                'token_balance_unchanged': no_transfer,
                'function_called': tx_data[:10] if tx_data else 'none',
                'parameters_match': params_match,
                'parameter_mismatches': param_mismatch_details if param_mismatch_details else None,
                'actual_spender': actual_spender,
                'expected_spender': self.spender_address
            }
        }
