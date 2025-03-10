import json
import os
import logging
import yaml
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Default configuration paths
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_CONFIG_DIR = "configs"

class ConfigError(Exception):
    """Base exception for configuration-related errors"""
    pass

@dataclass
class ApiKeys:
    """API keys configuration"""
    openai: str = ""
    telegramBot: str = ""
    rugCheck: str = ""
    birdeye: str = ""
    jupiter: str = ""

@dataclass
class SocialSettings:
    """Social media API settings"""
    twitterBearerToken: str = ""
    discordWebhook: str = ""
    telegramChatId: str = ""
    telegramChannels: List[str] = field(default_factory=list) 

@dataclass
class TradingSettings:
    """Trading parameters configuration"""
    liquidityThreshold: float = 1000.0
    maxSlippageBps: int = 50  # 0.5%
    minConfidenceScore: float = 7.0
    maxRiskScore: float = 4.0
    tradeSize: float = 0.1  # SOL
    maxDailyTrades: int = 10
    emergencyStopLossPercent: float = 15.0
    takeProfitPercent: float = 30.0
    useAiForExit: bool = True
    holdingPeriodHours: int = 24
    enableAutoTrading: bool = False  # Safety default

@dataclass
class RiskSettings:
    """Risk management configuration"""
    maxPortfolioRisk: float = 5.0  # % of portfolio
    maxPositionSize: float = 1.0  # SOL
    blacklistedCoins: List[str] = field(default_factory=list)
    blacklistedDevelopers: List[str] = field(default_factory=list)  
    requireRugCheck: bool = True
    minLiquidityLocked: float = 5000.0  # USD
    maxSupplyConcentration: float = 70.0  # % held by top 10
    cooldownPeriodMinutes: int = 60
    minHolders: int = 25  
    maxRiskScore: float = 70.0

@dataclass
class NetworkSettings:
    """Blockchain network configuration"""
    rpcUrl: str = "https://api.mainnet-beta.solana.com"
    fallbackRpcUrls: List[str] = field(default_factory=list)
    connectionTimeout: int = 10  # seconds
    maxRetries: int = 3
    retryDelay: int = 2  # seconds
    priorityFee: int = 100  # micro-lamports

@dataclass
class BotConfig:
    """Complete bot configuration"""
    apiKeys: ApiKeys = field(default_factory=ApiKeys)
    socialSettings: SocialSettings = field(default_factory=SocialSettings)
    tradingSettings: TradingSettings = field(default_factory=TradingSettings)
    riskSettings: RiskSettings = field(default_factory=RiskSettings)
    networkSettings: NetworkSettings = field(default_factory=NetworkSettings)
    loggingLevel: str = "INFO"
    environment: str = "production"
    lastUpdated: str = ""

def load_config(config_file: str = DEFAULT_CONFIG_FILE) -> BotConfig:
    """
    Load configuration settings from a JSON or YAML file and override with environment variables.
    
    Args:
        config_file: Path to the configuration file (.json or .yaml)
    
    Returns:
        BotConfig: Configuration object with all settings
    """
    # Check if file exists
    if not os.path.exists(config_file):
        logging.error(f"Configuration file '{config_file}' not found!")
        
        # Try alternative extensions
        path = Path(config_file)
        alt_extensions = [".json", ".yaml", ".yml"]
        for ext in alt_extensions:
            alt_path = path.with_suffix(ext)
            if alt_path.exists():
                logging.info(f"Found alternative config file: {alt_path}")
                config_file = str(alt_path)
                break
        else:
            # Look in default config directory
            for ext in alt_extensions:
                alt_path = Path(DEFAULT_CONFIG_DIR) / path.with_suffix(ext).name
                if alt_path.exists():
                    logging.info(f"Found config in default directory: {alt_path}")
                    config_file = str(alt_path)
                    break
            else:
                logging.warning("No configuration file found, using defaults and environment variables")
                return override_config_from_env(BotConfig())  # Use defaults

    try:
        # Determine file type and parse accordingly
        path = Path(config_file)
        if path.suffix.lower() in ['.yaml', '.yml']:
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f)
        else:  # Default to JSON
            with open(config_file, "r") as f:
                config_data = json.load(f)
        
        # Create config object with loaded data
        config = create_config_from_dict(config_data)
        
        # Update with environment variables
        config = override_config_from_env(config)
        
        # Set last updated timestamp
        config.lastUpdated = datetime.datetime.now().isoformat()
        
        # Configure logging level based on config
        setup_logging(config.loggingLevel)
        
        # Log loaded configuration (without API keys)
        log_config_summary(config)
        
        return config
    
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {config_file}: {e}")
        raise ConfigError(f"Invalid JSON in config file: {e}")
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML from {config_file}: {e}")
        raise ConfigError(f"Invalid YAML in config file: {e}")
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
        raise ConfigError(f"Configuration loading error: {e}")

def create_config_from_dict(data: Dict[str, Any]) -> BotConfig:
    """
    Create a config object from a dictionary.
    
    Args:
        data: Dictionary with configuration data
    
    Returns:
        BotConfig: Configuration object
    """
    # Extract sections with defaults
    api_keys_data = data.get("apiKeys", {})
    social_settings_data = data.get("socialSettings", {})
    trading_settings_data = data.get("tradingSettings", {})
    risk_settings_data = data.get("riskSettings", {})
    network_settings_data = data.get("networkSettings", {})
    
    # Create config object
    config = BotConfig(
        apiKeys=ApiKeys(**api_keys_data) if api_keys_data else ApiKeys(),
        socialSettings=SocialSettings(**social_settings_data) if social_settings_data else SocialSettings(),
        tradingSettings=TradingSettings(**trading_settings_data) if trading_settings_data else TradingSettings(),
        riskSettings=RiskSettings(**risk_settings_data) if risk_settings_data else RiskSettings(),
        networkSettings=NetworkSettings(**network_settings_data) if network_settings_data else NetworkSettings(),
        loggingLevel=data.get("loggingLevel", "INFO"),
        environment=data.get("environment", "production"),
        lastUpdated=data.get("lastUpdated", "")
    )
    
    return config

def override_config_from_env(config: BotConfig) -> BotConfig:
    """
    Override configuration with environment variables.
    
    Args:
        config: Configuration object to update
    
    Returns:
        BotConfig: Updated configuration object
    """
    # API Keys
    config.apiKeys.openai = os.getenv("OPENAI_API_KEY", config.apiKeys.openai)
    config.apiKeys.telegramBot = os.getenv("TELEGRAM_BOT_API_KEY", config.apiKeys.telegramBot)
    config.apiKeys.rugCheck = os.getenv("RUGCHECK_API_KEY", config.apiKeys.rugCheck)
    config.apiKeys.birdeye = os.getenv("BIRDEYE_API_KEY", config.apiKeys.birdeye)
    config.apiKeys.jupiter = os.getenv("JUPITER_API_KEY", config.apiKeys.jupiter)
    
    # Social Settings
    config.socialSettings.twitterBearerToken = os.getenv("TWITTER_BEARER_TOKEN", config.socialSettings.twitterBearerToken)
    config.socialSettings.discordWebhook = os.getenv("DISCORD_WEBHOOK", config.socialSettings.discordWebhook)
    config.socialSettings.telegramChatId = os.getenv("TELEGRAM_CHAT_ID", config.socialSettings.telegramChatId)
    
    # Trading Settings
    env_liquidity = os.getenv("LIQUIDITY_THRESHOLD")
    if env_liquidity:
        config.tradingSettings.liquidityThreshold = float(env_liquidity)
    
    env_trade_size = os.getenv("TRADE_SIZE")
    if env_trade_size:
        config.tradingSettings.tradeSize = float(env_trade_size)
    
    env_max_trades = os.getenv("MAX_DAILY_TRADES")
    if env_max_trades:
        config.tradingSettings.maxDailyTrades = int(env_max_trades)
    
    # Auto-trading must be explicitly enabled
    env_auto_trading = os.getenv("ENABLE_AUTO_TRADING", "").lower()
    config.tradingSettings.enableAutoTrading = env_auto_trading in ["true", "yes", "1"]
    
    # Risk Settings
    env_max_risk = os.getenv("MAX_PORTFOLIO_RISK")
    if env_max_risk:
        config.riskSettings.maxPortfolioRisk = float(env_max_risk)
    
    env_max_position = os.getenv("MAX_POSITION_SIZE")
    if env_max_position:
        config.riskSettings.maxPositionSize = float(env_max_position)
    
    # Network Settings
    config.networkSettings.rpcUrl = os.getenv("SOLANA_RPC_URL", config.networkSettings.rpcUrl)
    
    env_fallback_urls = os.getenv("SOLANA_FALLBACK_RPC_URLS")
    if env_fallback_urls:
        config.networkSettings.fallbackRpcUrls = [url.strip() for url in env_fallback_urls.split(",")]
    
    # General Settings
    config.loggingLevel = os.getenv("LOGGING_LEVEL", config.loggingLevel)
    config.environment = os.getenv("ENVIRONMENT", config.environment)
    
    return config

def setup_logging(level_name: str) -> None:
    """
    Configure logging based on level name.
    
    Args:
        level_name: Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    level = level_map.get(level_name.upper(), logging.INFO)
    logging.getLogger().setLevel(level)
    logging.info(f"Logging level set to {level_name}")

def log_config_summary(config: BotConfig) -> None:
    """
    Log a summary of the loaded configuration without sensitive data.
    
    Args:
        config: Configuration object
    """
    # Create a copy for logging (without sensitive data)
    log_data = asdict(config)
    
    # Remove sensitive data
    if "apiKeys" in log_data:
        for key in log_data["apiKeys"]:
            if log_data["apiKeys"][key]:
                log_data["apiKeys"][key] = "CONFIGURED"
            else:
                log_data["apiKeys"][key] = "NOT SET"
    
    if "socialSettings" in log_data:
        for key in log_data["socialSettings"]:
            if log_data["socialSettings"][key]:
                log_data["socialSettings"][key] = "CONFIGURED"
            else:
                log_data["socialSettings"][key] = "NOT SET"
    
    # Log configuration summary
    logging.info("Configuration loaded successfully:")
    logging.info(f"  Environment: {config.environment}")
    logging.info(f"  Auto-trading: {'ENABLED' if config.tradingSettings.enableAutoTrading else 'DISABLED'}")
    logging.info(f"  Trading size: {config.tradingSettings.tradeSize} SOL")
    logging.info(f"  Max daily trades: {config.tradingSettings.maxDailyTrades}")
    logging.info(f"  Liquidity threshold: ${config.tradingSettings.liquidityThreshold}")
    logging.info(f"  Blacklisted tokens: {len(config.riskSettings.blacklistedCoins)}")
    
    # Log API keys status
    logging.info("API Keys:")
    for key, value in log_data["apiKeys"].items():
        logging.info(f"  {key}: {value}")

def save_config(config: BotConfig, config_file: str = DEFAULT_CONFIG_FILE) -> None:
    """
    Save configuration to a file.
    
    Args:
        config: Configuration object
        config_file: Path to save the configuration file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(config_file)), exist_ok=True)
        
        # Update timestamp
        config.lastUpdated = datetime.datetime.now().isoformat()
        
        # Convert to dictionary
        config_dict = asdict(config)
        
        # Determine file type and save accordingly
        path = Path(config_file)
        if path.suffix.lower() in ['.yaml', '.yml']:
            with open(config_file, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        else:  # Default to JSON
            with open(config_file, "w") as f:
                json.dump(config_dict, f, indent=2)
        
        logging.info(f"Configuration saved to {config_file}")
    
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        raise ConfigError(f"Configuration saving error: {e}")

def create_default_config(config_file: str = DEFAULT_CONFIG_FILE) -> BotConfig:
    """
    Create a default configuration file if it doesn't exist.
    
    Args:
        config_file: Path to save the configuration file
    
    Returns:
        BotConfig: Default configuration object
    """
    if os.path.exists(config_file):
        logging.warning(f"Configuration file {config_file} already exists. Not overwriting.")
        return load_config(config_file)
    
    # Create default configuration
    config = BotConfig()
    
    # Risk settings defaults
    config.riskSettings.blacklistedCoins = [
        "11111111111111111111111111111111",  # Example blacklisted address
        "SoLEGNVQfVPMvYVtx7SySvwTQTc6ogiu1QJbNzWYh"  # Example blacklisted address
    ]
    
    # Network settings defaults
    config.networkSettings.fallbackRpcUrls = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-api.projectserum.com"
    ]
    
    # Save the default configuration
    save_config(config, config_file)
    logging.info(f"Default configuration created at {config_file}")
    
    return config

def get_environment_type() -> str:
    """
    Determine the environment type (development, staging, production).
    
    Returns:
        str: Environment type
    """
    return os.getenv("ENVIRONMENT", "production").lower()

def is_production() -> bool:
    """
    Check if the environment is production.
    
    Returns:
        bool: True if environment is production
    """
    return get_environment_type() == "production"

def is_trading_enabled(config: BotConfig) -> bool:
    """
    Check if auto-trading is enabled based on configuration and environment.
    
    Args:
        config: Configuration object
    
    Returns:
        bool: True if trading is enabled
    """
    if not config.tradingSettings.enableAutoTrading:
        logging.info("Auto-trading is disabled in configuration")
        return False
    
    if get_environment_type() != "production" and not os.getenv("FORCE_TRADING", "").lower() in ["true", "yes", "1"]:
        logging.warning(f"Auto-trading disabled in {get_environment_type()} environment without FORCE_TRADING")
        return False
    
    return True

if __name__ == "__main__":
    try:
        # If no config exists, create a default one
        if not os.path.exists(DEFAULT_CONFIG_FILE):
            config = create_default_config(DEFAULT_CONFIG_FILE)
            print(f"Created default configuration at {DEFAULT_CONFIG_FILE}")
        else:
            # Load existing configuration
            config = load_config(DEFAULT_CONFIG_FILE)
            print("Configuration loaded successfully.")
        
        # Display configuration summary
        print("\nConfiguration Summary:")
        print(f"Environment: {config.environment}")
        print(f"Auto-Trading: {'Enabled' if config.tradingSettings.enableAutoTrading else 'Disabled'}")
        print(f"Trading Size: {config.tradingSettings.tradeSize} SOL")
        print(f"Max Daily Trades: {config.tradingSettings.maxDailyTrades}")
        print(f"Liquidity Threshold: ${config.tradingSettings.liquidityThreshold}")
        
        # Check if trading is enabled
        if is_trading_enabled(config):
            print("\nAuto-trading is ENABLED")
        else:
            print("\nAuto-trading is DISABLED")
    
    except Exception as e:
        print(f"Configuration error: {e}")