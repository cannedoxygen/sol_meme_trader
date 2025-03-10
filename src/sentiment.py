import requests
import logging
import os
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, wait_chain, retry_if_exception_type
from dotenv import load_dotenv

# Import OpenAI client
import openai

# Load environment variables from .env file
load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Initialize OpenAI client with proper error handling
try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")
    # Create a dummy client that will raise clear errors when used
    class DummyOpenAIClient:
        class ChatCompletions:
            def create(self, *args, **kwargs):
                raise ValueError("OpenAI client not properly initialized. Check your API key.")
        chat = ChatCompletions()
    client = DummyOpenAIClient()

# Constants
MAX_TWEETS_TO_ANALYZE = 15
CACHE_EXPIRY_SECONDS = 1800  # 30 minutes
SENTIMENT_MODEL = os.getenv("OPENAI_SENTIMENT_MODEL", "gpt-4o")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

# Cache for sentiment results
sentiment_cache = {}
cache_timestamps = {}

@dataclass
class SentimentResult:
    """Structured result from sentiment analysis"""
    sentiment_score: float  # -1 to +1 scale
    sentiment_label: str    # "positive", "neutral", "negative"
    confidence: float       # 0 to 1 scale
    bullish_signals: List[str]
    bearish_signals: List[str]
    neutral_signals: List[str]
    key_themes: List[str]
    engagement_level: str   # "high", "medium", "low"
    summary: str
    analyzed_at: str

class SentimentError(Exception):
    """Base exception for sentiment analysis errors"""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_chain(
        # Wait 2 seconds between first and second try
        wait_exponential(multiplier=1, min=2, max=4),
        # Wait longer between the second and third try
        wait_exponential(multiplier=2, min=5, max=10)
    ),
    retry=retry_if_exception_type((requests.RequestException, openai.OpenAIError))
)
def fetch_tweets(token_symbol: str, twitter_bearer_token: str, count: int = MAX_TWEETS_TO_ANALYZE) -> List[Dict[str, Any]]:
    """
    Fetch recent tweets mentioning a specific token from Twitter's API.
    
    Args:
        token_symbol: The token's symbol or name for search
        twitter_bearer_token: Twitter API bearer token
        count: Maximum number of tweets to retrieve
        
    Returns:
        List of tweets with text and metadata
    """
    if not twitter_bearer_token:
        logging.warning("No Twitter bearer token provided, cannot fetch tweets")
        return []
        
    search_url = "https://api.twitter.com/2/tweets/search/recent"
    
    # Fix: Make the token symbol more search-friendly
    clean_symbol = token_symbol.strip().replace("$", "").replace("#", "")
    # Avoid searching for too short tokens (could return unrelated results)
    if len(clean_symbol) < 3:
        return []
    
    # Create a better query that avoids Twitter API errors
    query = f"{clean_symbol} OR #{clean_symbol} -is:retweet lang:en"
    
    query_params = {
        "query": query,
        "tweet.fields": "created_at,public_metrics,author_id,lang",
        "max_results": str(min(count, 100)),  # Twitter API limit is 100
        "expansions": "author_id"
    }
    
    headers = {
        "Authorization": f"Bearer {twitter_bearer_token}"
    }
    
    try:
        logging.info(f"Fetching tweets for token symbol: {token_symbol}")
        response = requests.get(search_url, params=query_params, headers=headers, timeout=10)
        
        # Check for rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get('retry-after', 60))
            logging.warning(f"Twitter rate limit reached. Retry after {retry_after} seconds")
            time.sleep(min(retry_after, 60))  # Cap at 60 seconds max wait
            raise requests.RequestException(f"Rate limited by Twitter - retry after {retry_after}s")
            
        response.raise_for_status()
        
        tweets_data = response.json()
        tweets = tweets_data.get("data", [])
        
        if not tweets:
            logging.info(f"No tweets found for token symbol: {token_symbol}")
            return []
            
        # Add user data to tweets if available
        users = {user["id"]: user for user in tweets_data.get("includes", {}).get("users", [])}
        
        enhanced_tweets = []
        for tweet in tweets:
            # Add user data if available
            if "author_id" in tweet and tweet["author_id"] in users:
                tweet["user"] = users[tweet["author_id"]]
                
            enhanced_tweets.append(tweet)
            
        logging.info(f"Found {len(enhanced_tweets)} tweets for {token_symbol}")
        return enhanced_tweets
        
    except requests.RequestException as e:
        logging.error(f"Error fetching tweets for token {token_symbol}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error fetching tweets: {e}")
        return []

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5)
)
def analyze_sentiment_with_ai(texts: List[str], token_info: Dict[str, Any]) -> SentimentResult:
    """
    Analyze sentiment of texts using OpenAI's API.
    
    Args:
        texts: List of text content to analyze
        token_info: Context information about the token
        
    Returns:
        SentimentResult object with sentiment analysis
    """
    if not texts:
        logging.warning(f"No texts provided for sentiment analysis of {token_info.get('symbol', 'unknown token')}")
        return create_neutral_sentiment()
    
    # Prepare context about the token
    token_name = token_info.get('name', 'Unknown')
    token_symbol = token_info.get('symbol', 'Unknown')
    token_desc = token_info.get('description', '')
    
    # Combine all texts for analysis with context
    combined_text = "\n\n".join([f"Tweet {i+1}: {text}" for i, text in enumerate(texts)])
    
    prompt = f"""
Analyze the sentiment and market signals in these tweets about {token_name} ({token_symbol}), a Solana token.

Token Information:
{json.dumps(token_info, indent=2)}

Tweets:
{combined_text}

Based solely on these tweets, analyze:
1. Overall sentiment (positive, neutral, or negative) with a numerical score from -1 to +1
2. Confidence in your sentiment assessment (0-1 scale)
3. Bullish signals or positive catalysts mentioned
4. Bearish signals or concerns mentioned
5. Neutral observations
6. Key themes or topics discussed
7. Level of engagement (high, medium, low)
8. Brief summary of overall market sentiment (2-3 sentences)

Return your analysis as a JSON object with these exact fields:
{
  "sentiment_score": float (-1 to +1),
  "sentiment_label": string ("positive", "neutral", "negative"),
  "confidence": float (0 to 1),
  "bullish_signals": [string array],
  "bearish_signals": [string array],
  "neutral_signals": [string array], 
  "key_themes": [string array],
  "engagement_level": string ("high", "medium", "low"),
  "summary": string
}
"""

    try:
        # Use OpenAI API for sentiment analysis
        logging.info(f"Analyzing sentiment for {token_symbol} with {len(texts)} tweets")
        
        # Check if model supports JSON mode
        json_mode_models = ["gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo", "gpt-4-1106-preview", "gpt-3.5-turbo-1106"]
        use_json_mode = any(model in SENTIMENT_MODEL for model in json_mode_models)
        
        # Prepare completion parameters
        completion_params = {
            "model": SENTIMENT_MODEL,
            "messages": [
                {"role": "system", "content": "You are a cryptocurrency market sentiment analyst specializing in social media analysis."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
        }
        
        # Add response_format only for supported models
        if use_json_mode:
            completion_params["response_format"] = {"type": "json_object"}
        
        response = client.chat.completions.create(**completion_params)
        
        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response text - handle models that don't return proper JSON
        try:
            result_json = json.loads(result_text)
        except json.JSONDecodeError:
            # Extract JSON from text if needed
            try:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}")
                if json_start >= 0 and json_end >= 0:
                    result_json = json.loads(result_text[json_start:json_end+1])
                else:
                    raise ValueError("Could not extract valid JSON from response")
            except Exception as e:
                logging.error(f"Failed to parse JSON from response: {e}")
                return create_neutral_sentiment()
        
        # Create SentimentResult object
        sentiment_result = SentimentResult(
            sentiment_score=float(result_json.get("sentiment_score", 0)),
            sentiment_label=result_json.get("sentiment_label", "neutral"),
            confidence=float(result_json.get("confidence", 0.5)),
            bullish_signals=result_json.get("bullish_signals", []),
            bearish_signals=result_json.get("bearish_signals", []),
            neutral_signals=result_json.get("neutral_signals", []),
            key_themes=result_json.get("key_themes", []),
            engagement_level=result_json.get("engagement_level", "low"),
            summary=result_json.get("summary", "No clear sentiment detected."),
            analyzed_at=datetime.now().isoformat()
        )
        
        logging.info(f"Sentiment analysis for {token_symbol}: {sentiment_result.sentiment_label} ({sentiment_result.sentiment_score:.2f})")
        return sentiment_result
        
    except openai.OpenAIError as e:
        # Handle different OpenAI errors appropriately
        if "Rate limit" in str(e):
            logging.error(f"OpenAI API rate limit reached: {e}")
            time.sleep(15)  # Wait before retry
        else:
            logging.error(f"OpenAI API error during sentiment analysis: {e}")
        raise
    except Exception as e:
        logging.error(f"Error during sentiment analysis: {e}")
        return create_neutral_sentiment()

def create_neutral_sentiment() -> SentimentResult:
    """Create a neutral sentiment result when analysis fails or no data is available"""
    return SentimentResult(
        sentiment_score=0.0,
        sentiment_label="neutral",
        confidence=0.5,
        bullish_signals=[],
        bearish_signals=[],
        neutral_signals=["Insufficient data for analysis"],
        key_themes=["No data"],
        engagement_level="low",
        summary="Insufficient data to determine sentiment.",
        analyzed_at=datetime.now().isoformat()
    )

def create_synthetic_sentiment(token_info: Dict[str, Any]) -> SentimentResult:
    """
    Create a synthetic sentiment result when Twitter API is unavailable but we need some result.
    Used for testing or when actual API is down but trading decisions still need to be made.
    
    Args:
        token_info: Token data to base synthetic sentiment on
        
    Returns:
        Synthetic SentimentResult
    """
    token_symbol = token_info.get("symbol", "UNKNOWN")
    token_name = token_info.get("name", "Unknown Token")
    
    # Create a deterministic but seemingly random sentiment based on the token address/symbol
    # This ensures the same token always gets the same sentiment in synthetic mode
    seed_str = token_info.get("address", token_symbol)
    random.seed(seed_str)
    
    # Generate a sentiment score between -0.7 and 0.7
    sentiment_score = (random.random() * 1.4) - 0.7
    
    # Determine label based on score
    if sentiment_score > 0.2:
        sentiment_label = "positive"
    elif sentiment_score < -0.2:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"
    
    # Generate confidence between 0.4 and 0.8
    confidence = 0.4 + (random.random() * 0.4)
    
    # Generate engagement level
    engagement_options = ["low", "medium", "high"]
    engagement_weights = [0.5, 0.3, 0.2]  # More likely to be low
    engagement_level = random.choices(engagement_options, weights=engagement_weights)[0]
    
    # Generate themes based on token name
    common_themes = ["solana", "memecoin", "crypto", "trading", "launch", "price", "community"]
    selected_themes = random.sample(common_themes, k=min(4, len(common_themes)))
    if len(token_symbol) >= 3:
        selected_themes.append(token_symbol.lower())
    
    # Generate signals based on sentiment
    if sentiment_label == "positive":
        bullish_signals = [
            f"Growing community interest in {token_symbol}",
            f"Positive mentions of {token_name} tokenomics",
            "Users expressing intention to buy and hold"
        ]
        bearish_signals = ["Some profit taking expected"]
        neutral_signals = ["Normal market fluctuations noted"]
    elif sentiment_label == "negative":
        bullish_signals = [f"Some users still bullish on {token_symbol} long term"]
        bearish_signals = [
            f"Concerns about {token_name} price action",
            "Selling pressure detected in community",
            "Comparison to other tokens with better performance"
        ]
        neutral_signals = ["Mixed opinions on future potential"]
    else:
        bullish_signals = [f"Some positive mentions of {token_symbol}"]
        bearish_signals = ["Some concerns about market timing"]
        neutral_signals = [
            "Balanced discussion about pros and cons",
            f"Limited strong opinions on {token_name}",
            "Wait and see attitude prevalent"
        ]
    
    # Create synthetic summary
    summary = f"Synthetic sentiment analysis shows {sentiment_label} sentiment for {token_symbol} with {confidence:.2f} confidence. " \
              f"Engagement level appears to be {engagement_level}. This is based on synthetic modeling, not actual social data."
    
    return SentimentResult(
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label,
        confidence=confidence,
        bullish_signals=bullish_signals,
        bearish_signals=bearish_signals,
        neutral_signals=neutral_signals,
        key_themes=selected_themes,
        engagement_level=engagement_level,
        summary=summary,
        analyzed_at=datetime.now().isoformat()
    )

def analyze_tweets_for_token(token_info: Dict[str, Any], twitter_bearer_token: str = TWITTER_BEARER_TOKEN,
                            use_synthetic: bool = False) -> SentimentResult:
    """
    Analyze the sentiment of recent tweets mentioning a specific token.
    
    Args:
        token_info: Dictionary with token information (including 'symbol', 'name')
        twitter_bearer_token: Twitter API bearer token for authentication
        use_synthetic: Whether to use synthetic sentiment when real data can't be fetched
        
    Returns:
        SentimentResult object with analysis results
    
    This function:
      1. Fetches recent tweets via Twitter API
      2. Sends tweets to OpenAI's API for sentiment analysis
      3. Returns structured sentiment results
    """
    token_symbol = token_info.get("symbol", "")
    token_name = token_info.get("name", "")
    
    if not token_symbol and not token_name:
        logging.error("No token symbol or name provided for sentiment analysis")
        return create_neutral_sentiment()
    
    search_term = token_symbol or token_name
    
    # Check cache first
    cache_key = search_term.lower()
    current_time = time.time()
    
    if cache_key in sentiment_cache and current_time - cache_timestamps.get(cache_key, 0) < CACHE_EXPIRY_SECONDS:
        logging.info(f"Using cached sentiment analysis for {search_term}")
        return sentiment_cache[cache_key]
    
    try:
        # Try both symbol and name for better coverage
        tweets = []
        if token_symbol:
            tweets = fetch_tweets(token_symbol, twitter_bearer_token)
            
        # If no tweets found with symbol, try name
        if not tweets and token_name and token_name != token_symbol:
            tweets = fetch_tweets(token_name, twitter_bearer_token)
            
        if not tweets:
            logging.info(f"No tweets found for token {search_term}")
            # If requested, return synthetic sentiment instead of neutral
            if use_synthetic:
                sentiment_result = create_synthetic_sentiment(token_info)
                logging.info(f"Created synthetic sentiment for {search_term}: {sentiment_result.sentiment_label}")
                
                # Cache the synthetic result (but for shorter time)
                sentiment_cache[cache_key] = sentiment_result
                cache_timestamps[cache_key] = current_time
                
                return sentiment_result
            return create_neutral_sentiment()
            
        # Extract tweet text for analysis
        texts = [tweet.get("text", "") for tweet in tweets if tweet.get("text")]
        
        # Perform sentiment analysis
        sentiment_result = analyze_sentiment_with_ai(texts, token_info)
        
        # Cache the result
        sentiment_cache[cache_key] = sentiment_result
        cache_timestamps[cache_key] = current_time
        
        return sentiment_result
        
    except Exception as e:
        logging.error(f"Error during tweet analysis for {search_term}: {e}")
        # If requested, return synthetic sentiment on error
        if use_synthetic:
            try:
                sentiment_result = create_synthetic_sentiment(token_info)
                logging.info(f"Created synthetic sentiment on error for {search_term}: {sentiment_result.sentiment_label}")
                return sentiment_result
            except Exception as e2:
                logging.error(f"Error creating synthetic sentiment: {e2}")
        return create_neutral_sentiment()

def get_sentiment_score(token_info: Dict[str, Any], twitter_bearer_token: str = TWITTER_BEARER_TOKEN,
                       use_synthetic: bool = False) -> float:
    """
    Get a simplified sentiment score for trading decisions.
    
    Args:
        token_info: Dictionary with token information
        twitter_bearer_token: Twitter API bearer token
        use_synthetic: Whether to use synthetic data when real data unavailable
        
    Returns:
        float: Sentiment score between -1 and +1
    """
    result = analyze_tweets_for_token(token_info, twitter_bearer_token, use_synthetic)
    
    # Adjust score based on confidence
    adjusted_score = result.sentiment_score * result.confidence
    
    # Further adjust based on engagement level
    engagement_multiplier = {
        "high": 1.0,
        "medium": 0.8,
        "low": 0.6
    }.get(result.engagement_level, 0.7)
    
    final_score = adjusted_score * engagement_multiplier
    
    logging.info(f"Final sentiment score for {token_info.get('symbol', 'unknown')}: {final_score:.2f}")
    return final_score

def get_market_pulse(tokens: List[Dict[str, Any]], twitter_bearer_token: str = TWITTER_BEARER_TOKEN,
                    use_synthetic: bool = False) -> Dict[str, Any]:
    """
    Get overall market sentiment by analyzing multiple tokens.
    
    Args:
        tokens: List of token information dictionaries
        twitter_bearer_token: Twitter API bearer token
        use_synthetic: Whether to use synthetic data when real data unavailable
        
    Returns:
        dict: Market pulse with overall sentiment and per-token analysis
    """
    if not tokens:
        logging.warning("No tokens provided for market pulse analysis")
        return {
            "overall_sentiment": "neutral",
            "sentiment_score": 0.0,
            "token_sentiments": {},
            "trending_themes": [],
            "analyzed_at": datetime.now().isoformat()
        }
    
    # Get sentiment for each token
    token_sentiments = {}
    total_score = 0.0
    valid_scores = 0
    all_themes = []
    
    for token in tokens[:10]:  # Limit to 10 tokens for efficiency
        token_symbol = token.get("symbol", "")
        if not token_symbol:
            continue
            
        sentiment = analyze_tweets_for_token(token, twitter_bearer_token, use_synthetic)
        
        token_sentiments[token_symbol] = {
            "score": sentiment.sentiment_score,
            "label": sentiment.sentiment_label,
            "confidence": sentiment.confidence,
            "key_themes": sentiment.key_themes
        }
        
        # Accumulate for average
        if sentiment.confidence > 0.5:  # Only count high-confidence scores
            total_score += sentiment.sentiment_score
            valid_scores += 1
            all_themes.extend(sentiment.key_themes)
    
    # Calculate average sentiment
    avg_sentiment = total_score / valid_scores if valid_scores > 0 else 0
    
    # Determine overall sentiment label
    overall_label = "neutral"
    if avg_sentiment > 0.3:
        overall_label = "positive"
    elif avg_sentiment < -0.3:
        overall_label = "negative"
    
    # Find trending themes
    theme_counts = {}
    for theme in all_themes:
        theme_counts[theme] = theme_counts.get(theme, 0) + 1
    
    # Sort by frequency
    trending_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
    trending_themes = [theme for theme, count in trending_themes[:5]]
    
    return {
        "overall_sentiment": overall_label,
        "sentiment_score": avg_sentiment,
        "token_sentiments": token_sentiments,
        "trending_themes": trending_themes,
        "analyzed_at": datetime.now().isoformat()
    }

def clean_sentiment_cache():
    """Remove expired items from sentiment cache"""
    current_time = time.time()
    expired_keys = [k for k, timestamp in cache_timestamps.items() 
                   if current_time - timestamp > CACHE_EXPIRY_SECONDS]
    
    for key in expired_keys:
        if key in sentiment_cache:
            del sentiment_cache[key]
        if key in cache_timestamps:
            del cache_timestamps[key]
            
    logging.debug(f"Cleaned {len(expired_keys)} expired items from sentiment cache")
    
    # Proactively clean cache if it gets too large
    if len(sentiment_cache) > 200:  # Arbitrary limit to prevent memory issues
        # Keep only the most recently accessed entries
        sorted_entries = sorted([(k, v) for k, v in cache_timestamps.items()], key=lambda x: x[1], reverse=True)
        # Keep the 100 most recent entries
        entries_to_keep = sorted_entries[:100]
        entries_to_remove = sorted_entries[100:]
        
        # Remove older entries
        for key, _ in entries_to_remove:
            if key in sentiment_cache:
                del sentiment_cache[key]
            if key in cache_timestamps:
                del cache_timestamps[key]
        
        logging.info(f"Cache size limit reached. Pruned {len(entries_to_remove)} older entries from sentiment cache.")

def format_sentiment_report(token_info: Dict[str, Any], sentiment: SentimentResult) -> str:
    """
    Format a human-readable sentiment report.
    
    Args:
        token_info: Token information dictionary
        sentiment: SentimentResult object
        
    Returns:
        Formatted sentiment report string
    """
    token_name = token_info.get("name", "Unknown Token")
    token_symbol = token_info.get("symbol", "UNKN")
    
    report = []
    report.append(f"Sentiment Analysis for {token_name} ({token_symbol}):")
    report.append(f"Overall: {sentiment.sentiment_label.capitalize()} ({sentiment.sentiment_score:.2f})")
    report.append(f"Confidence: {sentiment.confidence:.2f}")
    report.append(f"Engagement: {sentiment.engagement_level.capitalize()}")
    
    report.append("\nBullish Signals:")
    for signal in sentiment.bullish_signals:
        report.append(f"- {signal}")
        
    report.append("\nBearish Signals:")
    for signal in sentiment.bearish_signals:
        report.append(f"- {signal}")
        
    report.append("\nKey Themes:")
    for theme in sentiment.key_themes:
        report.append(f"- {theme}")
        
    report.append("\nSummary:")
    report.append(sentiment.summary)
    
    report.append(f"\nAnalyzed at: {sentiment.analyzed_at}")
    
    return "\n".join(report)

if __name__ == "__main__":
    # Example usage
    token_info = {
        "symbol": "MEME",
        "name": "Memecoin",
        "description": "A popular meme token on Solana",
        "address": "EXAMPLE_TOKEN_ADDRESS"
    }
    
    twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
    
    if not twitter_bearer:
        print("Warning: TWITTER_BEARER_TOKEN not set in environment, using synthetic sentiment")
        sentiment = analyze_tweets_for_token(token_info, use_synthetic=True)
    else:
        print(f"Analyzing sentiment for {token_info['symbol']}...")
        sentiment = analyze_tweets_for_token(token_info, twitter_bearer)
    
    print(format_sentiment_report(token_info, sentiment))
    
    # Test sentiment score
    score = get_sentiment_score(token_info, twitter_bearer, use_synthetic=True)
    print(f"\nSentiment score (scaled by confidence and engagement): {score:.2f}")
    
    # Test market pulse
    sample_tokens = [
        {"symbol": "MEME", "name": "Memecoin", "address": "addr1"},
        {"symbol": "DOGE", "name": "Dogecoin", "address": "addr2"},
        {"symbol": "PEPE", "name": "Pepe Token", "address": "addr3"}
    ]
    
    print("\nTesting market pulse with synthetic data:")
    pulse = get_market_pulse(sample_tokens, use_synthetic=True)
    print(f"Overall market sentiment: {pulse['overall_sentiment']} ({pulse['sentiment_score']:.2f})")
    print(f"Trending themes: {', '.join(pulse['trending_themes'])}")
    
    # Test cache cleanup
    clean_sentiment_cache()
    print(f"Cache size after cleanup: {len(sentiment_cache)}")