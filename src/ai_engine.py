import openai
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Initialize OpenAI client
client = openai.OpenAI()

# Constants
ANALYSIS_MODEL = os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-4")
CACHE_EXPIRY_SECONDS = 900  # 15 minutes
MAX_TOKEN_HISTORY = 5  # Maximum token history entries to include

# List of models known to support response_format
MODELS_WITH_RESPONSE_FORMAT = [
    "gpt-4-turbo",
    "gpt-4-0125",
    "gpt-4-1106",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125"
]

# Cache for AI evaluations
evaluation_cache = {}
cache_timestamps = {}

class AIError(Exception):
    """Base exception for AI-related errors"""
    pass

@dataclass
class TokenEvaluation:
    """Comprehensive token evaluation result"""
    ai_confidence: float  # 0-10 scale
    risk_score: float     # 0-10 scale
    recommendation: str   # "BUY", "HOLD", "AVOID"
    price_prediction: Dict[str, Any]  # Short/medium term projections
    key_factors: List[Dict[str, str]]  # Influencing factors with sentiment
    trading_insights: str  # Additional trading guidance
    market_context: str   # Market environment context
    confidence_reasons: List[str]  # Reasons for confidence level
    risk_reasons: List[str]  # Reasons for risk assessment
    evaluation_time: str  # ISO timestamp
    token_address: str   # Token address
    token_name: str      # Token name

def create_default_evaluation(token_data: Dict[str, Any]) -> TokenEvaluation:
    """
    Create a default neutral evaluation when analysis fails.
    
    Args:
        token_data: Token information
    
    Returns:
        TokenEvaluation with neutral/default values
    """
    token_address = token_data.get("address", "unknown")
    token_name = token_data.get("name", "Unknown Token")
    
    return TokenEvaluation(
        ai_confidence=5.0,
        risk_score=5.0,
        recommendation="HOLD",
        price_prediction={
            "short_term": {"direction": "neutral", "confidence": 0.5},
            "medium_term": {"direction": "neutral", "confidence": 0.5}
        },
        key_factors=[
            {"factor": "Insufficient data", "impact": "neutral", "importance": "high"}
        ],
        trading_insights="Insufficient data for detailed analysis. Default to cautious approach.",
        market_context="Analysis defaulted due to insufficient data or processing error.",
        confidence_reasons=["Default confidence due to analysis limitations"],
        risk_reasons=["Default risk assessment due to analysis limitations"],
        evaluation_time=datetime.now().isoformat(),
        token_address=token_address,
        token_name=token_name
    )

def supports_response_format(model: str) -> bool:
    """
    Check if the specified model supports the response_format parameter.
    
    Args:
        model: The model name
        
    Returns:
        bool: True if the model supports response_format
    """
    return any(supported_model in model for supported_model in MODELS_WITH_RESPONSE_FORMAT)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(openai.OpenAIError)
)
def evaluate_token(token_data: Dict[str, Any], market_context: Optional[Dict[str, Any]] = None, 
                  token_history: Optional[List[Dict[str, Any]]] = None) -> TokenEvaluation:
    """
    Evaluate token data using OpenAI's API.
    
    Args:
        token_data: Token information (liquidity, volume, price change, etc.)
        market_context: Additional market context (optional)
        token_history: Historical data for the token (optional)
        
    Returns:
        TokenEvaluation with comprehensive analysis
    """
    token_address = token_data.get("address", "unknown")
    
    # Check cache first
    cache_key = token_address
    current_time = time.time()
    
    if cache_key in evaluation_cache and current_time - cache_timestamps.get(cache_key, 0) < CACHE_EXPIRY_SECONDS:
        logging.info(f"Using cached evaluation for {token_address}")
        return evaluation_cache[cache_key]
    
    prompt = create_evaluation_prompt(token_data, market_context, token_history)
    
    try:
        logging.info(f"Requesting AI evaluation for token {token_data.get('name', 'unknown')}")
        
        # Create base parameters for the API call
        params = {
            "model": ANALYSIS_MODEL,
            "messages": [
                {"role": "system", "content": "You are a cryptocurrency trading expert specializing in analyzing Solana tokens. Your response must be valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2  # Low temperature for more consistent outputs
        }
        
        # Add response_format only if the model supports it
        if supports_response_format(ANALYSIS_MODEL):
            params["response_format"] = {"type": "json_object"}
            logging.info(f"Using response_format with model {ANALYSIS_MODEL}")
        else:
            logging.info(f"Model {ANALYSIS_MODEL} may not support response_format, omitting parameter")
        
        # Call OpenAI's API with the appropriate parameters
        response = client.chat.completions.create(**params)
        
        result_text = response.choices[0].message.content.strip()
        logging.debug(f"OpenAI raw response: {result_text}")
        
        # Parse the returned JSON
        evaluation = parse_evaluation_response(result_text, token_data)
        
        # Cache the evaluation
        evaluation_cache[cache_key] = evaluation
        cache_timestamps[cache_key] = current_time
        
        logging.info(f"AI Evaluation for {token_data.get('name', '')}: Confidence={evaluation.ai_confidence}, "
                    f"Risk={evaluation.risk_score}, Recommendation={evaluation.recommendation}")
        
        return evaluation
    
    except openai.OpenAIError as oe:
        logging.error(f"OpenAI API error: {oe}")
        
        # If the error is related to response_format, retry without it
        if "response_format" in str(oe) and supports_response_format(ANALYSIS_MODEL):
            logging.warning(f"Error with response_format, retrying without it for model {ANALYSIS_MODEL}")
            try:
                response = client.chat.completions.create(
                    model=ANALYSIS_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a cryptocurrency trading expert specializing in analyzing Solana tokens. IMPORTANT: Your response must be valid JSON only, with no other text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                
                result_text = response.choices[0].message.content.strip()
                evaluation = parse_evaluation_response(result_text, token_data)
                
                # Cache the evaluation
                evaluation_cache[cache_key] = evaluation
                cache_timestamps[cache_key] = current_time
                
                return evaluation
            except Exception as retry_e:
                logging.error(f"Error during retry without response_format: {retry_e}")
                return create_default_evaluation(token_data)
        else:
            raise
            
    except json.JSONDecodeError as je:
        logging.error(f"JSON parsing error: {je}. Raw response: {result_text if 'result_text' in locals() else 'No response'}")
        return create_default_evaluation(token_data)
    except Exception as e:
        logging.error(f"Unexpected error during AI evaluation: {e}")
        return create_default_evaluation(token_data)

def create_evaluation_prompt(token_data: Dict[str, Any], market_context: Optional[Dict[str, Any]] = None, 
                           token_history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Create a comprehensive prompt for token evaluation.
    
    Args:
        token_data: Token information
        market_context: Additional market context (optional)
        token_history: Historical data for the token (optional)
        
    Returns:
        Formatted prompt string
    """
    # Format token data for prompt
    token_info = {
        "name": token_data.get("name", "Unknown"),
        "symbol": token_data.get("symbol", "Unknown"),
        "address": token_data.get("address", "Unknown"),
        "liquidity": token_data.get("liquidity", 0),
        "volume_24h": token_data.get("v24hUSD", 0),
        "price_usd": token_data.get("priceUSD", 0),
        "market_cap": token_data.get("marketCap", 0),
        "price_change_24h": token_data.get("priceChange24h", 0),
        "holders": token_data.get("holders", 0),
        "is_boosted": token_data.get("is_boosted", False),
        "listing_time": token_data.get("listingTime", ""),
        "age_minutes": token_data.get("age_minutes", 0)
    }
    
    # Format history if provided
    history_text = ""
    if token_history:
        # Limit history to most recent entries
        recent_history = token_history[-MAX_TOKEN_HISTORY:] if len(token_history) > MAX_TOKEN_HISTORY else token_history
        history_text = "Token Price History:\n" + json.dumps(recent_history, indent=2)
    
    # Format market context if provided
    market_text = ""
    if market_context:
        market_text = "Market Context:\n" + json.dumps(market_context, indent=2)
    
    # Build the prompt
    prompt = f"""
Analyze the following Solana token and provide a detailed evaluation in JSON format.

Token Data:
{json.dumps(token_info, indent=2)}

{history_text}

{market_text}

Based on this information, provide a comprehensive analysis considering:
1. Liquidity depth and stability
2. Trading volume and trends
3. Price action and volatility
4. Market cap and token valuation
5. Holder distribution (if available)
6. Token age and maturity
7. Current market environment

Return a detailed JSON object with the following structure:
{{
  "ai_confidence": <float 0-10, higher means more promising>,
  "risk_score": <float 0-10, lower means less risk>,
  "recommendation": <"BUY", "HOLD", or "AVOID">,
  "price_prediction": {{
    "short_term": {{
      "direction": <"bullish", "neutral", or "bearish">,
      "confidence": <float 0-1>
    }},
    "medium_term": {{
      "direction": <"bullish", "neutral", or "bearish">,
      "confidence": <float 0-1>
    }}
  }},
  "key_factors": [
    {{
      "factor": <description of key factor>,
      "impact": <"bullish", "neutral", or "bearish">,
      "importance": <"high", "medium", or "low">
    }},
    ... (include 3-5 key factors)
  ],
  "trading_insights": <string with specific trading guidance>,
  "confidence_reasons": [<list of reasons for confidence score>],
  "risk_reasons": [<list of reasons for risk score>]
}}
"""
    return prompt

def parse_evaluation_response(response_text: str, token_data: Dict[str, Any]) -> TokenEvaluation:
    """
    Parse the AI response and convert to TokenEvaluation object.
    
    Args:
        response_text: JSON response from OpenAI
        token_data: Original token data
        
    Returns:
        TokenEvaluation object
    """
    try:
        # Clean up response text to handle potential non-JSON prefixes or suffixes
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        
        if json_start >= 0 and json_end >= 0:
            clean_json = response_text[json_start:json_end+1]
        else:
            clean_json = response_text
            
        # Parse the returned JSON
        evaluation = json.loads(clean_json)
        
        # Extract basic fields with defaults
        ai_confidence = float(evaluation.get("ai_confidence", 5))
        risk_score = float(evaluation.get("risk_score", 5))
        recommendation = evaluation.get("recommendation", "HOLD")
        
        # Validate recommendation
        valid_recommendations = ["BUY", "HOLD", "AVOID"]
        if recommendation not in valid_recommendations:
            logging.warning(f"Invalid recommendation: {recommendation}. Defaulting to HOLD.")
            recommendation = "HOLD"
        
        # Ensure values are within valid ranges
        ai_confidence = max(0, min(10, ai_confidence))
        risk_score = max(0, min(10, risk_score))
        
        # Extract nested fields
        price_prediction = evaluation.get("price_prediction", {
            "short_term": {"direction": "neutral", "confidence": 0.5},
            "medium_term": {"direction": "neutral", "confidence": 0.5}
        })
        
        key_factors = evaluation.get("key_factors", [
            {"factor": "No key factors provided", "impact": "neutral", "importance": "medium"}
        ])
        
        trading_insights = evaluation.get("trading_insights", "No specific trading insights provided.")
        market_context = evaluation.get("market_context", "No market context provided.")
        confidence_reasons = evaluation.get("confidence_reasons", ["No confidence reasons provided."])
        risk_reasons = evaluation.get("risk_reasons", ["No risk reasons provided."])
        
        # Create the TokenEvaluation object
        token_evaluation = TokenEvaluation(
            ai_confidence=ai_confidence,
            risk_score=risk_score,
            recommendation=recommendation,
            price_prediction=price_prediction,
            key_factors=key_factors,
            trading_insights=trading_insights,
            market_context=market_context,
            confidence_reasons=confidence_reasons,
            risk_reasons=risk_reasons,
            evaluation_time=datetime.now().isoformat(),
            token_address=token_data.get("address", "unknown"),
            token_name=token_data.get("name", "Unknown Token")
        )
        
        return token_evaluation
    
    except Exception as e:
        logging.error(f"Error parsing evaluation response: {e}")
        return create_default_evaluation(token_data)

def get_market_analysis(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get broader market analysis using AI.
    
    Args:
        market_data: Market-wide data and indicators
        
    Returns:
        Dictionary with market analysis
    """
    # Validate and normalize market data to avoid misleading zero values
    sol_price = market_data.get("sol_price", 0)
    if sol_price == 0:
        sol_price = 100  # Use a reasonable default if we don't have real data
    
    tvl = market_data.get("global_metrics", {}).get("total_solana_defi_tvl", 0)
    if tvl == 0:
        tvl = 2_000_000_000  # Use ~$2B as a reasonable placeholder
    
    volume = market_data.get("global_metrics", {}).get("sol_24h_volume", 0)
    if volume == 0:
        volume = 500_000_000  # Use ~$500M as a reasonable placeholder
    
    new_token_count = market_data.get("global_metrics", {}).get("new_token_count_24h", 0)
    if new_token_count == 0:
        new_token_count = 10  # Use a reasonable placeholder
    
    # Prepare normalized market data
    normalized_market_data = {
        "timestamp": market_data.get("timestamp", datetime.now().isoformat()),
        "sol_price": sol_price,
        "global_metrics": {
            "total_solana_defi_tvl": tvl,
            "sol_24h_volume": volume,
            "new_token_count_24h": new_token_count
        }
    }
    
    prompt = f"""
Analyze the following cryptocurrency market data and provide a high-level market analysis.

Market Data:
{json.dumps(normalized_market_data, indent=2)}

Based on this information, provide a comprehensive market analysis including:
1. Overall market sentiment
2. Solana ecosystem outlook
3. Market risk assessment
4. Liquidity conditions
5. Key market trends
6. Opportunity assessment for new tokens

Return your analysis as a JSON object with these exact fields:
{{
  "market_sentiment": <"bullish", "neutral", or "bearish">,
  "solana_outlook": <"positive", "neutral", or "negative">,
  "risk_level": <"low", "moderate", "high", or "extreme">,
  "liquidity_conditions": <"abundant", "adequate", "tight", or "scarce">,
  "key_trends": [<list of current market trends>],
  "trading_opportunities": <"abundant", "selective", "limited", or "avoid">,
  "market_summary": <concise overall market summary>
}}
"""
    
    try:
        # Create base parameters for the API call
        params = {
            "model": ANALYSIS_MODEL,
            "messages": [
                {"role": "system", "content": "You are a cryptocurrency market analyst specializing in market trends and environment analysis. Your response must be valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        # Add response_format only if the model supports it
        if supports_response_format(ANALYSIS_MODEL):
            params["response_format"] = {"type": "json_object"}
        
        # Call OpenAI's API
        response = client.chat.completions.create(**params)
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up response text to handle potential non-JSON prefixes or suffixes
        json_start = result_text.find('{')
        json_end = result_text.rfind('}')
        
        if json_start >= 0 and json_end >= 0:
            clean_json = result_text[json_start:json_end+1]
        else:
            clean_json = result_text
            
        analysis = json.loads(clean_json)
        
        # Add timestamp
        analysis["analyzed_at"] = datetime.now().isoformat()
        
        logging.info(f"Market analysis complete: {analysis.get('market_sentiment', 'unknown')} sentiment, "
                    f"{analysis.get('risk_level', 'unknown')} risk")
        
        return analysis
    
    except Exception as e:
        logging.error(f"Error during market analysis: {e}")
        
        # If the error is related to response_format, retry without it
        if "response_format" in str(e) and supports_response_format(ANALYSIS_MODEL):
            try:
                response = client.chat.completions.create(
                    model=ANALYSIS_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a cryptocurrency market analyst specializing in market trends and environment analysis. IMPORTANT: Your response must be valid JSON only, with no other text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Clean up response text
                json_start = result_text.find('{')
                json_end = result_text.rfind('}')
                
                if json_start >= 0 and json_end >= 0:
                    clean_json = result_text[json_start:json_end+1]
                else:
                    clean_json = result_text
                    
                analysis = json.loads(clean_json)
                analysis["analyzed_at"] = datetime.now().isoformat()
                return analysis
            except Exception:
                # Fall back to default response
                pass
                
        return {
            "market_sentiment": "neutral",
            "solana_outlook": "neutral",
            "risk_level": "moderate",
            "liquidity_conditions": "adequate",
            "key_trends": ["Growing activity in the Solana ecosystem", "Increasing meme coin launches", "Rising adoption of Solana DeFi platforms"],
            "trading_opportunities": "selective",
            "market_summary": "The Solana market is showing mixed signals with moderate risk levels. While there's ongoing activity in meme coins and DeFi, traders should remain selective with investments and conduct thorough research.",
            "analyzed_at": datetime.now().isoformat()
        }

def analyze_token_fundamentals(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform a deeper analysis of token fundamentals beyond simple metrics.
    
    Args:
        token_data: Enhanced token data including detailed metrics
    
    Returns:
        Dictionary with fundamental analysis
    """
    # Extract token metadata for analysis
    token_name = token_data.get('name', 'Unknown')
    token_symbol = token_data.get('symbol', 'Unknown')
    token_desc = token_data.get('description', '')
    twitter = token_data.get('twitter', '')
    discord = token_data.get('discord', '')
    website = token_data.get('website', '')
    
    # Prepare social media info if available
    social_info = {}
    if twitter:
        social_info["twitter"] = twitter
    if discord:
        social_info["discord"] = discord
    if website:
        social_info["website"] = website
    
    analysis_prompt = f"""
Conduct a comprehensive fundamental analysis of this Solana token:
{json.dumps(token_data, indent=2)}

Focus on:
- Project utility and use case
- Team information (if available)
- Community engagement and growth
- Tokenomics and distribution model
- Competitive positioning in Solana ecosystem
- Short-term (24h) and medium-term (7d) price projections
- Key risk factors specific to this token

Return a concise JSON with these keys:
{{
  "project_score": <0-10 rating of overall project quality>,
  "utility_assessment": <description of token utility and real-world use cases>,
  "community_assessment": <evaluation of community strength and engagement>,
  "tokenomics_assessment": <analysis of token economics and distribution>,
  "competitive_advantage": <token's unique selling points or disadvantages>,
  "short_term_projection": {{ "outlook": <"bullish", "neutral", or "bearish">, "confidence": <0-10> }},
  "medium_term_projection": {{ "outlook": <"bullish", "neutral", or "bearish">, "confidence": <0-10> }},
  "fair_value_estimate": <percentage relative to current price, e.g. -20 means overvalued by 20%>,
  "key_risk_factors": [<list of specific risks>],
  "key_bullish_factors": [<list of specific positive catalysts>]
}}
"""
    
    try:
        # Create base parameters for the API call
        params = {
            "model": ANALYSIS_MODEL,
            "messages": [
                {"role": "system", "content": "You are a quantitative cryptocurrency analyst specializing in fundamental token analysis. Your response must be valid JSON only."},
                {"role": "user", "content": analysis_prompt}
            ],
            "temperature": 0.3
        }
        
        # Add response_format only if the model supports it
        if supports_response_format(ANALYSIS_MODEL):
            params["response_format"] = {"type": "json_object"}
        
        # Using the Chat Completion API for detailed analysis
        response = client.chat.completions.create(**params)
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up response text
        json_start = result_text.find('{')
        json_end = result_text.rfind('}')
        
        if json_start >= 0 and json_end >= 0:
            clean_json = result_text[json_start:json_end+1]
        else:
            clean_json = result_text
            
        analysis = json.loads(clean_json)
        
        # Add timestamp and token identifiers
        analysis["analyzed_at"] = datetime.now().isoformat()
        analysis["token_address"] = token_data.get("address", "unknown")
        analysis["token_name"] = token_name
        analysis["token_symbol"] = token_symbol
        
        logging.info(f"Fundamental analysis completed for token {token_name}")
        return analysis
    
    except Exception as e:
        logging.error(f"Error during fundamental analysis: {e}")
        
        # If the error is related to response_format, retry without it
        if "response_format" in str(e) and supports_response_format(ANALYSIS_MODEL):
            try:
                response = client.chat.completions.create(
                    model=ANALYSIS_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a quantitative cryptocurrency analyst specializing in fundamental token analysis. IMPORTANT: Your response must be valid JSON only, with no other text."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    temperature=0.3
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Clean up response text
                json_start = result_text.find('{')
                json_end = result_text.rfind('}')
                
                if json_start >= 0 and json_end >= 0:
                    clean_json = result_text[json_start:json_end+1]
                else:
                    clean_json = result_text
                    
                analysis = json.loads(clean_json)
                
                # Add timestamp and token identifiers
                analysis["analyzed_at"] = datetime.now().isoformat()
                analysis["token_address"] = token_data.get("address", "unknown")
                analysis["token_name"] = token_name
                analysis["token_symbol"] = token_symbol
                
                return analysis
            except Exception:
                # Fall back to default response
                pass
                
        return {
            "project_score": 5,
            "utility_assessment": "Analysis failed - insufficient data",
            "community_assessment": "Analysis failed - insufficient data",
            "tokenomics_assessment": "Analysis failed - insufficient data",
            "competitive_advantage": "Analysis failed - insufficient data",
            "short_term_projection": {"outlook": "neutral", "confidence": 5},
            "medium_term_projection": {"outlook": "neutral", "confidence": 5},
            "fair_value_estimate": 0,
            "key_risk_factors": ["Analysis failed - insufficient data"],
            "key_bullish_factors": ["Analysis failed - insufficient data"],
            "analyzed_at": datetime.now().isoformat(),
            "token_address": token_data.get("address", "unknown"),
            "token_name": token_name,
            "token_symbol": token_symbol
        }

def clean_evaluation_cache():
    """Remove expired items from evaluation cache"""
    current_time = time.time()
    expired_keys = [k for k, timestamp in cache_timestamps.items() 
                  if current_time - timestamp > CACHE_EXPIRY_SECONDS]
    
    for key in expired_keys:
        if key in evaluation_cache:
            del evaluation_cache[key]
        if key in cache_timestamps:
            del cache_timestamps[key]
            
    logging.debug(f"Cleaned {len(expired_keys)} expired items from evaluation cache")

def get_exit_recommendation(token_data: Dict[str, Any], entry_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get AI recommendation for exiting a position.
    
    Args:
        token_data: Current token data
        entry_details: Details about entry position
        
    Returns:
        Dictionary with exit recommendation
    """
    # Calculate profit/loss
    entry_price = entry_details.get("entry_price", 0)
    current_price = token_data.get("priceUSD", 0)
    
    if entry_price and current_price:
        profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
    else:
        profit_loss_pct = 0
    
    # Format holding period
    entry_time = entry_details.get("entry_time", "")
    holding_period = "unknown"
    
    if entry_time:
        try:
            entry_dt = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
            now = datetime.now().astimezone()
            hours_held = (now - entry_dt).total_seconds() / 3600
            holding_period = f"{hours_held:.1f} hours"
        except:
            holding_period = "unknown"
    
    prompt = f"""
Analyze this token position and provide an exit recommendation:

Token: {token_data.get('name', 'Unknown')} ({token_data.get('symbol', 'Unknown')})
Current Price: ${current_price}
Entry Price: ${entry_price}
Profit/Loss: {profit_loss_pct:.2f}%
Holding Period: {holding_period}
Current Liquidity: ${token_data.get('liquidity', 0)}
24h Volume: ${token_data.get('v24hUSD', 0)}
24h Price Change: {token_data.get('priceChange24h', 0)}%

Token Details:
{json.dumps(token_data, indent=2)}

Entry Details:
{json.dumps(entry_details, indent=2)}

Provide an exit recommendation with the following JSON structure:
{{
  "recommendation": <"HOLD", "SELL", "TAKE_PARTIAL_PROFIT", "CUT_LOSSES">,
  "confidence": <0-10 confidence in recommendation>,
  "reasoning": <explanation for recommendation>,
  "target_price": <optional target price to consider selling>,
  "stop_loss": <optional stop loss recommendation>,
  "risk_assessment": <assessment of continued holding risk>,
  "timeframe": <recommended timeframe for reevaluation>
}}
"""
    
    try:
        # Create base parameters for the API call
        params = {
            "model": ANALYSIS_MODEL,
            "messages": [
                {"role": "system", "content": "You are a cryptocurrency trading expert specializing in exit strategy optimization. Your response must be valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        # Add response_format only if the model supports it
        if supports_response_format(ANALYSIS_MODEL):
            params["response_format"] = {"type": "json_object"}
        
        # Call OpenAI's API
        response = client.chat.completions.create(**params)
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up response text
        json_start = result_text.find('{')
        json_end = result_text.rfind('}')
        
        if json_start >= 0 and json_end >= 0:
            clean_json = result_text[json_start:json_end+1]
        else:
            clean_json = result_text
            
        recommendation = json.loads(clean_json)
        
        # Add additional information
        recommendation["profit_loss_pct"] = profit_loss_pct
        recommendation["analyzed_at"] = datetime.now().isoformat()
        
        logging.info(f"Exit recommendation for {token_data.get('symbol', 'unknown')}: {recommendation.get('recommendation', 'unknown')}")
        return recommendation
    
    except Exception as e:
        logging.error(f"Error getting exit recommendation: {e}")
        
        # If the error is related to response_format, retry without it
        if "response_format" in str(e) and supports_response_format(ANALYSIS_MODEL):
            try:
                response = client.chat.completions.create(
                    model=ANALYSIS_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a cryptocurrency trading expert specializing in exit strategy optimization. IMPORTANT: Your response must be valid JSON only, with no other text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Clean up response text
                json_start = result_text.find('{')
                json_end = result_text.rfind('}')
                
                if json_start >= 0 and json_end >= 0:
                    clean_json = result_text[json_start:json_end+1]
                else:
                    clean_json = result_text
                    
                recommendation = json.loads(clean_json)
                recommendation["profit_loss_pct"] = profit_loss_pct
                recommendation["analyzed_at"] = datetime.now().isoformat()
                return recommendation
            except Exception:
                # Fall back to default response
                pass
        
        # Default recommendation if all else fails
        return {
            "recommendation": "HOLD",
            "confidence": 5,
            "reasoning": "Insufficient data for analysis. Defaulting to hold recommendation.",
            "target_price": None,
            "stop_loss": entry_price * 0.9 if entry_price > 0 else None,
            "risk_assessment": "Unable to properly assess risk due to data limitations",
            "timeframe": "24 hours",
            "profit_loss_pct": profit_loss_pct,
            "analyzed_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    try:
        # Example usage for testing
        test_token = {
            "name": "Example Token",
            "symbol": "EXMPL",
            "address": "ExampleAddress123",
            "liquidity": 50000,
            "v24hUSD": 25000,
            "priceUSD": 0.0001,
            "marketCap": 1000000,
            "priceChange24h": 5,
            "holders": 500,
            "is_boosted": False,
            "listingTime": "2025-02-27T00:00:00Z",
            "age_minutes": 720
        }
        
        test_market = {
            "sol_price": 130,
            "global_metrics": {
                "total_solana_defi_tvl": 2500000000,
                "sol_24h_volume": 750000000,
                "new_token_count_24h": 15
            }
        }
        
        print("Testing AI evaluation...")
        evaluation = evaluate_token(test_token, test_market)
        print(f"Recommendation: {evaluation.recommendation}")
        print(f"Confidence: {evaluation.ai_confidence}/10")
        print(f"Risk score: {evaluation.risk_score}/10")
        
        print("\nTesting market analysis...")
        market = get_market_analysis(test_market)
        print(f"Market sentiment: {market.get('market_sentiment', 'unknown')}")
        print(f"Risk level: {market.get('risk_level', 'unknown')}")
        print(f"Summary: {market.get('market_summary', 'None')}")
        
    except Exception as e:
        logging.error(f"Error during testing: {e}")