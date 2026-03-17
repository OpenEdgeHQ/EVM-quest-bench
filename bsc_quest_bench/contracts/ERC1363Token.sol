// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ERC1363Token
 * @dev ERC1363 Token implementation for testing
 * 
 * ERC1363 is an extension of ERC20 that supports executing code on receiver contracts
 * after transfer or approval, similar to how ERC721 safeTransfer works.
 */

interface IERC1363Receiver {
    function onTransferReceived(
        address operator,
        address from,
        uint256 value,
        bytes calldata data
    ) external returns (bytes4);
}

interface IERC1363Spender {
    function onApprovalReceived(
        address owner,
        uint256 value,
        bytes calldata data
    ) external returns (bytes4);
}

contract ERC1363Token {
    string public name = "ERC1363 Token";
    string public symbol = "E1363";
    uint8 public decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(uint256 _initialSupply) {
        totalSupply = _initialSupply;
        balanceOf[msg.sender] = _initialSupply;
        emit Transfer(address(0), msg.sender, _initialSupply);
    }

    // Standard ERC20 functions
    function transfer(address to, uint256 value) public returns (bool) {
        require(to != address(0), "ERC1363: transfer to zero address");
        require(balanceOf[msg.sender] >= value, "ERC1363: insufficient balance");

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
        require(to != address(0), "ERC1363: transfer to zero address");
        require(balanceOf[from] >= value, "ERC1363: insufficient balance");
        require(allowance[from][msg.sender] >= value, "ERC1363: insufficient allowance");

        balanceOf[from] -= value;
        balanceOf[to] += value;
        allowance[from][msg.sender] -= value;
        emit Transfer(from, to, value);
        return true;
    }

    // ERC1363 functions
    
    /**
     * @dev Transfer tokens and optionally call onTransferReceived
     * @param to The address to transfer to
     * @param value The amount to transfer
     * @return true if successful
     */
    function transferAndCall(address to, uint256 value) public returns (bool) {
        return transferAndCall(to, value, "");
    }
    
    /**
     * @dev Transfer tokens and optionally call onTransferReceived with data
     * @param to The address to transfer to
     * @param value The amount to transfer
     * @param data Additional data to pass to receiver
     * @return true if successful
     */
    function transferAndCall(address to, uint256 value, bytes memory data) public returns (bool) {
        // Directly perform the transfer logic inline instead of calling transfer()
        require(balanceOf[msg.sender] >= value, "Insufficient balance");
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
        
        // Check if recipient is a contract
        uint256 codeSize;
        assembly {
            codeSize := extcodesize(to)
        }
        
        // If recipient is a contract, call onTransferReceived
        if (codeSize > 0) {
            try IERC1363Receiver(to).onTransferReceived(
                msg.sender,
                msg.sender,
                value,
                data
            ) returns (bytes4 retval) {
                require(
                    retval == IERC1363Receiver.onTransferReceived.selector,
                    "ERC1363: receiver rejected tokens"
                );
            } catch {
                // If receiver doesn't implement interface, that's ok
                // Just like regular transfer
            }
        }
        
        return true;
    }

    /**
     * @dev Approve and call onApprovalReceived
     * @param spender The address to approve
     * @param value The amount to approve
     * @return true if successful
     */
    function approveAndCall(address spender, uint256 value) public returns (bool) {
        return approveAndCall(spender, value, "");
    }

    /**
     * @dev Approve and call onApprovalReceived with data
     * @param spender The address to approve
     * @param value The amount to approve
     * @param data Additional data to pass to spender
     * @return true if successful
     */
    function approveAndCall(address spender, uint256 value, bytes memory data) public returns (bool) {
        require(approve(spender, value), "ERC1363: approve failed");
        
        // Check if spender is a contract
        uint256 codeSize;
        assembly {
            codeSize := extcodesize(spender)
        }
        
        // If spender is a contract, call onApprovalReceived
        if (codeSize > 0) {
            try IERC1363Spender(spender).onApprovalReceived(
                msg.sender,
                value,
                data
            ) returns (bytes4 retval) {
                require(
                    retval == IERC1363Spender.onApprovalReceived.selector,
                    "ERC1363: spender rejected approval"
                );
            } catch {
                // If spender doesn't implement interface, that's ok
                // Just like regular approval
            }
        }
        
        return true;
    }

    // Utility function for testing - mint tokens to any address
    function mint(address to, uint256 value) public {
        require(to != address(0), "ERC1363: mint to zero address");
        totalSupply += value;
        balanceOf[to] += value;
        emit Transfer(address(0), to, value);
    }
}

