import logging
import requests
import json
import time
import base64
from typing import Dict, Any, Optional, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime

# Flexible import for different solana package versions
try:
    # Try newer solders package first
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction, VersionedTransaction
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    SOLANA_PACKAGE_VERSION = "new"
except ImportError:
    try:
        # Try older solana package
        from solana.keypair import Keypair
        from solana.publickey import PublicKey as Pubkey
        from solana.transaction import Transaction
        from solana.rpc.api import Client
        SOLANA_PACKAGE_VERSION = "old"
    except ImportError:
        # Fallback to simulation mode
        logging.warning("Solana packages not properly installed. Running in simulation mode only.")
        SOLANA_PACKAGE_VERSION = "simulation"
        
        # Define minimal classes for simulation
        class Keypair:
            def __init__(self):
                self.public_key = "SIMULATION_PUBKEY"
            
            def pubkey(self):
                return "SIMULATION_PUBKEY"
                
        class Pubkey:
            @staticmethod
            def from_string(s):
                return "SIMULATION_PUBKEY"
                
        class Transaction:
            def __init__(self, *args, **kwargs):
                pass
                
        class Client:
            def __init__(self, *args, **kwargs):
                pass
            
            def get_recent_blockhash(self):
                return {"result": {"value": {"blockhash": "SIMULATION_BLOCKHASH"}}}
            
            def send_transaction(self, *args, **kwargs):
                return {"result": "SIMULATED_TX_SIGNATURE"}

# Configure production logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Constants
JUPITER_API_BASE = "https://quote-api.jup.ag/v6"
LAMPORTS_PER_SOL = 1_000_000_000  # 10^9
SLIPPAGE_BPS_DEFAULT = 50  # 0.5%
RETRIES_DEFAULT = 3
MAX_TRANSACTION_SIZE = 1232  # bytes
DEFAULT_PRIORITY_FEE = 100  # lamports per compute unit

def swap_via_jupiter(
    solana_client: Client, 
    wallet: Keypair, 
    token_in: str, 
    token_out: str, 
    amount_in: int,
    slippage_bps: int = SLIPPAGE_BPS_DEFAULT,
    priority_fee: int = DEFAULT_PRIORITY_FEE
) -> Optional[str]:
    """
    Execute a swap using the Jupiter API to trade tokens on Solana.
    
    Args:
        solana_client: Instance of Solana client for on-chain communication
        wallet: Wallet object with signing capabilities
        token_in: Mint address of the input token (e.g., SOL)
        token_out: Mint address of the target token
        amount_in: Amount to trade in the smallest unit (e.g., lamports)
        slippage_bps: Slippage tolerance in basis points (1 bp = 0.01%)
        priority_fee: Priority fee in lamports per compute unit
    
    Returns:
        str: Transaction signature if successful, or None if failed
    """
    logging.info(f"Executing trade: Swap {amount_in} units of {token_in} for {token_out}")
    
    # Check if we're in simulation mode
    if SOLANA_PACKAGE_VERSION == "simulation":
        logging.warning("SIMULATION MODE: No actual transaction will be executed")
        time.sleep(2)  # Simulate processing time
        tx_sig = f"SIMULATED_TX_{int(time.time())}"
        logging.info(f"Simulated trade executed. Tx Signature: {tx_sig}")
        return tx_sig
    
    try:
        # Step 1: Get a quote from Jupiter
        quote = get_jupiter_quote(token_in, token_out, amount_in, slippage_bps)
        if not quote:
            logging.error("Failed to get quote from Jupiter")
            return None
        
        # Step 2: Get the swap transaction
        swap_tx = get_jupiter_swap_transaction(quote, wallet.pubkey())
        if not swap_tx:
            logging.error("Failed to get swap transaction from Jupiter")
            return None
        
        # Step 3: Sign and send the transaction
        tx_data = swap_tx.get("swapTransaction")
        if not tx_data:
            logging.error("No swap transaction data received from Jupiter")
            return None
        
        # Convert from base64 to bytes
        tx_bytes = base64.b64decode(tx_data)
        
        # Send the serialized transaction
        tx_sig = send_transaction(solana_client, wallet, tx_bytes, priority_fee)
        if tx_sig:
            logging.info(f"Trade executed successfully. Tx Signature: {tx_sig}")
            
            # Wait for confirmation
            confirm_transaction(solana_client, tx_sig)
            
            return tx_sig
        else:
            logging.error("Failed to send transaction")
            return None
            
    except Exception as e:
        logging.error(f"Error executing trade: {e}")
        return None

@retry(
    stop=stop_after_attempt(RETRIES_DEFAULT),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
def get_jupiter_quote(
    token_in: str, 
    token_out: str, 
    amount_in: int,
    slippage_bps: int = SLIPPAGE_BPS_DEFAULT
) -> Optional[Dict[str, Any]]:
    """
    Get a quote from Jupiter API for a token swap.
    
    Args:
        token_in: Input token mint address
        token_out: Output token mint address
        amount_in: Amount of input token (in smallest units)
        slippage_bps: Slippage tolerance in basis points
        
    Returns:
        Dict containing the quote information or None if failed
    """
    url = f"{JUPITER_API_BASE}/quote"
    params = {
        "inputMint": token_in,
        "outputMint": token_out,
        "amount": amount_in,
        "slippageBps": slippage_bps
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        quote = response.json()
        
        logging.info(f"Jupiter quote: {amount_in} of {token_in} → {quote.get('outAmount')} of {token_out} " +
                    f"(Impact: {quote.get('priceImpactPct', 0)}%)")
        return quote
    except requests.RequestException as e:
        logging.error(f"Error getting Jupiter quote: {e}")
        raise  # Will be retried
    except Exception as e:
        logging.error(f"Unexpected error getting Jupiter quote: {e}")
        return None

@retry(
    stop=stop_after_attempt(RETRIES_DEFAULT),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
def get_jupiter_swap_transaction(quote: Dict[str, Any], user_public_key: Union[str, Pubkey]) -> Optional[Dict[str, Any]]:
    """
    Get a swap transaction from Jupiter API using a quote.
    
    Args:
        quote: Quote object from get_jupiter_quote
        user_public_key: User's public key for the transaction
        
    Returns:
        Dict containing the swap transaction or None if failed
    """
    url = f"{JUPITER_API_BASE}/swap"
    
    # Convert Pubkey to string if needed
    if hasattr(user_public_key, 'to_string'):
        user_public_key = user_public_key.to_string()
    elif hasattr(user_public_key, '__str__'):
        user_public_key = str(user_public_key)
    
    # Extract data from quote
    data = {
        "quoteResponse": quote,
        "userPublicKey": user_public_key,
        "wrapUnwrapSOL": True  # Handle wrapping/unwrapping SOL automatically
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        swap_tx = response.json()
        
        logging.info(f"Jupiter swap transaction received")
        return swap_tx
    except requests.RequestException as e:
        logging.error(f"Error getting Jupiter swap transaction: {e}")
        raise  # Will be retried
    except Exception as e:
        logging.error(f"Unexpected error getting Jupiter swap transaction: {e}")
        return None

def send_transaction(
    solana_client: Client, 
    wallet: Keypair, 
    tx_bytes: bytes,
    priority_fee: int = DEFAULT_PRIORITY_FEE
) -> Optional[str]:
    """
    Send a serialized transaction to the Solana network.
    
    Args:
        solana_client: Solana RPC client
        wallet: Wallet keypair for signing
        tx_bytes: Serialized transaction bytes
        priority_fee: Priority fee in lamports per compute unit
        
    Returns:
        Transaction signature if successful, None otherwise
    """
    try:
        if SOLANA_PACKAGE_VERSION == "simulation":
            tx_sig = f"SIMULATED_TX_{int(time.time())}"
            return tx_sig
        
        # For versioned transactions (solders)
        if SOLANA_PACKAGE_VERSION == "new" and hasattr(VersionedTransaction, 'deserialize'):
            try:
                # Try to deserialize as a versioned transaction first
                tx = VersionedTransaction.deserialize(tx_bytes)
                # Set compute budget for priority fee if needed
                if priority_fee > 0:
                    # Note: In a real implementation, we'd need to add compute budget instruction
                    # But Jupiter transactions should already include it
                    pass
                
                # Sign the transaction 
                # Note: Jupiter transactions come pre-signed, we just need to submit
                # But if additional signing is needed:
                # tx.sign([wallet])
                
                # Send the transaction
                opts = TxOpts(skip_preflight=False, preflight_commitment="confirmed")
                result = solana_client.send_transaction(tx, opts=opts)
                tx_sig = result.value
                return tx_sig
            except Exception as e:
                logging.warning(f"Failed to process as versioned transaction: {e}")
                # Fall back to legacy transaction format
                pass
        
        # For legacy transactions
        # This is a simplified implementation for older Solana package versions
        # In a real implementation, we would handle both transaction types properly
        logging.info("Sending transaction using legacy method")
        result = solana_client.send_raw_transaction(
            tx_bytes, 
            opts={"skipPreflight": False, "preflightCommitment": "confirmed"}
        )
        tx_sig = result["result"]
        return tx_sig
        
    except Exception as e:
        logging.error(f"Error sending transaction: {e}")
        return None

def confirm_transaction(solana_client: Client, signature: str, max_retries: int = 40, retry_delay: float = 0.5) -> bool:
    """
    Confirm a transaction has been processed by the network.
    
    Args:
        solana_client: Solana RPC client
        signature: Transaction signature to confirm
        max_retries: Maximum number of confirmation attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    if SOLANA_PACKAGE_VERSION == "simulation":
        time.sleep(1)  # Simulate confirmation delay
        return True
        
    for i in range(max_retries):
        try:
            response = solana_client.get_signature_statuses([signature])
            status = response["result"]["value"][0]
            
            if status is None:
                logging.debug(f"Transaction {signature} not found yet. Retry {i+1}/{max_retries}")
            elif status.get("err") is not None:
                logging.error(f"Transaction {signature} failed: {status['err']}")
                return False
            elif status.get("confirmationStatus") == "confirmed" or status.get("confirmations", 0) > 0:
                logging.info(f"Transaction {signature} confirmed!")
                return True
                
            time.sleep(retry_delay)
        except Exception as e:
            logging.error(f"Error checking transaction status: {e}")
            time.sleep(retry_delay)
            
    logging.warning(f"Transaction {signature} not confirmed after {max_retries} attempts")
    return False

def execute_buy(
    solana_client: Client, 
    wallet: Keypair, 
    token_in: str, 
    token_out: str, 
    amount_in: int,
    slippage_bps: int = SLIPPAGE_BPS_DEFAULT,
    priority_fee: int = DEFAULT_PRIORITY_FEE
) -> Optional[str]:
    """
    Execute a BUY order using the swap function.
    
    Args:
        solana_client: Solana RPC client
        wallet: Wallet keypair
        token_in: Input token mint (usually SOL)
        token_out: Token to be bought
        amount_in: Amount of token_in to swap
        slippage_bps: Slippage tolerance in basis points
        priority_fee: Priority fee in lamports per compute unit
        
    Returns:
        Transaction signature or None
    """
    logging.info(f"Initiating BUY order: Swap {amount_in} of {token_in} for {token_out}")
    tx_signature = swap_via_jupiter(solana_client, wallet, token_in, token_out, amount_in, slippage_bps, priority_fee)
    
    if tx_signature:
        logging.info(f"BUY order executed. Tx Signature: {tx_signature}")
    else:
        logging.error("BUY order failed.")
    
    return tx_signature

def execute_sell(
    solana_client: Client, 
    wallet: Keypair, 
    token_in: str, 
    token_out: str, 
    amount_in: int,
    slippage_bps: int = SLIPPAGE_BPS_DEFAULT,
    priority_fee: int = DEFAULT_PRIORITY_FEE
) -> Optional[str]:
    """
    Execute a SELL order using the swap function.
    
    Args:
        solana_client: Solana RPC client
        wallet: Wallet keypair
        token_in: Token to sell
        token_out: Token to receive (usually SOL)
        amount_in: Amount of token_in to swap
        slippage_bps: Slippage tolerance in basis points
        priority_fee: Priority fee in lamports per compute unit
        
    Returns:
        Transaction signature or None
    """
    logging.info(f"Initiating SELL order: Swap {amount_in} of {token_in} for {token_out}")
    tx_signature = swap_via_jupiter(solana_client, wallet, token_in, token_out, amount_in, slippage_bps, priority_fee)
    
    if tx_signature:
        logging.info(f"SELL order executed. Tx Signature: {tx_signature}")
    else:
        logging.error("SELL order failed.")
    
    return tx_signature

def estimate_swap(
    token_in: str, 
    token_out: str, 
    amount_in: int,
    slippage_bps: int = SLIPPAGE_BPS_DEFAULT
) -> Dict[str, Any]:
    """
    Estimate the result of a swap without executing it.
    
    Args:
        token_in: Input token mint
        token_out: Output token mint
        amount_in: Amount of input token (in smallest units)
        slippage_bps: Slippage tolerance in basis points
        
    Returns:
        Dict with swap estimate details
    """
    try:
        quote = get_jupiter_quote(token_in, token_out, amount_in, slippage_bps)
        if not quote:
            return {
                "success": False,
                "error": "Failed to get quote"
            }
        
        return {
            "success": True,
            "input_amount": amount_in,
            "output_amount": int(quote.get("outAmount", 0)),
            "price_impact_pct": quote.get("priceImpactPct", 0),
            "minimum_received": int(quote.get("otherAmountThreshold", 0)),
            "platform_fee": quote.get("platformFee", 0),
            "route_plan": quote.get("routePlan", [])
        }
    except Exception as e:
        logging.error(f"Error estimating swap: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def get_token_balance(client: Client, wallet: Keypair, token_address: str) -> int:
    """
    Get the token balance for a specific token address
    
    Args:
        client: Solana RPC client
        wallet: Wallet keypair
        token_address: Token mint address
    
    Returns:
        int: Token balance in smallest units (or 0 if error)
    """
    if SOLANA_PACKAGE_VERSION == "simulation":
        return 1000000000  # Return dummy value in simulation mode
    
    try:
        # For SOL token, get SOL balance
        if token_address == "So11111111111111111111111111111111111111112":
            response = client.get_balance(wallet.pubkey())
            return response.value
            
        # For SPL tokens, get token accounts
        from spl.token.client import Token
        from spl.token.constants import TOKEN_PROGRAM_ID

        # Get token accounts owned by the wallet
        token_accounts = client.get_token_accounts_by_owner(
            wallet.pubkey(),
            {"mint": Pubkey.from_string(token_address)}
        )
        
        # Find the token account for this mint
        balance = 0
        for account in token_accounts.value:
            # Parse the token account data
            account_data = Token.unpack_account_data(account.account.data)
            balance += account_data.amount
            
        return balance
    except Exception as e:
        logging.error(f"Error getting token balance for {token_address}: {e}")
        return 0

if __name__ == "__main__":
    # For testing, we simulate a buy and sell order.
    # In production, solana_client and wallet should be properly instantiated objects.
    
    # Create dummy client and wallet for testing
    solana_client = Client("https://api.mainnet-beta.solana.com")
    wallet = Keypair()  # This creates a random keypair for testing
    
    # SOL mint address
    sol_mint = "So11111111111111111111111111111111111111112"
    # Example meme token address
    meme_token = "EXAMPLE_TOKEN_MINT_ADDRESS"
    
    # Test a simulated BUY order: swapping SOL for a meme token.
    buy_result = execute_buy(
        solana_client, 
        wallet, 
        token_in=sol_mint, 
        token_out=meme_token, 
        amount_in=100000000  # 0.1 SOL in lamports
    )
    
    if buy_result:
        print(f"Buy successful with tx signature: {buy_result}")
    
    # Test a simulated SELL order: swapping the meme token back to SOL.
    sell_result = execute_sell(
        solana_client, 
        wallet, 
        token_in=meme_token, 
        token_out=sol_mint, 
        amount_in=1000000  # Example token amount
    )
    
    if sell_result:
        print(f"Sell successful with tx signature: {sell_result}")
        
    # Test swap estimation
    estimate = estimate_swap(
        token_in=sol_mint,
        token_out=meme_token,
        amount_in=100000000  # 0.1 SOL in lamports
    )
    
    print("Swap Estimate:")
    print(json.dumps(estimate, indent=2))