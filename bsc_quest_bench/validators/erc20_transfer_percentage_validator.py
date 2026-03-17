"""
ERC20 Percentage Token Transfer Validator

Validates that an ERC20 token percentage transfer transaction is correctly executed
"""

from typing import Dict, Any


class ERC20TransferPercentageValidator:
    """Validator for ERC20 percentage token transfers"""
    
    def __init__(self, token_address: str, to_address: str, percentage: int, token_decimals: int = 18):
        """
        Initialize validator
        
        Args:
            token_address: ERC20 token contract address
            to_address: Expected recipient address
            percentage: Expected percentage of balance to transfer (e.g., 50 for 50%)
            token_decimals: Token decimals (default: 18)
        """
        self.expected_token = token_address.lower()
        self.expected_to = to_address.lower()
        self.percentage = percentage
        self.token_decimals = token_decimals
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the transaction execution results
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: Blockchain state before transaction
            state_after: Blockchain state after transaction
            
        Returns:
            Validation results including score and details
        """
        score = 0
        details = {}
        checks = []
        
        # Get token balances
        sender_balance_before = state_before.get('token_balance', 0)
        
        # Calculate expected transfer amount (percentage of balance before)
        expected_amount_wei = int(sender_balance_before * self.percentage / 100)
        
        # Check 1: Transaction success (30 points)
        tx_success = receipt.get('status') == 1
        if tx_success:
            score += 30
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'points': 30,
                'message': 'Transaction executed successfully'
            })
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'points': 0,
                'message': f"Transaction failed with status: {receipt.get('status')}"
            })
            return {
                'score': score,
                'max_score': self.max_score,
                'passed': False,
                'checks': checks,
                'details': details
            }
        
        # Check 2: Contract address correct (20 points)
        actual_to = tx.get('to', '').lower()
        contract_correct = actual_to == self.expected_token
        
        if contract_correct:
            score += 20
            checks.append({
                'name': 'Contract Address',
                'passed': True,
                'points': 20,
                'message': f'Correct token contract: {self.expected_token}'
            })
        else:
            checks.append({
                'name': 'Contract Address',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_token}, Got: {actual_to}'
            })
        
        details['expected_token'] = self.expected_token
        details['actual_to'] = actual_to
        
        # Check 3: Function signature (10 points)
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:
            function_selector = tx_data[:10].lower()
            expected_selector = '0xa9059cbb'  # transfer(address,uint256)
            
            if function_selector == expected_selector:
                score += 10
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 10,
                    'message': 'Correct ERC20 transfer function signature'
                })
                
                # Decode parameters
                try:
                    if len(tx_data) >= 138:
                        recipient_hex = tx_data[10:74]
                        amount_hex = tx_data[74:138]
                        
                        recipient_address = '0x' + recipient_hex[-40:]
                        amount_value = int(amount_hex, 16)
                        
                        details['decoded_recipient'] = recipient_address.lower()
                        details['decoded_amount'] = amount_value
                except Exception as e:
                    details['decode_error'] = str(e)
            else:
                checks.append({
                    'name': 'Function Signature',
                    'passed': False,
                    'points': 0,
                    'message': f'Expected: {expected_selector}, Got: {function_selector}'
                })
        else:
            checks.append({
                'name': 'Function Signature',
                'passed': False,
                'points': 0,
                'message': 'No data field or too short'
            })
        
        details['function_selector'] = tx_data[:10] if tx_data else None
        
        # Check 4: Transfer amount is correct percentage (30 points)
        sender_balance_after = state_after.get('token_balance', 0)
        actual_transfer_amount = sender_balance_before - sender_balance_after
        
        # Allow 0.1% tolerance for calculation differences
        tolerance = int(expected_amount_wei * 0.001)
        amount_correct = abs(actual_transfer_amount - expected_amount_wei) <= tolerance
        
        if amount_correct:
            score += 30
            checks.append({
                'name': 'Transfer Amount (Percentage)',
                'passed': True,
                'points': 30,
                'message': f'Correct: {self.percentage}% of {sender_balance_before} tokens = {expected_amount_wei} (smallest unit)'
            })
        else:
            checks.append({
                'name': 'Transfer Amount (Percentage)',
                'passed': False,
                'points': 0,
                'message': f'Expected: {expected_amount_wei} ({self.percentage}% of {sender_balance_before}), Got: {actual_transfer_amount}'
            })
        
        details['sender_balance_before'] = sender_balance_before
        details['expected_amount'] = expected_amount_wei
        details['percentage'] = self.percentage
        details['actual_transfer_amount'] = actual_transfer_amount
        
        # Check 5: Receiver token balance increased correctly (10 points)
        receiver_balance_before = state_before.get('target_token_balance', 0)
        receiver_balance_after = state_after.get('target_token_balance', 0)
        receiver_change = receiver_balance_after - receiver_balance_before
        
        receiver_correct = abs(receiver_change - expected_amount_wei) <= tolerance
        
        if receiver_correct:
            score += 10
            checks.append({
                'name': 'Receiver Balance Increase',
                'passed': True,
                'points': 10,
                'message': f'Receiver balance increased by {receiver_change} (expected: {expected_amount_wei})'
            })
        else:
            checks.append({
                'name': 'Receiver Balance Increase',
                'passed': False,
                'points': 0,
                'message': f'Expected increase: {expected_amount_wei}, Actual: {receiver_change}'
            })
        
        details['receiver_balance_before'] = receiver_balance_before
        details['receiver_balance_after'] = receiver_balance_after
        details['receiver_change'] = receiver_change
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }

