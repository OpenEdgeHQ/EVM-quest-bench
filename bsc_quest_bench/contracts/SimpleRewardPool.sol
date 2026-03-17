// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title SimpleRewardPool
 * @dev A simple reward pool for testing harvest functionality
 * Users stake LP tokens and earn CAKE rewards over time
 */
contract SimpleRewardPool {
    IERC20 public stakingToken;  // LP token
    IERC20 public rewardToken;   // CAKE token
    
    // Reward per second (0.01 CAKE per second)
    uint256 public rewardRate = 10000000000000000; // 0.01 * 10^18
    
    struct UserInfo {
        uint256 amount;           // Amount of LP tokens staked
        uint256 rewardDebt;       // Reward debt
        uint256 lastUpdateTime;   // Last time rewards were updated
    }
    
    mapping(address => UserInfo) public userInfo;
    
    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);
    event Harvest(address indexed user, uint256 amount);
    
    constructor(address _stakingToken, address _rewardToken) {
        stakingToken = IERC20(_stakingToken);
        rewardToken = IERC20(_rewardToken);
    }
    
    /**
     * @dev Calculate pending rewards for a user
     * @param _user User address
     * @return Pending reward amount
     */
    function pendingReward(address _user) public view returns (uint256) {
        UserInfo memory user = userInfo[_user];
        if (user.amount == 0) {
            return 0;
        }
        
        // Calculate rewards based on time elapsed since last update
        uint256 timeElapsed = block.timestamp - user.lastUpdateTime;
        uint256 reward = (timeElapsed * rewardRate * user.amount) / 1e18;
        
        return reward;
    }
    
    /**
     * @dev Deposit LP tokens for staking
     * @param _amount Amount of LP tokens to stake
     */
    function deposit(uint256 _amount) external {
        require(_amount > 0, "Amount must be greater than 0");
        
        UserInfo storage user = userInfo[msg.sender];
        
        // Harvest pending rewards before deposit
        if (user.amount > 0) {
            _harvest(msg.sender);
        }
        
        // Transfer LP tokens from user to contract
        require(
            stakingToken.transferFrom(msg.sender, address(this), _amount),
            "Transfer failed"
        );
        
        // Update user info
        user.amount += _amount;
        user.lastUpdateTime = block.timestamp;
        
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
        
        // Harvest pending rewards before withdraw
        _harvest(msg.sender);
        
        // Update user info
        user.amount -= _amount;
        user.lastUpdateTime = block.timestamp;
        
        // Transfer LP tokens from contract to user
        require(
            stakingToken.transfer(msg.sender, _amount),
            "Transfer failed"
        );
        
        emit Withdraw(msg.sender, _amount);
    }
    
    /**
     * @dev Emergency withdraw - withdraw all staked tokens without claiming rewards
     * Used in emergency situations to quickly retrieve staked assets
     */
    function emergencyWithdraw() external {
        UserInfo storage user = userInfo[msg.sender];
        uint256 amount = user.amount;
        require(amount > 0, "No staked amount");
        
        // Clear user info (forfeit rewards)
        user.amount = 0;
        user.lastUpdateTime = 0;
        
        // Transfer LP tokens from contract to user
        require(
            stakingToken.transfer(msg.sender, amount),
            "Transfer failed"
        );
        
        emit Withdraw(msg.sender, amount);
    }
    
    /**
     * @dev Harvest accumulated rewards
     */
    function harvest() external {
        _harvest(msg.sender);
    }
    
    /**
     * @dev Internal function to harvest rewards
     * @param _user User address
     */
    function _harvest(address _user) internal {
        UserInfo storage user = userInfo[_user];
        
        uint256 pending = pendingReward(_user);
        
        if (pending > 0) {
            // Update last update time
            user.lastUpdateTime = block.timestamp;
            
            // Transfer rewards to user
            require(
                rewardToken.transfer(_user, pending),
                "Reward transfer failed"
            );
            
            emit Harvest(_user, pending);
        }
    }
    
    /**
     * @dev Get user's staked amount
     * @param _user User address
     * @return amount Staked amount
     * @return rewardDebt Reward debt (for compatibility)
     */
    function getUserInfo(address _user) external view returns (uint256 amount, uint256 rewardDebt) {
        UserInfo memory user = userInfo[_user];
        return (user.amount, user.rewardDebt);
    }
}

