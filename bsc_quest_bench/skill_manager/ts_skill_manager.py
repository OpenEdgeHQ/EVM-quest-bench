"""
TypeScript Skill Manager for Quest Bench

Executes TypeScript transaction generation code
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional


class TypeScriptSkillManager:
    """TypeScript Code Execution Manager"""
    
    def __init__(
        self,
        use_bun: bool = True,
        bun_path: Optional[str] = None
    ):
        """
        Initialize manager
        
        Args:
            use_bun: Whether to use Bun (recommended)
            bun_path: Bun executable path (optional)
        """
        self.use_bun = use_bun
        
        if bun_path:
            self.runtime = bun_path
        elif use_bun:
            self.runtime = self._find_bun_path()
        else:
            self.runtime = 'node'
        
        # Use local skill_runner
        quest_bench_root = Path(__file__).parent.parent
        self.runner_script = str(quest_bench_root / 'skill_runner' / 'runBscSkill.ts')
        
        if not Path(self.runner_script).exists():
            raise FileNotFoundError(
                f"Runner script not found: {self.runner_script}\n"
                f"Please ensure skill_runner/runBscSkill.ts exists"
            )
    
    def _find_bun_path(self) -> str:
        """Find Bun executable"""
        bun_paths = [
            os.path.expanduser('~/.bun/bin/bun'),
            '/usr/local/bin/bun',
            'bun',
        ]
        
        for bun_path in bun_paths:
            try:
                result = subprocess.run(
                    [bun_path, '--version'],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if result.returncode == 0:
                    return bun_path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return 'bun'
    
    def execute_skill(
        self,
        code_file: str,
        provider_url: str,
        agent_address: str,
        deployed_contracts: Dict[str, str],
        timeout: int = 60000
    ) -> Dict[str, Any]:
        """
        Execute TypeScript code
        
        Args:
            code_file: TypeScript file path
            provider_url: RPC URL
            agent_address: Test address
            deployed_contracts: Deployed contracts
            timeout: Timeout (milliseconds)
            
        Returns:
            Execution result dictionary
        """
        start_time = time.time()
        
        contracts_json = json.dumps(deployed_contracts)
        
        command = [
            self.runtime,
            self.runner_script,
            code_file,
            provider_url,
            agent_address,
            contracts_json,
            str(timeout)
        ]
        
        print(f"🔍 [DEBUG] Executing command:")
        print(f"🔍 [DEBUG]   Runtime: {self.runtime}")
        print(f"🔍 [DEBUG]   Script: {self.runner_script}")
        print(f"🔍 [DEBUG]   Code file: {code_file}")
        print(f"🔍 [DEBUG]   Provider: {provider_url}")
        print(f"🔍 [DEBUG]   Address: {agent_address}")
        print(f"🔍 [DEBUG]   Timeout: {timeout}ms")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout / 1000
            )
            
            execution_time = time.time() - start_time
            
            # Print STDERR for debug logs
            if result.stderr:
                print(f"\n🔍 [DEBUG] TypeScript STDERR output:")
                print("─" * 80)
                print(result.stderr)
                print("─" * 80)
            
            if result.returncode == 0:
                output_lines = result.stdout.strip().split('\n')
                last_line = output_lines[-1] if output_lines else '{}'
                
                try:
                    output_data = json.loads(last_line)
                    
                    if output_data.get('success'):
                        # Check if this is a query result (not a transaction)
                        if output_data.get('is_query'):
                            return {
                                'success': True,
                                'is_query': True,
                                'tx_object': output_data.get('tx_object', {}),
                                'execution_time': execution_time
                            }
                        return {
                            'success': True,
                            'serialized_tx': output_data.get('serialized_tx', ''),
                            'tx_object': output_data.get('tx_object', {}),
                            'execution_time': execution_time
                        }
                    else:
                        return {
                            'success': False,
                            'error': output_data.get('error', 'Unknown error'),
                            'execution_time': execution_time
                        }
                except json.JSONDecodeError as e:
                    return {
                        'success': False,
                        'error': f"Failed to parse output: {e}\nOutput: {last_line[:200]}",
                        'execution_time': execution_time
                    }
            else:
                error_msg = result.stderr or result.stdout or 'Unknown error'
                print(f"\n🔍 [DEBUG] Execution failed with return code: {result.returncode}")
                if result.stderr:
                    print(f"🔍 [DEBUG] STDERR:\n{result.stderr}")
                if result.stdout:
                    print(f"🔍 [DEBUG] STDOUT:\n{result.stdout}")
                return {
                    'success': False,
                    'error': f"Execution failed: {error_msg}",
                    'execution_time': execution_time
                }
        
        except subprocess.TimeoutExpired as e:
            execution_time = time.time() - start_time
            print(f"\n🔍 [DEBUG] Process timed out after {execution_time:.2f}s")
            print(f"🔍 [DEBUG] Configured timeout: {timeout}ms ({timeout/1000}s)")
            # Try to get partial output
            if hasattr(e, 'stderr') and e.stderr:
                print(f"🔍 [DEBUG] Partial STDERR before timeout:\n{e.stderr}")
            if hasattr(e, 'stdout') and e.stdout:
                print(f"🔍 [DEBUG] Partial STDOUT before timeout:\n{e.stdout}")
            return {
                'success': False,
                'error': f'Timeout after {timeout}ms',
                'execution_time': execution_time
            }
        
        except FileNotFoundError:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'error': f'{self.runtime} not found',
                'execution_time': execution_time
            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'execution_time': execution_time
            }

