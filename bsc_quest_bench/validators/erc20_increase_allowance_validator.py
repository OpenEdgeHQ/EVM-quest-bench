"""Validator for erc20_increase_allowance operation"""

from typing import Dict, Any


class ERC20IncreaseAllowanceValidator:
    """Validator for erc20_increase_allowance operation"""
    
    def __init__(self, token_address: str, spender_address: str, 
                 added_value: float, agent_address: str, token_decimals: int = 18):
        self.token_address = token_address.lower()
        self.spender_address = spender_address.lower()
        self.added_value = added_value
        self.agent_address = agent_address.lower()
        self.token_decimals = token_decimals
        self.added_value_wei = int(self.added_value * 10**self.token_decimals)
    
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
        
        # increaseAllowance selector: 0x39509351
        if isinstance(tx_data, str) and tx_data.startswith('0x39509351'):
            correct_function = True
        elif hasattr(tx_data, 'hex') and tx_data.hex().startswith('39509351'):
            correct_function = True
        
        function_score = 20 if correct_function else 0
        total_score += function_score
        
        checks.append({
            'name': 'Correct Function Called',
            'passed': correct_function,
            'score': function_score,
            'max_score': 20,
            'message': 'Called increaseAllowance(address,uint256)' if correct_function else f'Wrong function called. Expected increaseAllowance (0x39509351), got {tx_data[:10] if tx_data else "none"}'
        })
        
        # Decode actual parameters from transaction data
        actual_added_value_wei = self.added_value_wei  # Default to generated parameter
        actual_spender = None
        params_match = True
        param_mismatch_details = []
        
        if correct_function and len(tx_data) >= 138:
            try:
                # increaseAllowance(address spender, uint256 addedValue)
                # Data layout: 0x + 8 (selector) + 64 (spender) + 64 (addedValue)
                spender_hex = tx_data[10:74]  # Skip '0x39509351', take next 64 chars
                actual_spender = '0x' + spender_hex[-40:]  # Last 40 chars = 20 bytes = address
                
                added_value_hex = tx_data[74:138]  # Next 64 chars
                actual_added_value_wei = int(added_value_hex, 16)
                
                print(f"🔍 Decoded transaction parameters:")
                print(f"   Spender: {actual_spender}")
                print(f"   Added Value: {actual_added_value_wei / 10**self.token_decimals:.2f}")
                
                # Compare with generated parameters
                if actual_spender.lower() != self.spender_address.lower():
                    params_match = False
                    param_mismatch_details.append(f"spender mismatch: expected {self.spender_address}, got {actual_spender}")
                
                # No tolerance for amount (exact match required)
                if abs(actual_added_value_wei - self.added_value_wei) > 0:
                    params_match = False
                    param_mismatch_details.append(f"added_value mismatch: expected {self.added_value:.2f}, got {actual_added_value_wei / 10**self.token_decimals:.2f}")
                
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
        allowance_increase = allowance_after - allowance_before
        
        # Use actual added_value for validation
        expected_added_value = actual_added_value_wei / 10**self.token_decimals
        
        # 3. Allowance Increased Correctly (40 points)
        # increaseAllowance() ADDS to the current allowance
        # So we check if allowance increased by the specified addedValue (exact match)
        allowance_valid = allowance_increase == actual_added_value_wei
        allowance_score = 40 if allowance_valid else 0
        total_score += allowance_score
        
        allowance_message = f'Allowance increased by {allowance_increase / 10**self.token_decimals:.2f} (expected: {expected_added_value:.2f}). Before: {allowance_before / 10**self.token_decimals:.2f}, After: {allowance_after / 10**self.token_decimals:.2f}' if allowance_valid else f'Allowance increase mismatch. Expected increase: {expected_added_value:.2f}, actual increase: {allowance_increase / 10**self.token_decimals:.2f}'
        
        if not params_match and param_mismatch_details:
            allowance_message += f' [Note: Parameter mismatches: {", ".join(param_mismatch_details)}]'
        
        checks.append({
            'name': 'Allowance Increased Correctly',
            'passed': allowance_valid,
            'score': allowance_score,
            'max_score': 40,
            'message': allowance_message
        })
        
        # 4. No Token Transfer (10 points)
        # Token balance should not change for increaseAllowance
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
            'message': 'Token balance unchanged (increaseAllowance does not transfer)' if no_transfer else f'Token balance changed unexpectedly. Before: {balance_before / 10**self.token_decimals:.4f}, After: {balance_after / 10**self.token_decimals:.4f}'
        })
        
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': max_score,
            'checks': checks,
            'details': {
                'added_value': expected_added_value,
                'allowance_before': allowance_before / 10**self.token_decimals,
                'allowance_after': allowance_after / 10**self.token_decimals,
                'allowance_increase': allowance_increase / 10**self.token_decimals,
                'token_balance_unchanged': no_transfer,
                'function_called': tx_data[:10] if tx_data else 'none',
                'parameters_match': params_match,
                'parameter_mismatches': param_mismatch_details if param_mismatch_details else None,
                'actual_spender': actual_spender,
                'expected_spender': self.spender_address
            }
        }

