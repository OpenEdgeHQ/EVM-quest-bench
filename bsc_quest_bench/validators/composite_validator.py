"""
Generic Composite Validator for Multi-Round Interaction Problems

This validator handles composite problems by:
1. Supporting multi-round interaction results
2. Validating error reports (if LLM detects issues)
3. Validating task completion (checking final chain state)
4. Checking parameter compliance (CRITICAL: no unauthorized modifications)
5. Modular scoring using atomic validator components
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from web3 import Web3


class CompositeValidator:
    """
    Generic validator for all composite problems
    
    Validates composite problems by:
    - Checking if LLM reported an error (and if it's valid)
    - OR checking final chain state and parameter compliance
    - Using modular scoring components from atomic validators
    """
    
    def __init__(self, agent_address: str = None, **kwargs):
        """
        Initialize composite validator
        
        Args:
            agent_address: Agent's blockchain address (optional, can be set later)
            **kwargs: Additional parameters (ignored for compatibility)
        """
        self.agent_address = Web3.to_checksum_address(agent_address) if agent_address else None
        self.composite_def = None
        self.scoring_components = []
    
    def load_composite_definition(self, composite_id: str) -> Dict[str, Any]:
        """
        Load composite problem definition from JSON
        
        Args:
            composite_id: Composite problem ID
        
        Returns:
            Composite problem definition dictionary
        """
        # Try multiple possible paths
        possible_paths = [
            Path(__file__).parent.parent / 'question_bank' / 'composite_problems' / f'{composite_id}.json',
            Path(__file__).parent.parent / 'question_bank' / 'composite_problems' / 'basic_workflows' / f'{composite_id}.json',
        ]
        
        for composite_path in possible_paths:
            if composite_path.exists():
                with open(composite_path, 'r', encoding='utf-8') as f:
                    self.composite_def = json.load(f)
                    self._extract_scoring_components()
                    return self.composite_def
        
        raise FileNotFoundError(f"Composite problem definition not found: {composite_id}")
    
    def _extract_scoring_components(self):
        """Extract scoring strategy from composite definition"""
        if not self.composite_def:
            return
        
        # scoring_strategy can be at top level OR nested in composite_structure
        # Check both locations for backward compatibility
        self.scoring_strategy = self.composite_def.get('scoring_strategy', {})
        
        # If not found at root level, check inside composite_structure
        if not self.scoring_strategy:
            composite_structure = self.composite_def.get('composite_structure', {})
            self.scoring_strategy = composite_structure.get('scoring_strategy', {})
    
    def _get_param_value(self, param_name: str, default: Any = ''):
        """
        Get parameter value from composite definition
        
        Args:
            param_name: Parameter name
            default: Default value if not found
        
        Returns:
            Parameter value (fixed or default)
        """
        if not self.composite_def:
            return default
        
        params = self.composite_def.get('parameters', {})
        param_config = params.get(param_name, {})
        generation = param_config.get('generation', {})
        
        # Check for fixed value
        if generation.get('method') == 'fixed':
            return generation.get('value', default)
        
        # Check for from_list (use first value)
        if generation.get('method') == 'from_list':
            addresses = generation.get('addresses', [])
            if addresses:
                return addresses[0]
        
        return default
    
    def validate(
        self,
        tx: Dict[str, Any] = None,
        receipt: Dict[str, Any] = None,
        state_before: Dict[str, Any] = None,
        state_after: Dict[str, Any] = None,
        # Legacy composite parameters (for future multi-turn support)
        final_submission: Dict[str, Any] = None,
        chain_state: Dict[str, Any] = None,
        task_params: Dict[str, Any] = None,
        interaction_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main validation entry point
        
        Compatible with both atomic validator interface and composite validator interface.
        
        Atomic interface (current implementation):
            - tx: Transaction object
            - receipt: Transaction receipt
            - state_before: State snapshot before transaction
            - state_after: State snapshot after transaction
        
        Composite interface (future multi-turn support):
            - final_submission: LLM's final submission (may contain error report)
            - chain_state: Final blockchain state
            - task_params: Original task parameters
            - interaction_history: Full history of all interactions
        
        Returns:
            Validation result with score and details
        """
        # Set agent_address from transaction if not already set
        if not self.agent_address and tx:
            from eth_utils import to_checksum_address
            self.agent_address = to_checksum_address(tx.get('from', ''))
        
        print(f"\n{'='*70}")
        print(f"Validating Composite Problem: {self.composite_def.get('id', 'unknown')}")
        print(f"{'='*70}\n")
        
        # Detect which interface is being used
        if final_submission is not None:
            # Multi-turn interface: use new validation logic
            print("📋 Using multi-turn validation mode")
            return self._validate_multi_turn(final_submission, chain_state, task_params, interaction_history)
        else:
            # Atomic interface: use single-turn logic (for backwards compatibility)
            print("📋 Using single-turn (atomic) validation mode")
            return self._validate_task_completion_atomic(tx, receipt, state_before, state_after)
    
    def _validate_error_report(
        self,
        error_report: Dict[str, Any],
        chain_state: Dict[str, Any],
        task_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate error report from LLM
        
        LLM gets 100 points if:
        - The reported error type is correct
        - The environment really has that error
        
        Args:
            error_report: LLM's error report
            chain_state: Current blockchain state
            task_params: Task parameters
        
        Returns:
            Validation result
        """
        print("📋 LLM Reported an Error")
        print(f"{'-'*70}")
        
        error_type = error_report.get('error_type', 'UNKNOWN')
        error_message = error_report.get('error_message', '')
        
        print(f"Error Type: {error_type}")
        print(f"Error Message: {error_message}")
        print()
        
        # Verify if the error is valid
        is_valid_error = self._check_error_validity(error_type, chain_state, task_params)
        
        if is_valid_error:
            print("✅ Error Report is VALID")
            print(f"   The environment indeed has this error.")
            score = 100.0
            passed = True
            status = "error_correctly_reported"
        else:
            print("❌ Error Report is INVALID")
            print(f"   The environment does NOT have this error (false alarm).")
            score = 0.0
            passed = False
            status = "error_falsely_reported"
        
        print(f"\n{'='*70}")
        print(f"Final Score: {score:.2f}/100")
        print(f"Status: {status}")
        print(f"{'='*70}\n")
        
        return {
            'score': score,
            'max_score': 100.0,
            'passed': passed,
            'status': status,
            'validation_mode': 'error_report',
            'error_type': error_type,
            'error_message': error_message,
            'is_valid_error': is_valid_error,
            'details': {
                'reported_error': error_report,
                'chain_state': chain_state
            }
        }
    
    def _check_error_validity(
        self,
        error_type: str,
        chain_state: Dict[str, Any],
        task_params: Dict[str, Any]
    ) -> bool:
        """
        Check if the reported error actually exists in the environment
        
        Args:
            error_type: Type of error reported
            chain_state: Current blockchain state
            task_params: Task parameters
        
        Returns:
            True if error is valid, False otherwise
        """
        # Get required amount and actual balance
        required_amount = task_params.get('amount', 0)
        actual_balance = chain_state.get('initial_state', {}).get('token_balance', 0)
        
        if error_type == 'TOKEN_INSUFFICIENT_BALANCE':
            # Check if balance is really insufficient
            return actual_balance < required_amount
        
        elif error_type == 'BNB_INSUFFICIENT_BALANCE':
            bnb_balance = chain_state.get('initial_state', {}).get('bnb_balance', 0)
            required_bnb = task_params.get('amount', 0)
            return bnb_balance < required_bnb
        
        elif error_type in ['ALLOWANCE_INSUFFICIENT', 'NO_APPROVAL']:
            allowance = chain_state.get('initial_state', {}).get('allowance', 0)
            required_allowance = task_params.get('amount', 0)
            return allowance < required_allowance
        
        # Add more error type checks as needed
        
        # Unknown error type or not applicable
        return False
    
    def _validate_multi_turn(
        self,
        final_submission: Dict[str, Any],
        chain_state: Dict[str, Any],
        task_params: Dict[str, Any],
        interaction_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate multi-turn interaction result
        
        Two possible outcomes:
        1. LLM detected and reported an error (error_detected: true)
        2. LLM completed the task successfully
        
        Args:
            final_submission: LLM's final submission
            chain_state: Final blockchain state
            task_params: Original task parameters
            interaction_history: Full interaction history
        
        Returns:
            Validation result with score
        """
        print("🎯 Validating Multi-Turn Composite Task")
        print(f"{'-'*70}\n")
        
        # Check if LLM reported an error
        if final_submission.get('error_detected'):
            return self._validate_error_report(final_submission, chain_state, task_params)
        else:
            # LLM claims task is complete - validate from interaction history
            return self._validate_task_completion(chain_state, task_params, interaction_history)
    
    def _validate_task_completion_atomic(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate task completion using atomic validator interface
        
        This is a simplified version for current single-transaction composite problems.
        It directly calls the key operation's atomic validator.
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
        
        Returns:
            Validation result
        """
        print("🎯 Validating Composite Task (Atomic Interface)")
        print(f"{'-'*70}")
        
        # Get scoring strategy
        method = self.scoring_strategy.get('method', 'atomic_validator_reuse')
        key_op_id = self.scoring_strategy.get('key_operation_id')
        
        print(f"Key Operation: {key_op_id}")
        print(f"Strategy: {method}")
        print()
        
        # Load and call atomic validator
        atomic_validator = self._load_atomic_validator(key_op_id, tx)
        if not atomic_validator:
            print(f"❌ Failed to load atomic validator for '{key_op_id}'")
            return {
                'score': 0.0,
                'max_score': 100.0,
                'passed': False,
                'status': 'validator_load_failed',
                'details': {'error': f'Validator not found: {key_op_id}'}
            }
        
        print(f"✅ Loaded atomic validator: {atomic_validator.__class__.__name__}")
        print()
        
        # Call atomic validator directly
        try:
            # The atomic validator expects: validate(tx, receipt, state_before, state_after)
            atomic_result = atomic_validator.validate(
                tx=tx,
                receipt=receipt,
                state_before=state_before,
                state_after=state_after
            )
            
            score = atomic_result.get('score', 0.0)
            max_score = atomic_result.get('max_score', 100.0)
            passed = atomic_result.get('passed', False)
            
            print(f"📈 Atomic Validator Score: {score:.2f}/{max_score:.2f}")
            if 'checks' in atomic_result:
                print("\n   Check Breakdown:")
                checks = atomic_result.get('checks', {})
                # Checks can be either a dict or a list
                if isinstance(checks, dict):
                    for check_name, check_result in checks.items():
                        status = '✅' if check_result.get('passed', False) else '❌'
                        check_score = check_result.get('score', 0)
                        print(f"   {status} {check_name}: {check_score:.2f}")
                elif isinstance(checks, list):
                    for idx, check_result in enumerate(checks):
                        check_name = check_result.get('name', f'Check {idx+1}')
                        status = '✅' if check_result.get('passed', False) else '❌'
                        check_score = check_result.get('score', 0)
                        print(f"   {status} {check_name}: {check_score:.2f}")
            
            print(f"\n{'='*70}")
            print(f"Final Score: {score:.2f}/{max_score:.2f}")
            print(f"Status: {'✅ PASSED' if passed else '❌ FAILED'}")
            print(f"{'='*70}\n")
            
            return {
                'score': score,
                'max_score': max_score,
                'passed': passed,
                'status': 'completed',
                'validation_mode': 'atomic_interface',
                'checks': atomic_result.get('checks', {}),
                'details': {
                    'atomic_validator': atomic_validator.__class__.__name__,
                    'atomic_result': atomic_result
                }
            }
            
        except Exception as e:
            print(f"❌ Error calling atomic validator: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'score': 0.0,
                'max_score': 100.0,
                'passed': False,
                'status': 'validation_error',
                'details': {'error': str(e)}
            }
    
    def _validate_task_completion(
        self,
        chain_state: Dict[str, Any],
        task_params: Dict[str, Any],
        interaction_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate task completion
        
        Validation logic:
        1. Check if this is a pure query problem
        2. For transaction problems: Check if a transaction was executed (chain state changed)
        3. Base score = 100 if task completed, 0 otherwise
        4. Step decay is applied by controller (optimal_steps / actual_steps)
        
        Args:
            chain_state: Final blockchain state
            task_params: Original task parameters  
            interaction_history: All interactions
        
        Returns:
            Validation result
        """
        print("🎯 LLM Submitted Task Completion")
        print(f"{'-'*70}\n")
        
        # Step 1: Check if this is a pure query problem
        if self._is_pure_query_problem():
            return self._validate_pure_query_completion(task_params, interaction_history)
        
        # Step 2: Get atomic operations info
        composite_structure = self.composite_def.get('composite_structure', {})
        atomic_operations = composite_structure.get('atomic_operations', [])
        key_op_id = self.scoring_strategy.get('key_operation_id')
        
        print(f"📋 Atomic Operations: {len(atomic_operations)}")
        print(f"🔑 Key Operation: {key_op_id or 'Not specified'}")
        print()
        
        # Step 3: Check if final transaction was executed
        # This validates that the chain state was modified (task completed)
        final_tx_hash = None
        
        if interaction_history:
            # Find the last transaction that was executed
            for rd in reversed(interaction_history):
                ar = rd.get('action_result', {})
                if ar.get('tx_hash'):
                    final_tx_hash = ar['tx_hash']
                    break
        
        # Step 4: Determine pass/fail based on transaction execution
        if final_tx_hash:
            print(f"✅ Transaction executed: {final_tx_hash[:20]}...")
            print(f"   Chain state modified - task completed")
            base_score = 100.0
            passed = True
            status = 'completed'
            message = 'Transaction executed successfully'
        else:
            print(f"❌ No transaction executed")
            print(f"   Chain state unchanged - task not completed")
            base_score = 0.0
            passed = False
            status = 'failed'
            message = 'No transaction was executed'
        
        print(f"\n{'='*70}")
        print(f"Base Score: {base_score:.2f}/100")
        print(f"Status: {'✅ PASSED' if passed else '❌ FAILED'}")
        print(f"{'='*70}\n")
        
        return {
            'score': base_score,
            'max_score': 100.0,
            'passed': passed,
            'status': status,
            'validation_mode': 'transaction_execution',
            'details': {
                'tx_hash': final_tx_hash,
                'message': message
            }
        }
    
    def _is_pure_query_problem(self) -> bool:
        """
        Check if this composite problem consists only of query operations
        
        Returns:
            True if all atomic operations are queries, False otherwise
        """
        if not self.composite_def:
            print("[DEBUG] _is_pure_query_problem: composite_def not loaded")
            return False
        
        composite_structure = self.composite_def.get('composite_structure', {})
        atomic_operations = composite_structure.get('atomic_operations', [])
        
        if not atomic_operations:
            print("[DEBUG] _is_pure_query_problem: no atomic_operations found")
            return False
        
        # Check if all operations are query operations
        for op in atomic_operations:
            atomic_id = op.get('atomic_id', '')
            # Query operations typically start with 'query_'
            if not atomic_id.startswith('query_'):
                print(f"[DEBUG] _is_pure_query_problem: found non-query operation: {atomic_id}")
                return False
        
        print(f"[DEBUG] _is_pure_query_problem: All {len(atomic_operations)} operations are queries")
        return True
    
    def _validate_pure_query_completion(
        self,
        task_params: Dict[str, Any],
        interaction_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate completion of a pure query problem
        
        For pure query problems, we validate that:
        1. LLM successfully executed all required queries
        2. LLM returned the query results
        
        Note: LLM may batch multiple queries into a single execution.
        We check the returned data to count how many queries were completed.
        
        Args:
            task_params: Original task parameters
            interaction_history: All interactions
        
        Returns:
            Validation result
        """
        print("📊 Validating Pure Query Problem")
        print(f"{'-'*70}\n")
        
        # Get expected number of queries from composite definition
        composite_structure = self.composite_def.get('composite_structure', {})
        atomic_operations = composite_structure.get('atomic_operations', [])
        expected_queries = len(atomic_operations)
        
        # Count successful query operations
        successful_queries = 0
        total_queries = 0
        query_results = []
        batched_query_count = 0
        
        if interaction_history:
            for round_data in interaction_history:
                round_num = round_data.get('round', '?')
                action_result = round_data.get('action_result', {})
                parsed_response = round_data.get('parsed_response', {})
                action = parsed_response.get('action', '')
                
                # Check if this was a query action or successful execution
                if action_result and isinstance(action_result, dict):
                    is_query = action_result.get('is_query', False)
                    is_success = action_result.get('success', False)
                    
                    if is_query or is_success:
                        total_queries += 1
                        
                        if is_success:
                            successful_queries += 1
                            print(f"✅ Round {round_num}: Query succeeded")
                            query_results.append(action_result)
                            
                            # Check if this is a batched query result with multiple balances
                            # Look for 'balances' dict, 'query_result', or 'data.portfolio'
                            balances = action_result.get('balances', {})
                            
                            # Check query_result field
                            if not balances:
                                query_result = action_result.get('query_result', {})
                                if isinstance(query_result, dict):
                                    balances = query_result.get('balances', {})
                                    if not balances:
                                        data = query_result.get('data', {})
                                        if isinstance(data, dict):
                                            balances = data.get('portfolio', data.get('balances', {}))
                            
                            # Check data.portfolio or data.balances
                            if not balances:
                                data = action_result.get('data', {})
                                if isinstance(data, dict):
                                    balances = data.get('portfolio', data.get('balances', {}))
                            
                            if balances and isinstance(balances, dict):
                                batched_count = len(balances)
                                if batched_count > 1:
                                    batched_query_count = batched_count
                                    print(f"   📦 Batched query detected: {batched_count} balances returned")
                                    for asset, info in balances.items():
                                        if isinstance(info, dict):
                                            balance = info.get('formatted', info.get('balanceHuman', '?'))
                                            print(f"      - {asset}: {balance}")
                        else:
                            print(f"❌ Round {round_num}: Query failed")
        
        print()
        
        # If batched queries detected, use that count instead
        if batched_query_count >= expected_queries:
            successful_queries = batched_query_count
            total_queries = batched_query_count
            print(f"📦 Batch query mode: {batched_query_count} queries completed in 1 round")
        
        print(f"📈 Query Statistics:")
        print(f"   Expected queries: {expected_queries}")
        print(f"   Executed queries: {total_queries}")
        print(f"   Successful queries: {successful_queries}")
        print()
        
        # Score based on successful queries
        if expected_queries > 0:
            # Give full score if LLM completed the required queries
            # Note: LLM might batch them into fewer rounds
            if successful_queries >= expected_queries:
                score = 100.0
                passed = True
                status = 'all_queries_completed'
                message = f'All {expected_queries} queries completed successfully'
            elif successful_queries > 0:
                # Partial credit based on completed queries
                score = (successful_queries / expected_queries) * 100.0
                passed = successful_queries >= expected_queries * 0.5  # Pass if >= 50% queries done
                status = 'partial_queries_completed'
                message = f'{successful_queries}/{expected_queries} queries completed'
            else:
                score = 0.0
                passed = False
                status = 'no_queries_completed'
                message = 'No queries were successfully completed'
        else:
            # No expected queries defined, just check if any were successful
            if successful_queries > 0:
                score = 100.0
                passed = True
                status = 'queries_completed'
                message = f'{successful_queries} queries completed successfully'
            else:
                score = 0.0
                passed = False
                status = 'no_queries_completed'
                message = 'No queries were completed'
        
        print(f"{'='*70}")
        print(f"Final Score: {score:.2f}/100")
        print(f"Status: {'✅ PASSED' if passed else '❌ FAILED'}")
        print(f"{'='*70}\n")
        
        return {
            'score': score,
            'max_score': 100.0,
            'passed': passed,
            'status': status,
            'validation_mode': 'pure_query',
            'details': {
                'expected_queries': expected_queries,
                'total_queries': total_queries,
                'successful_queries': successful_queries,
                'query_results': query_results,
                'message': message
            }
        }
    
    def _check_parameter_compliance(
        self,
        chain_state: Dict[str, Any],
        task_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if LLM strictly followed the required parameters
        
        This is CRITICAL: any parameter modification results in 0 score
        
        Args:
            chain_state: Final blockchain state
            task_params: Original task parameters
        
        Returns:
            Compliance check result
        """
        print("🔍 Checking Parameter Compliance...")
        print(f"{'-'*70}")
        
        # Find the transfer transaction
        transfer_txs = [
            tx for tx in chain_state.get('transactions', [])
            if tx.get('function_name') == 'transfer'
        ]
        
        if not transfer_txs:
            return {
                'compliant': False,
                'violation_reason': 'No transfer transaction found',
                'details': {'expected': 'transfer transaction', 'actual': 'none'}
            }
        
        # Get the last transfer transaction (in case of multiple attempts)
        transfer_tx = transfer_txs[-1]
        
        # Check transfer amount
        required_amount = task_params.get('amount')
        actual_amount = transfer_tx.get('decoded_input', {}).get('amount')
        
        # Convert to same units for comparison (handle decimals)
        token_decimals = task_params.get('token_decimals', 18)
        required_amount_wei = int(required_amount * (10 ** token_decimals))
        
        print(f"Required Amount: {required_amount} tokens ({required_amount_wei} wei)")
        print(f"Actual Amount:   {actual_amount} wei")
        
        if actual_amount != required_amount_wei:
            return {
                'compliant': False,
                'violation_reason': f'Transfer amount mismatch: required {required_amount}, got {actual_amount / (10**token_decimals)}',
                'details': {
                    'parameter': 'amount',
                    'required': required_amount_wei,
                    'actual': actual_amount
                }
            }
        
        # Check recipient address
        required_address = Web3.to_checksum_address(task_params.get('to_address'))
        actual_address = Web3.to_checksum_address(transfer_tx.get('decoded_input', {}).get('to', ''))
        
        print(f"Required Address: {required_address}")
        print(f"Actual Address:   {actual_address}")
        
        if actual_address != required_address:
            return {
                'compliant': False,
                'violation_reason': f'Recipient address mismatch',
                'details': {
                    'parameter': 'to_address',
                    'required': required_address,
                    'actual': actual_address
                }
            }
        
        return {
            'compliant': True,
            'details': {
                'amount_check': 'passed',
                'address_check': 'passed'
            }
        }
    
    def _score_key_operation(
        self,
        chain_state: Dict[str, Any],
        task_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Score based on key operation by DIRECTLY REUSING atomic validator
        
        This method loads the atomic validator for the key operation and calls it directly,
        eliminating code duplication and ensuring consistency.
        
        Args:
            chain_state: Final blockchain state
            task_params: Task parameters
        
        Returns:
            Scoring result with breakdown
        """
        print("\n📊 Scoring Key Operation...")
        print(f"{'-'*70}")
        
        # Get scoring strategy
        method = self.scoring_strategy.get('method', 'atomic_validator_reuse')
        
        if method != 'atomic_validator_reuse':
            print(f"⚠️  Warning: Unsupported scoring method '{method}', using atomic_validator_reuse")
        
        # Get key operation info
        key_op_id = self.scoring_strategy.get('key_operation_id')
        key_op_step = self.scoring_strategy.get('key_operation_step', 2)
        
        print(f"Key Operation: {key_op_id} (Step {key_op_step})")
        print(f"Strategy: Directly reuse atomic validator (zero code duplication)")
        print()
        
        # Load atomic validator
        atomic_validator = self._load_atomic_validator(key_op_id)
        if not atomic_validator:
            print(f"❌ Failed to load atomic validator for '{key_op_id}'")
            return {
                'score': 0.0,
                'breakdown': [],
                'details': {'error': f'Validator not found: {key_op_id}'}
            }
        
        print(f"✅ Loaded atomic validator: {atomic_validator.__class__.__name__}")
        print()
        
        # Call atomic validator directly
        try:
            # The atomic validator expects: validate(transaction, initial_state, final_state)
            # We need to extract these from chain_state
            atomic_result = atomic_validator.validate(
                chain_state.get('key_operation_transaction', {}),
                chain_state.get('initial_state', {}),
                chain_state.get('final_state', {})
            )
            
            score = atomic_result.get('score', 0.0)
            details = atomic_result.get('details', {})
            
            print(f"📈 Atomic Validator Score: {score:.2f}/100")
            if 'checks' in atomic_result:
                print("\n   Check Breakdown:")
                for check_name, check_result in atomic_result.get('checks', {}).items():
                    status = '✅' if check_result.get('passed', False) else '❌'
                    print(f"   {status} {check_name}: {check_result.get('score', 0):.2f}")
            
            return {
                'score': score,
                'breakdown': atomic_result.get('checks', {}),
                'details': {
                    'atomic_validator': atomic_validator.__class__.__name__,
                    'atomic_result': atomic_result
                }
            }
        
        except Exception as e:
            print(f"❌ Error calling atomic validator: {e}")
            import traceback
            traceback.print_exc()
            return {
                'score': 0.0,
                'breakdown': [],
                'details': {'error': str(e)}
            }
    
    def _load_atomic_validator(self, atomic_id: str, tx: Dict[str, Any] = None):
        """
        Load atomic validator by atomic problem ID
        
        Args:
            atomic_id: Atomic problem ID (e.g., 'erc20_transfer_fixed')
            tx: Transaction object (for extracting parameters)
        
        Returns:
            Atomic validator instance, or None if not found
        """
        # Map atomic_id to validator class name
        # Format: atomic_id_to_class_name (e.g., erc20_transfer_fixed -> ERC20TransferValidator)
        validator_map = {
            'erc20_transfer_fixed': 'ERC20TransferValidator',
            'erc20_transfer_percentage': 'ERC20TransferPercentageValidator',
            'erc20_transfer_max_amount': 'ERC20TransferMaxAmountValidator',
            'bnb_transfer_basic': 'BNBTransferValidator',
            'bnb_transfer_percentage': 'BNBTransferPercentageValidator',
            'bnb_transfer_max_amount': 'BNBTransferMaxAmountValidator',
            'erc20_approve': 'ERC20ApproveValidator',
            'erc20_transferfrom_basic': 'ERC20TransferFromBasicValidator',
            'erc721_transfer': 'ERC721TransferValidator',
            'swap_exact_tokens_for_tokens': 'SwapExactTokensForTokensValidator',
            'swap_exact_bnb_for_tokens': 'SwapExactBNBForTokensValidator',
            'swap_exact_tokens_for_bnb': 'SwapExactTokensForBNBValidator',
            'add_liquidity_bnb_token': 'AddLiquidityBNBTokenValidator',
            'add_liquidity_tokens': 'AddLiquidityTokensValidator',
            'stake_single_token': 'StakeSingleTokenValidator',
            'stake_lp_tokens': 'StakeLPTokensValidator',
            'unstake_lp_tokens': 'UnstakeLPTokensValidator',
            'harvest_rewards': 'HarvestRewardsValidator',
            'wbnb_deposit': 'WBNBDepositValidator',
            'wbnb_withdraw': 'WBNBWithdrawValidator',
            'remove_liquidity_tokens': 'RemoveLiquidityTokensValidator',
            'remove_liquidity_bnb_token': 'RemoveLiquidityBNBTokenValidator',
            'swap_exact_tokens_for_bnb': 'SwapExactTokensForBNBValidator',
            # Add more mappings as needed
        }
        
        validator_class_name = validator_map.get(atomic_id)
        if not validator_class_name:
            print(f"⚠️  Warning: No validator mapping for '{atomic_id}'")
            return None
        
        try:
            # Import from validators module
            from bsc_quest_bench import validators
            validator_class = getattr(validators, validator_class_name, None)
            
            if validator_class is None:
                print(f"⚠️  Warning: Validator class '{validator_class_name}' not found")
                return None
            
            # Instantiate validator with appropriate parameters
            # Different validators have different constructor signatures
            # For ERC20 transfers, we need to extract token_address, to_address and amount from tx
            if atomic_id == 'erc20_transfer_fixed':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Token address is the target of the transaction
                token_address = tx.get('to', '')
                
                # Decode transfer parameters from transaction data
                # transfer(address to, uint256 amount) - selector: 0xa9059cbb
                tx_data = tx.get('data', '')
                if len(tx_data) < 138:  # 0x (2) + selector (8) + to (64) + amount (64)
                    print(f"❌ Invalid transaction data length")
                    return None
                
                # Extract to_address (bytes 4-36 after selector)
                to_address_hex = '0x' + tx_data[34:74]  # Remove leading zeros
                from eth_utils import to_checksum_address
                to_address = to_checksum_address(to_address_hex)
                
                # Extract amount (bytes 36-68 after selector)
                amount_hex = tx_data[74:138]
                amount_wei = int(amount_hex, 16)
                amount_ether = amount_wei / (10**18)
                
                print(f"   Decoded parameters:")
                print(f"   - token_address: {token_address}")
                print(f"   - to_address: {to_address}")
                print(f"   - amount: {amount_ether} tokens ({amount_wei} wei)")
                
                return validator_class(
                    token_address=token_address,
                    to_address=to_address,
                    amount=amount_ether,
                    token_decimals=18  # Default to 18, can be made configurable later
                )
            
            elif atomic_id == 'erc20_transfer_percentage':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Token address is the target of the transaction
                token_address = tx.get('to', '')
                
                # Decode transfer parameters from transaction data
                # transfer(address to, uint256 amount) - selector: 0xa9059cbb
                tx_data = tx.get('data', '')
                if len(tx_data) < 138:  # 0x (2) + selector (8) + to (64) + amount (64)
                    print(f"❌ Invalid transaction data length")
                    return None
                
                # Extract to_address (bytes 4-36 after selector)
                to_address_hex = '0x' + tx_data[34:74]  # Remove leading zeros
                from eth_utils import to_checksum_address
                to_address = to_checksum_address(to_address_hex)
                
                # Get percentage from task_params or default to 100%
                percentage = self._get_param_value('percentage') or 100
                
                print(f"   Decoded percentage transfer parameters:")
                print(f"   - token_address: {token_address}")
                print(f"   - to_address: {to_address}")
                print(f"   - percentage: {percentage}%")
                
                return validator_class(
                    token_address=token_address,
                    to_address=to_address,
                    percentage=int(percentage),
                    token_decimals=18
                )
            
            elif atomic_id == 'erc20_transfer_max_amount':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Token address is the target of the transaction
                token_address = tx.get('to', '')
                
                # Decode transfer parameters from transaction data
                # transfer(address to, uint256 amount) - selector: 0xa9059cbb
                tx_data = tx.get('data', '')
                if len(tx_data) < 138:  # 0x (2) + selector (8) + to (64) + amount (64)
                    print(f"❌ Invalid transaction data length")
                    return None
                
                # Extract to_address (bytes 4-36 after selector)
                to_address_hex = '0x' + tx_data[34:74]  # Remove leading zeros
                from eth_utils import to_checksum_address
                to_address = to_checksum_address(to_address_hex)
                
                # Extract amount (bytes 36-68 after selector)
                amount_hex = tx_data[74:138]
                amount_wei = int(amount_hex, 16)
                amount_ether = amount_wei / (10**18)
                
                print(f"   Decoded max amount transfer parameters:")
                print(f"   - token_address: {token_address}")
                print(f"   - to_address: {to_address}")
                print(f"   - amount: {amount_ether} tokens ({amount_wei} wei)")
                
                return validator_class(
                    token_address=token_address,
                    to_address=to_address,
                    amount=amount_ether,
                    token_decimals=18
                )
            
            elif atomic_id == 'bnb_transfer_basic':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Extract to_address and amount from transaction
                to_address = tx.get('to', '')
                
                # Value is in Wei
                value_wei = tx.get('value', 0)
                if isinstance(value_wei, str):
                    value_wei = int(value_wei, 16) if value_wei.startswith('0x') else int(value_wei)
                amount_bnb = value_wei / (10**18)
                
                print(f"   Decoded BNB transfer parameters:")
                print(f"   - to_address: {to_address}")
                print(f"   - amount: {amount_bnb} BNB ({value_wei} wei)")
                
                return validator_class(
                    to_address=to_address,
                    amount=amount_bnb
                )
            
            elif atomic_id == 'erc20_approve':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Token address is the target of the transaction
                token_address = tx.get('to', '')
                
                # Decode approve parameters from transaction data
                # approve(address spender, uint256 amount) - selector: 0x095ea7b3
                tx_data = tx.get('data', '')
                if len(tx_data) < 138:  # 0x (2) + selector (8) + spender (64) + amount (64)
                    print(f"❌ Invalid transaction data length")
                    return None
                
                # Extract spender_address (bytes 4-36 after selector)
                spender_address_hex = '0x' + tx_data[34:74]  # Remove leading zeros
                from eth_utils import to_checksum_address
                spender_address = to_checksum_address(spender_address_hex)
                
                # Extract amount (bytes 36-68 after selector)
                amount_hex = tx_data[74:138]
                amount_wei = int(amount_hex, 16)
                amount_ether = amount_wei / (10**18)
                
                print(f"   Decoded approve parameters:")
                print(f"   - token_address: {token_address}")
                print(f"   - spender_address: {spender_address}")
                print(f"   - amount: {amount_ether} tokens ({amount_wei} wei)")
                
                return validator_class(
                    token_address=token_address,
                    spender_address=spender_address,
                    amount=amount_ether,
                    agent_address=self.agent_address
                )
            
            elif atomic_id == 'erc20_transferfrom_basic':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Token address is the target of the transaction
                token_address = tx.get('to', '')
                
                # Decode transferFrom parameters from transaction data
                # transferFrom(address from, address to, uint256 amount) - selector: 0x23b872dd
                tx_data = tx.get('data', '')
                if len(tx_data) < 202:  # 0x (2) + selector (8) + from (64) + to (64) + amount (64)
                    print(f"❌ Invalid transaction data length for ERC20 transferFrom")
                    return None
                
                # Extract from_address (bytes 4-36 after selector)
                from_address_hex = '0x' + tx_data[34:74]
                from eth_utils import to_checksum_address
                from_address = to_checksum_address(from_address_hex)
                
                # Extract to_address (bytes 36-68 after selector)
                to_address_hex = '0x' + tx_data[98:138]
                to_address = to_checksum_address(to_address_hex)
                
                # Extract amount (bytes 68-100 after selector)
                amount_hex = tx_data[138:202]
                amount_wei = int(amount_hex, 16)
                amount_tokens = amount_wei / (10**18)
                
                print(f"   Decoded ERC20 transferFrom parameters:")
                print(f"   - token_address: {token_address}")
                print(f"   - from_address: {from_address}")
                print(f"   - to_address: {to_address}")
                print(f"   - amount: {amount_tokens} tokens ({amount_wei} wei)")
                print(f"   - agent_address (spender): {self.agent_address}")
                
                return validator_class(
                    token_address=token_address,
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount_tokens,
                    agent_address=self.agent_address,
                    token_decimals=18
                )
            
            elif atomic_id == 'erc721_transfer':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # NFT contract address is the target of the transaction
                nft_address = tx.get('to', '')
                
                # Decode transferFrom parameters from transaction data
                # transferFrom(address from, address to, uint256 tokenId) - selector: 0x23b872dd
                tx_data = tx.get('data', '')
                if len(tx_data) < 202:  # 0x (2) + selector (8) + from (64) + to (64) + tokenId (64)
                    print(f"❌ Invalid transaction data length for transferFrom")
                    return None
                
                # Extract from_address (bytes 4-36 after selector) - not needed, but for logging
                from_address_hex = '0x' + tx_data[34:74]
                from eth_utils import to_checksum_address
                from_address = to_checksum_address(from_address_hex)
                
                # Extract to_address (bytes 36-68 after selector)
                to_address_hex = '0x' + tx_data[98:138]
                to_address = to_checksum_address(to_address_hex)
                
                # Extract tokenId (bytes 68-100 after selector)
                token_id_hex = tx_data[138:202]
                token_id = int(token_id_hex, 16)
                
                print(f"   Decoded NFT transfer parameters:")
                print(f"   - nft_address: {nft_address}")
                print(f"   - from_address: {from_address}")
                print(f"   - to_address: {to_address}")
                print(f"   - token_id: {token_id}")
                
                return validator_class(
                    nft_address=nft_address,
                    to_address=to_address,
                    token_id=token_id
                )
            
            elif atomic_id == 'stake_single_token':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Pool address is the target of the transaction
                pool_address = tx.get('to', '')
                
                # Decode deposit parameters from transaction data
                # deposit(uint256 _amount) - selector: 0xb6b55f25
                tx_data = tx.get('data', '')
                if len(tx_data) < 74:  # 0x (2) + selector (8) + amount (64)
                    print(f"❌ Invalid transaction data length for deposit")
                    return None
                
                # Extract amount (bytes 4-36 after selector)
                amount_hex = tx_data[10:74]  # Skip '0x' and 8 char selector
                amount_wei = int(amount_hex, 16)
                amount_tokens = amount_wei / (10**18)
                
                # Get token_address from composite definition
                # Try multiple parameter names for compatibility
                token_address = self._get_param_value('token_address')
                if not token_address:
                    # Fallback to cake_address for CAKE staking scenarios
                    token_address = self._get_param_value('cake_address')
                if not token_address:
                    # Fallback to staking_token_address
                    token_address = self._get_param_value('staking_token_address')
                
                print(f"   Decoded staking parameters:")
                print(f"   - pool_address: {pool_address}")
                print(f"   - token_address: {token_address}")
                print(f"   - stake_amount: {amount_tokens} tokens ({amount_wei} wei)")
                print(f"   - user_address: {self.agent_address}")
                
                return validator_class(
                    stake_amount=amount_tokens,
                    token_address=token_address,
                    pool_address=pool_address,
                    user_address=self.agent_address
                )
            
            elif atomic_id == 'stake_lp_tokens':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Pool address is the target of the transaction
                pool_address = tx.get('to', '')
                
                # Decode deposit parameters from transaction data
                # deposit(uint256 _amount) - selector: 0xb6b55f25
                tx_data = tx.get('data', '')
                if len(tx_data) < 74:  # 0x (2) + selector (8) + amount (64)
                    print(f"❌ Invalid transaction data length for LP staking deposit")
                    return None
                
                # Extract amount (bytes 4-36 after selector)
                amount_hex = tx_data[10:74]  # Skip '0x' and 8 char selector
                amount_wei = int(amount_hex, 16)
                amount_tokens = amount_wei / (10**18)
                
                # Get lp_token_address from composite definition
                lp_token_address = self._get_param_value('lp_token_address')
                
                print(f"   Decoded LP staking parameters:")
                print(f"   - pool_address: {pool_address}")
                print(f"   - lp_token_address: {lp_token_address}")
                print(f"   - stake_amount: {amount_tokens} LP tokens ({amount_wei} wei)")
                print(f"   - user_address: {self.agent_address}")
                
                return validator_class(
                    stake_amount=amount_tokens,
                    lp_token_address=lp_token_address,
                    pool_address=pool_address,
                    user_address=self.agent_address
                )
            
            elif atomic_id == 'swap_exact_bnb_for_tokens':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Router address is the target of the transaction
                router_address = tx.get('to', '')
                
                # Get BNB amount from transaction value
                value_wei = tx.get('value', 0)
                if isinstance(value_wei, str):
                    value_wei = int(value_wei, 16) if value_wei.startswith('0x') else int(value_wei)
                amount_in_bnb = value_wei / (10**18)
                
                # Get token_address and slippage from composite definition
                token_address = self._get_param_value('token_address')
                slippage = self._get_param_value('slippage', 5.0)
                
                print(f"   Decoded swap parameters:")
                print(f"   - router_address: {router_address}")
                print(f"   - token_address: {token_address}")
                print(f"   - amount_in: {amount_in_bnb} BNB ({value_wei} wei)")
                print(f"   - slippage: {slippage}%")
                
                return validator_class(
                    router_address=router_address,
                    token_address=token_address,
                    amount_in=amount_in_bnb,
                    token_decimals=18,
                    slippage=slippage
                )
            
            elif atomic_id == 'wbnb_deposit':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # WBNB address is the target of the transaction
                wbnb_address = tx.get('to', '')
                
                # Get BNB amount from transaction value
                value_wei = tx.get('value', 0)
                if isinstance(value_wei, str):
                    value_wei = int(value_wei, 16) if value_wei.startswith('0x') else int(value_wei)
                amount_bnb = value_wei / (10**18)
                
                print(f"   Decoded WBNB deposit parameters:")
                print(f"   - wbnb_address: {wbnb_address}")
                print(f"   - amount: {amount_bnb} BNB ({value_wei} wei)")
                
                return validator_class(
                    wbnb_address=wbnb_address,
                    amount=amount_bnb
                )
            
            elif atomic_id == 'wbnb_withdraw':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # WBNB address is the target of the transaction
                wbnb_address = tx.get('to', '')
                
                # Decode withdraw parameters from transaction data
                # withdraw(uint256 wad) - selector: 0x2e1a7d4d
                tx_data = tx.get('data', '')
                if len(tx_data) < 74:  # 0x (2) + selector (8) + amount (64)
                    print(f"❌ Invalid transaction data length for WBNB withdraw")
                    return None
                
                # Extract amount (bytes 4-36 after selector)
                amount_hex = tx_data[10:74]  # Skip '0x' and 8 char selector
                amount_wei = int(amount_hex, 16)
                amount_wbnb = amount_wei / (10**18)
                
                print(f"   Decoded WBNB withdraw parameters:")
                print(f"   - wbnb_address: {wbnb_address}")
                print(f"   - amount: {amount_wbnb} WBNB ({amount_wei} wei)")
                
                return validator_class(
                    wbnb_address=wbnb_address,
                    amount=amount_wbnb
                )
            
            elif atomic_id == 'harvest_rewards':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Pool address is the target of the transaction
                pool_address = tx.get('to', '')
                
                # Get reward_token_address from composite definition
                reward_token_address = self._get_param_value('reward_token_address')
                
                print(f"   Decoded harvest parameters:")
                print(f"   - pool_address: {pool_address}")
                print(f"   - reward_token_address: {reward_token_address}")
                print(f"   - user_address: {self.agent_address}")
                
                return validator_class(
                    reward_token_address=reward_token_address,
                    pool_address=pool_address,
                    user_address=self.agent_address
                )
            
            elif atomic_id == 'swap_exact_tokens_for_tokens':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Router address is the target of the transaction
                router_address = tx.get('to', '')
                
                # Decode swapExactTokensForTokens parameters from transaction data
                # swapExactTokensForTokens(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline)
                # selector: 0x38ed1739
                tx_data = tx.get('data', '')
                if len(tx_data) < 74:  # At least selector + amountIn
                    print(f"❌ Invalid transaction data length for swap")
                    return None
                
                # Extract amountIn (bytes 4-36 after selector)
                amount_in_hex = tx_data[10:74]  # Skip '0x' and 8 char selector
                amount_in_wei = int(amount_in_hex, 16)
                
                # Get token addresses and other params from composite definition
                token_in_address = self._get_param_value('token_in_address')
                token_out_address = self._get_param_value('token_out_address')
                token_in_decimals = self._get_param_value('token_in_decimals', 18)
                token_out_decimals = self._get_param_value('token_out_decimals', 18)
                slippage = self._get_param_value('slippage', 5.0)
                
                amount_in_tokens = amount_in_wei / (10**token_in_decimals)
                
                print(f"   Decoded swap parameters:")
                print(f"   - router_address: {router_address}")
                print(f"   - token_in_address: {token_in_address}")
                print(f"   - token_out_address: {token_out_address}")
                print(f"   - amount_in: {amount_in_tokens} tokens ({amount_in_wei} wei)")
                print(f"   - slippage: {slippage}%")
                
                return validator_class(
                    router_address=router_address,
                    token_in_address=token_in_address,
                    token_out_address=token_out_address,
                    amount_in=amount_in_tokens,
                    token_in_decimals=token_in_decimals,
                    token_out_decimals=token_out_decimals,
                    slippage=slippage
                )
            
            elif atomic_id == 'add_liquidity_tokens':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Router address is the target of the transaction
                router_address = tx.get('to', '')
                
                # Decode addLiquidity parameters from transaction data
                # addLiquidity(address tokenA, address tokenB, uint amountADesired, uint amountBDesired, uint amountAMin, uint amountBMin, address to, uint deadline)
                # selector: 0xe8e33700
                tx_data = tx.get('data', '')
                if len(tx_data) < 138:  # At least selector + tokenA + tokenB
                    print(f"❌ Invalid transaction data length for addLiquidity")
                    return None
                
                # Extract amountADesired (bytes 68-100 after selector, 3rd parameter)
                # Skip: 0x (2) + selector (8) + tokenA (64) + tokenB (64) = 138
                amount_a_hex = tx_data[138:202]  # 64 chars for amountADesired
                amount_a_wei = int(amount_a_hex, 16)
                
                # Extract amountBDesired (bytes 100-132 after selector, 4th parameter)
                amount_b_hex = tx_data[202:266]  # 64 chars for amountBDesired
                amount_b_wei = int(amount_b_hex, 16)
                
                # Get token addresses and decimals from composite definition
                token_a_address = self._get_param_value('token_a_address')
                token_b_address = self._get_param_value('token_b_address')
                token_a_decimals = self._get_param_value('token_a_decimals', 18)
                token_b_decimals = self._get_param_value('token_b_decimals', 18)
                
                amount_token_a = amount_a_wei / (10**token_a_decimals)
                amount_token_b = amount_b_wei / (10**token_b_decimals)
                
                print(f"   Decoded add liquidity parameters:")
                print(f"   - router_address: {router_address}")
                print(f"   - token_a_address: {token_a_address}")
                print(f"   - token_b_address: {token_b_address}")
                print(f"   - amount_token_a: {amount_token_a} tokens ({amount_a_wei} wei)")
                print(f"   - amount_token_b: {amount_token_b} tokens ({amount_b_wei} wei)")
                
                return validator_class(
                    router_address=router_address,
                    token_a_address=token_a_address,
                    token_b_address=token_b_address,
                    amount_token_a=amount_token_a,
                    amount_token_b=amount_token_b,
                    token_a_decimals=token_a_decimals,
                    token_b_decimals=token_b_decimals
                )
            
            elif atomic_id == 'remove_liquidity_tokens':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Router address is the target of the transaction
                router_address = tx.get('to', '')
                
                # Decode removeLiquidity parameters from transaction data
                # removeLiquidity(address tokenA, address tokenB, uint liquidity, uint amountAMin, uint amountBMin, address to, uint deadline)
                # selector: 0xbaa2abde
                tx_data = tx.get('data', '')
                if len(tx_data) < 138:  # At least selector + tokenA + tokenB
                    print(f"❌ Invalid transaction data length for removeLiquidity")
                    return None
                
                # Get token addresses and percentage from composite definition
                token_a_address = self._get_param_value('token_a_address')
                token_b_address = self._get_param_value('token_b_address')
                liquidity_percentage = self._get_param_value('liquidity_percentage', 50.0)
                
                print(f"   Decoded remove liquidity parameters:")
                print(f"   - router_address: {router_address}")
                print(f"   - token_a_address: {token_a_address}")
                print(f"   - token_b_address: {token_b_address}")
                print(f"   - liquidity_percentage: {liquidity_percentage}%")
                
                return validator_class(
                    router_address=router_address,
                    token_a_address=token_a_address,
                    token_b_address=token_b_address,
                    liquidity_percentage=liquidity_percentage
                )
            
            elif atomic_id == 'remove_liquidity_bnb_token':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Router address is the target of the transaction
                router_address = tx.get('to', '')
                
                # Decode removeLiquidityETH parameters from transaction data
                # removeLiquidityETH(address token, uint liquidity, uint amountTokenMin, uint amountETHMin, address to, uint deadline)
                # selector: 0x02751cec
                tx_data = tx.get('data', '')
                if len(tx_data) < 74:  # At least selector + token
                    print(f"❌ Invalid transaction data length for removeLiquidityETH")
                    return None
                
                # Get token address and other params from composite definition
                token_address = self._get_param_value('token_address')
                token_decimals = self._get_param_value('token_decimals', 18)
                liquidity_percentage = self._get_param_value('liquidity_percentage', 50.0)
                slippage = self._get_param_value('slippage', 5.0)
                
                print(f"   Decoded remove liquidity BNB parameters:")
                print(f"   - router_address: {router_address}")
                print(f"   - token_address: {token_address}")
                print(f"   - liquidity_percentage: {liquidity_percentage}%")
                print(f"   - slippage: {slippage}%")
                
                return validator_class(
                    router_address=router_address,
                    token_address=token_address,
                    liquidity_percentage=liquidity_percentage,
                    token_decimals=token_decimals,
                    slippage=slippage
                )
            
            elif atomic_id == 'swap_exact_tokens_for_bnb':
                if not tx:
                    print(f"❌ Transaction object required for {atomic_id}")
                    return None
                
                # Router address is the target of the transaction
                router_address = tx.get('to', '')
                
                # Decode swapExactTokensForETH parameters from transaction data
                # swapExactTokensForETH(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline)
                # selector: 0x18cbafe5
                tx_data = tx.get('data', '')
                if len(tx_data) < 74:  # At least selector + amountIn
                    print(f"❌ Invalid transaction data length for swapExactTokensForETH")
                    return None
                
                # Extract amountIn (bytes 4-36 after selector)
                amount_in_hex = tx_data[10:74]  # Skip '0x' and 8 char selector
                amount_in_wei = int(amount_in_hex, 16)
                
                # Get token address and other params from composite definition
                token_address = self._get_param_value('token_address')
                token_decimals = self._get_param_value('token_decimals', 18)
                slippage = self._get_param_value('slippage', 5.0)
                
                amount_in_tokens = amount_in_wei / (10**token_decimals)
                
                print(f"   Decoded swap to BNB parameters:")
                print(f"   - router_address: {router_address}")
                print(f"   - token_address: {token_address}")
                print(f"   - amount_in: {amount_in_tokens} tokens ({amount_in_wei} wei)")
                print(f"   - slippage: {slippage}%")
                
                return validator_class(
                    router_address=router_address,
                    token_address=token_address,
                    amount_in=amount_in_tokens,
                    token_decimals=token_decimals,
                    slippage=slippage
                )
            
            else:
                # Default: only pass agent_address
                return validator_class(self.agent_address)
        
        except Exception as e:
            print(f"❌ Error loading validator '{validator_class_name}': {e}")
            import traceback
            traceback.print_exc()
            return None


def validate_composite(
    composite_id: str,
    agent_address: str,
    final_submission: Dict[str, Any],
    chain_state: Dict[str, Any],
    task_params: Dict[str, Any],
    interaction_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convenience function to validate a composite problem
    
    Args:
        composite_id: Composite problem ID
        agent_address: Agent's address
        final_submission: LLM's final submission
        chain_state: Final blockchain state
        task_params: Original task parameters
        interaction_history: Full interaction history
    
    Returns:
        Validation result
    """
    validator = CompositeValidator(agent_address)
    validator.load_composite_definition(composite_id)
    return validator.validate(final_submission, chain_state, task_params, interaction_history)


# Example usage
if __name__ == "__main__":
    print("Composite Validator - Generic validator for multi-round interaction problems")
    print("\nFeatures:")
    print("  ✅ Multi-round interaction support")
    print("  ✅ Error report validation")
    print("  ✅ Parameter compliance checking (CRITICAL)")
    print("  ✅ Modular scoring using atomic components")
    print("  ✅ Normalized 100-point scoring")

