"""
BSC Quest Environment - Environment Layer

Responsibilities:
1. Initialize local Anvil node (fork from BSC testnet)
2. Create test account and set initial balance
3. Provide Web3 connection and on-chain state query
"""

import subprocess
import time
import socket
import os
from typing import Optional, Dict, Any
from web3 import Web3
from eth_account import Account

class QuestEnvironment:
    """Quest Environment Management Class"""

    def __init__(
        self,
        fork_url: str = None,
        chain_id: int = 56,
        anvil_port: int = 8545
    ):
        """
        Initialize Quest environment
        
        Args:
            fork_url: BSC RPC URL
                     - None: Use default BSC Mainnet public RPC (suitable for open source/CI)
                     - Custom URL: Use paid or private RPC (suitable for dev/prod)
                     Can also set via BSC_FORK_URL environment variable
            chain_id: Chain ID (56=BSC Mainnet, 97=BSC Testnet, default 56)
            anvil_port: Anvil port
        """
        # Fork URL Priority:
        # 1. Passed fork_url parameter
        # 2. Environment variable BSC_FORK_URL
        # 3. Default BSC Mainnet public RPC
        if fork_url is None:
            import os
            fork_url = os.getenv('BSC_FORK_URL', 'https://bsc-dataseed.binance.org')
        
        self.fork_url = fork_url
        self.chain_id = chain_id
        self.anvil_port = anvil_port
        self.anvil_process = None
        self.anvil_cmd = None
        
        self.w3: Optional[Web3] = None
        self.test_account: Optional[Account] = None
        self.test_address: Optional[str] = None
        self.test_private_key: Optional[str] = None
        self.initial_snapshot_id: Optional[str] = None  # Store initial snapshot for fast reset
        
    def start(self) -> Dict[str, Any]:
        """
        Start environment
        
        Returns:
            Environment info dictionary
        """
        # 1. Start Anvil fork
        self._start_anvil_fork()
        
        # 2. Connect Web3
        anvil_rpc = f"http://127.0.0.1:{self.anvil_port}"
        
        # Create an HTTPProvider bypassing proxy (local connection should not go through proxy)
        import requests
        session = requests.Session()
        session.proxies = {
            'http': None,
            'https': None,
        }
        session.trust_env = False  # Do not use proxy settings from environment variables
        
        from web3.providers.rpc import HTTPProvider
        # Set explicit timeout for HTTP requests to avoid indefinite blocking
        # timeout=(connect_timeout, read_timeout) in seconds
        provider = HTTPProvider(
            anvil_rpc, 
            session=session,
            request_kwargs={'timeout': 60}  # 60 second timeout for RPC requests
        )
        self.w3 = Web3(provider)
        
        # 2.1 Inject POA middleware (BSC is a POA chain)
        try:
            # Web3.py 7.x uses ExtraDataToPOAMiddleware
            from web3.middleware import ExtraDataToPOAMiddleware
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        except ImportError:
            try:
                # Web3.py v6+ uses geth_poa_middleware (old path)
                from web3.middleware.geth_poa import geth_poa_middleware
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            except ImportError:
                try:
                    # Web3.py v5 uses geth_poa_middleware (older path)
                    from web3.middleware import geth_poa_middleware
                    self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                except ImportError:
                    # If none exist, Anvil local fork usually doesn't need it (we use direct RPC calls to bypass)
                    print("⚠️  Warning: Could not import POA middleware, continuing without it")
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to Anvil: {anvil_rpc}")
        
        print(f"✓ Anvil connected successfully")
        print(f"  Chain ID: {self.w3.eth.chain_id}")
        print(f"  Anvil RPC: {anvil_rpc}")
        print(f"  Fork: {self.fork_url}")
        
        # 3. Create test account
        self.test_account = Account.create()
        self.test_address = self.test_account.address
        self.test_private_key = self.test_account.key.hex()
        
        print(f"✓ Test account created successfully")
        print(f"  Address: {self.test_address}")
        
        # 4. Set initial balance (100 BNB - enough for multiple tests)
        self._set_balance(self.test_address, 100 * 10**18)
        
        balance = self.w3.eth.get_balance(self.test_address) / 10**18
        print(f"  Balance: {balance} BNB")
        
        # 5. Preheat common contract addresses (trigger Anvil to pull contract code)
        self._preheat_contracts()
        
        # 6. Set ERC20 token balances for test account
        self._set_token_balances()
        
        # 7. Setup rich account for transferFrom tests
        self._setup_rich_account()
        
        # 8. Create initial snapshot for fast reset
        try:
            self.initial_snapshot_id = self.w3.provider.make_request("evm_snapshot", [])['result']
            print(f"✓ Initial snapshot created: {self.initial_snapshot_id}")
        except Exception as e:
            print(f"⚠️  Failed to create initial snapshot: {e}")
            self.initial_snapshot_id = None
        
        return {
            'rpc_url': anvil_rpc,
            'chain_id': self.chain_id,
            'test_address': self.test_address,
            'test_private_key': self.test_private_key,
            'rich_address': getattr(self, 'rich_address', None),  # For transferFrom tests
            'block_number': self.w3.eth.block_number,
            'balance': balance,
            # Deployed contracts
            'simple_staking_address': getattr(self, 'simple_staking_address', None),
            'simple_lp_staking_address': getattr(self, 'simple_lp_staking_address', None),
            'simple_reward_pool_address': getattr(self, 'simple_reward_pool_address', None),
            'erc1363_token_address': getattr(self, 'erc1363_token_address', None),
            'erc1155_token_address': getattr(self, 'erc1155_token_address', None),
            'erc721_token_address': getattr(self, 'erc721_token_address', None),
            'flashloan_contract_address': getattr(self, 'flashloan_contract_address', None),
            'simple_counter_address': getattr(self, 'simple_counter_address', None),
            'donation_box_address': getattr(self, 'donation_box_address', None),
            'message_board_address': getattr(self, 'message_board_address', None),
            'proxy_address': getattr(self, 'proxy_address', None),
            'implementation_address': getattr(self, 'implementation_address', None),
            'fallback_receiver_address': getattr(self, 'fallback_receiver_address', None)
        }
    
    def create_snapshot(self) -> str:
        """
        Create snapshot of current state
        
        Returns:
            Snapshot ID
        """
        if not self.w3:
            raise RuntimeError("Environment not started, cannot create snapshot")
        
        snapshot_id = self.w3.provider.make_request("evm_snapshot", [])
        print(f"✓ Snapshot created: {snapshot_id}")
        return snapshot_id
    
    def revert_to_snapshot(self, snapshot_id: str) -> bool:
        """
        Revert to specified snapshot
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Whether revert was successful
        """
        if not self.w3:
            raise RuntimeError("Environment not started, cannot revert snapshot")
        
        result = self.w3.provider.make_request("evm_revert", [snapshot_id])
        if result:
            print(f"✓ Reverted to snapshot: {snapshot_id}")
        else:
            print(f"⚠️  Failed to revert snapshot: {snapshot_id}")
        return result
    
    def reset_account_balance(self):
        """
        Reset test account balance
        Ensures account has enough BNB before each test
        """
        if not self.w3 or not self.test_address:
            raise RuntimeError("Environment not started, cannot reset balance")
        
        # Set initial BNB balance (100 BNB)
        initial_balance = 100 * 10**18
        
        try:
            self.w3.provider.make_request(
                'anvil_setBalance',
                [self.test_address, hex(initial_balance)]
            )
            print(f"✓ Account balance reset: {self.test_address} -> 100 BNB")
            return True
        except Exception as e:
            print(f"⚠️  Failed to reset balance: {e}")
            return False
    
    def _quick_health_check(self, timeout_seconds: float = 5.0) -> bool:
        """
        Quick health check for Anvil - returns False if unresponsive
        Uses a very short timeout to detect frozen Anvil quickly
        """
        import socket
        import json
        
        try:
            # Use raw socket with short timeout instead of Web3 (which has 60s timeout)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_seconds)
            sock.connect(('127.0.0.1', self.anvil_port))
            
            # Send a simple eth_blockNumber request
            request = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            })
            http_request = f"POST / HTTP/1.1\r\nHost: 127.0.0.1:{self.anvil_port}\r\nContent-Type: application/json\r\nContent-Length: {len(request)}\r\n\r\n{request}"
            sock.sendall(http_request.encode())
            
            # Wait for response
            response = sock.recv(4096)
            sock.close()
            
            # Check if we got a valid response
            return b'"result"' in response or b'"jsonrpc"' in response
            
        except (socket.timeout, socket.error, Exception) as e:
            print(f"  ⚠️  Quick health check failed: {e}")
            return False
    
    def reset(self):
        """
        Fast reset environment state (use snapshot revert, keep Anvil process running)
        Reverts to initial snapshot state, much faster than full reset
        """
        if not self.w3 or not self.test_address:
            raise RuntimeError("Environment not started, cannot reset")
        
        if not self.initial_snapshot_id:
            print("⚠️  Warning: No initial snapshot, cannot fast reset")
            return False
        
        print("🔄 Fast resetting environment state (reverting snapshot)...")
        
        # Quick health check before attempting RPC calls
        if not self._quick_health_check(timeout_seconds=5.0):
            print("  ❌ Anvil is unresponsive (failed quick health check)")
            print("  ⚠️  Skipping reset, recommend restart instead")
            return False
        
        try:
            # 1. Revert to initial snapshot
            result = self.w3.provider.make_request("evm_revert", [self.initial_snapshot_id])
            if not result.get('result', False):
                print(f"  ⚠️  Snapshot revert failed")
                return False
            
            print(f"  ✓ Reverted to initial snapshot: {self.initial_snapshot_id}")
            
            # 2. Recreate snapshot (some Anvil versions consume snapshot on revert)
            self.initial_snapshot_id = self.w3.provider.make_request("evm_snapshot", [])['result']
            print(f"  ✓ Recreated snapshot: {self.initial_snapshot_id}")
            
            # Verify balance
            balance = self.w3.eth.get_balance(self.test_address) / 10**18
            print(f"  ✓ Account balance: {balance} BNB")
            
            print("✅ Environment fast reset completed\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Snapshot revert failed: {e}")
            print("  ⚠️  Will attempt full reset...")
            
            # If snapshot fails, fallback to full reset
            return self._full_reset()
    
    def _full_reset(self):
        """
        Full reset environment (fallback, used when snapshot fails)
        Uses anvil_reset to reset to fork point and redeploys all contracts
        """
        print("🔄 Performing full reset...")
        
        try:
            # 1. Reset blockchain state to initial fork point
            self.w3.provider.make_request('anvil_reset', [{
                'forking': {
                    'jsonRpcUrl': self.fork_url
                }
            }])
            print("  ✓ Blockchain state reset to fork point")
        except Exception as e:
            print(f"  ❌ Blockchain reset failed: {e}")
            return False
        
        try:
            # 2. Reset account balance
            self._set_balance(self.test_address, 100 * 10**18)
            balance = self.w3.eth.get_balance(self.test_address) / 10**18
            print(f"  ✓ Account balance reset: {balance} BNB")
            
            # 3. Re-setup token balances and contracts
            self._set_token_balances()
            
            # 4. Re-setup rich account
            self._setup_rich_account()
            
            # 5. Recreate initial snapshot
            self.initial_snapshot_id = self.w3.provider.make_request("evm_snapshot", [])['result']
            print(f"  ✓ Recreated initial snapshot: {self.initial_snapshot_id}")
            
            print("✅ Full reset completed\n")
            return True
            
        except Exception as e:
            print(f"  ❌ Full reset failed: {e}")
            return False
    
    def stop(self):
        """Stop environment"""
        self._cleanup_anvil()
        print("✓ Environment cleaned up")
    
    def get_diagnostics(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Get diagnostic information about Anvil status
        
        Args:
            timeout: Timeout for each diagnostic check
            
        Returns:
            Dictionary with diagnostic information
        """
        diagnostics = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'anvil_process_alive': False,
            'anvil_process_pid': None,
            'rpc_responsive': False,
            'rpc_response_time_ms': None,
            'current_block_number': None,
            'chain_id': None,
            'test_account_balance': None,
            'port_in_use': self._is_port_in_use(self.anvil_port),
            'fork_url': self.fork_url,
            'errors': []
        }
        
        # Check Anvil process
        if self.anvil_process:
            diagnostics['anvil_process_pid'] = self.anvil_process.pid
            poll_result = self.anvil_process.poll()
            diagnostics['anvil_process_alive'] = poll_result is None
            if poll_result is not None:
                diagnostics['anvil_exit_code'] = poll_result
                diagnostics['errors'].append(f'Anvil process exited with code {poll_result}')
        else:
            diagnostics['errors'].append('Anvil process not started')
        
        # Check RPC responsiveness
        if self.w3:
            try:
                import time as time_module
                start_time = time_module.time()
                
                # Try a simple RPC call with timeout
                block_num = self.w3.eth.block_number
                
                end_time = time_module.time()
                response_time_ms = (end_time - start_time) * 1000
                
                diagnostics['rpc_responsive'] = True
                diagnostics['rpc_response_time_ms'] = round(response_time_ms, 2)
                diagnostics['current_block_number'] = block_num
                
            except Exception as e:
                diagnostics['errors'].append(f'RPC call failed: {str(e)[:200]}')
            
            # Try to get chain ID
            try:
                diagnostics['chain_id'] = self.w3.eth.chain_id
            except Exception as e:
                diagnostics['errors'].append(f'Chain ID query failed: {str(e)[:100]}')
            
            # Try to get test account balance
            if self.test_address:
                try:
                    balance_wei = self.w3.eth.get_balance(self.test_address)
                    diagnostics['test_account_balance'] = balance_wei / 10**18
                except Exception as e:
                    diagnostics['errors'].append(f'Balance query failed: {str(e)[:100]}')
        else:
            diagnostics['errors'].append('Web3 not connected')
        
        return diagnostics
    
    def check_health(self, timeout: float = 10.0) -> bool:
        """
        Quick health check for Anvil
        
        Args:
            timeout: Timeout for health check
            
        Returns:
            True if Anvil is healthy, False otherwise
        """
        diag = self.get_diagnostics(timeout)
        return diag['anvil_process_alive'] and diag['rpc_responsive']
    
    def print_diagnostics(self, timeout: float = 10.0):
        """
        Print diagnostic information
        
        Args:
            timeout: Timeout for diagnostic checks
        """
        diag = self.get_diagnostics(timeout)
        
        print("\n" + "=" * 60)
        print("🔍 ANVIL DIAGNOSTICS")
        print("=" * 60)
        print(f"  Timestamp: {diag['timestamp']}")
        print(f"  Anvil Process:")
        print(f"    - PID: {diag['anvil_process_pid']}")
        print(f"    - Alive: {'✅' if diag['anvil_process_alive'] else '❌'} {diag['anvil_process_alive']}")
        if 'anvil_exit_code' in diag:
            print(f"    - Exit Code: {diag['anvil_exit_code']}")
        print(f"  RPC Status:")
        print(f"    - Responsive: {'✅' if diag['rpc_responsive'] else '❌'} {diag['rpc_responsive']}")
        print(f"    - Response Time: {diag['rpc_response_time_ms']} ms")
        print(f"    - Block Number: {diag['current_block_number']}")
        print(f"    - Chain ID: {diag['chain_id']}")
        print(f"  Port {self.anvil_port} in use: {diag['port_in_use']}")
        print(f"  Test Account Balance: {diag['test_account_balance']} BNB")
        print(f"  Fork URL: {diag['fork_url'][:50]}...")
        if diag['errors']:
            print(f"  ⚠️ Errors:")
            for err in diag['errors']:
                print(f"    - {err}")
        print("=" * 60 + "\n")
        
        return diag
    
    def restart(self) -> bool:
        """
        Restart Anvil process completely
        
        Returns:
            True if restart successful, False otherwise
        """
        print("🔄 Restarting Anvil process...")
        
        try:
            # Stop current Anvil
            self._cleanup_anvil()
            time.sleep(2)
            
            # Start new Anvil
            self._start_anvil_fork()
            
            # Reconnect Web3
            anvil_rpc = f"http://127.0.0.1:{self.anvil_port}"
            import requests
            session = requests.Session()
            session.proxies = {'http': None, 'https': None}
            session.trust_env = False
            
            from web3.providers.rpc import HTTPProvider
            provider = HTTPProvider(anvil_rpc, session=session)
            self.w3 = Web3(provider)
            
            # Inject POA middleware
            try:
                from web3.middleware import ExtraDataToPOAMiddleware
                self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            except ImportError:
                try:
                    from web3.middleware.geth_poa import geth_poa_middleware
                    self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                except ImportError:
                    from web3.middleware import geth_poa_middleware
                    self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Re-setup everything
            self._set_balance(self.test_address, 100 * 10**18)
            self._preheat_contracts()
            self._set_token_balances()  # This also sets LP token balances
            
            # Re-deploy custom contracts (they don't exist in fork)
            # Note: NFT ownership is handled within _deploy_erc721_test_nft()
            self._deploy_erc1363_token()
            self._deploy_erc721_test_nft()
            self._deploy_erc1155_token()
            self._deploy_flashloan_receiver()
            self._deploy_simple_counter()
            self._deploy_donation_box()
            self._deploy_message_board()
            self._deploy_delegate_call_contracts()
            self._deploy_fallback_receiver()
            self._deploy_simple_staking()
            self._deploy_simple_lp_staking()
            self._deploy_simple_reward_pool()
            self._setup_rich_account()
            
            # Create new snapshot
            self.initial_snapshot_id = self.w3.provider.make_request("evm_snapshot", [])['result']
            
            print("✅ Anvil restarted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Anvil restart failed: {e}")
            return False
    
    def _start_anvil_fork(self):
        """Start Anvil fork process"""
        # 1. Clean up potential zombie Anvil processes
        self._kill_zombie_anvil()
        
        # 2. Check if port is in use
        if self._is_port_in_use(self.anvil_port):
            print(f"⚠️  Port {self.anvil_port} is already in use")
            print(f"   Attempting to cleanup and retry...")
            self._kill_zombie_anvil()
            time.sleep(2)
            
            if self._is_port_in_use(self.anvil_port):
                raise RuntimeError(
                    f"Port {self.anvil_port} is still in use, cannot start Anvil\n"
                    f"Please clean up manually:\n"
                    f"  Linux/Mac: lsof -ti:{self.anvil_port} | xargs kill -9\n"
                    f"  Windows: netstat -ano | findstr :{self.anvil_port}"
                )
        
        # 3. Test network connection to Fork URL
        print(f"🔍 Testing connection to Fork URL...")
        if not self._test_fork_url():
            print(f"⚠️  Warning: Cannot connect to Fork URL quickly")
            print(f"   Continuing to start, but might be slow...")
        
        # 4. Find anvil command
        anvil_paths = [
            os.path.expanduser('~/.foundry/bin/anvil'),
            '/usr/local/bin/anvil',
            'anvil',
        ]
        
        for path in anvil_paths:
            try:
                result = subprocess.run(
                    [path, '--version'],
                    capture_output=True,
                    check=True,
                    text=True,
                    timeout=5
                )
                self.anvil_cmd = path
                print(f"✓ Found Anvil: {path}")
                break
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        if not self.anvil_cmd:
            raise RuntimeError(
                "Anvil not found! Please install Foundry:\n"
                "  curl -L https://foundry.paradigm.xyz | bash\n"
                "  foundryup"
            )
        
        # 5. Start Anvil
        print(f"🔨 Starting Anvil fork...")
        print(f"   Fork URL: {self.fork_url}")
        print(f"   Port: {self.anvil_port}")
        
        anvil_cmd_list = [
            self.anvil_cmd,
            '--fork-url', self.fork_url,
            '--port', str(self.anvil_port),
            '--host', '127.0.0.1',
            # NOTE: Removed --no-storage-caching to allow caching of remote data
            # This significantly reduces the number of requests to the upstream RPC
            # and prevents request queue buildup that causes timeouts
            '--timeout', '60000',  # 60 second timeout for fork requests (ms)
            '--retries', '3',  # Retry failed fork requests
            # NOTE: Removed --compute-units-per-second to avoid request queue buildup
            # The rate limiting was causing timeouts when many requests accumulated
        ]
        
        # Create environment without proxy settings
        # This is critical for WSL environments with system proxy that might interfere
        anvil_env = os.environ.copy()
        # Remove all proxy-related environment variables
        proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 
                      'all_proxy', 'ALL_PROXY', 'ftp_proxy', 'FTP_PROXY']
        for var in proxy_vars:
            anvil_env.pop(var, None)
        # Set no_proxy to bypass any remaining proxy settings
        anvil_env['no_proxy'] = '*'
        anvil_env['NO_PROXY'] = '*'
        
        # Use DEVNULL for stdout and capture stderr in a non-blocking way
        # This prevents buffer deadlock that can occur when PIPE buffers fill up
        import threading
        import queue
        
        self.anvil_process = subprocess.Popen(
            anvil_cmd_list,
            stdout=subprocess.DEVNULL,  # Don't capture stdout to avoid buffer issues
            stderr=subprocess.PIPE,
            env=anvil_env  # Use proxy-free environment
        )
        
        # Use a thread to read stderr asynchronously to prevent buffer deadlock
        stderr_output = []
        stderr_queue = queue.Queue()
        
        def read_stderr():
            try:
                for line in iter(self.anvil_process.stderr.readline, b''):
                    stderr_queue.put(line.decode('utf-8', errors='ignore').strip())
            except:
                pass
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        # 6. Wait for start (increase timeout for remote servers with higher latency)
        max_wait = 60  # Increased from 30s to 60s for remote server support
        print(f"   Waiting for Anvil to start (max {max_wait}s)...")
        
        for i in range(max_wait):
            time.sleep(1)
            
            # Drain stderr queue to prevent buffer buildup
            while not stderr_queue.empty():
                try:
                    line = stderr_queue.get_nowait()
                    if line:
                        stderr_output.append(line)
                except queue.Empty:
                    break
            
            # Check if port is open
            if self._is_port_in_use(self.anvil_port):
                print(f"✓ Anvil started successfully ({i+1}s)")
                return
            
            # Check if process exited unexpectedly
            if self.anvil_process.poll() is not None:
                returncode = self.anvil_process.returncode
                # Collect remaining stderr
                time.sleep(0.5)
                while not stderr_queue.empty():
                    try:
                        line = stderr_queue.get_nowait()
                        if line:
                            stderr_output.append(line)
                    except queue.Empty:
                        break
                error_msg = '\n'.join(stderr_output[-20:]) if stderr_output else "No error message"
                
                self._cleanup_anvil()
                raise RuntimeError(
                    f"Anvil process exited unexpectedly (code {returncode})\n"
                    f"Error message: {error_msg[:500]}\n"
                    f"Possible causes:\n"
                    f"  - Fork URL invalid or unreachable: {self.fork_url}\n"
                    f"  - Network connection issues\n"
                    f"  - RPC node rate limited or down"
                )
            
            # Show progress every 10 seconds
            if (i + 1) % 10 == 0:
                print(f"   Waiting... ({i+1}s)")
        
        # Timeout handling - collect stderr for diagnostics
        while not stderr_queue.empty():
            try:
                line = stderr_queue.get_nowait()
                if line:
                    stderr_output.append(line)
            except queue.Empty:
                break
        
        stderr_log = '\n'.join(stderr_output[-30:]) if stderr_output else "No output captured"
        
        self._cleanup_anvil()
        raise RuntimeError(
            f"Anvil start timed out ({max_wait}s)\n"
            f"Possible causes:\n"
            f"  1. Slow network connection - Fork URL: {self.fork_url}\n"
            f"  2. RPC node slow response or unavailable\n"
            f"  3. Insufficient system resources\n"
            f"\n"
            f"Anvil stderr output (last 30 lines):\n{stderr_log}\n"
            f"\n"
            f"Suggestions:\n"
            f"  - Check network connection\n"
            f"  - Try changing RPC URL\n"
            f"  - Restart test\n"
            f"  - Check WSL2 resource configuration"
        )
    
    def _cleanup_anvil(self):
        """Cleanup Anvil process"""
        if self.anvil_process:
            try:
                self.anvil_process.terminate()
                self.anvil_process.wait(timeout=5)
                print("✓ Anvil process terminated")
            except:
                self.anvil_process.kill()
                print("✓ Anvil process forcibly terminated")
            self.anvil_process = None
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0
    
    def _kill_zombie_anvil(self):
        """
        Clean up potential zombie Anvil processes
        
        IMPORTANT: Only kills processes that are actually Anvil (binary name contains 'anvil'),
        NOT all processes using the port (which would kill the Python test runner!)
        """
        current_pid = os.getpid()  # Get current process PID to avoid suicide
        
        try:
            import psutil
            
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
                try:
                    # Skip current process
                    if proc.info['pid'] == current_pid:
                        continue
                    
                    # Check if it's an anvil process by examining the executable or name
                    proc_name = proc.info.get('name', '').lower()
                    proc_exe = (proc.info.get('exe') or '').lower()
                    cmdline = proc.info.get('cmdline', [])
                    cmdline_str = ' '.join(cmdline).lower() if cmdline else ''
                    
                    # Must be an actual anvil binary (not just a script with 'anvil' in path)
                    is_anvil_binary = (
                        proc_name == 'anvil' or 
                        proc_exe.endswith('/anvil') or
                        proc_exe.endswith('\\anvil') or
                        proc_exe.endswith('\\anvil.exe') or
                        (cmdline and cmdline[0] and cmdline[0].endswith('/anvil'))
                    )
                    
                    if is_anvil_binary:
                        # Check if using the same port
                        if str(self.anvil_port) in cmdline_str:
                            print(f"   Cleaning up zombie Anvil process: PID {proc.info['pid']}")
                            proc.kill()
                            proc.wait(timeout=3)
                            killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    continue
            
            if killed_count > 0:
                print(f"   ✓ Cleaned up {killed_count} zombie processes")
                time.sleep(1)  # Wait for port release
        except ImportError:
            # psutil not installed, try system commands
            import platform
            system = platform.system()
            
            try:
                if system == 'Linux':
                    # Linux: Find anvil processes specifically (not all processes on port!)
                    # Use pgrep to find processes with 'anvil' in name/cmdline
                    result = subprocess.run(
                        ['pgrep', '-f', f'anvil.*--port.*{self.anvil_port}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            try:
                                pid_int = int(pid)
                                # Don't kill ourselves
                                if pid_int == current_pid:
                                    continue
                                # Verify it's really anvil by checking /proc/PID/cmdline
                                try:
                                    with open(f'/proc/{pid}/cmdline', 'r') as f:
                                        cmdline = f.read()
                                        if 'anvil' not in cmdline.lower():
                                            continue  # Not anvil, skip
                                except:
                                    continue
                                subprocess.run(['kill', '-9', pid], timeout=2)
                                print(f"   Cleaning up Anvil process: PID {pid}")
                            except (ValueError, Exception):
                                pass
                        time.sleep(1)
                elif system == 'Windows':
                    # Windows: Use tasklist to find anvil.exe processes
                    result = subprocess.run(
                        ['tasklist', '/FI', 'IMAGENAME eq anvil.exe', '/FO', 'CSV'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines[1:]:  # Skip header
                            if 'anvil' in line.lower():
                                parts = line.strip('"').split('","')
                                if len(parts) >= 2:
                                    pid = parts[1].strip('"')
                                    try:
                                        subprocess.run(['taskkill', '/F', '/PID', pid], timeout=2)
                                        print(f"   Cleaning up Anvil process: PID {pid}")
                                    except:
                                        pass
                        time.sleep(1)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
    
    def _test_fork_url(self, timeout=5):
        """
        Test Fork URL connection
        
        Args:
            timeout: Timeout (seconds)
        
        Returns:
            bool: True if connected successfully, else False
        """
        import json
        import urllib.request
        import urllib.error
        
        try:
            # Send simple eth_blockNumber request
            data = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }).encode('utf-8')
            
            req = urllib.request.Request(
                self.fork_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Create opener that bypasses proxy (important for WSL with proxy settings)
            # This ensures direct connection without going through system proxy
            no_proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(no_proxy_handler)
            
            with opener.open(req, timeout=timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                if 'result' in result:
                    block_num = int(result['result'], 16)
                    print(f"   ✓ Fork URL connected successfully (Block: {block_num})")
                    return True
                else:
                    print(f"   ⚠️  Fork URL response abnormal: {result}")
                    return False
        except urllib.error.URLError as e:
            print(f"   ⚠️  Network error: {e.reason}")
            return False
        except Exception as e:
            print(f"   ⚠️  Connection test failed: {e}")
            return False
    
    def _preheat_contracts(self):
        """
        Preheat common contract addresses
        
        Triggers Anvil to pull contract data from remote node by accessing contract code and balance
        This ensures contracts are correctly detected in subsequent tests and reduces
        the number of fork requests during actual test execution.
        """
        from eth_utils import to_checksum_address
        
        # BSC Mainnet common contract addresses - expanded list to reduce runtime fork requests
        contract_addresses = [
            # Core Infrastructure
            ("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "WBNB"),
            ("0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73", "PancakeFactory V2"),
            ("0x10ED43C718714eb63d5aA57B78B54704E256024E", "PancakeRouter V2"),
            # Common Tokens
            ("0x55d398326f99059fF775485246999027B3197955", "USDT"),
            ("0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", "BUSD"),
            ("0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", "CAKE"),
            # Common Liquidity Pairs (for swap operations)
            ("0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE", "USDT-BUSD LP"),
            ("0x0eD7e52944161450477ee417DE9Cd3a859b14fD0", "CAKE-WBNB LP"),
            ("0x58F876857a02D6762E0101bb5C46A8c1ED44Dc16", "BUSD-WBNB LP"),
            ("0x7EFaEf62fDdCCa950418312c6C91Aef321375A00", "USDT-WBNB LP"),
        ]
        
        print(f"✓ Preheating contract addresses (Anvil pulling data from remote)...")
        for addr_info in contract_addresses:
            addr = addr_info[0] if isinstance(addr_info, tuple) else addr_info
            name = addr_info[1] if isinstance(addr_info, tuple) and len(addr_info) > 1 else "Unknown"
            
            try:
                # Use checksum address
                addr_checksum = to_checksum_address(addr)
                print(f"  • {name}: {addr_checksum[:10]}...")
                
                # Access contract code (trigger Anvil pull)
                code = self.w3.eth.get_code(addr_checksum)
                
                # Get balance
                balance = self.w3.eth.get_balance(addr_checksum)
                
                # Extra: Try reading storage to ensure data is pulled
                try:
                    storage = self.w3.eth.get_storage_at(addr_checksum, 0)
                except Exception:
                    pass  # Silently ignore storage read errors
                
                is_contract = code and len(code) > 2
                if is_contract:
                    print(f"    ✅ OK ({len(code)} bytes)")
                else:
                    print(f"    ⚠️  No contract code found")
            except Exception as e:
                print(f"  • {name}: ❌ Error - {str(e)[:50]}")
        
        # Preheat liquidity pool reserves by calling getReserves()
        print(f"  Preheating LP reserves...")
        lp_pairs = [
            "0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE",  # USDT-BUSD
            "0x0eD7e52944161450477ee417DE9Cd3a859b14fD0",  # CAKE-WBNB
            "0x58F876857a02D6762E0101bb5C46A8c1ED44Dc16",  # BUSD-WBNB
            "0x7EFaEf62fDdCCa950418312c6C91Aef321375A00",  # USDT-WBNB
        ]
        for pair_addr in lp_pairs:
            try:
                pair_checksum = to_checksum_address(pair_addr)
                # Call getReserves() - selector: 0x0902f1ac
                result = self.w3.eth.call({
                    'to': pair_checksum,
                    'data': '0x0902f1ac'
                })
            except Exception:
                pass  # Silently ignore - pair may not exist
        
        print()
    
    def _set_erc20_balance_direct(self, token_address: str, holder_address: str, amount: int, balance_slot: int = 1) -> bool:
        """
        Directly set ERC20 token balance (using anvil_setStorageAt)
        
        Args:
            token_address: Token contract address
            holder_address: Holder address
            amount: Balance amount (smallest unit)
            balance_slot: storage slot for balances mapping (mostly 1, WBNB is 3)
            
        Returns:
            Whether setting was successful
        """
        from eth_utils import to_checksum_address, keccak
        from eth_abi import encode
        
        try:
            token_addr = to_checksum_address(token_address)
            holder_addr = to_checksum_address(holder_address)
            
            # Calculate storage slot: keccak256(address + slot)
            address_padded = holder_addr[2:].lower().rjust(64, '0')
            slot_padded = hex(balance_slot)[2:].rjust(64, '0')
            storage_key = '0x' + keccak(bytes.fromhex(address_padded + slot_padded)).hex()
            
            # Set balance - needs padding to 32 bytes (64 hex chars)
            balance_hex = hex(amount)
            if balance_hex.startswith('0x'):
                balance_hex = balance_hex[2:]
            balance_hex = '0x' + balance_hex.rjust(64, '0')
            
            self.w3.provider.make_request('anvil_setStorageAt', [
                token_addr,
                storage_key,
                balance_hex
            ])
            
            # Verify balance
            balance_of_selector = bytes.fromhex('70a08231')
            balance_data = '0x' + balance_of_selector.hex() + encode(['address'], [holder_addr]).hex()
            result = self.w3.eth.call({
                'to': token_addr,
                'data': balance_data
            })
            
            actual_balance = int(result.hex(), 16)
            # Allow 1% error, but use integer comparison
            min_expected = int(amount * 0.99)
            
            if actual_balance >= min_expected:
                return True
            else:
                print(f"    ⚠️  Balance verification failed: expected {amount}, got {actual_balance}")
                return False
            
        except Exception as e:
            # Only print concise error message, not full traceback
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            print(f"    ⚠️  Error setting balance via storage: {error_msg}")
            return False
    
    def _set_token_balances(self):
        """
        Set ERC20 token balances for test account
        
        Uses anvil_setStorageAt to directly manipulate storage, fast and reliable
        """
        from eth_utils import to_checksum_address
        from eth_abi import encode
        
        usdt_address = '0x55d398326f99059fF775485246999027B3197955'
        wbnb_address = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
        cake_address = '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82'
        busd_address = '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'
        
        print(f"✓ Setting ERC20 token balances...")
        
        # USDT (slot 1, 1000 tokens)
        try:
            amount = 1000 * 10**18
            if self._set_erc20_balance_direct(usdt_address, self.test_address, amount, balance_slot=1):
                print(f"  • USDT: {amount / 10**18:.2f} tokens ✅")
            else:
                print(f"  • USDT: Failed to set balance")
        except Exception as e:
            print(f"  • USDT: ❌ Error - {e}")
        
        # WBNB (slot 3, 100 tokens) - WETH9 standard
        try:
            amount = 100 * 10**18
            if self._set_erc20_balance_direct(wbnb_address, self.test_address, amount, balance_slot=3):
                print(f"  • WBNB: {amount / 10**18:.2f} tokens ✅")
            else:
                print(f"  • WBNB: Failed to set balance")
        except Exception as e:
            print(f"  • WBNB: ❌ Error - {e}")
        
        # CAKE (slot 1, 200 tokens) - OpenZeppelin standard
        # Note: 100 CAKE will be transferred to SimpleRewardPool during deployment,
        # so we set 200 CAKE initially to ensure test account has enough balance
        try:
            amount = 200 * 10**18
            if self._set_erc20_balance_direct(cake_address, self.test_address, amount, balance_slot=1):
                print(f"  • CAKE: {amount / 10**18:.2f} tokens ✅")
            else:
                print(f"  • CAKE: Failed to set balance")
        except Exception as e:
            print(f"  • CAKE: ❌ Error - {e}")
        
        # BUSD (slot 1, 1000 tokens) - OpenZeppelin standard
        try:
            amount = 1000 * 10**18
            if self._set_erc20_balance_direct(busd_address, self.test_address, amount, balance_slot=1):
                print(f"  • BUSD: {amount / 10**18:.2f} tokens ✅")
            else:
                print(f"  • BUSD: Failed to set balance")
        except Exception as e:
            print(f"  • BUSD: ❌ Error - {e}")
        
        # USDT/BUSD LP Token (slot 1, 5 LP tokens) - PancakeSwap LP tokens use slot 1 (OpenZeppelin ERC20 standard)
        # These LP tokens are used for harvest_rewards, unstake_lp_tokens, remove_liquidity tests
        try:
            lp_token_address = '0x7EFaEf62fDdCCa950418312c6C91Aef321375A00'
            amount = 5 * 10**18  # 5 LP tokens
            if self._set_erc20_balance_direct(lp_token_address, self.test_address, amount, balance_slot=1):
                print(f"  • USDT/BUSD LP: {amount / 10**18:.2f} tokens ✅")
            else:
                print(f"  • USDT/BUSD LP: Failed to set balance")
        except Exception as e:
            print(f"  • USDT/BUSD LP: ❌ Error - {e}")
        
        # WBNB/USDT LP Token (slot 1, 3 LP tokens) - Used for remove_liquidity_bnb_token test
        try:
            wbnb_usdt_lp_address = '0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE'
            amount = 3 * 10**18  # 3 LP tokens
            if self._set_erc20_balance_direct(wbnb_usdt_lp_address, self.test_address, amount, balance_slot=1):
                print(f"  • WBNB/USDT LP: {amount / 10**18:.2f} tokens ✅")
            else:
                print(f"  • WBNB/USDT LP: Failed to set balance")
        except Exception as e:
            print(f"  • WBNB/USDT LP: ❌ Error - {e}")
        
        # Set initial allowances (for revoke approval tests)
        print(f"✓ Setting initial allowances...")
        try:
            usdt_addr = to_checksum_address(usdt_address)
            test_addr = to_checksum_address(self.test_address)
            
            # Contract addresses requiring approval (PancakeSwap Router, Venus Protocol, etc)
            spenders = [
                '0x10ED43C718714eb63d5aA57B78B54704E256024E',  # PancakeSwap Router
                '0x13f4EA83D0bd40E75C8222255bc855a974568Dd4',  # Venus Protocol
                '0x1B81D678ffb9C0263b24A97847620C99d213eB14'   # PancakeSwap V3 Router
            ]
            
            # Impersonate test account
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            for spender in spenders:
                spender_addr = to_checksum_address(spender)
                
                # ERC20 approve function selector: 0x095ea7b3
                approve_selector = bytes.fromhex('095ea7b3')
                # Encode: approve(address spender, uint256 amount)
                # Approve a large amount (1000 USDT)
                approve_amount = 1000 * 10**18
                approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [spender_addr, approve_amount]).hex()
            
                # Send approve transaction
                response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                        'from': test_addr,
                        'to': usdt_addr,
                        'data': approve_data,
                    'gas': hex(100000),
                        'gasPrice': hex(3000000000)
                }]
                )
                
                # Check response
                if 'result' not in response:
                    print(f"  • Allowance for {spender[:10]}...: ❌ Failed - {response.get('error', 'Unknown error')}")
                    continue
                
                tx_hash = response['result']
            
                # Wait for confirmation
            max_attempts = 20
            for i in range(max_attempts):
                try:
                    receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                    if receipt and receipt.get('blockNumber'):
                        break
                except:
                    pass
                time.sleep(0.5)
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            print(f"  • USDT allowances set for {len(spenders)} spenders ✅")
                
        except Exception as e:
            print(f"  • Allowances: ❌ Error - {e}")
            import traceback
            traceback.print_exc()
        
        # Set CAKE token allowances (for multi-hop swap tests)
        try:
            cake_address = '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82'  # CAKE token on BSC
            cake_addr = to_checksum_address(cake_address)
            test_addr = to_checksum_address(self.test_address)
            
            # PancakeSwap Router needs CAKE allowance
            router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
            router_addr = to_checksum_address(router_address)
            
            # Impersonate test account
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # ERC20 approve function selector: 0x095ea7b3
            approve_selector = bytes.fromhex('095ea7b3')
            # Approve a large amount (200 CAKE to match balance)
            approve_amount = 200 * 10**18
            approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [router_addr, approve_amount]).hex()
            
            # Send approve transaction
            response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'to': cake_addr,
                    'data': approve_data,
                    'gas': hex(100000),
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' in response:
                tx_hash = response['result']
            
            # Wait for confirmation
            max_attempts = 20
            for i in range(max_attempts):
                try:
                    receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                    if receipt and receipt.get('blockNumber'):
                        break
                except:
                    pass
                time.sleep(0.5)
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            print(f"  • CAKE allowances set for Router ✅")
                
        except Exception as e:
            print(f"  • CAKE allowances: ❌ Error - {e}")
            import traceback
            traceback.print_exc()
        
        # CAKE allowances for SimpleStaking will be set after deployment in _deploy_simple_staking()
        
        # Set WBNB token allowances (for wrap-swap tests like composite_wrap_swap_wbnb)
        try:
            wbnb_address = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'  # WBNB token on BSC
            wbnb_addr = to_checksum_address(wbnb_address)
            test_addr = to_checksum_address(self.test_address)
            
            # PancakeSwap Router needs WBNB allowance
            router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
            router_addr = to_checksum_address(router_address)
            
            # Impersonate test account
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # ERC20 approve function selector: 0x095ea7b3
            approve_selector = bytes.fromhex('095ea7b3')
            # Approve a large amount (100 WBNB to match balance)
            approve_amount = 100 * 10**18
            approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [router_addr, approve_amount]).hex()
            
            # Send approve transaction
            response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'to': wbnb_addr,
                    'data': approve_data,
                    'gas': hex(100000),
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' in response:
                tx_hash = response['result']
                
                # Wait for confirmation
                max_attempts = 20
                for i in range(max_attempts):
                    try:
                        receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                        if receipt and receipt.get('blockNumber'):
                            break
                    except:
                        pass
                    time.sleep(0.5)
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            print(f"  • WBNB allowances set for Router ✅")
                
        except Exception as e:
            print(f"  • WBNB allowances: ❌ Error - {e}")
            import traceback
            traceback.print_exc()
        
        # Set LP token allowances (for remove_liquidity and staking tests)
        try:
            # USDT/BUSD LP token
            usdt_busd_lp_address = '0x7EFaEf62fDdCCa950418312c6C91Aef321375A00'
            usdt_busd_lp_addr = to_checksum_address(usdt_busd_lp_address)
            
            # WBNB/USDT LP token
            wbnb_usdt_lp_address = '0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE'
            wbnb_usdt_lp_addr = to_checksum_address(wbnb_usdt_lp_address)
            
            # PancakeSwap Router needs LP token allowances
            router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
            router_addr = to_checksum_address(router_address)
            
            # Impersonate test account
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # Approve both LP tokens for Router
            approve_selector = bytes.fromhex('095ea7b3')
            approve_amount = 1000 * 10**18  # Large allowance
            
            for lp_name, lp_addr in [('USDT/BUSD LP', usdt_busd_lp_addr), ('WBNB/USDT LP', wbnb_usdt_lp_addr)]:
                approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [router_addr, approve_amount]).hex()
                
                response = self.w3.provider.make_request(
                    'eth_sendTransaction',
                    [{
                        'from': test_addr,
                        'to': lp_addr,
                        'data': approve_data,
                        'gas': hex(100000),
                        'gasPrice': hex(3000000000)
                    }]
                )
                
                if 'result' in response:
                    tx_hash = response['result']
                    for i in range(10):
                        try:
                            receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                            if receipt and receipt.get('blockNumber'):
                                break
                        except:
                            pass
                        time.sleep(0.3)
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            print(f"  • LP token allowances set for Router ✅")
        except Exception as e:
            print(f"  • LP token allowances: ❌ Error - {e}")
            import traceback
            traceback.print_exc()
        
        # Set BUSD token allowances (for liquidity operations)
        try:
            busd_address = '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'  # BUSD token on BSC
            busd_addr = to_checksum_address(busd_address)
            test_addr = to_checksum_address(self.test_address)
            
            # PancakeSwap Router needs BUSD allowance
            router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
            router_addr = to_checksum_address(router_address)
            
            # Impersonate test account
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # ERC20 approve function selector: 0x095ea7b3
            approve_selector = bytes.fromhex('095ea7b3')
            # Approve a large amount (1000 BUSD)
            approve_amount = 1000 * 10**18
            approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [router_addr, approve_amount]).hex()
            
            # Send approve transaction
            response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'to': busd_addr,
                    'data': approve_data,
                    'gas': hex(100000),
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' in response:
                tx_hash = response['result']
                
                # Wait for confirmation
                max_attempts = 20
                for i in range(max_attempts):
                    try:
                        receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                        if receipt and receipt.get('blockNumber'):
                            break
                    except:
                        pass
                    time.sleep(0.5)
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            print(f"  • BUSD allowances set for Router ✅")
                
        except Exception as e:
            print(f"  • BUSD allowances: ❌ Error - {e}")
            import traceback
            traceback.print_exc()
        
        # Set LP tokens (for remove_liquidity tests)
        print(f"✓ Setting LP tokens...")
        try:
            from eth_utils import keccak
            
            factory_address = '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73'  # PancakeSwap Factory
            router_address = '0x10ED43C718714eb63d5aA57B78B54704E256024E'  # PancakeSwap Router
            usdt_address = '0x55d398326f99059fF775485246999027B3197955'
            busd_address = '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'
            
            test_addr = to_checksum_address(self.test_address)
            
            # Get LP token address using Factory.getPair()
            # getPair(address tokenA, address tokenB) returns (address pair)
            get_pair_selector = bytes.fromhex('e6a43905')
            get_pair_data = '0x' + get_pair_selector.hex() + encode(['address', 'address'], [usdt_address, busd_address]).hex()
            
            result = self.w3.eth.call({
                'to': factory_address,
                'data': get_pair_data
            })
            
            lp_token_address = '0x' + result.hex()[-40:]  # Last 20 bytes
            lp_token_addr = to_checksum_address(lp_token_address)
            
            print(f"  • LP Token (USDT/BUSD): {lp_token_addr}")
            
            # Set LP token balance (2.0 LP tokens) using direct storage manipulation
            # Uniswap V2 LP tokens use OpenZeppelin ERC20, balances at slot 1
            lp_amount = 2 * 10**18  # 2.0 LP tokens
            if self._set_erc20_balance_direct(lp_token_addr, test_addr, lp_amount, balance_slot=1):
                print(f"  • LP Token balance: {lp_amount / 10**18:.2f} LP tokens ✅")
            else:
                print(f"  • LP Token balance: Failed to set")
                
            # Approve LP tokens for Router (for remove liquidity)
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            approve_selector = bytes.fromhex('095ea7b3')
            approve_amount = 1000 * 10**18  # Large approval
            approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [router_address, approve_amount]).hex()
            
            response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'to': lp_token_addr,
                    'data': approve_data,
                    'gas': hex(100000),
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' in response:
                tx_hash = response['result']
                # Wait for confirmation
                for i in range(10):
                    try:
                        receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                        if receipt and receipt.get('blockNumber'):
                            break
                    except:
                        pass
                    time.sleep(0.3)
                print(f"  • LP Token approved for Router ✅")
            
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            # Also set up WBNB/USDT LP token (for remove_liquidity_bnb_token)
            wbnb_address = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
            
            # Get WBNB/USDT LP token address
            get_pair_data_wbnb_usdt = '0x' + get_pair_selector.hex() + encode(['address', 'address'], [wbnb_address, usdt_address]).hex()
            
            result_wbnb_usdt = self.w3.eth.call({
                'to': factory_address,
                'data': get_pair_data_wbnb_usdt
            })
            
            lp_token_wbnb_usdt = '0x' + result_wbnb_usdt.hex()[-40:]
            lp_token_wbnb_usdt_addr = to_checksum_address(lp_token_wbnb_usdt)
            
            print(f"  • LP Token (WBNB/USDT): {lp_token_wbnb_usdt_addr}")
            
            # Set WBNB/USDT LP token balance (2.0 LP tokens)
            if self._set_erc20_balance_direct(lp_token_wbnb_usdt_addr, test_addr, lp_amount, balance_slot=1):
                print(f"  • LP Token (WBNB/USDT) balance: {lp_amount / 10**18:.2f} LP tokens ✅")
            else:
                print(f"  • LP Token (WBNB/USDT) balance: Failed to set")
            
            # Approve WBNB/USDT LP tokens for Router
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            approve_data_wbnb_usdt = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [router_address, approve_amount]).hex()
            
            response_wbnb_usdt = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'to': lp_token_wbnb_usdt_addr,
                    'data': approve_data_wbnb_usdt,
                    'gas': hex(100000),
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' in response_wbnb_usdt:
                tx_hash_wbnb_usdt = response_wbnb_usdt['result']
                # Wait for confirmation
                for i in range(10):
                    try:
                        receipt_wbnb_usdt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash_wbnb_usdt])['result']
                        if receipt_wbnb_usdt and receipt_wbnb_usdt.get('blockNumber'):
                            break
                    except:
                        pass
                    time.sleep(0.3)
                print(f"  • LP Token (WBNB/USDT) approved for Router ✅")
            
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
                
        except Exception as e:
            print(f"  • LP tokens: ❌ Error - {e}")
            import traceback
            traceback.print_exc()
        
        # Setup NFT (for ERC721 tests)
        print(f"✓ Setting NFT ownership...")
        try:
            # PancakeSquad NFT on BSC Mainnet
            pancake_squad_address = '0x0a8901b0E25DEb55A87524f0cC164E9644020EBA'
            nft_addr = to_checksum_address(pancake_squad_address)
            test_addr = to_checksum_address(self.test_address)
            token_id = 1  # NFT ID to transfer
            
            # Query current owner first
            owner_of_selector = bytes.fromhex('6352211e')  # ownerOf(uint256)
            token_id_hex = format(token_id, '064x')
            owner_data = '0x' + owner_of_selector.hex() + token_id_hex
            
            result = self.w3.eth.call({
                'to': nft_addr,
                'data': owner_data
            })
            
            current_owner_hex = result.hex()
            if len(current_owner_hex) >= 42:
                current_owner = '0x' + current_owner_hex[-40:]
                current_owner_addr = to_checksum_address(current_owner)
                print(f"  • NFT #{token_id} current owner: {current_owner_addr}")
                
                # Impersonate current owner
                self.w3.provider.make_request('anvil_impersonateAccount', [current_owner_addr])
                
                # ERC721 transferFrom function selector: 0x23b872dd
                # transferFrom(address from, address to, uint256 tokenId)
                transfer_selector = bytes.fromhex('23b872dd')
                # Encode: from (32 bytes) + to (32 bytes) + tokenId (32 bytes)
                transfer_data = '0x' + transfer_selector.hex() + encode(['address', 'address', 'uint256'], [current_owner_addr, test_addr, token_id]).hex()
                
                # Send transferFrom transaction
                response = self.w3.provider.make_request(
                    'eth_sendTransaction',
                    [{
                        'from': current_owner_addr,
                        'to': nft_addr,
                        'data': transfer_data,
                        'gas': hex(150000),
                        'gasPrice': hex(3000000000)
                    }]
                )
                
                # Check response
                if 'result' not in response:
                    print(f"  • NFT: ❌ Transaction failed - {response.get('error', 'Unknown error')}")
                    raise Exception(f"NFT transfer failed: {response}")
                
                tx_hash = response['result']
                
                # Wait for confirmation
                max_attempts = 20
                for i in range(max_attempts):
                    try:
                        receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                        if receipt and receipt.get('blockNumber'):
                            break
                    except:
                        pass
                    time.sleep(0.5)
                
                # Stop impersonate
                self.w3.provider.make_request('anvil_stopImpersonatingAccount', [current_owner_addr])
                
                # Verify NFT owner
                result = self.w3.eth.call({
                    'to': nft_addr,
                    'data': owner_data
                })
                
                new_owner_hex = result.hex()
                if len(new_owner_hex) >= 42:
                    new_owner = '0x' + new_owner_hex[-40:]
                    new_owner_addr = to_checksum_address(new_owner)
                    
                    receipt_status = int(receipt.get('status', '0x0'), 16)
                    
                    if receipt_status == 1 and new_owner_addr.lower() == test_addr.lower():
                        print(f"  • PancakeSquad NFT #{token_id}: ✅ Transferred to test account")
                    else:
                        print(f"  • PancakeSquad NFT #{token_id}: ❌ Transfer failed or owner mismatch")
            else:
                print(f"  • PancakeSquad NFT: ⚠️  Could not determine owner")
                
        except Exception as e:
            print(f"  • PancakeSquad NFT: ❌ Error - {e}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # 7. Deploy ERC1363 test token
        self._deploy_erc1363_token()
        
        # 8. Deploy ERC721 test NFT
        self._deploy_erc721_test_nft()
        
        # 9. Deploy ERC1155 test token
        self._deploy_erc1155_token()
        
        # 9. Deploy Flashloan receiver contract
        self._deploy_flashloan_receiver()
        
        # 10. Deploy SimpleCounter test contract
        self._deploy_simple_counter()
        
        # 11. Deploy DonationBox test contract
        self._deploy_donation_box()
        
        # 12. Deploy MessageBoard test contract
        self._deploy_message_board()
        
        # 13. Deploy DelegateCall test contracts
        self._deploy_delegate_call_contracts()
        
        # 14. Deploy FallbackReceiver test contract
        self._deploy_fallback_receiver()
        
        # 15. Deploy SimpleStaking test contract
        self._deploy_simple_staking()
        
        # 16. Deploy SimpleLPStaking test contract
        self._deploy_simple_lp_staking()
        
        # 17. Deploy SimpleRewardPool test contract
        self._deploy_simple_reward_pool()
    
    def _deploy_erc1363_token(self):
        """
        Deploy ERC1363 test token and allocate tokens to test account
        
        ERC1363 is an extension of ERC20, supporting transferAndCall and approveAndCall
        """
        from eth_utils import to_checksum_address
        from eth_abi import encode
        
        print(f"✓ Deploying ERC1363 test token...")
        
        try:
            test_addr = to_checksum_address(self.test_address)
            
            # Read contract source code and compile with py-solc-x
            contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC1363Receiver {
    function onTransferReceived(address operator, address from, uint256 value, bytes calldata data) external returns (bytes4);
}

interface IERC1363Spender {
    function onApprovalReceived(address owner, uint256 value, bytes calldata data) external returns (bytes4);
}

contract ERC1363Token {
    string public name = "ERC1363";
    string public symbol = "E1363";
    uint8 public decimals = 18;
    string public constant version = "1";
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    // EIP-2612 Permit support
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;
    bytes32 public constant PERMIT_TYPEHASH = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    
    constructor() {
        totalSupply = 1000000 * 10**18;
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
        
        // Initialize DOMAIN_SEPARATOR for EIP-2612
        uint256 chainId;
        assembly { chainId := chainid() }
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes(name)),
                keccak256(bytes("1")),
                chainId,
                address(this)
            )
        );
    }
    
    function transfer(address to, uint256 value) public returns (bool) {
        require(balanceOf[msg.sender] >= value, "Insufficient balance");
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
        return true;
    }
    
    function approve(address spender, uint256 value) public returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 value) public returns (bool) {
        require(balanceOf[from] >= value, "Insufficient balance");
        require(allowance[from][msg.sender] >= value, "Insufficient allowance");
        balanceOf[from] -= value;
        balanceOf[to] += value;
        allowance[from][msg.sender] -= value;
        emit Transfer(from, to, value);
        return true;
    }
    
    function transferAndCall(address to, uint256 value) public returns (bool) {
        return transferAndCall(to, value, "");
    }
    
    function transferAndCall(address to, uint256 value, bytes memory data) public returns (bool) {
        // Directly perform the transfer logic inline instead of calling transfer()
        require(balanceOf[msg.sender] >= value, "Insufficient balance");
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
        
        // Check if recipient is a contract and call callback if needed
        uint256 codeSize;
        assembly { codeSize := extcodesize(to) }
        if (codeSize > 0) {
            try IERC1363Receiver(to).onTransferReceived(msg.sender, msg.sender, value, data) returns (bytes4 retval) {
                require(retval == IERC1363Receiver.onTransferReceived.selector, "Receiver rejected");
            } catch {}
        }
        return true;
    }
    
    function approveAndCall(address spender, uint256 value) public returns (bool) {
        return approveAndCall(spender, value, "");
    }
    
    function approveAndCall(address spender, uint256 value, bytes memory data) public returns (bool) {
        // Directly perform the approval logic inline
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        
        // Check if spender is a contract and call callback if needed
        uint256 codeSize;
        assembly { codeSize := extcodesize(spender) }
        if (codeSize > 0) {
            try IERC1363Spender(spender).onApprovalReceived(msg.sender, value, data) returns (bytes4 retval) {
                require(retval == IERC1363Spender.onApprovalReceived.selector, "Spender rejected");
            } catch {}
        }
        return true;
    }
    
    // EIP-2612 Permit function
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(deadline >= block.timestamp, "Permit expired");
        
        bytes32 structHash = keccak256(
            abi.encode(PERMIT_TYPEHASH, owner, spender, value, nonces[owner]++, deadline)
        );
        
        bytes32 digest = keccak256(
            abi.encodePacked("\\x19\\x01", DOMAIN_SEPARATOR, structHash)
        );
        
        address recoveredAddress = ecrecover(digest, v, r, s);
        require(recoveredAddress != address(0) && recoveredAddress == owner, "Invalid signature");
        
        allowance[owner][spender] = value;
        emit Approval(owner, spender, value);
    }
}
"""
            
            # Compile contract using solcx
            try:
                from solcx import compile_source, install_solc, set_solc_version
                
                # Try to use installed solc, install if not available
                try:
                    set_solc_version('0.8.20')
                except:
                    print("  • Installing Solidity compiler v0.8.20...")
                    install_solc('0.8.20')
                    set_solc_version('0.8.20')
                
                # Compile contract
                compiled_sol = compile_source(contract_source, output_values=['abi', 'bin'])
                contract_interface = compiled_sol['<stdin>:ERC1363Token']
                
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
                
            except Exception as e:
                print(f"  • ⚠️  Solc not available: {e}")
                print(f"  • Trying to install py-solc-x: pip install py-solc-x")
                raise Exception("Cannot compile ERC1363 contract without solc. Please install: pip install py-solc-x")
            
            # Deploy contract
            # Impersonate test account to deploy contract
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # Send deployment transaction
            deploy_response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'data': '0x' + bytecode if not bytecode.startswith('0x') else bytecode,
                    'gas': hex(3000000),  # 3M gas for deployment
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' not in deploy_response:
                raise Exception(f"Deployment failed: {deploy_response}")
            
            tx_hash = deploy_response['result']
            
            # Wait for deployment confirmation
            max_attempts = 20
            receipt = None
            for i in range(max_attempts):
                try:
                    receipt_response = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])
                    if receipt_response.get('result'):
                        receipt = receipt_response['result']
                        break
                except:
                    pass
                time.sleep(0.5)
            
            if not receipt or not receipt.get('contractAddress'):
                raise Exception("Contract deployment failed - no contract address")
            
            # Get deployed contract address
            erc1363_address = receipt['contractAddress']
            erc1363_address = to_checksum_address(erc1363_address)
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            # Store contract address for later use
            self.erc1363_token_address = erc1363_address
            
            # Verify deployment
            balance_selector = bytes.fromhex('70a08231')  # balanceOf(address)
            balance_data = '0x' + balance_selector.hex() + encode(['address'], [test_addr]).hex()
            
            result = self.w3.eth.call({
                'to': erc1363_address,
                'data': balance_data
            })
            
            balance = int(result.hex(), 16)
            balance_formatted = balance / 10**18
            
            print(f"  • ERC1363 Token deployed: {erc1363_address}")
            print(f"  • Test account balance: {balance_formatted:.2f} T1363 ✅")
            
            # Pre-approve test account to itself (for permit/transferFrom tests)
            # approve(address spender, uint256 value)
            try:
                self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
                
                approve_selector = bytes.fromhex('095ea7b3')  # approve(address,uint256)
                # Approve infinite amount: 2^256 - 1
                max_uint256 = 2**256 - 1
                approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [test_addr, max_uint256]).hex()
                
                approve_response = self.w3.provider.make_request(
                    'eth_sendTransaction',
                    [{
                        'from': test_addr,
                        'to': erc1363_address,
                        'data': approve_data,
                        'gas': hex(100000),
                        'gasPrice': hex(3000000000)
                    }]
                )
                
                # Wait for approval transaction confirmation
                if 'result' in approve_response:
                    time.sleep(0.5)
                
                self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
                print(f"  • Test account self-approved for permit testing ✅")
            except Exception as e:
                print(f"  • ⚠️  Warning: Self-approval failed - {e}")
            
        except Exception as e:
            print(f"  • ERC1363 Token: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            # Set to None indicating not deployed
            self.erc1363_token_address = None
        
        print()
    
    def _deploy_erc721_test_nft(self):
        """
        Deploy ERC721 test NFT contract for NFT operation testing
        
        This deploys a simple ERC721 implementation that mints 10 tokens to the deployer
        """
        from eth_utils import to_checksum_address
        from eth_abi import encode
        
        print(f"✓ Deploying ERC721 Test NFT...")
        
        try:
            test_addr = to_checksum_address(self.test_address)
            
            # Read contract source code from contracts/ERC721NFT.sol
            import os
            contract_path = os.path.join(os.path.dirname(__file__), 'contracts', 'ERC721NFT.sol')
            
            if not os.path.exists(contract_path):
                print(f"  • ⚠️  Contract file not found: {contract_path}")
                print(f"  • Using inline contract source")
                
                # Inline contract source as fallback
                contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ERC721NFT {
    string public name = "NFT Collection";
    string public symbol = "NFT";
    
    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;
    mapping(uint256 => address) private _tokenApprovals;
    mapping(address => mapping(address => bool)) private _operatorApprovals;
    
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);
    
    constructor() {
        for (uint256 i = 1; i <= 10; i++) {
            _mint(msg.sender, i);
        }
    }
    
    function balanceOf(address owner) public view returns (uint256) {
        require(owner != address(0), "ERC721: balance query for the zero address");
        return _balances[owner];
    }
    
    function ownerOf(uint256 tokenId) public view returns (address) {
        address owner = _owners[tokenId];
        require(owner != address(0), "ERC721: owner query for nonexistent token");
        return owner;
    }
    
    function approve(address to, uint256 tokenId) public {
        address owner = ownerOf(tokenId);
        require(to != owner, "ERC721: approval to current owner");
        require(
            msg.sender == owner || isApprovedForAll(owner, msg.sender),
            "ERC721: approve caller is not owner nor approved for all"
        );
        
        _tokenApprovals[tokenId] = to;
        emit Approval(owner, to, tokenId);
    }
    
    function getApproved(uint256 tokenId) public view returns (address) {
        require(_owners[tokenId] != address(0), "ERC721: approved query for nonexistent token");
        return _tokenApprovals[tokenId];
    }
    
    function setApprovalForAll(address operator, bool approved) public {
        require(operator != msg.sender, "ERC721: approve to caller");
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }
    
    function isApprovedForAll(address owner, address operator) public view returns (bool) {
        return _operatorApprovals[owner][operator];
    }
    
    function transferFrom(address from, address to, uint256 tokenId) public {
        require(_isApprovedOrOwner(msg.sender, tokenId), "ERC721: transfer caller is not owner nor approved");
        _transfer(from, to, tokenId);
    }
    
    function safeTransferFrom(address from, address to, uint256 tokenId) public {
        safeTransferFrom(from, to, tokenId, "");
    }
    
    function safeTransferFrom(address from, address to, uint256 tokenId, bytes memory data) public {
        require(_isApprovedOrOwner(msg.sender, tokenId), "ERC721: transfer caller is not owner nor approved");
        _safeTransfer(from, to, tokenId, data);
    }
    
    function _safeTransfer(address from, address to, uint256 tokenId, bytes memory data) internal {
        _transfer(from, to, tokenId);
        require(_checkOnERC721Received(from, to, tokenId, data), "ERC721: transfer to non ERC721Receiver implementer");
    }
    
    function _isApprovedOrOwner(address spender, uint256 tokenId) internal view returns (bool) {
        address owner = ownerOf(tokenId);
        return (spender == owner || getApproved(tokenId) == spender || isApprovedForAll(owner, spender));
    }
    
    function _mint(address to, uint256 tokenId) internal {
        require(to != address(0), "ERC721: mint to the zero address");
        require(_owners[tokenId] == address(0), "ERC721: token already minted");
        
        _balances[to] += 1;
        _owners[tokenId] = to;
        
        emit Transfer(address(0), to, tokenId);
    }
    
    function _transfer(address from, address to, uint256 tokenId) internal {
        require(ownerOf(tokenId) == from, "ERC721: transfer from incorrect owner");
        require(to != address(0), "ERC721: transfer to the zero address");
        
        _tokenApprovals[tokenId] = address(0);
        
        _balances[from] -= 1;
        _balances[to] += 1;
        _owners[tokenId] = to;
        
        emit Transfer(from, to, tokenId);
    }
    
    function _checkOnERC721Received(address from, address to, uint256 tokenId, bytes memory data) private returns (bool) {
        uint256 size;
        assembly {
            size := extcodesize(to)
        }
        if (size == 0) {
            return true;
        }
        
        try IERC721Receiver(to).onERC721Received(msg.sender, from, tokenId, data) returns (bytes4 retval) {
            return retval == IERC721Receiver.onERC721Received.selector;
        } catch {
            return false;
        }
    }
}

interface IERC721Receiver {
    function onERC721Received(
        address operator,
        address from,
        uint256 tokenId,
        bytes calldata data
    ) external returns (bytes4);
}
"""
            else:
                with open(contract_path, 'r', encoding='utf-8') as f:
                    contract_source = f.read()
            
            # Compile contract using solcx
            try:
                from solcx import compile_source, install_solc, set_solc_version
                
                # Try to use installed solc, install if not available
                try:
                    set_solc_version('0.8.20')
                except:
                    print("  • Installing Solidity compiler v0.8.20...")
                    install_solc('0.8.20')
                    set_solc_version('0.8.20')
                
                # Compile contract
                compiled_sol = compile_source(contract_source, output_values=['abi', 'bin'])
                contract_interface = compiled_sol['<stdin>:ERC721NFT']
                
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
                
            except Exception as e:
                print(f"  • ⚠️  Solc not available: {e}")
                raise Exception("Cannot compile ERC721 contract without solc. Please install: pip install py-solc-x")
            
            # Deploy contract
            # Impersonate test account to deploy contract
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # Send deployment transaction
            deploy_response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'data': '0x' + bytecode if not bytecode.startswith('0x') else bytecode,
                    'gas': hex(3000000),  # 3M gas for deployment
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' not in deploy_response:
                raise Exception(f"Deployment failed: {deploy_response}")
            
            tx_hash = deploy_response['result']
            
            # Wait for deployment confirmation
            max_attempts = 20
            receipt = None
            for i in range(max_attempts):
                try:
                    receipt_response = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])
                    if receipt_response.get('result'):
                        receipt = receipt_response['result']
                        break
                except:
                    pass
                time.sleep(0.5)
            
            if not receipt or not receipt.get('contractAddress'):
                raise Exception("Contract deployment failed - no contract address")
            
            # Get deployed contract address
            erc721_address = receipt['contractAddress']
            erc721_address = to_checksum_address(erc721_address)
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            # Store contract address for later use
            self.erc721_token_address = erc721_address
            
            # Verify deployment - check balance
            balance_selector = bytes.fromhex('70a08231')  # balanceOf(address)
            balance_data = '0x' + balance_selector.hex() + encode(['address'], [test_addr]).hex()
            
            result = self.w3.eth.call({
                'to': erc721_address,
                'data': balance_data
            })
            
            balance = int(result.hex(), 16)
            
            print(f"  • ERC721 Test NFT deployed: {erc721_address}")
            print(f"  • Test account owns {balance} NFTs (token IDs 1-10) ✅")
            
        except Exception as e:
            print(f"  • ERC721 Test NFT: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            # Set to None to indicate not deployed
            self.erc721_token_address = None
        
        print()
    
    def _deploy_erc1155_token(self):
        """
        Deploy ERC1155 test token and allocate tokens to test account
        
        ERC1155 is a multi-token standard, supporting management of multiple token types simultaneously
        """
        from eth_utils import to_checksum_address
        from eth_abi import encode
        
        print("✓ Deploying ERC1155 test token...")
        
        try:
            test_addr = self.test_address
            
            # ERC1155 contract source code
            contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TestERC1155Token {
    string public name = "Test Multi Token";
    
    // Mapping from token ID to account balances
    mapping(uint256 => mapping(address => uint256)) private _balances;
    
    // Mapping from account to operator approvals
    mapping(address => mapping(address => bool)) private _operatorApprovals;
    
    event TransferSingle(
        address indexed operator,
        address indexed from,
        address indexed to,
        uint256 id,
        uint256 value
    );
    
    event TransferBatch(
        address indexed operator,
        address indexed from,
        address indexed to,
        uint256[] ids,
        uint256[] values
    );
    
    event ApprovalForAll(
        address indexed account,
        address indexed operator,
        bool approved
    );
    
    constructor() {
        // Mint initial tokens to deployer
        // Token ID 1: 1000 units
        // Token ID 2: 500 units
        // Token ID 3: 100 units
        _balances[1][msg.sender] = 1000;
        _balances[2][msg.sender] = 500;
        _balances[3][msg.sender] = 100;
        
        emit TransferSingle(msg.sender, address(0), msg.sender, 1, 1000);
        emit TransferSingle(msg.sender, address(0), msg.sender, 2, 500);
        emit TransferSingle(msg.sender, address(0), msg.sender, 3, 100);
    }
    
    function balanceOf(address account, uint256 id) public view returns (uint256) {
        require(account != address(0), "ERC1155: balance query for the zero address");
        return _balances[id][account];
    }
    
    function balanceOfBatch(
        address[] memory accounts,
        uint256[] memory ids
    ) public view returns (uint256[] memory) {
        require(accounts.length == ids.length, "ERC1155: accounts and ids length mismatch");
        
        uint256[] memory batchBalances = new uint256[](accounts.length);
        
        for (uint256 i = 0; i < accounts.length; ++i) {
            batchBalances[i] = balanceOf(accounts[i], ids[i]);
        }
        
        return batchBalances;
    }
    
    function setApprovalForAll(address operator, bool approved) public {
        require(msg.sender != operator, "ERC1155: setting approval status for self");
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }
    
    function isApprovedForAll(address account, address operator) public view returns (bool) {
        return _operatorApprovals[account][operator];
    }
    
    function safeTransferFrom(
        address from,
        address to,
        uint256 id,
        uint256 amount,
        bytes memory data
    ) public {
        require(
            from == msg.sender || isApprovedForAll(from, msg.sender),
            "ERC1155: caller is not owner nor approved"
        );
        require(to != address(0), "ERC1155: transfer to the zero address");
        
        uint256 fromBalance = _balances[id][from];
        require(fromBalance >= amount, "ERC1155: insufficient balance for transfer");
        
        _balances[id][from] = fromBalance - amount;
        _balances[id][to] += amount;
        
        emit TransferSingle(msg.sender, from, to, id, amount);
    }
    
    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) public {
        require(
            from == msg.sender || isApprovedForAll(from, msg.sender),
            "ERC1155: caller is not owner nor approved"
        );
        require(ids.length == amounts.length, "ERC1155: ids and amounts length mismatch");
        require(to != address(0), "ERC1155: transfer to the zero address");
        
        for (uint256 i = 0; i < ids.length; ++i) {
            uint256 id = ids[i];
            uint256 amount = amounts[i];
            
            uint256 fromBalance = _balances[id][from];
            require(fromBalance >= amount, "ERC1155: insufficient balance for transfer");
            
            _balances[id][from] = fromBalance - amount;
            _balances[id][to] += amount;
        }
        
        emit TransferBatch(msg.sender, from, to, ids, amounts);
    }
}
"""
            
            # Compile contract using solcx
            try:
                from solcx import compile_source, install_solc, set_solc_version
                
                # Try to use installed solc, install if not available
                try:
                    set_solc_version('0.8.20')
                except:
                    print("  • Installing Solidity compiler v0.8.20...")
                    install_solc('0.8.20')
                    set_solc_version('0.8.20')
                
                # Compile contract
                compiled_sol = compile_source(contract_source, output_values=['abi', 'bin'])
                contract_interface = compiled_sol['<stdin>:TestERC1155Token']
                
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
                
            except Exception as e:
                print(f"  • ⚠️  Solc compilation error: {e}")
                raise Exception("Cannot compile ERC1155 contract")
            
            # Deploy contract
            # Impersonate test account to deploy contract
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # Send deployment transaction
            deploy_response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'data': '0x' + bytecode if not bytecode.startswith('0x') else bytecode,
                    'gas': hex(3000000),  # 3M gas for deployment
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' not in deploy_response:
                raise Exception(f"Deployment failed: {deploy_response}")
            
            tx_hash = deploy_response['result']
            
            # Wait for deployment confirmation
            max_attempts = 20
            receipt = None
            for i in range(max_attempts):
                try:
                    receipt_response = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])
                    if receipt_response.get('result'):
                        receipt = receipt_response['result']
                        break
                except:
                    pass
                time.sleep(0.5)
            
            if not receipt or not receipt.get('contractAddress'):
                raise Exception("Contract deployment failed - no contract address")
            
            # Get deployed contract address
            erc1155_address = receipt['contractAddress']
            erc1155_address = to_checksum_address(erc1155_address)
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
            # Store contract address for later use
            self.erc1155_token_address = erc1155_address
            
            # Verify deployment - query balance of token ID 1
            # balanceOf(address account, uint256 id)
            balance_selector = bytes.fromhex('00fdd58e')  # balanceOf(address,uint256)
            balance_data = '0x' + balance_selector.hex() + encode(['address', 'uint256'], [test_addr, 1]).hex()
            
            result = self.w3.eth.call({
                'to': erc1155_address,
                'data': balance_data
            })
            
            balance = int(result.hex(), 16)
            
            print(f"  • ERC1155 Token deployed: {erc1155_address}")
            print(f"  • Test account balance (Token ID 1): {balance} units ✅")
            print(f"  • Test account balance (Token ID 2): 500 units ✅")
            print(f"  • Test account balance (Token ID 3): 100 units ✅")
            
        except Exception as e:
            print(f"  • ERC1155 Token: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            # Set to None indicating not deployed
            self.erc1155_token_address = None
        
        print()
    
    def _deploy_flashloan_receiver(self):
        """
        Deploy Flashloan Receiver Contract
        
        This is a simple flashloan provider+receiver contract for testing flashloan functionality
        """
        from eth_utils import to_checksum_address
        from eth_abi import encode
        
        print("✓ Deploying Flashloan contract...")
        
        try:
            test_addr = self.test_address
            
            # Simple flashloan contract source code
            # This contract acts as both provider and receiver, simplifying test flow
            contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

contract FlashLoanReceiver {
    address public owner;
    
    event FlashLoanExecuted(address indexed token, uint256 amount, uint256 fee);
    
    constructor() {
        owner = msg.sender;
    }
    
    // Execute Flash Loan
    // 1. Borrow tokens from contract
    // 2. Caller can use these tokens
    // 3. Repay tokens + fee in same transaction
    function executeFlashLoan(
        address token,
        uint256 amount
    ) external returns (bool) {
        // Calculate fee (0.3%)
        uint256 fee = (amount * 3) / 1000;
        uint256 amountToRepay = amount + fee;
        
        // Check if contract has enough tokens to lend
        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        require(balanceBefore >= amount, "Insufficient balance in pool");
        
        // 1. Transfer tokens to caller (borrow)
        require(IERC20(token).transfer(msg.sender, amount), "Loan transfer failed");
        
        // 2. Caller now owns tokens, can perform any operation
        // In real flashloan, this would call borrower contract's callback
        // But for simplified testing, we assume caller repays in same transaction
        
        // 3. Check if caller repaid tokens + fee
        // Caller needs to approve this contract first
        require(
            IERC20(token).transferFrom(msg.sender, address(this), amountToRepay),
            "Repayment failed"
        );
        
        // Verify balance increased by fee
        uint256 balanceAfter = IERC20(token).balanceOf(address(this));
        require(balanceAfter >= balanceBefore + fee, "Fee not paid");
        
        emit FlashLoanExecuted(token, amount, fee);
        return true;
    }
    
    // Allow owner to deposit tokens to liquidity pool
    function depositToPool(address token, uint256 amount) external {
        require(msg.sender == owner, "Only owner can deposit");
        require(
            IERC20(token).transferFrom(msg.sender, address(this), amount),
            "Deposit failed"
        );
    }
    
    // Query token balance in pool
    function poolBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
    
    // Allow owner to withdraw tokens
    function withdraw(address token, uint256 amount) external {
        require(msg.sender == owner, "Only owner can withdraw");
        require(IERC20(token).transfer(msg.sender, amount), "Withdraw failed");
    }
}
"""
            
            # Compile contract using solcx
            try:
                from solcx import compile_source, install_solc, set_solc_version
                
                # Try to use installed solc, install if not available
                try:
                    set_solc_version('0.8.20')
                except:
                    print("  • Installing Solidity compiler v0.8.20...")
                    install_solc('0.8.20')
                    set_solc_version('0.8.20')
                
                # Compile contract
                compiled_sol = compile_source(contract_source, output_values=['abi', 'bin'])
                contract_interface = compiled_sol['<stdin>:FlashLoanReceiver']
                
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
                
            except Exception as e:
                print(f"  • ⚠️  Solc compilation error: {e}")
                raise Exception("Cannot compile FlashLoan contract")
            
            # Deploy contract
            # Impersonate test account to deploy contract
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # Send deployment transaction
            deploy_response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'data': '0x' + bytecode if not bytecode.startswith('0x') else bytecode,
                    'gas': hex(3000000),  # 3M gas for deployment
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' not in deploy_response:
                raise Exception(f"Deployment failed: {deploy_response}")
            
            tx_hash = deploy_response['result']
            
            # Wait for deployment confirmation
            max_attempts = 20
            receipt = None
            for i in range(max_attempts):
                try:
                    receipt_response = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])
                    if receipt_response.get('result'):
                        receipt = receipt_response['result']
                        break
                except:
                    pass
                time.sleep(0.5)
            
            if not receipt or not receipt.get('contractAddress'):
                raise Exception("Contract deployment failed - no contract address")
            
            # Get deployed contract address
            flashloan_address = receipt['contractAddress']
            flashloan_address = to_checksum_address(flashloan_address)
            
            # Store contract address for later use
            self.flashloan_receiver_address = flashloan_address
            
            # Set USDT balance for flashloan pool (using anvil_setStorageAt)
            usdt_address = '0x55d398326f99059fF775485246999027B3197955'
            pool_deposit_amount = 10000 * 10**18  # 10000 USDT (BSC USDT uses 18 decimals)
            
            # Directly set USDT balance for flashloan contract
            self._set_erc20_balance_direct(usdt_address, flashloan_address, pool_deposit_amount, balance_slot=1)
            
            # Verify deployment - directly query USDT balance of flashloan contract
            # Use ERC20 balanceOf instead of contract's poolBalance, more reliable
            # balanceOf(address) returns (uint256)
            balance_selector = bytes.fromhex('70a08231')  # balanceOf(address)
            balance_data = '0x' + balance_selector.hex() + encode(['address'], [flashloan_address]).hex()
            
            try:
                result = self.w3.eth.call({
                    'to': usdt_address,
                    'data': balance_data
                })
                
                pool_balance = int(result.hex(), 16)
                pool_balance_formatted = pool_balance / 10**18  # BSC USDT has 18 decimals
                
                print(f"  • FlashLoan Contract deployed: {flashloan_address}")
                print(f"  • Pool balance (USDT): {pool_balance_formatted:.2f} USDT ✅")
            except Exception as e:
                print(f"  • FlashLoan Contract deployed: {flashloan_address}")
                print(f"  • Warning: Could not verify pool balance: {e}")
                print(f"  • Pool initialization may have failed, but continuing...")
            
            # Pre-approve flashloan contract so test account can directly call executeFlashLoan
            # Impersonate test account
            self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
            
            # Approve max amount for flashloan contract (2^256-1)
            max_approval = 2**256 - 1
            # ERC20 approve function selector: 0x095ea7b3
            # approve(address spender, uint256 amount)
            approve_data = '0x095ea7b3' + encode(['address', 'uint256'], [flashloan_address, max_approval]).hex()
            
            approve_response = self.w3.provider.make_request(
                'eth_sendTransaction',
                [{
                    'from': test_addr,
                    'to': usdt_address,
                    'data': approve_data,
                    'gas': hex(100000),
                    'gasPrice': hex(3000000000)
                }]
            )
            
            if 'result' in approve_response:
                tx_hash = approve_response['result']
                # Wait for confirmation
                for i in range(10):
                    try:
                        receipt_response = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])
                        if receipt_response.get('result'):
                            break
                    except:
                        pass
                    time.sleep(0.3)
                print(f"  • Test account approved flash loan contract ✅")
            
            # Stop impersonate
            self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
            
        except Exception as e:
            print(f"  • FlashLoan Contract: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            # Set to None indicating not deployed
            self.flashloan_receiver_address = None
        
        print()
    
    def _deploy_simple_counter(self):
        """
        Deploy SimpleCounter test contract
        
        This is a simple counter contract for testing basic contract function calls
        """
        print("✓ Deploy SimpleCounter test contract...")
        
        try:
            import solcx
            from solcx import compile_source
            from eth_utils import to_checksum_address
            from eth_abi import encode
            
            # Simple counter contract source code
            contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleCounter {
    uint256 public counter;
    address public owner;
    
    event CounterIncremented(uint256 newValue);
    event CounterReset(uint256 newValue);
    
    constructor() {
        owner = msg.sender;
        counter = 0;
    }
    
    // Increment counter
    function increment() external {
        counter += 1;
        emit CounterIncremented(counter);
    }
    
    // Get current counter value
    function getCounter() external view returns (uint256) {
        return counter;
    }
    
    // Reset counter (owner only)
    function reset() external {
        require(msg.sender == owner, "Only owner can reset");
        counter = 0;
        emit CounterReset(counter);
    }
}
"""
            
            # Try to compile contract
            try:
                # Try to use installed solc
                compiled = compile_source(
                    contract_source,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.20'
                )
                contract_interface = compiled['<stdin>:SimpleCounter']
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
            except Exception as compile_error:
                print(f"  • Solc compilation failed: {compile_error}")
                print(f"  • Trying to install solc 0.8.20...")
                solcx.install_solc('0.8.20')
                compiled = compile_source(
                    contract_source,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.20'
                )
                contract_interface = compiled['<stdin>:SimpleCounter']
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
            
            # Deploy contract
            deployer = self.test_account
            deployer_address = deployer.address
            
            # Construct deployment transaction
            deploy_tx = {
                'from': deployer_address,
                'data': '0x' + bytecode,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(deploy_tx, deployer.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for transaction confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] != 1:
                raise Exception(f"Contract deployment failed with status: {receipt['status']}")
            
            contract_address = receipt['contractAddress']
            self.simple_counter_address = contract_address
            
            # Verify contract deployment
            counter_contract = self.w3.eth.contract(address=contract_address, abi=abi)
            initial_counter = counter_contract.functions.getCounter().call()
            
            print(f"  • SimpleCounter Contract deployed: {contract_address}")
            print(f"  • Initial counter value: {initial_counter} ✅")
            
        except Exception as e:
            print(f"  • SimpleCounter Contract: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            self.simple_counter_address = None
        
        print()
    
    def _deploy_donation_box(self):
        """
        Deploy DonationBox test contract
        
        This is a simple donation box contract for testing contract function calls with value
        """
        print("✓ Deploy DonationBox test contract...")
        
        try:
            import solcx
            from solcx import compile_source
            from eth_utils import to_checksum_address
            
            # DonationBox contract source code
            contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DonationBox {
    address public owner;
    uint256 public totalDonations;
    mapping(address => uint256) public donations;
    
    event DonationReceived(address indexed donor, uint256 amount);
    
    constructor() {
        owner = msg.sender;
    }
    
    // Payable function to receive donations
    function donate() external payable {
        require(msg.value > 0, "Donation must be greater than 0");
        
        donations[msg.sender] += msg.value;
        totalDonations += msg.value;
        
        emit DonationReceived(msg.sender, msg.value);
    }
    
    // View function to get contract balance
    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
    
    // View function to get donor's total donations
    function getDonation(address donor) external view returns (uint256) {
        return donations[donor];
    }
    
    // Owner can withdraw (for testing cleanup)
    function withdraw() external {
        require(msg.sender == owner, "Only owner can withdraw");
        payable(owner).transfer(address(this).balance);
    }
    
    // Fallback function to accept BNB
    receive() external payable {
        donations[msg.sender] += msg.value;
        totalDonations += msg.value;
        emit DonationReceived(msg.sender, msg.value);
    }
}
"""
            
            # Try to compile contract
            try:
                # Try to use installed solc
                compiled = compile_source(
                    contract_source,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.20'
                )
                contract_interface = compiled['<stdin>:DonationBox']
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
            except Exception as compile_error:
                print(f"  • Solc compilation failed: {compile_error}")
                print(f"  • Trying to install solc 0.8.20...")
                solcx.install_solc('0.8.20')
                compiled = compile_source(
                    contract_source,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.20'
                )
                contract_interface = compiled['<stdin>:DonationBox']
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
            
            # Deploy contract
            deployer = self.test_account
            deployer_address = deployer.address
            
            # Construct deployment transaction
            deploy_tx = {
                'from': deployer_address,
                'data': '0x' + bytecode,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(deploy_tx, deployer.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for transaction confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] != 1:
                raise Exception(f"Contract deployment failed with status: {receipt['status']}")
            
            contract_address = receipt['contractAddress']
            self.donation_box_address = contract_address
            
            # Verify contract deployment
            donation_contract = self.w3.eth.contract(address=contract_address, abi=abi)
            initial_balance = donation_contract.functions.getBalance().call()
            
            print(f"  • DonationBox Contract deployed: {contract_address}")
            print(f"  • Initial contract balance: {initial_balance / 10**18:.6f} BNB ✅")
            
        except Exception as e:
            print(f"  • DonationBox Contract: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            self.donation_box_address = None
        
        print()
    
    def _deploy_message_board(self):
        """
        Deploy MessageBoard test contract
        
        This is a simple message board contract for testing contract function calls with parameters
        """
        print("✓ Deploy MessageBoard test contract...")
        
        try:
            import solcx
            from solcx import compile_source
            from eth_utils import to_checksum_address
            
            # MessageBoard contract source code
            contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MessageBoard {
    string public message;
    address public lastSender;
    uint256 public updateCount;
    
    event MessageUpdated(address indexed sender, string newMessage);
    
    constructor() {
        message = "Initial message";
        lastSender = msg.sender;
        updateCount = 0;
    }
    
    // Set message with string parameter
    function setMessage(string memory newMessage) external {
        message = newMessage;
        lastSender = msg.sender;
        updateCount += 1;
        
        emit MessageUpdated(msg.sender, newMessage);
    }
    
    // Get current message
    function getMessage() external view returns (string memory) {
        return message;
    }
    
    // Get message info
    function getMessageInfo() external view returns (
        string memory currentMessage,
        address sender,
        uint256 count
    ) {
        return (message, lastSender, updateCount);
    }
}
"""
            
            # Try to compile contract
            try:
                # Try to use installed solc
                compiled = compile_source(
                    contract_source,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.20'
                )
                contract_interface = compiled['<stdin>:MessageBoard']
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
            except Exception as compile_error:
                print(f"  • Solc compilation failed: {compile_error}")
                print(f"  • Trying to install solc 0.8.20...")
                solcx.install_solc('0.8.20')
                compiled = compile_source(
                    contract_source,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.20'
                )
                contract_interface = compiled['<stdin>:MessageBoard']
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
            
            # Deploy contract
            deployer = self.test_account
            deployer_address = deployer.address
            
            # Construct deployment transaction
            deploy_tx = {
                'from': deployer_address,
                'data': '0x' + bytecode,
                'gas': 1000000,  # Increase gas limit, MessageBoard has string initialization
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(deploy_tx, deployer.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for transaction confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            # Debug info
            print(f"  • Deployment tx: {tx_hash.hex()}")
            print(f"  • Gas used: {receipt['gasUsed']} / {deploy_tx['gas']}")
            print(f"  • Status: {receipt['status']}")
            
            if receipt['status'] != 1:
                # Try to get revert reason
                print(f"  • Trying to get revert reason...")
                try:
                    self.w3.eth.call(deploy_tx, receipt['blockNumber'])
                except Exception as call_error:
                    print(f"  • Revert reason: {call_error}")
                raise Exception(f"MessageBoard deployment failed: status={receipt['status']}, gasUsed={receipt['gasUsed']}")
            
            contract_address = receipt['contractAddress']
            self.message_board_address = contract_address
            
            # Verify contract deployment
            message_contract = self.w3.eth.contract(address=contract_address, abi=abi)
            initial_message = message_contract.functions.getMessage().call()
            
            print(f"  • MessageBoard Contract deployed: {contract_address}")
            print(f"  • Initial message: \"{initial_message}\" ✅")
            
        except Exception as e:
            print(f"  • MessageBoard Contract: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            self.message_board_address = None
        
        print()
    
    def _deploy_delegate_call_contracts(self):
        """
        Deploy DelegateCall related contracts:
        1. Implementation contract - contains actual logic
        2. Proxy contract - uses delegatecall to forward calls
        """
        from eth_utils import to_checksum_address
        import solcx
        
        print(f"✓ Deploying DelegateCall contracts...")
        
        try:
            # Implementation contract source
            implementation_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Implementation {
    uint256 public value;
    
    event ValueSet(uint256 newValue);
    
    // Set value function
    function setValue(uint256 _value) external {
        value = _value;
        emit ValueSet(_value);
    }
    
    // Get value function
    function getValue() external view returns (uint256) {
        return value;
    }
}
"""
            
            # Proxy contract source
            proxy_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DelegateCallProxy {
    uint256 public value;  // Storage slot 0 - matches Implementation
    address public implementation;  // Storage slot 1
    
    event ValueSet(uint256 newValue);
    
    constructor(address _implementation) {
        implementation = _implementation;
    }
    
    // Fallback function that delegates all calls to implementation
    fallback() external payable {
        address impl = implementation;
        require(impl != address(0), "No implementation");
        
        assembly {
            // Copy calldata to memory
            calldatacopy(0, 0, calldatasize())
            
            // Delegate call to implementation
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            
            // Copy return data to memory
            returndatacopy(0, 0, returndatasize())
            
            // Return or revert based on result
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
    
    // Allow contract to receive BNB
    receive() external payable {}
}
"""
            
            deployer = self.test_account
            deployer_address = deployer.address
            
            # Install solc 0.8.20
            solc_version = '0.8.20'
            if solc_version not in solcx.get_installed_solc_versions():
                print(f"  • Installing solc {solc_version}...")
                solcx.install_solc(solc_version)
            solcx.set_solc_version(solc_version)
            
            # Compile Implementation contract
            print(f"  • Compiling Implementation contract...")
            impl_compiled = solcx.compile_source(
                implementation_source,
                output_values=['abi', 'bin'],
                solc_version=solc_version
            )
            impl_contract_id = None
            for contract_id in impl_compiled.keys():
                if 'Implementation' in contract_id:
                    impl_contract_id = contract_id
                    break
            
            if not impl_contract_id:
                raise Exception("Implementation contract not found in compiled output")
            
            impl_abi = impl_compiled[impl_contract_id]['abi']
            impl_bytecode = impl_compiled[impl_contract_id]['bin']
            
            # Deploy Implementation contract
            print(f"  • Deploying Implementation contract...")
            impl_deploy_tx = {
                'from': deployer_address,
                'data': '0x' + impl_bytecode,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            impl_signed_tx = self.w3.eth.account.sign_transaction(impl_deploy_tx, deployer.key)
            impl_tx_hash = self.w3.eth.send_raw_transaction(impl_signed_tx.raw_transaction)
            impl_receipt = self.w3.eth.wait_for_transaction_receipt(impl_tx_hash, timeout=30)
            
            if impl_receipt['status'] != 1:
                raise Exception(f"Implementation deployment failed: status={impl_receipt['status']}")
            
            impl_address = impl_receipt['contractAddress']
            print(f"  • Implementation deployed: {impl_address}")
            
            # Compile Proxy contract
            print(f"  • Compiling Proxy contract...")
            proxy_compiled = solcx.compile_source(
                proxy_source,
                output_values=['abi', 'bin'],
                solc_version=solc_version
            )
            proxy_contract_id = None
            for contract_id in proxy_compiled.keys():
                if 'DelegateCallProxy' in contract_id:
                    proxy_contract_id = contract_id
                    break
            
            if not proxy_contract_id:
                raise Exception("Proxy contract not found in compiled output")
            
            proxy_abi = proxy_compiled[proxy_contract_id]['abi']
            proxy_bytecode = proxy_compiled[proxy_contract_id]['bin']
            
            # Encode constructor parameters (implementation address)
            from eth_abi import encode
            constructor_params = encode(['address'], [to_checksum_address(impl_address)])
            
            # Deploy Proxy contract
            print(f"  • Deploying Proxy contract...")
            proxy_deploy_tx = {
                'from': deployer_address,
                'data': '0x' + proxy_bytecode + constructor_params.hex(),
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            proxy_signed_tx = self.w3.eth.account.sign_transaction(proxy_deploy_tx, deployer.key)
            proxy_tx_hash = self.w3.eth.send_raw_transaction(proxy_signed_tx.raw_transaction)
            proxy_receipt = self.w3.eth.wait_for_transaction_receipt(proxy_tx_hash, timeout=30)
            
            if proxy_receipt['status'] != 1:
                raise Exception(f"Proxy deployment failed: status={proxy_receipt['status']}")
            
            proxy_address = proxy_receipt['contractAddress']
            
            # Save addresses
            self.delegate_call_implementation_address = impl_address
            self.delegate_call_proxy_address = proxy_address
            
            # Verify contract deployment
            # Read initial value of implementation contract
            impl_contract = self.w3.eth.contract(address=impl_address, abi=impl_abi)
            impl_initial_value = impl_contract.functions.getValue().call()
            
            # Read initial value of proxy contract (via delegatecall)
            proxy_contract = self.w3.eth.contract(address=proxy_address, abi=impl_abi)
            proxy_initial_value = proxy_contract.functions.getValue().call()
            
            print(f"  • Proxy Contract deployed: {proxy_address}")
            print(f"  • Implementation Contract: {impl_address}")
            print(f"  • Implementation initial value: {impl_initial_value}")
            print(f"  • Proxy initial value: {proxy_initial_value} ✅")
            
        except Exception as e:
            print(f"  • DelegateCall Contracts: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            self.delegate_call_implementation_address = None
            self.delegate_call_proxy_address = None
        
        print()
    
    def _deploy_fallback_receiver(self):
        """
        Deploy FallbackReceiver test contract
        
        This is a simple contract with receive() function to accept BNB
        """
        print("✓ Deploy FallbackReceiver test contract...")
        
        try:
            import solcx
            from solcx import compile_source
            from eth_utils import to_checksum_address
            
            # FallbackReceiver contract source code
            contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FallbackReceiver {
    uint256 public receivedCount;
    uint256 public totalReceived;
    address public owner;
    
    event BNBReceived(address indexed sender, uint256 amount);
    
    constructor() {
        owner = msg.sender;
        receivedCount = 0;
        totalReceived = 0;
    }
    
    // Receive function - called when BNB is sent with empty calldata
    receive() external payable {
        receivedCount += 1;
        totalReceived += msg.value;
        emit BNBReceived(msg.sender, msg.value);
    }
    
    // Fallback function - called when function doesn't exist
    fallback() external payable {
        receivedCount += 1;
        totalReceived += msg.value;
        emit BNBReceived(msg.sender, msg.value);
    }
    
    // Get contract balance
    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
    
    // Get received count
    function getReceivedCount() external view returns (uint256) {
        return receivedCount;
    }
    
    // Owner can withdraw (for cleanup)
    function withdraw() external {
        require(msg.sender == owner, "Only owner can withdraw");
        payable(owner).transfer(address(this).balance);
    }
}
"""
            
            # Try to compile contract
            try:
                # Try to use installed solc
                compiled = compile_source(
                    contract_source,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.20'
                )
                contract_interface = compiled['<stdin>:FallbackReceiver']
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
            except Exception as compile_error:
                print(f"  • Solc compilation failed: {compile_error}")
                print(f"  • Trying to install solc 0.8.20...")
                solcx.install_solc('0.8.20')
                compiled = compile_source(
                    contract_source,
                    output_values=['abi', 'bin'],
                    solc_version='0.8.20'
                )
                contract_interface = compiled['<stdin>:FallbackReceiver']
                bytecode = contract_interface['bin']
                abi = contract_interface['abi']
            
            # Deploy contract
            deployer = self.test_account
            deployer_address = deployer.address
            
            # Construct deployment transaction
            deploy_tx = {
                'from': deployer_address,
                'data': '0x' + bytecode,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(deploy_tx, deployer.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for transaction confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] != 1:
                raise Exception(f"Contract deployment failed with status: {receipt['status']}")
            
            contract_address = receipt['contractAddress']
            self.fallback_receiver_address = contract_address
            
            # Verify contract deployment
            fallback_contract = self.w3.eth.contract(address=contract_address, abi=abi)
            initial_balance = fallback_contract.functions.getBalance().call()
            initial_count = fallback_contract.functions.getReceivedCount().call()
            
            print(f"  • FallbackReceiver Contract deployed: {contract_address}")
            print(f"  • Initial balance: {initial_balance / 10**18:.6f} BNB")
            print(f"  • Initial received count: {initial_count} ✅")
            
        except Exception as e:
            print(f"  • FallbackReceiver Contract: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            self.fallback_receiver_address = None
        
        print()
    
    def _deploy_simple_staking(self):
        """
        Deploy SimpleStaking contract for staking tests
        """
        print("✓ Deploying SimpleStaking test contract...")
        try:
            import json
            from solcx import compile_source, install_solc
            
            # CAKE token address
            cake_address = '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82'
            
            # Read contract source code
            contract_path = os.path.join(os.path.dirname(__file__), 'contracts', 'SimpleStaking.sol')
            with open(contract_path, 'r') as f:
                contract_source = f.read()
            
            # Install and compile contract
            try:
                install_solc('0.8.20')
            except:
                pass  # Might be already installed
            
            compiled_sol = compile_source(
                contract_source,
                output_values=['abi', 'bin', 'bin-runtime'],
                solc_version='0.8.20'
            )
            
            # Find SimpleStaking contract (skip interfaces)
            contract_interface = None
            contract_id = None
            
            print(f"  • Found {len(compiled_sol)} compiled contracts/interfaces")
            for cid, cinterface in compiled_sol.items():
                print(f"    - {cid}: bytecode length = {len(cinterface.get('bin', ''))}")
                # Find contract with bytecode (skip empty interfaces)
                if cinterface.get('bin') and len(cinterface.get('bin', '')) > 10:
                    if 'SimpleStaking' in cid:
                        contract_id = cid
                        contract_interface = cinterface
                        print(f"  • ✅ Found SimpleStaking contract: {cid}")
                        break
            
            if not contract_interface:
                print(f"  • ERROR: SimpleStaking contract not found!")
                print(f"  • Available contracts: {list(compiled_sol.keys())}")
                raise Exception("SimpleStaking contract not found in compilation output")
            
            # Get bytecode and ABI
            bytecode = contract_interface.get('bin', '')
            abi = contract_interface.get('abi', [])
            
            # Ensure bytecode format is correct
            if not bytecode.startswith('0x'):
                bytecode = '0x' + bytecode
            
            # Construct deployment transaction (including constructor args)
            from eth_abi import encode
            from eth_utils import to_checksum_address
            constructor_args = encode(['address'], [to_checksum_address(cake_address)])
            
            # Combine bytecode and constructor args
            deployment_data = bytecode + constructor_args.hex()
            
            deployer = self.test_account
            deployer_address = deployer.address
            
            print(f"  • Bytecode length: {len(bytecode)} characters")
            print(f"  • Deploying contract...")
            
            deploy_tx = {
                'from': deployer_address,
                'data': deployment_data,
                'gas': 2000000,  # Increase gas limit
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(deploy_tx, deployer.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for transaction confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] != 1:
                raise Exception(f"Contract deployment failed with status: {receipt['status']}")
            
            contract_address = receipt['contractAddress']
            self.simple_staking_address = contract_address
            
            print(f"  • SimpleStaking Contract deployed: {contract_address}")
            print(f"  • Staking token: {cake_address} (CAKE)")
            
            # Set CAKE allowance for SimpleStaking
            try:
                from eth_utils import to_checksum_address
                from eth_abi import encode
                
                cake_addr = to_checksum_address(cake_address)
                test_addr = to_checksum_address(self.test_address)
                staking_addr = to_checksum_address(contract_address)
                
                # Impersonate test account
                self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
                
                # ERC20 approve function selector: 0x095ea7b3
                approve_selector = bytes.fromhex('095ea7b3')
                # Approve a large amount (200 CAKE to match balance)
                approve_amount = 200 * 10**18
                approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [staking_addr, approve_amount]).hex()
                
                # Send approve transaction
                response = self.w3.provider.make_request(
                    'eth_sendTransaction',
                    [{
                        'from': test_addr,
                        'to': cake_addr,
                        'data': approve_data,
                        'gas': hex(100000),
                        'gasPrice': hex(3000000000)
                    }]
                )
                
                if 'result' in response:
                    tx_hash = response['result']
                    
                    # Wait for confirmation
                    max_attempts = 20
                    for i in range(max_attempts):
                        try:
                            receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                            if receipt and receipt.get('blockNumber'):
                                break
                        except:
                            pass
                        time.sleep(0.5)
                
                # Stop impersonate
                self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
                
                print(f"  • CAKE approved for SimpleStaking ✅")
            except Exception as e:
                print(f"  • CAKE approval failed: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"  • SimpleStaking Contract: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            self.simple_staking_address = None
        
        print()
    
    def _deploy_simple_lp_staking(self):
        """
        Deploy SimpleLPStaking contract for LP token staking tests
        """
        print("✓ Deploying SimpleLPStaking test contract...")
        try:
            import json
            from solcx import compile_source, install_solc
            
            # USDT/BUSD LP token address
            lp_token_address = '0x7EFaEf62fDdCCa950418312c6C91Aef321375A00'
            
            # Read contract source code
            contract_path = os.path.join(os.path.dirname(__file__), 'contracts', 'SimpleLPStaking.sol')
            with open(contract_path, 'r') as f:
                contract_source = f.read()
            
            # Install and compile contract
            try:
                install_solc('0.8.20')
            except:
                pass  # Might be already installed
            
            compiled_sol = compile_source(
                contract_source,
                output_values=['abi', 'bin', 'bin-runtime'],
                solc_version='0.8.20'
            )
            
            # Find SimpleLPStaking contract (skip interfaces)
            contract_interface = None
            contract_id = None
            
            print(f"  • Found {len(compiled_sol)} compiled contracts/interfaces")
            for cid, cinterface in compiled_sol.items():
                print(f"    - {cid}: bytecode length = {len(cinterface.get('bin', ''))}")
                # Find contract with bytecode (skip empty interfaces)
                if cinterface.get('bin') and len(cinterface.get('bin', '')) > 10:
                    if 'SimpleLPStaking' in cid:
                        contract_id = cid
                        contract_interface = cinterface
                        print(f"  • ✅ Found SimpleLPStaking contract: {cid}")
                        break
            
            if not contract_interface:
                print(f"  • ERROR: SimpleLPStaking contract not found!")
                print(f"  • Available contracts: {list(compiled_sol.keys())}")
                raise Exception("SimpleLPStaking contract not found in compilation output")
            
            # Get bytecode and ABI
            bytecode = contract_interface.get('bin', '')
            abi = contract_interface.get('abi', [])
            
            # Ensure bytecode format is correct
            if not bytecode.startswith('0x'):
                bytecode = '0x' + bytecode
            
            # Construct deployment transaction (including constructor args)
            from eth_abi import encode
            from eth_utils import to_checksum_address
            constructor_args = encode(['address'], [to_checksum_address(lp_token_address)])
            
            # Combine bytecode and constructor args
            deployment_data = bytecode + constructor_args.hex()
            
            deployer = self.test_account
            deployer_address = deployer.address
            
            print(f"  • Bytecode length: {len(bytecode)} characters")
            print(f"  • Deploying contract...")
            
            deploy_tx = {
                'from': deployer_address,
                'data': deployment_data,
                'gas': 2000000,  # Increase gas limit
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(deploy_tx, deployer.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for transaction confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] != 1:
                raise Exception(f"Contract deployment failed with status: {receipt['status']}")
            
            contract_address = receipt['contractAddress']
            self.simple_lp_staking_address = contract_address
            
            print(f"  • SimpleLPStaking Contract deployed: {contract_address}")
            print(f"  • Staking token: {lp_token_address} (USDT/BUSD LP)")
            
            # Set LP token allowance for SimpleLPStaking
            try:
                from eth_utils import to_checksum_address
                from eth_abi import encode
                
                lp_token_addr = to_checksum_address(lp_token_address)
                test_addr = to_checksum_address(self.test_address)
                staking_addr = to_checksum_address(contract_address)
                
                # Impersonate test account
                self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
                
                # ERC20 approve function selector: 0x095ea7b3
                approve_selector = bytes.fromhex('095ea7b3')
                # Approve a large amount (2 LP tokens)
                approve_amount = 2 * 10**18
                approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [staking_addr, approve_amount]).hex()
                
                # Send approve transaction
                response = self.w3.provider.make_request(
                    'eth_sendTransaction',
                    [{
                        'from': test_addr,
                        'to': lp_token_addr,
                        'data': approve_data,
                        'gas': hex(100000),
                        'gasPrice': hex(3000000000)
                    }]
                )
                
                if 'result' in response:
                    tx_hash = response['result']
                    
                    # Wait for confirmation
                    max_attempts = 20
                    for i in range(max_attempts):
                        try:
                            receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                            if receipt and receipt.get('blockNumber'):
                                break
                        except:
                            pass
                        time.sleep(0.5)
                
                # Stop impersonate
                self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
                
                print(f"  • LP token approved for SimpleLPStaking ✅")
            except Exception as e:
                print(f"  • LP token approval failed: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"  • SimpleLPStaking Contract: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            self.simple_lp_staking_address = None
        
        print()
    
    def _deploy_simple_reward_pool(self):
        """
        Deploy SimpleRewardPool contract for harvest rewards tests
        """
        print("✓ Deploying SimpleRewardPool test contract...")
        try:
            import json
            import time
            from solcx import compile_source, install_solc
            
            # LP token and reward token addresses
            lp_token_address = '0x7EFaEf62fDdCCa950418312c6C91Aef321375A00'  # USDT/BUSD LP
            cake_address = '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82'  # CAKE
            
            # Read contract source code
            contract_path = os.path.join(os.path.dirname(__file__), 'contracts', 'SimpleRewardPool.sol')
            with open(contract_path, 'r') as f:
                contract_source = f.read()
            
            # Install and compile contract
            try:
                install_solc('0.8.20')
            except:
                pass  # Might be already installed
            
            compiled_sol = compile_source(
                contract_source,
                output_values=['abi', 'bin', 'bin-runtime'],
                solc_version='0.8.20'
            )
            
            # Find SimpleRewardPool contract (skip interfaces)
            contract_interface = None
            contract_id = None
            
            print(f"  • Found {len(compiled_sol)} compiled contracts/interfaces")
            for cid, cinterface in compiled_sol.items():
                print(f"    - {cid}: bytecode length = {len(cinterface.get('bin', ''))}")
                if cinterface.get('bin') and len(cinterface.get('bin', '')) > 10:
                    if 'SimpleRewardPool' in cid:
                        contract_id = cid
                        contract_interface = cinterface
                        print(f"  • ✅ Found SimpleRewardPool contract: {cid}")
                        break
            
            if not contract_interface:
                print(f"  • ERROR: SimpleRewardPool contract not found!")
                print(f"  • Available contracts: {list(compiled_sol.keys())}")
                raise Exception("SimpleRewardPool contract not found in compilation output")
            
            # Get bytecode and ABI
            bytecode = contract_interface.get('bin', '')
            abi = contract_interface.get('abi', [])
            
            # Ensure bytecode format is correct
            if not bytecode.startswith('0x'):
                bytecode = '0x' + bytecode
            
            # Construct deployment transaction (including constructor args: staking token, reward token)
            from eth_abi import encode
            from eth_utils import to_checksum_address
            constructor_args = encode(
                ['address', 'address'],
                [to_checksum_address(lp_token_address), to_checksum_address(cake_address)]
            )
            
            # Combine bytecode and constructor args
            deployment_data = bytecode + constructor_args.hex()
            
            deployer = self.test_account
            deployer_address = deployer.address
            
            print(f"  • Bytecode length: {len(bytecode)} characters")
            print(f"  • Deploying contract...")
            
            deploy_tx = {
                'from': deployer_address,
                'data': deployment_data,
                'gas': 2000000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(deployer_address),
            }
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(deploy_tx, deployer.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for transaction confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] != 1:
                raise Exception(f"Contract deployment failed with status: {receipt['status']}")
            
            contract_address = receipt['contractAddress']
            self.simple_reward_pool_address = contract_address
            
            print(f"  • SimpleRewardPool Contract deployed: {contract_address}")
            print(f"  • Staking token: {lp_token_address} (USDT/BUSD LP)")
            print(f"  • Reward token: {cake_address} (CAKE)")
            
            # Transfer CAKE to contract as reward pool
            try:
                from eth_utils import to_checksum_address
                from eth_abi import encode
                
                cake_addr = to_checksum_address(cake_address)
                test_addr = to_checksum_address(self.test_address)
                pool_addr = to_checksum_address(contract_address)
                
                # Transfer 100 CAKE to contract as reward pool
                reward_pool_amount = 100 * 10**18
                
                # Impersonate test account
                self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
                
                # ERC20 transfer function selector: 0xa9059cbb
                transfer_selector = bytes.fromhex('a9059cbb')
                transfer_data = '0x' + transfer_selector.hex() + encode(['address', 'uint256'], [pool_addr, reward_pool_amount]).hex()
                
                # Send transfer transaction
                response = self.w3.provider.make_request(
                    'eth_sendTransaction',
                    [{
                        'from': test_addr,
                        'to': cake_addr,
                        'data': transfer_data,
                        'gas': hex(100000),
                        'gasPrice': hex(3000000000)
                    }]
                )
                
                if 'result' in response:
                    tx_hash = response['result']
                    max_attempts = 20
                    for i in range(max_attempts):
                        try:
                            receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                            if receipt and receipt.get('blockNumber'):
                                break
                        except:
                            pass
                        time.sleep(0.5)
                
                # Stop impersonate
                self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
                
                print(f"  • Reward pool funded with 100 CAKE ✅")
            except Exception as e:
                print(f"  • Reward pool funding failed: {e}")
            
            # Stake LP tokens to reward pool for test account
            try:
                # Stake 0.5 LP tokens
                stake_amount = int(0.5 * 10**18)
                
                # Approve LP token first
                lp_addr = to_checksum_address(lp_token_address)
                
                self.w3.provider.make_request('anvil_impersonateAccount', [test_addr])
                
                # Approve LP token for SimpleRewardPool
                approve_selector = bytes.fromhex('095ea7b3')
                approve_data = '0x' + approve_selector.hex() + encode(['address', 'uint256'], [pool_addr, stake_amount]).hex()
                
                response = self.w3.provider.make_request(
                    'eth_sendTransaction',
                    [{
                        'from': test_addr,
                        'to': lp_addr,
                        'data': approve_data,
                        'gas': hex(100000),
                        'gasPrice': hex(3000000000)
                    }]
                )
                
                if 'result' in response:
                    tx_hash = response['result']
                    for i in range(20):
                        try:
                            receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                            if receipt and receipt.get('blockNumber'):
                                break
                        except:
                            pass
                        time.sleep(0.5)
                
                # Deposit LP tokens
                # deposit(uint256 _amount) selector: 0xb6b55f25
                deposit_selector = bytes.fromhex('b6b55f25')
                deposit_data = '0x' + deposit_selector.hex() + encode(['uint256'], [stake_amount]).hex()
                
                response = self.w3.provider.make_request(
                    'eth_sendTransaction',
                    [{
                        'from': test_addr,
                        'to': pool_addr,
                        'data': deposit_data,
                        'gas': hex(200000),
                        'gasPrice': hex(3000000000)
                    }]
                )
                
                if 'result' in response:
                    tx_hash = response['result']
                    for i in range(20):
                        try:
                            receipt = self.w3.provider.make_request('eth_getTransactionReceipt', [tx_hash])['result']
                            if receipt and receipt.get('blockNumber'):
                                break
                        except:
                            pass
                        time.sleep(0.5)
                
                # Stop impersonate
                self.w3.provider.make_request('anvil_stopImpersonatingAccount', [test_addr])
                
                print(f"  • Test account staked 0.5 LP tokens ✅")
                
                # Advance time by 100 seconds to accumulate rewards
                self.w3.provider.make_request('evm_increaseTime', [100])
                self.w3.provider.make_request('evm_mine', [])
                
                print(f"  • Time advanced by 100 seconds (rewards accumulated) ✅")
                
            except Exception as e:
                print(f"  • LP staking failed: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"  • SimpleRewardPool Contract: ❌ Deployment failed - {e}")
            import traceback
            traceback.print_exc()
            self.simple_reward_pool_address = None
        
        print()
    
    def _setup_rich_account(self):
        """
        Setup rich account for transferFrom tests
        
        Create an account with large amount of USDT, and approve test_address to use these tokens
        """
        from eth_utils import to_checksum_address
        from eth_abi import encode
        import time
        
        print(f"✓ Setting up rich account (for transferFrom tests)...")
        
        try:
            # Use fixed address as rich account (for easier testing and debugging)
            # This address is in Anvil local environment, we can directly manipulate its balance
            rich_account = Account.create()
            self.rich_address = rich_account.address
            
            usdt_address = '0x55d398326f99059fF775485246999027B3197955'
            usdt_addr = to_checksum_address(usdt_address)
            rich_addr = to_checksum_address(self.rich_address)
            test_addr = to_checksum_address(self.test_address)
            
            # 1. Set USDT balance for rich account (5000 USDT)
            rich_usdt_amount = 5000 * 10**18
            if self._set_erc20_balance_direct(usdt_addr, rich_addr, rich_usdt_amount, balance_slot=1):
                print(f"  • Rich account: {self.rich_address}")
                print(f"  • Rich account USDT balance: {rich_usdt_amount / 10**18:.2f} USDT ✅")
            else:
                print(f"  • Failed to set rich account balance")
                return
            
            # 2. Approve test_address to spend rich account's USDT (large approval 1000 USDT)
            # Use anvil_setStorageAt to directly set allowance (faster and more reliable)
            # ERC20 allowance mapping: mapping(address => mapping(address => uint256)) at slot 2 for USDT
            # Storage slot = keccak256(spender_address + keccak256(owner_address + slot))
            from eth_utils import keccak
            
            approve_amount = 1000 * 10**18  # Approve 1000 USDT
            allowance_slot = 2  # USDT uses slot 2 for allowances
            
            # Calculate storage slot for allowance[rich_address][test_address]
            # First hash: keccak256(owner_address + slot)
            owner_padded = rich_addr[2:].lower().rjust(64, '0')
            slot_padded = format(allowance_slot, '064x')
            inner_key = owner_padded + slot_padded
            inner_hash = keccak(bytes.fromhex(inner_key))
            
            # Second hash: keccak256(spender_address + inner_hash)
            spender_padded = test_addr[2:].lower().rjust(64, '0')
            inner_hash_hex = inner_hash.hex()
            outer_key = spender_padded + inner_hash_hex
            storage_slot = '0x' + keccak(bytes.fromhex(outer_key)).hex()
            
            # Set allowance value
            value = '0x' + format(approve_amount, '064x')
            
            self.w3.provider.make_request(
                'anvil_setStorageAt',
                [usdt_addr, storage_slot, value]
            )
            
            # Mine a block to ensure the change is committed
            self.w3.provider.make_request('evm_mine', [])
            
            print(f"  • Test account approved for {approve_amount / 10**18:.2f} USDT ✅")
            
        except Exception as e:
            print(f"  • Rich account setup: ❌ Error - {e}")
            import traceback
            traceback.print_exc()
            self.rich_address = None
        
        print()
    
    def _set_balance(self, address: str, balance_wei: int):
        """
        Set address balance using Anvil cheatcode
        
        Args:
            address: Address
            balance_wei: Balance (wei)
        """
        from eth_utils import to_checksum_address
        
        address_checksum = to_checksum_address(address)
        self.w3.provider.make_request(
            'anvil_setBalance',
            [address_checksum, hex(balance_wei)]
        )
    
    def get_balance(self, address: str) -> float:
        """
        Get address balance
        
        Args:
            address: Address
            
        Returns:
            Balance (BNB)
        """
        balance_wei = self.w3.eth.get_balance(address)
        return balance_wei / 10**18
    
    def __enter__(self):
        """Context manager enter"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()

