"""Validator for erc20_decrease_allowance operation"""

from typing import Dict, Any


class ERC20DecreaseAllowanceValidator:
    """Validator for erc20_decrease_allowance operation"""
    
    def __init__(self, token_address: str, spender_address: str, 
                 subtracted_value: float, agent_address: str, token_decimals: int = 18):
        self.token_address = token_address.lower()
        self.spender_address = spender_address.lower()
        self.subtracted_value = subtracted_value
        self.agent_address = agent_address.lower()
        self.token_decimals = token_decimals
        self.subtracted_value_wei = int(self.subtracted_value * 10**self.token_decimals)
    
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
            'message': 'Transaction executed successfully' if tx_success else 'Transaction failed (possibly due to underflow: subtractedValue > current allowance)'
        })
        
        if not tx_success:
            # If transaction failed, skip other checks
            return {
                'passed': False,
                'score': total_score,
                'max_score': max_score,
                'checks': checks,
                'details': {
                    'transaction_failed': True,
                    'possible_reason': 'Underflow protection: subtractedValue may exceed current allowance'
                }
            }
        
        # 2. Correct Function Called (20 points)
        tx_data = tx.get('data', '') if isinstance(tx, dict) else tx.data if hasattr(tx, 'data') else ''
        correct_function = False
        
        # decreaseAllowance selector: 0xa457c2d7
        if isinstance(tx_data, str) and tx_data.startswith('0xa457c2d7'):
            correct_function = True
        elif hasattr(tx_data, 'hex') and tx_data.hex().startswith('a457c2d7'):
            correct_function = True
        
        function_score = 20 if correct_function else 0
        total_score += function_score
        
        checks.append({
            'name': 'Correct Function Called',
            'passed': correct_function,
            'score': function_score,
            'max_score': 20,
            'message': 'Called decreaseAllowance(address,uint256)' if correct_function else f'Wrong function called. Expected decreaseAllowance (0xa457c2d7), got {tx_data[:10] if tx_data else "none"}'
        })
        
        # Decode actual parameters from transaction data
        actual_subtracted_value_wei = self.subtracted_value_wei  # Default to generated parameter
        actual_spender = None
        params_match = True
        param_mismatch_details = []
        
        if correct_function and len(tx_data) >= 138:
            try:
                # decreaseAllowance(address spender, uint256 subtractedValue)
                # Data layout: 0x + 8 (selector) + 64 (spender) + 64 (subtractedValue)
                spender_hex = tx_data[10:74]  # Skip '0xa457c2d7', take next 64 chars
                actual_spender = '0x' + spender_hex[-40:]  # Last 40 chars = 20 bytes = address
                
                subtracted_value_hex = tx_data[74:138]  # Next 64 chars
                actual_subtracted_value_wei = int(subtracted_value_hex, 16)
                
                print(f"🔍 Decoded transaction parameters:")
                print(f"   Spender: {actual_spender}")
                print(f"   Subtracted Value: {actual_subtracted_value_wei / 10**self.token_decimals:.2f}")
                
                # Compare with generated parameters
                if actual_spender.lower() != self.spender_address.lower():
                    params_match = False
                    param_mismatch_details.append(f"spender mismatch: expected {self.spender_address}, got {actual_spender}")
                
                # No tolerance for amount (exact match required)
                if abs(actual_subtracted_value_wei - self.subtracted_value_wei) > 0:
                    params_match = False
                    param_mismatch_details.append(f"subtracted_value mismatch: expected {self.subtracted_value:.2f}, got {actual_subtracted_value_wei / 10**self.token_decimals:.2f}")
                
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
        allowance_decrease = allowance_before - allowance_after
        
        # Use actual subtracted_value for validation
        expected_subtracted_value = actual_subtracted_value_wei / 10**self.token_decimals
        
        # 3. Allowance Decreased Correctly (40 points)
        # decreaseAllowance() SUBTRACTS from the current allowance
        # So we check if allowance decreased by the specified subtractedValue (exact match)
        allowance_valid = allowance_decrease == actual_subtracted_value_wei
        allowance_score = 40 if allowance_valid else 0
        total_score += allowance_score
        
        allowance_message = f'Allowance decreased by {allowance_decrease / 10**self.token_decimals:.2f} (expected: {expected_subtracted_value:.2f}). Before: {allowance_before / 10**self.token_decimals:.2f}, After: {allowance_after / 10**self.token_decimals:.2f}' if allowance_valid else f'Allowance decrease mismatch. Expected decrease: {expected_subtracted_value:.2f}, actual decrease: {allowance_decrease / 10**self.token_decimals:.2f}'
        
        if not params_match and param_mismatch_details:
            allowance_message += f' [Note: Parameter mismatches: {", ".join(param_mismatch_details)}]'
        
        checks.append({
            'name': 'Allowance Decreased Correctly',
            'passed': allowance_valid,
            'score': allowance_score,
            'max_score': 40,
            'message': allowance_message
        })
        
        # 4. No Token Transfer (10 points)
        # Token balance should not change for decreaseAllowance
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
            'message': 'Token balance unchanged (decreaseAllowance does not transfer)' if no_transfer else f'Token balance changed unexpectedly. Before: {balance_before / 10**self.token_decimals:.4f}, After: {balance_after / 10**self.token_decimals:.4f}'
        })
        
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': max_score,
            'checks': checks,
            'details': {
                'subtracted_value': expected_subtracted_value,
                'allowance_before': allowance_before / 10**self.token_decimals,
                'allowance_after': allowance_after / 10**self.token_decimals,
                'allowance_decrease': allowance_decrease / 10**self.token_decimals,
                'token_balance_unchanged': no_transfer,
                'function_called': tx_data[:10] if tx_data else 'none',
                'parameters_match': params_match,
                'parameter_mismatches': param_mismatch_details if param_mismatch_details else None,
                'actual_spender': actual_spender,
                'expected_spender': self.spender_address
            }
        }

