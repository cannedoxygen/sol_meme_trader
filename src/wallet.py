import os
import logging
import json
import base64
from enum import Enum
from typing import Optional, List, Dict, Any, Union

# Solana dependencies
from solders.keypair import Keypair  # Using solders for keypair handling
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.rpc.types import TokenAccountOpts
from solana.exceptions import SolanaRpcException
from dotenv import load_dotenv

# Retry mechanism
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Constants
SOL_MINT = "So11111111111111111111111111111111111111112"
LAMPORTS_PER_SOL = 1_000_000_000  # 10^9
MAX_BALANCE_CACHE_AGE = 30  # seconds

# Cache for token balances
_balance_cache = {}
_cache_timestamp = 0

class WalletError(Exception):
    """Base exception for wallet-related errors"""
    pass

class WalletLoadError(WalletError):
    """Exception raised when wallet loading fails"""
    pass

class RPCError(WalletError):
    """Exception raised for RPC communication issues"""
    pass

class BalanceError(WalletError):
    """Exception raised for balance-related issues"""
    pass

class TokenType(Enum):
    """Enum for token types"""
    SOL = "SOL"
    SPL = "SPL"

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(SolanaRpcException)
)
def get_solana_client() -> Client:
    """
    Initialize the Solana RPC client using the configured RPC URL with fallback options.
    
    Returns:
        Client: Solana RPC client instance.
    """
    # Primary RPC URL
    primary_rpc_url = os.getenv("SOLANA_RPC_URL")
    
    # Fallback RPC URLs (comma-separated in .env)
    fallback_urls = os.getenv("SOLANA_FALLBACK_RPC_URLS", "").split(",")
    fallback_urls = [url.strip() for url in fallback_urls if url.strip()]
    
    # Add default public RPCs as last resort
    if not fallback_urls:
        fallback_urls = ["https://api.mainnet-beta.solana.com", "https://solana-api.projectserum.com"]
    
    # Ensure we have a primary URL
    if not primary_rpc_url:
        if fallback_urls:
            primary_rpc_url = fallback_urls[0]
            fallback_urls = fallback_urls[1:]
            logging.warning("SOLANA_RPC_URL not set, using first fallback URL")
        else:
            logging.error("No Solana RPC URLs available")
            raise ValueError("Solana RPC URL is not set in .env and no fallbacks available")

    # Try connecting to primary RPC
    logging.info(f"Connecting to Solana RPC at {primary_rpc_url}")
    client = Client(primary_rpc_url)

    # Check if the RPC is reachable
    try:
        version = client.get_version()
        logging.info(f"Solana RPC Connection Successful: {version}")
        return client
    except Exception as e:
        logging.error(f"Error connecting to primary Solana RPC: {e}")
        
        # Try fallbacks if primary fails
        for fallback_url in fallback_urls:
            try:
                logging.info(f"Trying fallback RPC at {fallback_url}")
                client = Client(fallback_url)
                version = client.get_version()
                logging.info(f"Fallback RPC Connection Successful: {version}")
                return client
            except Exception as fallback_e:
                logging.error(f"Error connecting to fallback RPC {fallback_url}: {fallback_e}")
        
        # If we get here, all RPCs failed
        logging.critical("All Solana RPC connections failed")
        raise RPCError("Unable to connect to any Solana RPC endpoint")

def load_wallet() -> Keypair:
    """
    Load the Solana wallet keypair from the private key.
    Supports multiple formats (bytes array, base58, JSON).

    Returns:
        Keypair: Solana wallet keypair for signing transactions.
    """
    # Try different environment variable names for the private key
    private_key = os.getenv("SOLANA_WALLET_PRIVATE_KEY") or os.getenv("SOLANA_PRIVATE_KEY")
    
    if not private_key:
        logging.error("Solana wallet private key not found in environment variables")
        raise WalletLoadError("Solana wallet private key is not set in .env")

    try:
        # Check if it's a JSON bytes array
        if private_key.startswith("[") and private_key.endswith("]"):
            try:
                private_key_list = json.loads(private_key)
                
                # Validate the key length
                if len(private_key_list) != 64:
                    logging.error("Invalid Solana private key format: Incorrect length")
                    raise WalletLoadError("Solana private key must be 64 bytes")
                
                # Create keypair from bytes
                wallet = Keypair.from_bytes(bytes(private_key_list))
                log_wallet_info(wallet, "from bytes array")
                return wallet
            except json.JSONDecodeError:
                logging.warning("Private key looks like JSON but isn't valid, trying other formats...")
        
        # Check if it's a base58 encoded private key
        try:
            # First, assume it might be a base58 key
            wallet = Keypair.from_base58_string(private_key)
            log_wallet_info(wallet, "from base58 string")
            return wallet
        except Exception as e:
            logging.warning(f"Not a valid base58 key: {e}")
        
        # Try as a file path
        if os.path.exists(private_key):
            try:
                with open(private_key, 'r') as f:
                    file_content = f.read().strip()
                    if file_content.startswith("[") and file_content.endswith("]"):
                        private_key_list = json.loads(file_content)
                        wallet = Keypair.from_bytes(bytes(private_key_list))
                        log_wallet_info(wallet, "from key file")
                        return wallet
                    else:
                        raise WalletLoadError("Key file contains unrecognized format")
            except Exception as e:
                logging.error(f"Error reading key file: {e}")
        
        # If we got here, none of the formats worked
        raise WalletLoadError("Could not parse private key in any supported format")
    
    except Exception as e:
        logging.error(f"Error loading Solana wallet: {e}")
        raise WalletLoadError(f"Failed to load wallet: {e}")

def log_wallet_info(wallet: Keypair, source: str) -> None:
    """Log wallet information safely"""
    public_key = wallet.pubkey()
    logging.info(f"Solana wallet loaded successfully {source}. Public Key: {public_key}")

def get_sol_balance(client: Client, pubkey: Union[str, Pubkey]) -> float:
    """
    Get SOL balance for a wallet.
    
    Args:
        client: Solana RPC client
        pubkey: Wallet public key (string or Pubkey)
    
    Returns:
        float: Balance in SOL (not lamports)
    """
    try:
        # Convert string to Pubkey if needed
        if isinstance(pubkey, str):
            pubkey = Pubkey.from_string(pubkey)
        
        response = client.get_balance(pubkey)
        balance_lamports = response.value
        balance_sol = balance_lamports / LAMPORTS_PER_SOL
        logging.info(f"SOL Balance for {pubkey}: {balance_sol} SOL")
        return balance_sol
    except Exception as e:
        logging.error(f"Error getting SOL balance: {e}")
        raise BalanceError(f"Failed to get SOL balance: {e}")

def get_token_accounts(client: Client, wallet: Keypair) -> List[Dict[str, Any]]:
    """
    Get all SPL token accounts owned by the wallet.
    
    Args:
        client: Solana RPC client
        wallet: Wallet keypair
    
    Returns:
        List[Dict]: List of token accounts with balances
    """
    try:
        pubkey = wallet.pubkey()
        # Fix: Add program_id for SPL tokens
        program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")  # SPL Token program
        opts = TokenAccountOpts(program_id=program_id)
        response = client.get_token_accounts_by_owner(pubkey, opts)
        
        token_accounts = []
        for account in response.value:
            account_info = account.account.data.parsed
            if 'info' in account_info:
                token_info = account_info['info']
                token_accounts.append({
                    'mint': token_info.get('mint'),
                    'owner': token_info.get('owner'),
                    'amount': int(token_info.get('tokenAmount', {}).get('amount', 0)),
                    'decimals': token_info.get('tokenAmount', {}).get('decimals', 0),
                    'uiAmount': token_info.get('tokenAmount', {}).get('uiAmount', 0)
                })
        
        logging.info(f"Found {len(token_accounts)} token accounts for {pubkey}")
        return token_accounts
    except Exception as e:
        logging.error(f"Error getting token accounts: {e}")
        raise BalanceError(f"Failed to get token accounts: {e}")

def get_token_balance(client: Client, wallet: Keypair, token_mint: str) -> float:
    """
    Get balance for a specific SPL token.
    
    Args:
        client: Solana RPC client
        wallet: Wallet keypair
        token_mint: Token mint address
    
    Returns:
        float: Token balance in decimal format
    """
    try:
        # Special case for SOL
        if token_mint == SOL_MINT:
            return get_sol_balance(client, wallet.pubkey())
        
        # Get all token accounts
        accounts = get_token_accounts(client, wallet)
        
        # Find the specific token
        for account in accounts:
            if account['mint'] == token_mint:
                return account['uiAmount']
        
        # Token not found
        return 0.0
    except Exception as e:
        logging.error(f"Error getting token balance: {e}")
        raise BalanceError(f"Failed to get token balance: {e}")

def get_all_balances(client: Client, wallet: Keypair, refresh: bool = False) -> Dict[str, float]:
    """
    Get balances for all tokens owned by the wallet.
    Uses caching to prevent excessive RPC calls.
    
    Args:
        client: Solana RPC client
        wallet: Wallet keypair
        refresh: Force refresh the cache
    
    Returns:
        Dict[str, float]: Dictionary mapping token mints to balances
    """
    global _balance_cache, _cache_timestamp
    
    import time
    current_time = time.time()
    
    # Use cache if it's fresh enough and not forced to refresh
    if (not refresh and 
        _balance_cache and 
        current_time - _cache_timestamp < MAX_BALANCE_CACHE_AGE):
        logging.debug("Using cached wallet balances")
        return _balance_cache
    
    balances = {}
    
    try:
        # Get SOL balance
        balances[SOL_MINT] = get_sol_balance(client, wallet.pubkey())
        
        # Get SPL token balances
        accounts = get_token_accounts(client, wallet)
        for account in accounts:
            mint = account['mint']
            balances[mint] = account['uiAmount']
        
        # Update cache
        _balance_cache = balances
        _cache_timestamp = current_time
        
        logging.info(f"Wallet has {len(balances)} tokens including SOL")
        return balances
    except Exception as e:
        logging.error(f"Error getting all balances: {e}")
        raise BalanceError(f"Failed to get all balances: {e}")

def has_sufficient_balance(
    client: Client, 
    wallet: Keypair, 
    token_mint: str, 
    amount_needed: float
) -> bool:
    """
    Check if the wallet has sufficient balance for a token.
    
    Args:
        client: Solana RPC client
        wallet: Wallet keypair
        token_mint: Token mint address
        amount_needed: Amount needed in decimal format
    
    Returns:
        bool: True if sufficient balance is available
    """
    try:
        balance = get_token_balance(client, wallet, token_mint)
        is_sufficient = balance >= amount_needed
        
        if not is_sufficient:
            logging.warning(
                f"Insufficient balance: {balance} {token_mint} available, " +
                f"{amount_needed} needed"
            )
        
        return is_sufficient
    except Exception as e:
        logging.error(f"Error checking balance sufficiency: {e}")
        return False

def create_wallet_report(client: Client, wallet: Keypair) -> Dict[str, Any]:
    """
    Create a comprehensive report of wallet status.
    
    Args:
        client: Solana RPC client
        wallet: Wallet keypair
    
    Returns:
        Dict: Report with wallet information
    """
    try:
        pubkey = wallet.pubkey()
        balances = get_all_balances(client, wallet, refresh=True)
        
        # Format balances for reporting
        formatted_balances = []
        for mint, amount in balances.items():
            token_type = "SOL" if mint == SOL_MINT else "SPL"
            formatted_balances.append({
                "token_type": token_type,
                "mint": mint,
                "balance": amount
            })
        
        # Sort balances with SOL first, then by amount
        sorted_balances = sorted(
            formatted_balances,
            key=lambda x: (0 if x["token_type"] == "SOL" else 1, -x["balance"])
        )
        
        # Create the report
        report = {
            "wallet_address": str(pubkey),
            "sol_balance": balances.get(SOL_MINT, 0),
            "token_count": len(balances) - 1,  # Exclude SOL
            "balances": sorted_balances
        }
        
        logging.info(f"Wallet report generated for {pubkey}")
        return report
    except Exception as e:
        logging.error(f"Error creating wallet report: {e}")
        raise WalletError(f"Failed to create wallet report: {e}")

if __name__ == "__main__":
    try:
        # Basic connectivity and wallet test
        solana_client = get_solana_client()
        wallet = load_wallet()
        print(f"Wallet Public Key: {wallet.pubkey()}")
        
        # Generate wallet report
        report = create_wallet_report(solana_client, wallet)
        print("Wallet Report:")
        print(json.dumps(report, indent=2))
        
        # Example of balance check
        sol_balance = get_sol_balance(solana_client, wallet.pubkey())
        print(f"SOL Balance: {sol_balance}")
        
        # Example sufficiency check
        if has_sufficient_balance(solana_client, wallet, SOL_MINT, 0.1):
            print("Wallet has sufficient SOL for a 0.1 SOL transaction")
        else:
            print("Wallet does not have enough SOL")
    except Exception as e:
        logging.error(f"Critical error: {e}")