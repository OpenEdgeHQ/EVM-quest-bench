"""
ERC1363 ApproveAndCall Validator

Validate ERC1363 token approveAndCall operation execution.
"""

from typing import Dict, Any
from decimal import Decimal


class ERC20ApproveAndCall1363Validator:
    """Validate ERC1363 approveAndCall operation"""
    
    def __init__(
        self,
        token_address: str,
        spender_address: str,
        amount: float,
        token_decimals: int = 18
    ):
        self.token_address = token_address.lower()
        self.spender_address = spender_address.lower()
        
        # Use Decimal for precise calculation
        self.expected_amount = int(Decimal(str(amount)) * Decimal(10 ** token_decimals))
        self.token_decimals = token_decimals
        
        # approveAndCall function selector (accepts two overloaded versions)
        # 2 parameter version: approveAndCall(address,uint256) = 0x3177029f
        # 3 parameter version: approveAndCall(address,uint256,bytes) = 0xcae9ca51
        self.expected_selectors = ['0x3177029f', '0xcae9ca51']
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate ERC1363 approveAndCall transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result dictionary
        
        Checks:
        1. Transaction executed successfully (30%)
        2. Allowance correctly set (50%)
        3. Used function: approveAndCall function (correct selector)(20%)
        """
        
        checks = []
        total_score = 0
        
        # 1. Validate transaction success (30 points)
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
                'score': 30
            })
            # If transaction failed, return directly
            return {
                'passed': False,
                'score': 0,
                'max_score': self.max_score,
                'checks': checks,
                'details': {
                    'token_address': self.token_address,
                    'spender_address': self.spender_address,
                    'expected_amount': self.expected_amount,
                    'transaction_status': tx_status
                }
            }
        
        # 2. Validate allowance correctly set (50 points)
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        
        if allowance_after == self.expected_amount:
            checks.append({
                'name': 'Allowance Set Correctly',
                'passed': True,
                'message': f'Allowance correctly set to {self.expected_amount} units',
                'score': 50,
                'details': {
                    'allowance_before': allowance_before,
                    'allowance_after': allowance_after,
                    'expected_allowance': self.expected_amount
                }
            })
            total_score += 50
        else:
            checks.append({
                'name': 'Allowance Set Correctly',
                'passed': False,
                'message': f'Allowance mismatch. Expected: {self.expected_amount}, Got: {allowance_after}',
                'score': 50,
                'details': {
                    'allowance_before': allowance_before,
                    'allowance_after': allowance_after,
                    'expected_allowance': self.expected_amount
                }
            })
        
        # 3. Validate Used function: correct function selector (20 points)
        tx_data = tx.get('data', '') or tx.get('input', '')
        
        if isinstance(tx_data, bytes):
            tx_data = tx_data.hex()
        if isinstance(tx_data, str) and tx_data.startswith('0x'):
            tx_data = tx_data[2:]
        
        # Extract function selector (First 4 bytes = 8 hex chars)
        actual_selector = 'N/A'
        if len(tx_data) >= 8:
            actual_selector = '0x' + tx_data[:8]
            
            # Check if matches any expected selector
            if actual_selector.lower() in [s.lower() for s in self.expected_selectors]:
                # Determine which version is used
                version = "2-parameter" if actual_selector.lower() == '0x3177029f' else "3-parameter"
                checks.append({
                    'name': 'Function Selector',
                    'passed': True,
                    'message': f'Correct approveAndCall selector ({version}): {actual_selector}',
                    'score': 20,
                    'details': {
                        'expected': self.expected_selectors,
                        'actual': actual_selector,
                        'version': version
                    }
                })
                total_score += 20
            else:
                checks.append({
                    'name': 'Function Selector',
                    'passed': False,
                    'message': f'Incorrect function selector. Expected approveAndCall ({" or ".join(self.expected_selectors)}), got {actual_selector}',
                    'score': 20,
                    'details': {
                        'expected': self.expected_selectors,
                        'actual': actual_selector
                    }
                })
        else:
            checks.append({
                'name': 'Function Selector',
                'passed': False,
                'message': 'Transaction data too short or missing',
                'score': 20
            })
        
        # Aggregate results
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': self.max_score,
            'checks': checks,
            'details': {
                'token_address': self.token_address,
                'spender_address': self.spender_address,
                'expected_amount': self.expected_amount,
                'allowance_before': allowance_before,
                'allowance_after': allowance_after,
                'expected_selectors': self.expected_selectors,
                'actual_selector': actual_selector
            }
        }

