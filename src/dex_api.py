import requests
import logging
import os
import json
from datetime import datetime, timezone, timedelta
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging with detailed output
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Base URLs for APIs
BIRDEYE_BASE = "https://public-api.birdeye.so"
JUPITER_BASE = "https://quote-api.jup.ag/v6"

# API Keys from .env
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
if not BIRDEYE_API_KEY:
    raise ValueError("BIRDEYE_API_KEY not found in .env file")

# Timeframe and thresholds
NEW_TOKEN_TIMEFRAME_MINUTES = int(os.getenv("NEW_TOKEN_TIMEFRAME_MINUTES", "1440"))  # 24 hours default
BOOSTED_VOLUME_THRESHOLD = float(os.getenv("BOOSTED_VOLUME_THRESHOLD", "10000"))  # $10,000 default
MIN_LIQUIDITY_THRESHOLD = float(os.getenv("MIN_LIQUIDITY_THRESHOLD", "1000"))  # $1,000 default

# Cache for token metadata to reduce API calls
token_metadata_cache = {}
cache_expiry = {}
CACHE_DURATION = 3600  # 1 hour in seconds

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_new_solana_tokens():
    """
    Fetch newly listed Solana tokens from Birdeye's /defi/v2/tokens/new_listing endpoint.
    Returns:
        list: New Solana tokens listed within the configured timeframe
    """
    url = f"{BIRDEYE_BASE}/defi/v2/tokens/new_listing"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": BIRDEYE_API_KEY,
        "x-chain": "solana"
    }
    
    try:
        logging.debug(f"Requesting new tokens from {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if response.status_code != 200:
            logging.error(f"API returned non-200 status: {response.status_code}")
            logging.error(f"Response: {data}")
            return []
            
        logging.debug(f"Response status: {response.status_code}")
        
        tokens = data.get("data", {}).get("items", [])
        logging.info(f"Total tokens received: {len(tokens)}")
        
        current_time = datetime.now(timezone.utc)
        new_tokens = []
        boosted_tokens = []
        seen_tokens = set()  # Reset per poll

        for token in tokens:
            listing_time_str = token.get("liquidityAddedAt")
            if not listing_time_str:
                logging.debug(f"Skipping {token.get('address')}: No liquidityAddedAt")
                continue
                
            # Parse string like "2025-02-25T23:23:29" to datetime
            list_time = datetime.strptime(listing_time_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            age_minutes = (current_time - list_time).total_seconds() / 60
            token_address = token.get("address")
            token_name = token.get("name", "").lower()
            token_symbol = token.get("symbol", "").lower()
            volume_24h_usd = token.get("v24hUSD", 0)  # May be absent in new listings
            liquidity_usd = token.get("liquidity", 0)
            
            if age_minutes < NEW_TOKEN_TIMEFRAME_MINUTES:
                logging.debug(f"Token {token_address}: Age {age_minutes:.2f} min, Name: {token_name}, Symbol: {token_symbol}, Volume 24h: ${volume_24h_usd}, Liquidity: ${liquidity_usd}")
            
            if (age_minutes < NEW_TOKEN_TIMEFRAME_MINUTES and 
                token_address and 
                token_address not in seen_tokens and
                liquidity_usd >= MIN_LIQUIDITY_THRESHOLD):
                
                # Enrich token data with additional fields
                token_entry = {
                    "address": token_address,
                    "name": token_name,
                    "symbol": token_symbol,
                    "listingTime": listing_time_str,
                    "age_minutes": age_minutes,
                    "v24hUSD": volume_24h_usd,
                    "liquidity": liquidity_usd,
                    "marketCap": token.get("mc", 0),
                    "priceUSD": token.get("price", 0),
                    "holders": token.get("holders", 0),
                    "is_boosted": volume_24h_usd > BOOSTED_VOLUME_THRESHOLD
                }
                
                # Add metadata if available
                metadata = get_token_metadata(token_address)
                if metadata:
                    token_entry.update(metadata)
                
                new_tokens.append(token_entry)
                seen_tokens.add(token_address)
                logging.info(f"Added token: {token_name} (Age: {age_minutes:.2f} min, Boosted: {token_entry['is_boosted']}, Volume: ${volume_24h_usd}, Liquidity: ${liquidity_usd})")
                
                if token_entry["is_boosted"]:
                    boosted_tokens.append(token_entry)

        logging.info(f"Fetched {len(new_tokens)} new Solana tokens (last {NEW_TOKEN_TIMEFRAME_MINUTES/60:.1f} hours), {len(boosted_tokens)} boosted")
        return new_tokens

    except requests.RequestException as e:
        logging.error(f"Error fetching new Solana tokens: {e}")
        raise  # Let tenacity handle the retry
    except Exception as e:
        logging.error(f"Unexpected error in get_new_solana_tokens: {e}")
        return []

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
def get_token_metadata(token_address):
    """
    Get detailed metadata for a specific token.
    Caches results to reduce API calls.
    """
    # Check if we have cached data that's still valid
    current_time = time.time()
    if token_address in token_metadata_cache and current_time < cache_expiry.get(token_address, 0):
        logging.debug(f"Using cached metadata for {token_address}")
        return token_metadata_cache[token_address]
    
    url = f"{BIRDEYE_BASE}/defi/v2/token-metadata"
    params = {
        "address": token_address
    }
    headers = {
        "Accept": "application/json",
        "X-API-KEY": BIRDEYE_API_KEY,
        "x-chain": "solana"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        metadata = data.get("data", {})
        if metadata:
            # Extract relevant fields
            result = {
                "description": metadata.get("description", ""),
                "website": metadata.get("website", ""),
                "twitter": metadata.get("twitter", ""),
                "discord": metadata.get("discord", ""),
                "telegram": metadata.get("telegram", ""),
                "coingecko_id": metadata.get("coingeckoId", "")
            }
            
            # Cache the result
            token_metadata_cache[token_address] = result
            cache_expiry[token_address] = current_time + CACHE_DURATION
            
            return result
        return {}
    except Exception as e:
        logging.warning(f"Failed to get metadata for {token_address}: {e}")
        return {}

def get_trending_tokens(limit=20):
    """
    Get trending tokens based on various metrics (volume, price increase, etc.)
    
    Returns:
        list: Top trending tokens with metadata
    """
    url = f"{BIRDEYE_BASE}/defi/v2/trending-tokens"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": BIRDEYE_API_KEY,
        "x-chain": "solana"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        tokens = data.get("data", {}).get("items", [])
        trending_tokens = []
        
        for i, token in enumerate(tokens[:limit]):
            token_entry = {
                "address": token.get("address"),
                "name": token.get("name", ""),
                "symbol": token.get("symbol", ""),
                "priceUSD": token.get("price", 0),
                "v24hUSD": token.get("v24hUSD", 0),
                "priceChange24h": token.get("priceChange24h", 0),
                "liquidity": token.get("liquidity", 0),
                "marketCap": token.get("mc", 0),
                "trending_rank": i+1
            }
            trending_tokens.append(token_entry)
            
        logging.info(f"Fetched {len(trending_tokens)} trending tokens")
        return trending_tokens
    except Exception as e:
        logging.error(f"Error fetching trending tokens: {e}")
        return []

def get_token_price_history(token_address, timeframe="1H"):
    """
    Get historical price data for a specific token
    
    Args:
        token_address (str): Token mint address
        timeframe (str): Timeframe for chart data, e.g., "1H", "1D", "1W"
        
    Returns:
        list: Historical price data points
    """
    url = f"{BIRDEYE_BASE}/defi/v2/history-price"
    params = {
        "address": token_address,
        "timeframe": timeframe
    }
    headers = {
        "Accept": "application/json",
        "X-API-KEY": BIRDEYE_API_KEY,
        "x-chain": "solana"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        price_history = data.get("data", {}).get("items", [])
        logging.info(f"Fetched {len(price_history)} price data points for {token_address}")
        return price_history
    except Exception as e:
        logging.error(f"Error fetching price history for {token_address}: {e}")
        return []

def estimate_swap_price(token_in, token_out, amount_in):
    """
    Get an estimated price for swapping tokens using Jupiter API
    
    Args:
        token_in (str): Input token mint address
        token_out (str): Output token mint address
        amount_in (int): Amount of input token (in smallest units)
        
    Returns:
        dict: Swap quote with price, impact, etc.
    """
    url = f"{JUPITER_BASE}/quote"
    params = {
        "inputMint": token_in,
        "outputMint": token_out,
        "amount": amount_in,
        "slippageBps": 50  # 0.5% slippage
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        quote = response.json()
        
        result = {
            "input_amount": quote.get("inputAmount"),
            "output_amount": quote.get("outputAmount"),
            "price_impact_pct": quote.get("priceImpactPct"),
            "route_plan": quote.get("routePlan", [])
        }
        
        logging.info(f"Swap estimate: {amount_in} of {token_in} → {result['output_amount']} of {token_out} (Impact: {result['price_impact_pct']}%)")
        return result
    except Exception as e:
        logging.error(f"Error getting swap quote: {e}")
        return None

def poll_solana_tokens(num_requests=60, period=3600):
    """
    Poll Birdeye for new and boosted Solana tokens.
    
    Args:
        num_requests (int): Number of API requests to make during the period
        period (int): Total polling period in seconds
        
    Yields:
        list: New tokens found in each polling cycle
    """
    delay = period / num_requests
    while True:
        try:
            tokens = get_new_solana_tokens()
            unique_tokens = []
            seen_in_cycle = set()
            
            for token in tokens:
                address = token.get("address")
                if address and address not in seen_in_cycle:
                    unique_tokens.append(token)
                    seen_in_cycle.add(address)
            
            # Also check trending tokens occasionally (every 5 polls)
            current_time = time.time()
            if int(current_time / delay) % 5 == 0:
                trending = get_trending_tokens(limit=10)
                for token in trending:
                    address = token.get("address")
                    if address and address not in seen_in_cycle:
                        token["from_trending"] = True
                        unique_tokens.append(token)
                        seen_in_cycle.add(address)
                        
            logging.info(f"Polled {len(unique_tokens)} unique Solana tokens")
            yield unique_tokens
            time.sleep(delay)
        except Exception as e:
            logging.error(f"Error in polling cycle: {e}")
            time.sleep(delay)  # Continue polling despite errors

def cleanup_cache():
    """Remove expired items from the token metadata cache"""
    current_time = time.time()
    expired_keys = [k for k, exp_time in cache_expiry.items() if current_time > exp_time]
    
    for key in expired_keys:
        if key in token_metadata_cache:
            del token_metadata_cache[key]
        if key in cache_expiry:
            del cache_expiry[key]
            
    logging.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

if __name__ == "__main__":
    logging.info("Starting continuous polling of Solana tokens with Birdeye API...")
    logging.info(f"Configuration: New token timeframe: {NEW_TOKEN_TIMEFRAME_MINUTES} minutes")
    logging.info(f"Configuration: Boosted volume threshold: ${BOOSTED_VOLUME_THRESHOLD}")
    logging.info(f"Configuration: Min liquidity threshold: ${MIN_LIQUIDITY_THRESHOLD}")
    
    poller = poll_solana_tokens(num_requests=60, period=3600)  # Poll every minute in production
    poll_count = 0
    try:
        while True:
            tokens = next(poller)
            poll_count += 1
            logging.info(f"Test poll {poll_count}: Found {len(tokens)} tokens")
            
            # Periodically clean up the cache
            if poll_count % 10 == 0:
                cleanup_cache()
                
            if tokens:
                sample_token = tokens[0]
                logging.info(f"Sample token: {sample_token.get('name', 'Unknown')} " + 
                            f"(Boosted: {sample_token.get('is_boosted', False)}, " +
                            f"Volume: ${sample_token.get('v24hUSD', 0)}, " +
                            f"Liquidity: ${sample_token.get('liquidity', 0)})")
                
                # Test price estimation for the first token
                if len(tokens) > 0:
                    token_address = tokens[0].get("address")
                    if token_address:
                        # Get price history as an example
                        history = get_token_price_history(token_address, "1D")
                        if history:
                            logging.info(f"Price 24h ago: {history[0].get('value', 0)}, Latest: {history[-1].get('value', 0)}")
                        
                        # Estimate a swap as an example (SOL to token)
                        sol_to_token = estimate_swap_price(
                            "So11111111111111111111111111111111111111112",  # SOL mint
                            token_address,
                            100000000  # 0.1 SOL in lamports
                        )
                        if sol_to_token:
                            logging.info(f"Swap estimate: 0.1 SOL → {int(sol_to_token['output_amount'])} token units")
                            
    except KeyboardInterrupt:
        logging.info("Polling stopped by user.")