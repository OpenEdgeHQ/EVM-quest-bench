// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title SimpleLPStaking
 * @dev A simple LP token staking contract for testing purposes
 */
contract SimpleLPStaking {
    IERC20 public stakingToken;
    
    struct UserInfo {
        uint256 amount;           // Amount of LP tokens staked
        uint256 depositTime;      // Time of last deposit
    }
    
    mapping(address => UserInfo) public userInfo;
    
    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);
    
    constructor(address _stakingToken) {
        stakingToken = IERC20(_stakingToken);
    }
    
    /**
     * @dev Deposit LP tokens for staking
     * @param _amount Amount of LP tokens to stake
     */
    function deposit(uint256 _amount) external {
        require(_amount > 0, "Amount must be greater than 0");
        
        UserInfo storage user = userInfo[msg.sender];
        
        // Transfer LP tokens from user to contract
        require(
            stakingToken.transferFrom(msg.sender, address(this), _amount),
            "Transfer failed"
        );
        
        // Update user info
        user.amount += _amount;
        user.depositTime = block.timestamp;
        
        emit Deposit(msg.sender, _amount);
    }
    
    /**
     * @dev Withdraw staked LP tokens
     * @param _amount Amount of LP tokens to withdraw
     */
    function withdraw(uint256 _amount) external {
        UserInfo storage user = userInfo[msg.sender];
        require(user.amount >= _amount, "Insufficient staked amount");
        require(_amount > 0, "Amount must be greater than 0");
        
        // Update user info
        user.amount -= _amount;
        
        // Transfer LP tokens from contract to user
        require(
            stakingToken.transfer(msg.sender, _amount),
            "Transfer failed"
        );
        
        emit Withdraw(msg.sender, _amount);
    }
    
    /**
     * @dev Get user's staked amount
     * @param _user User address
     * @return amount Staked amount
     * @return depositTime Last deposit time
     */
    function getUserInfo(address _user) external view returns (uint256 amount, uint256 depositTime) {
        UserInfo memory user = userInfo[_user];
        return (user.amount, user.depositTime);
    }
}

