"""
ERC20 FlashLoan Validator

Validate flashloan operation.
"""

from typing import Dict, Any


class ERC20FlashLoanValidator:
    """Validate ERC20 flashloan operation"""
    
    def __init__(
        self,
        flashloan_contract_address: str,
        token_address: str,
        amount: float,
        token_decimals: int,
        fee_percentage: float
    ):
        self.flashloan_contract = flashloan_contract_address.lower()
        self.token_address = token_address.lower()
        self.amount = amount
        self.token_decimals = token_decimals
        self.fee_percentage = fee_percentage
        
        # Calculate fee (unit: token smallest unit)
        amount_smallest = int(amount * (10 ** token_decimals))
        self.expected_fee = int(amount_smallest * fee_percentage / 100)
        
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate flashloan transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result dictionary
        
        Checks:
        1. Transaction executed successfully (30%)
        2. Correct contract called: Flashloan contract (20%)
        3. Used function: executeFlashLoan function (20%)
        4. Paid correct fee (30%)
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
                    'flashloan_contract': self.flashloan_contract,
                    'token_address': self.token_address,
                    'amount': self.amount,
                    'expected_fee': self.expected_fee / (10 ** self.token_decimals),
                    'transaction_status': tx_status
                }
            }
        
        # 2. ValidateCorrect contract called: Flashloan contract (20 points)
        tx_to = tx.get('to', '').lower()
        if tx_to == self.flashloan_contract:
            checks.append({
                'name': 'Contract Address',
                'passed': True,
                'message': f'Correct flash loan contract: {tx_to}',
                'score': 20
            })
            total_score += 20
        else:
            checks.append({
                'name': 'Contract Address',
                'passed': False,
                'message': f'Wrong contract. Expected: {self.flashloan_contract}, Got: {tx_to}',
                'score': 20
            })
        
        # 3. ValidateUsed function: executeFlashLoan function (20 points)
        tx_data = tx.get('data', '') or tx.get('input', '')
        
        if isinstance(tx_data, bytes):
            tx_data = tx_data.hex()
        if isinstance(tx_data, str) and tx_data.startswith('0x'):
            tx_data = tx_data[2:]
        
        # executeFlashLoan(address,uint256) function selector
        # First 4 bytes of keccak256("executeFlashLoan(address,uint256)")
        expected_selector = '0x6065c245'
        actual_selector = 'N/A'
        
        if len(tx_data) >= 8:
            actual_selector = '0x' + tx_data[:8]
            
            if actual_selector.lower() == expected_selector.lower():
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'message': f'Correct executeFlashLoan selector: {actual_selector}',
                    'score': 20,
                    'details': {
                        'expected': expected_selector,
                        'actual': actual_selector
                    }
                })
                total_score += 20
            else:
                checks.append({
                    'name': 'Function Signature',
                    'passed': False,
                    'message': f'Incorrect function selector. Expected executeFlashLoan ({expected_selector}), got {actual_selector}',
                    'score': 20,
                    'details': {
                        'expected': expected_selector,
                        'actual': actual_selector
                    }
                })
        else:
            checks.append({
                'name': 'Function Signature',
                'passed': False,
                'message': 'Transaction data too short or missing',
                'score': 20
            })
        
        # 4. Validate fee payment (30 points)
        # Flashloan causes user balance to decrease by fee amount
        balance_before = state_before.get('token_balance', 0)
        balance_after = state_after.get('token_balance', 0)
        
        balance_decrease = balance_before - balance_after
        
        # Allow some error (due to precision issues)
        fee_tolerance = max(1, self.expected_fee // 100)  # 1% tolerance
        
        fee_check_passed = abs(balance_decrease - self.expected_fee) <= fee_tolerance
        
        if fee_check_passed:
            checks.append({
                'name': 'Fee Payment',
                'passed': True,
                'message': f'Flash loan fee paid correctly: {balance_decrease / (10 ** self.token_decimals):.6f} tokens',
                'score': 30,
                'details': {
                    'balance_before': balance_before / (10 ** self.token_decimals),
                    'balance_after': balance_after / (10 ** self.token_decimals),
                    'balance_decrease': balance_decrease / (10 ** self.token_decimals),
                    'expected_fee': self.expected_fee / (10 ** self.token_decimals),
                    'fee_percentage': self.fee_percentage
                }
            })
            total_score += 30
        else:
            checks.append({
                'name': 'Fee Payment',
                'passed': False,
                'message': f'Fee mismatch. Expected: {self.expected_fee / (10 ** self.token_decimals):.6f}, Actual: {balance_decrease / (10 ** self.token_decimals):.6f}',
                'score': 30,
                'details': {
                    'balance_before': balance_before / (10 ** self.token_decimals),
                    'balance_after': balance_after / (10 ** self.token_decimals),
                    'balance_decrease': balance_decrease / (10 ** self.token_decimals),
                    'expected_fee': self.expected_fee / (10 ** self.token_decimals),
                    'fee_percentage': self.fee_percentage
                }
            })
        
        # Aggregate results
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': self.max_score,
            'checks': checks,
            'details': {
                'flashloan_contract': self.flashloan_contract,
                'token_address': self.token_address,
                'amount': self.amount,
                'expected_fee': self.expected_fee / (10 ** self.token_decimals),
                'balance_before': balance_before / (10 ** self.token_decimals),
                'balance_after': balance_after / (10 ** self.token_decimals),
                'balance_decrease': balance_decrease / (10 ** self.token_decimals),
                'actual_selector': actual_selector
            }
        }

