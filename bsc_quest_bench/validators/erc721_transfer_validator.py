"""
ERC721 Transfer Validator

Validates that an ERC721 NFT was successfully transferred
"""

from typing import Dict, Any


class ERC721TransferValidator:
    """Validator for ERC721 NFT transfer transactions"""
    
    def __init__(self, nft_address: str, to_address: str, token_id: int, **kwargs):
        """
        Initialize validator
        
        Args:
            nft_address: ERC721 NFT contract address
            to_address: Expected recipient address
            token_id: NFT token ID that should be transferred
        """
        if not nft_address:
            raise ValueError("nft_address is required but was None or empty")
        if not to_address:
            raise ValueError("to_address is required but was None or empty")
        
        self.expected_nft = nft_address.lower()
        self.expected_recipient = to_address.lower()
        self.token_id = token_id
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
        
        # Check 2: NFT contract address correct (20 points)
        actual_to = tx.get('to', '').lower()
        contract_correct = actual_to == self.expected_nft
        
        if contract_correct:
            score += 20
            checks.append({
                'name': 'NFT Contract',
                'passed': True,
                'points': 20,
                'message': f'Correct NFT contract: {self.expected_nft}'
            })
        else:
            checks.append({
                'name': 'NFT Contract',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_nft}, Got: {actual_to}'
            })
        
        details['expected_nft'] = self.expected_nft
        details['actual_to'] = actual_to
        
        # Check 3: Function signature (20 points)
        # ERC721 transferFrom function selector: 0x23b872dd (keccak256("transferFrom(address,address,uint256)"))
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:
            function_selector = tx_data[:10].lower()
            expected_selector = '0x23b872dd'  # transferFrom(address,address,uint256)
            
            if function_selector == expected_selector:
                score += 20
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 20,
                    'message': 'Correct ERC721 transferFrom function signature'
                })
                
                # Decode parameters from data
                try:
                    if len(tx_data) >= 202:  # 0x(2) + selector(8) + from(64) + to(64) + tokenId(64) = 202
                        from_hex = tx_data[10:74]  # Next 64 chars (32 bytes)
                        to_hex = tx_data[74:138]  # Next 64 chars (32 bytes)
                        token_id_hex = tx_data[138:202]  # Next 64 chars (32 bytes)
                        
                        # Extract addresses (last 40 hex chars of the 64 char field)
                        from_addr = '0x' + from_hex[-40:].lower()
                        to_addr = '0x' + to_hex[-40:].lower()
                        token_id_value = int(token_id_hex, 16)
                        
                        details['decoded_from'] = from_addr
                        details['decoded_to'] = to_addr
                        details['decoded_token_id'] = token_id_value
                        
                        # Verify recipient address
                        if to_addr == self.expected_recipient:
                            details['recipient_address_correct'] = True
                        else:
                            details['recipient_address_correct'] = False
                            details['recipient_mismatch'] = f'Expected: {self.expected_recipient}, Got: {to_addr}'
                        
                        # Verify token ID
                        if token_id_value == self.token_id:
                            details['token_id_correct'] = True
                        else:
                            details['token_id_correct'] = False
                            details['token_id_mismatch'] = f'Expected: {self.token_id}, Got: {token_id_value}'
                            
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
        
        # Check 4: NFT ownership transferred (30 points)
        # Check if the NFT owner changed from agent to recipient
        owner_before = state_before.get('nft_owner', '').lower()
        owner_after = state_after.get('nft_owner', '').lower()
        
        ownership_transferred = owner_after == self.expected_recipient
        
        if ownership_transferred:
            score += 30
            checks.append({
                'name': 'NFT Ownership Transferred',
                'passed': True,
                'points': 30,
                'message': f'NFT #{self.token_id} ownership transferred to {self.expected_recipient}'
            })
        else:
            checks.append({
                'name': 'NFT Ownership Transferred',
                'passed': False,
                'points': 0,
                'message': f'Expected owner: {self.expected_recipient}, Actual owner: {owner_after}'
            })
        
        details['owner_before'] = owner_before
        details['owner_after'] = owner_after
        details['expected_owner'] = self.expected_recipient
        details['token_id'] = self.token_id
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }

