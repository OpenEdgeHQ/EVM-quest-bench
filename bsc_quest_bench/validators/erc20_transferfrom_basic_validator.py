from typing import Dict, Any, List

from decimal import Decimal

class ERC20TransferFromBasicValidator:
    """Validator for erc20_transferfrom_basic operation"""
    
    def __init__(self, token_address: str, from_address: str, to_address: str, 
                 amount: float, agent_address: str, token_decimals: int = 18):
        self.token_address = token_address.lower()
        self.from_address = from_address.lower()
        self.to_address = to_address.lower()
        self.amount = amount
        self.agent_address = agent_address.lower()
        self.token_decimals = token_decimals
        self.amount_wei = int(self.amount * 10**self.token_decimals)
    
    def validate(self, tx: Dict[str, Any], receipt: Dict[str, Any], 
                 state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate ERC20 transferFrom operation
        
        Checks:
        1. Transaction success (20 points)
        2. Correct function called (20 points)
        3. Allowance decreased correctly (20 points)
        4. From balance decreased correctly (20 points)
        5. To balance increased correctly (20 points)
        """
        checks = []
        total_score = 0
        max_score = 100
        
        # 1. Transaction Success (20 points)
        tx_success = receipt.get('status') == 1
        tx_score = 20 if tx_success else 0
        total_score += tx_score
        
        checks.append({
            'name': 'Transaction Success',
            'passed': tx_success,
            'score': tx_score,
            'max_score': 20,
            'message': 'Transaction executed successfully' if tx_success else f'Transaction failed with status: {receipt.get("status")}'
        })
        
        if not tx_success:
            return {
                'passed': False,
                'score': total_score,
                'max_score': max_score,
                'checks': checks,
                'error': 'Transaction failed'
            }
        
        # 2. Correct Function Called (20 points)
        # transferFrom function selector: 0x23b872dd
        tx_data = tx.get('data', '')
        correct_function = isinstance(tx_data, str) and tx_data.startswith('0x23b872dd')
        function_score = 20 if correct_function else 0
        total_score += function_score
        
        checks.append({
            'name': 'Correct Function Called',
            'passed': correct_function,
            'score': function_score,
            'max_score': 20,
            'message': 'Called transferFrom function' if correct_function else f'Wrong function called. Expected transferFrom (0x23b872dd), got: {tx_data[:10] if tx_data else "none"}'
        })
        
        # Decode actual parameters from transaction data
        # transferFrom(address from, address to, uint256 amount)
        # Data layout: 0x + 8 (selector) + 64 (from) + 64 (to) + 64 (amount)
        actual_amount_wei = self.amount_wei  # Default to generated parameter
        actual_from = None
        actual_to = None
        params_match = True  # Track if actual params match generated params
        param_mismatch_details = []
        
        if correct_function and len(tx_data) >= 202:  # 0x + 8 (selector) + 192 (3 params * 64)
            try:
                # Extract from_address
                from_hex = tx_data[10:74]  # Skip '0x23b872dd', take next 64 chars
                actual_from = '0x' + from_hex[-40:]  # Last 40 chars = address
                
                # Extract to_address
                to_hex = tx_data[74:138]  # Next 64 chars
                actual_to = '0x' + to_hex[-40:]  # Last 40 chars = address
                
                # Extract amount
                amount_hex = tx_data[138:202]  # Last 64 hex chars
                actual_amount_wei = int(amount_hex, 16)
                
                print(f"🔍 Decoded transaction parameters:")
                print(f"   From: {actual_from}")
                print(f"   To: {actual_to}")
                print(f"   Amount: {actual_amount_wei / 10**self.token_decimals:.4f}")
                
                # Verify parameters match generated parameters (case-insensitive for addresses)
                if actual_from.lower() != self.from_address.lower():
                    params_match = False
                    param_mismatch_details.append(f"from_address mismatch: expected {self.from_address}, got {actual_from}")
                
                if actual_to.lower() != self.to_address.lower():
                    params_match = False
                    param_mismatch_details.append(f"to_address mismatch: expected {self.to_address}, got {actual_to}")
                
                if abs(actual_amount_wei - self.amount_wei) > self.amount_wei * 0.01:
                    params_match = False
                    param_mismatch_details.append(f"amount mismatch: expected {self.amount:.4f}, got {actual_amount_wei / 10**self.token_decimals:.4f}")
                
                if not params_match:
                    print(f"⚠️  Parameter mismatches detected:")
                    for detail in param_mismatch_details:
                        print(f"     - {detail}")
                else:
                    print(f"✅ All parameters match generated values")
                    
            except Exception as e:
                print(f"⚠️  Failed to decode parameters from tx data: {e}, using generated parameters")
        
        # Get state changes
        # For transferFrom, we track:
        # - from_address balance (token_balance in state snapshot)
        # - to_address balance (target_token_balance in state snapshot)
        # - allowance (from_address has approved agent_address)
        
        from_balance_before = state_before.get('token_balance', 0)
        from_balance_after = state_after.get('token_balance', 0)
        from_balance_decrease = from_balance_before - from_balance_after
        
        to_balance_before = state_before.get('target_token_balance', 0)
        to_balance_after = state_after.get('target_token_balance', 0)
        to_balance_increase = to_balance_after - to_balance_before
        
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        allowance_decrease = allowance_before - allowance_after
        
        # Use actual amount for validation
        expected_amount = actual_amount_wei / 10**self.token_decimals
        
        # 3. Allowance Decreased Correctly (20 points)
        allowance_valid = abs(allowance_decrease - actual_amount_wei) <= actual_amount_wei * 0.001
        allowance_score = 20 if allowance_valid else 0
        total_score += allowance_score
        
        checks.append({
            'name': 'Allowance Decreased',
            'passed': allowance_valid,
            'score': allowance_score,
            'max_score': 20,
            'message': f'Allowance decreased by {allowance_decrease / 10**self.token_decimals:.4f} (expected: {expected_amount:.4f})' if allowance_valid else f'Allowance change mismatch. Expected: {expected_amount:.4f}, actual: {allowance_decrease / 10**self.token_decimals:.4f}'
        })
        
        # 4. From Balance Decreased (20 points)
        from_balance_valid = abs(from_balance_decrease - actual_amount_wei) <= actual_amount_wei * 0.001
        from_balance_score = 20 if from_balance_valid else 0
        total_score += from_balance_score
        
        checks.append({
            'name': 'From Balance Decreased',
            'passed': from_balance_valid,
            'score': from_balance_score,
            'max_score': 20,
            'message': f'From balance decreased by {from_balance_decrease / 10**self.token_decimals:.4f} (expected: {expected_amount:.4f})' if from_balance_valid else f'From balance change mismatch. Expected: {expected_amount:.4f}, actual: {from_balance_decrease / 10**self.token_decimals:.4f}'
        })
        
        # 5. To Balance Increased (20 points)
        to_balance_valid = abs(to_balance_increase - actual_amount_wei) <= actual_amount_wei * 0.001
        to_balance_score = 20 if to_balance_valid else 0
        total_score += to_balance_score
        
        # Add note about parameter mismatch if detected
        to_balance_message = f'To balance increased by {to_balance_increase / 10**self.token_decimals:.4f} (expected: {expected_amount:.4f})' if to_balance_valid else f'To balance change mismatch. Expected: {expected_amount:.4f}, actual: {to_balance_increase / 10**self.token_decimals:.4f}'
        
        if not params_match and param_mismatch_details:
            to_balance_message += f' [Note: Parameter mismatches detected: {", ".join(param_mismatch_details)}]'
        
        checks.append({
            'name': 'To Balance Increased',
            'passed': to_balance_valid,
            'score': to_balance_score,
            'max_score': 20,
            'message': to_balance_message
        })
        
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': max_score,
            'checks': checks,
            'details': {
                'transfer_amount': expected_amount,
                'from_balance_change': -from_balance_decrease / 10**self.token_decimals,
                'to_balance_change': to_balance_increase / 10**self.token_decimals,
                'allowance_change': -allowance_decrease / 10**self.token_decimals,
                'function_called': tx_data[:10] if tx_data else 'none',
                'parameters_match': params_match,
                'parameter_mismatches': param_mismatch_details if param_mismatch_details else None,
                'actual_from': actual_from,
                'actual_to': actual_to,
                'expected_from': self.from_address,
                'expected_to': self.to_address
            }
        }

