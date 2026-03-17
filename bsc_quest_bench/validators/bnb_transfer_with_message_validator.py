"""
BNB Transfer with Message Validator

Validates that a BNB transfer transaction includes a text message in the data field
"""

from typing import Dict, Any


class BNBTransferWithMessageValidator:
    """Validator for BNB transfers with attached text messages"""
    
    def __init__(self, to_address: str, amount: float, message: str):
        """
        Initialize validator
        
        Args:
            to_address: Expected recipient address
            amount: Expected transfer amount in BNB (float)
            message: Expected message text
        """
        from decimal import Decimal
        
        self.expected_to = to_address.lower()
        # Use Decimal for precise BNB to wei conversion
        self.expected_amount = int(Decimal(str(amount)) * Decimal(10**18))
        self.expected_message = message
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
        
        # Check 1: Transaction success (20 points)
        tx_success = receipt.get('status') == 1
        if tx_success:
            score += 20
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'points': 20,
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
        
        # Use the transaction object and receipt
        tx_object = tx
        tx_receipt = receipt
        
        # Check 2: Recipient address (20 points)
        actual_to = tx_object.get('to', '').lower()
        to_correct = actual_to == self.expected_to
        
        if to_correct:
            score += 20
            checks.append({
                'name': 'Recipient Address',
                'passed': True,
                'points': 20,
                'message': f'Correct recipient: {self.expected_to}'
            })
        else:
            checks.append({
                'name': 'Recipient Address',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_to}, Got: {actual_to}'
            })
        
        details['expected_to'] = self.expected_to
        details['actual_to'] = actual_to
        
        # Check 3: Transfer amount (20 points)
        actual_value = int(tx_object.get('value', 0))
        amount_correct = actual_value == self.expected_amount
        
        if amount_correct:
            score += 20
            checks.append({
                'name': 'Transfer Amount',
                'passed': True,
                'points': 20,
                'message': f'Correct amount: {self.expected_amount} wei'
            })
        else:
            checks.append({
                'name': 'Transfer Amount',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_amount} wei, Got: {actual_value} wei'
            })
        
        details['expected_amount'] = self.expected_amount
        details['actual_amount'] = actual_value
        
        # Check 4: Message in transaction data (30 points)
        tx_data = tx_object.get('data', '0x')
        
        # Decode the data field
        message_found = False
        message_correct = False
        decoded_message = None
        
        if tx_data and tx_data != '0x':
            try:
                # Remove '0x' prefix and convert hex to bytes
                data_bytes = bytes.fromhex(tx_data[2:])
                
                # Try to decode as UTF-8
                try:
                    decoded_message = data_bytes.decode('utf-8')
                    message_found = True
                    
                    # Check if expected message is in the decoded data
                    if self.expected_message in decoded_message:
                        message_correct = True
                    elif decoded_message.strip() == self.expected_message.strip():
                        message_correct = True
                except UnicodeDecodeError:
                    # Try to decode as ASCII
                    try:
                        decoded_message = data_bytes.decode('ascii', errors='ignore')
                        message_found = True
                        if self.expected_message in decoded_message:
                            message_correct = True
                    except:
                        pass
            except Exception as e:
                details['decode_error'] = str(e)
        
        if message_correct:
            score += 30
            checks.append({
                'name': 'Message in Data Field',
                'passed': True,
                'points': 30,
                'message': f'Message correctly encoded: "{self.expected_message}"'
            })
        elif message_found:
            # Message found but not exact match - no partial credit for consistency
            checks.append({
                'name': 'Message in Data Field',
                'passed': False,
                'points': 0,
                'message': f'Message found but not exact match. Expected: "{self.expected_message}", Got: "{decoded_message}"'
            })
        else:
            checks.append({
                'name': 'Message in Data Field',
                'passed': False,
                'points': 0,
                'message': f'No message found in transaction data. Expected: "{self.expected_message}"'
            })
        
        details['expected_message'] = self.expected_message
        details['tx_data'] = tx_data
        details['decoded_message'] = decoded_message
        
        # Check 5: Balance change (10 points)
        balance_before = state_before.get('balance', 0)
        balance_after = state_after.get('balance', 0)
        gas_used = tx_receipt.get('gasUsed', 0)
        gas_price = tx_receipt.get('effectiveGasPrice', 0)
        gas_cost = gas_used * gas_price
        
        expected_balance = balance_before - self.expected_amount - gas_cost
        balance_diff = abs(balance_after - expected_balance)
        
        # Allow 0.1% tolerance for rounding errors
        tolerance = max(int(self.expected_amount * 0.001), 1)
        balance_correct = balance_diff <= tolerance
        
        if balance_correct:
            score += 10
            checks.append({
                'name': 'Balance Change',
                'passed': True,
                'points': 10,
                'message': 'Balance decreased correctly (including gas)'
            })
        else:
            checks.append({
                'name': 'Balance Change',
                'passed': False,
                'points': 0,
                'message': f'Balance mismatch. Expected: {expected_balance}, Got: {balance_after}, Diff: {balance_diff}'
            })
        
        details['balance_before'] = balance_before
        details['balance_after'] = balance_after
        details['gas_cost'] = gas_cost
        details['expected_balance'] = expected_balance
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }

