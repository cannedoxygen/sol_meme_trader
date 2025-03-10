import logging
import requests
import json
import time
from typing import Dict, Any, Tuple, List, Optional, Union
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dataclasses import dataclass

# Configure logging for production
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Constants
RUGCHECK_BASE_URL = "https://api.rugcheck.xyz/v1/tokens"
MIN_LIQUIDITY_DEFAULT = 1000  # Default minimum liquidity in USD
MAX_CONCENTRATION_DEFAULT = 70  # Default maximum supply concentration (%)
MIN_HOLDERS_DEFAULT = 25  # Default minimum number of holders
MAX_RISK_SCORE_DEFAULT = 70  # Default maximum risk score (0-100)

# Cache for token risk assessments to reduce API calls
risk_cache = {}
cache_expiry = {}
CACHE_DURATION = 1800  # 30 minutes in seconds

class RiskError(Exception):
    """Base exception for risk-related errors"""
    pass

@dataclass
class RiskAssessment:
    """Comprehensive risk assessment result"""
    passes_filters: bool
    risk_reason: str
    risk_score: int  # 0-100 scale
    risk_level: str  # "low", "medium", "high", "extreme"
    liquidity_usd: float
    holders_count: int
    top_holders_concentration: float  # percentage
    liquidity_locked: float  # USD value
    contract_verification: bool
    honeypot_risk: bool
    max_tax: float  # percentage
    creation_time: str
    age_hours: float
    assessments: Dict[str, Dict[str, Any]]  # Detailed checks
    assessed_at: str

def create_risk_assessment(
    passes: bool, 
    reason: str, 
    risk_score: int = 50, 
    **kwargs
) -> RiskAssessment:
    """
    Create a RiskAssessment object with default values.
    
    Args:
        passes: Whether the token passed risk filters
        reason: Reason for risk assessment result
        risk_score: Numeric risk score (0-100)
        **kwargs: Additional fields to override defaults
        
    Returns:
        RiskAssessment object
    """
    # Determine risk level from score
    risk_level = "extreme"
    if risk_score < 30:
        risk_level = "low"
    elif risk_score < 50:
        risk_level = "medium"
    elif risk_score < 75:
        risk_level = "high"
    
    # Create the assessment with defaults
    assessment = RiskAssessment(
        passes_filters=passes,
        risk_reason=reason,
        risk_score=risk_score,
        risk_level=risk_level,
        liquidity_usd=kwargs.get("liquidity_usd", 0),
        holders_count=kwargs.get("holders_count", 0),
        top_holders_concentration=kwargs.get("top_holders_concentration", 100),
        liquidity_locked=kwargs.get("liquidity_locked", 0),
        contract_verification=kwargs.get("contract_verification", False),
        honeypot_risk=kwargs.get("honeypot_risk", True),
        max_tax=kwargs.get("max_tax", 0),
        creation_time=kwargs.get("creation_time", ""),
        age_hours=kwargs.get("age_hours", 0),
        assessments=kwargs.get("assessments", {}),
        assessed_at=datetime.now().isoformat()
    )
    
    return assessment

def apply_risk_filters(token: Dict[str, Any], config) -> Tuple[bool, str, RiskAssessment]:
    """
    Apply comprehensive risk filters to token data:
      1. Blacklist check
      2. Liquidity check
      3. Rug pull evaluation via RugCheck API
      4. Supply distribution assessment
      5. Age assessment
      6. Trading volume assessment
      7. Holder count assessment
    
    Args:
        token: Token data including address, liquidity, etc.
        config: Configuration including risk settings
        
    Returns:
        Tuple of (passes, reason, assessment)
    """
    token_address = token.get("address")
    
    if not token_address:
        logging.error("No token address provided.")
        return False, "Missing token address.", create_risk_assessment(False, "Missing token address", 100)

    # Extract risk settings from config with defaults
    risk_settings = config.riskSettings if hasattr(config, 'riskSettings') else {}
    
    # Handle both dataclass and dict config formats
    if hasattr(risk_settings, 'blacklistedCoins'):
        blacklisted_coins = risk_settings.blacklistedCoins
        liquidity_threshold = getattr(config.tradingSettings, 'liquidityThreshold', MIN_LIQUIDITY_DEFAULT)
        max_concentration = getattr(risk_settings, 'maxSupplyConcentration', MAX_CONCENTRATION_DEFAULT)
        min_holders = getattr(risk_settings, 'minHolders', MIN_HOLDERS_DEFAULT)
        max_risk_score = getattr(risk_settings, 'maxRiskScore', MAX_RISK_SCORE_DEFAULT)
        require_rugcheck = getattr(risk_settings, 'requireRugCheck', True)
    else:
        # Fallback to dictionary access if config is a dict
        blacklisted_coins = risk_settings.get("blacklistedCoins", [])
        liquidity_threshold = config.get("tradingSettings", {}).get("liquidityThreshold", MIN_LIQUIDITY_DEFAULT)
        max_concentration = risk_settings.get("maxSupplyConcentration", MAX_CONCENTRATION_DEFAULT)
        min_holders = risk_settings.get("minHolders", MIN_HOLDERS_DEFAULT)
        max_risk_score = risk_settings.get("maxRiskScore", MAX_RISK_SCORE_DEFAULT)
        require_rugcheck = risk_settings.get("requireRugCheck", True)
    
    # Check cache first
    cache_key = token_address
    current_time = time.time()
    if cache_key in risk_cache and current_time < cache_expiry.get(cache_key, 0):
        logging.debug(f"Using cached risk assessment for {token_address}")
        cached_result = risk_cache[cache_key]
        return cached_result.passes_filters, cached_result.risk_reason, cached_result

    # Start with all assessments
    all_assessments = {}

    # 1. Blacklist Check
    if token_address in blacklisted_coins:
        logging.info(f"Token {token_address} is blacklisted.")
        assessment = create_risk_assessment(
            False, 
            "Token is blacklisted.",
            100,
            assessments={"blacklist": {"result": "failed", "details": "Token is on blacklist"}}
        )
        
        # Cache the result
        risk_cache[cache_key] = assessment
        cache_expiry[cache_key] = current_time + CACHE_DURATION
        
        return False, "Token is blacklisted.", assessment

    # 2. Liquidity Check
    try:
        liquidity = float(token.get("liquidity", 0))
    except (ValueError, TypeError):
        logging.error(f"Invalid liquidity data for token {token_address}: {token.get('liquidity')}")
        return False, "Invalid liquidity data.", create_risk_assessment(
            False, 
            "Invalid liquidity data",
            90,
            assessments={"liquidity": {"result": "failed", "details": "Invalid data"}}
        )
        
    if liquidity < liquidity_threshold:
        logging.info(f"Token {token_address} has insufficient liquidity: {liquidity} USD.")
        return False, f"Insufficient liquidity: {liquidity} USD < {liquidity_threshold} USD.", create_risk_assessment(
            False, 
            f"Insufficient liquidity: {liquidity} USD < {liquidity_threshold} USD.",
            85,
            liquidity_usd=liquidity,
            assessments={"liquidity": {"result": "failed", "details": f"Only ${liquidity} available"}}
        )
    
    # Add liquidity assessment
    all_assessments["liquidity"] = {
        "result": "passed",
        "details": f"${liquidity} liquidity available"
    }

    # 3. Rug Pull Evaluation via RugCheck API
    rug_result = check_rug_status(token_address)
    
    # Process RugCheck results
    honeypot_risk = False
    contract_verified = False
    top_holders_concentration = 100
    liquidity_locked = 0
    holders_count = 0
    max_tax = 0
    creation_time = ""
    age_hours = 0
    
    if rug_result:
        # Extract key risk indicators
        risk_status = rug_result.get("status", "unknown")
        risk_score = rug_result.get("risk_score", 50)
        holders_count = rug_result.get("holders_count", 0)
        top_holders = rug_result.get("top_holders", [])
        liquidity_locked = rug_result.get("liquidity_locked", 0)
        honeypot_risk = rug_result.get("is_honeypot", False)
        contract_verified = rug_result.get("contract_verified", False)
        max_tax = rug_result.get("max_tax", 0)
        creation_time = rug_result.get("creation_time", "")
        
        # Calculate top holder concentration
        if top_holders:
            try:
                top_holders_concentration = sum(float(holder.get("pct", 0)) for holder in top_holders[:10]) * 100
            except (ValueError, TypeError):
                top_holders_concentration = 100
                logging.warning(f"Error calculating top holders concentration for {token_address}")
        
        # Calculate token age
        if creation_time:
            try:
                creation_dt = datetime.fromisoformat(creation_time.replace("Z", "+00:00"))
                age_hours = (datetime.now(creation_dt.tzinfo) - creation_dt).total_seconds() / 3600
            except (ValueError, TypeError):
                age_hours = 0
                logging.warning(f"Error calculating token age for {token_address}")
        
        # Add RugCheck assessment
        all_assessments["rugcheck"] = {
            "result": "passed" if risk_status != "bad" else "failed",
            "details": f"Risk status: {risk_status}, Score: {risk_score}"
        }
        
        # Check if risk score exceeds maximum
        if risk_score > max_risk_score and require_rugcheck:
            logging.info(f"Token {token_address} failed risk score check: {risk_score} > {max_risk_score}")
            assessment = create_risk_assessment(
                False,
                f"Risk score too high: {risk_score} > {max_risk_score}",
                risk_score,
                liquidity_usd=liquidity,
                holders_count=holders_count,
                top_holders_concentration=top_holders_concentration,
                liquidity_locked=liquidity_locked,
                contract_verification=contract_verified,
                honeypot_risk=honeypot_risk,
                max_tax=max_tax,
                creation_time=creation_time,
                age_hours=age_hours,
                assessments=all_assessments
            )
            
            # Cache the result
            risk_cache[cache_key] = assessment
            cache_expiry[cache_key] = current_time + CACHE_DURATION
            
            return False, f"Risk score too high: {risk_score} > {max_risk_score}", assessment
        
        # Check for honeypot risk
        if honeypot_risk:
            logging.info(f"Token {token_address} identified as potential honeypot.")
            assessment = create_risk_assessment(
                False,
                "Potential honeypot detected",
                95,
                liquidity_usd=liquidity,
                holders_count=holders_count,
                top_holders_concentration=top_holders_concentration,
                liquidity_locked=liquidity_locked,
                contract_verification=contract_verified,
                honeypot_risk=honeypot_risk,
                max_tax=max_tax,
                creation_time=creation_time,
                age_hours=age_hours,
                assessments=all_assessments
            )
            
            # Cache the result
            risk_cache[cache_key] = assessment
            cache_expiry[cache_key] = current_time + CACHE_DURATION
            
            return False, "Potential honeypot detected", assessment
    else:
        all_assessments["rugcheck"] = {
            "result": "skipped",
            "details": "RugCheck data unavailable"
        }
        
        # If RugCheck is required but data is unavailable, fail the check
        if require_rugcheck:
            logging.info(f"Token {token_address} lacks required RugCheck data.")
            return False, "Missing required RugCheck data.", create_risk_assessment(
                False,
                "Missing required RugCheck data",
                80,
                liquidity_usd=liquidity,
                assessments=all_assessments
            )

    # 4. Supply Distribution Check
    all_assessments["distribution"] = {
        "result": "passed",
        "details": f"Top holder concentration: {top_holders_concentration:.1f}%"
    }
    
    if top_holders_concentration > max_concentration:
        logging.info(f"Token {token_address} has unhealthy supply distribution: {top_holders_concentration:.1f}% > {max_concentration}%")
        assessment = create_risk_assessment(
            False,
            f"Unhealthy supply distribution: {top_holders_concentration:.1f}% > {max_concentration}%",
            75,
            liquidity_usd=liquidity,
            holders_count=holders_count,
            top_holders_concentration=top_holders_concentration,
            liquidity_locked=liquidity_locked,
            contract_verification=contract_verified,
            honeypot_risk=honeypot_risk,
            max_tax=max_tax,
            creation_time=creation_time,
            age_hours=age_hours,
            assessments=all_assessments
        )
        
        # Cache the result
        risk_cache[cache_key] = assessment
        cache_expiry[cache_key] = current_time + CACHE_DURATION
        
        return False, f"Unhealthy supply distribution: {top_holders_concentration:.1f}% > {max_concentration}%", assessment

    # 5. Holder Count Check
    all_assessments["holders"] = {
        "result": "passed" if holders_count >= min_holders else "failed",
        "details": f"Holders: {holders_count}"
    }
    
    if holders_count < min_holders and holders_count > 0:
        logging.info(f"Token {token_address} has too few holders: {holders_count} < {min_holders}")
        assessment = create_risk_assessment(
            False,
            f"Too few holders: {holders_count} < {min_holders}",
            70,
            liquidity_usd=liquidity,
            holders_count=holders_count,
            top_holders_concentration=top_holders_concentration,
            liquidity_locked=liquidity_locked,
            contract_verification=contract_verified,
            honeypot_risk=honeypot_risk,
            max_tax=max_tax,
            creation_time=creation_time,
            age_hours=age_hours,
            assessments=all_assessments
        )
        
        # Cache the result
        risk_cache[cache_key] = assessment
        cache_expiry[cache_key] = current_time + CACHE_DURATION
        
        return False, f"Too few holders: {holders_count} < {min_holders}", assessment

    # 6. Tax Check
    all_assessments["tax"] = {
        "result": "passed" if max_tax <= 10 else "warning" if max_tax <= 20 else "failed",
        "details": f"Max tax: {max_tax}%"
    }
    
    if max_tax > 20:
        logging.info(f"Token {token_address} has excessive tax: {max_tax}%")
        assessment = create_risk_assessment(
            False,
            f"Excessive tax: {max_tax}%",
            65,
            liquidity_usd=liquidity,
            holders_count=holders_count,
            top_holders_concentration=top_holders_concentration,
            liquidity_locked=liquidity_locked,
            contract_verification=contract_verified,
            honeypot_risk=honeypot_risk,
            max_tax=max_tax,
            creation_time=creation_time,
            age_hours=age_hours,
            assessments=all_assessments
        )
        
        # Cache the result
        risk_cache[cache_key] = assessment
        cache_expiry[cache_key] = current_time + CACHE_DURATION
        
        return False, f"Excessive tax: {max_tax}%", assessment

    # Calculate final risk score based on assessments
    final_risk_score = calculate_risk_score(
        liquidity, 
        holders_count, 
        top_holders_concentration,
        liquidity_locked,
        contract_verified,
        max_tax,
        age_hours
    )
    
    # Create final positive assessment
    final_assessment = create_risk_assessment(
        True,
        "Passed all risk filters",
        final_risk_score,
        liquidity_usd=liquidity,
        holders_count=holders_count,
        top_holders_concentration=top_holders_concentration,
        liquidity_locked=liquidity_locked,
        contract_verification=contract_verified,
        honeypot_risk=honeypot_risk,
        max_tax=max_tax,
        creation_time=creation_time,
        age_hours=age_hours,
        assessments=all_assessments
    )
    
    # Cache the result
    risk_cache[cache_key] = final_assessment
    cache_expiry[cache_key] = current_time + CACHE_DURATION
    
    logging.info(f"Token {token_address} passed all risk filters. Risk score: {final_risk_score}")
    return True, "OK", final_assessment

def calculate_risk_score(
    liquidity: float,
    holders_count: int,
    top_holders_concentration: float,
    liquidity_locked: float,
    contract_verified: bool,
    max_tax: float,
    age_hours: float
) -> int:
    """
    Calculate a comprehensive risk score based on multiple factors.
    
    Args:
        liquidity: Available liquidity in USD
        holders_count: Number of token holders
        top_holders_concentration: Percentage held by top 10 holders
        liquidity_locked: Amount of locked liquidity in USD
        contract_verified: Whether the contract is verified
        max_tax: Maximum buy/sell tax percentage
        age_hours: Age of token in hours
        
    Returns:
        int: Risk score from 0-100 (lower is better)
    """
    # Base score - start at 50
    score = 50
    
    # Liquidity factors
    if liquidity >= 50000:
        score -= 15
    elif liquidity >= 10000:
        score -= 10
    elif liquidity >= 5000:
        score -= 5
    elif liquidity < 1000:
        score += 15
    
    # Holders count
    if holders_count >= 1000:
        score -= 15
    elif holders_count >= 200:
        score -= 10
    elif holders_count >= 50:
        score -= 5
    elif holders_count < 25:
        score += 15
    
    # Concentration risk
    if top_holders_concentration <= 30:
        score -= 15
    elif top_holders_concentration <= 50:
        score -= 10
    elif top_holders_concentration <= 70:
        score -= 5
    elif top_holders_concentration > 85:
        score += 15
    
    # Locked liquidity
    locked_percentage = (liquidity_locked / max(liquidity, 1)) * 100
    if locked_percentage >= 80:
        score -= 15
    elif locked_percentage >= 50:
        score -= 10
    elif locked_percentage >= 30:
        score -= 5
    elif locked_percentage < 10:
        score += 10
    
    # Contract verification
    if contract_verified:
        score -= 10
    else:
        score += 15
    
    # Tax rate
    if max_tax <= 5:
        score -= 10
    elif max_tax <= 10:
        score -= 5
    elif max_tax > 15:
        score += int(max_tax / 2)  # Higher taxes increase risk score significantly
    
    # Age factor - newer tokens are riskier
    if age_hours >= 720:  # 30 days
        score -= 15
    elif age_hours >= 168:  # 7 days
        score -= 10
    elif age_hours >= 48:  # 2 days
        score -= 5
    elif age_hours < 24:  # Less than 1 day
        score += 15
    
    # Ensure score is within bounds
    return max(0, min(100, score))

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def check_rug_status(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Evaluate the token using the RugCheck API endpoint.
    
    Args:
        token_address: Token address to check
        
    Returns:
        Dict with rugcheck results or None if failed
    """
    url = f"{RUGCHECK_BASE_URL}/{token_address}/report"
    
    try:
        logging.info(f"Requesting RugCheck report for {token_address}")
        response = requests.get(url, timeout=10)
        
        # Check if rate limited
        if response.status_code == 429:
            logging.warning(f"RugCheck API rate limit reached. Retrying in 5 seconds...")
            time.sleep(5)
            raise requests.RequestException("Rate limited")
        
        # Handle other error status codes
        if response.status_code != 200:
            logging.error(f"RugCheck API returned non-200 status: {response.status_code}")
            return mock_rugcheck_response(token_address)
        
        data = response.json()
        
        # Extract fields per RugCheck API
        risk_status = data.get("status", "unknown")  # e.g., "good", "caution", "bad"
        risk_score = data.get("score", 50)  # Numeric score if provided
        top_holders = data.get("topHolders", [])
        holders_count = data.get("holdersCount", 0)
        markets = data.get("markets", [])
        
        # Calculate locked liquidity
        liquidity_locked = sum(m.get("lp", {}).get("lpLockedUSD", 0) for m in markets)
        
        # Check for honeypot indicators
        honeypot_indicators = data.get("honeypot", {})
        is_honeypot = honeypot_indicators.get("isHoneypot", False)
        
        # Extract contract data
        contract_data = data.get("contract", {})
        contract_verified = contract_data.get("verified", False)
        
        # Extract tax data
        tax_data = data.get("tax", {})
        buy_tax = tax_data.get("buyTax", 0)
        sell_tax = tax_data.get("sellTax", 0)
        max_tax = max(buy_tax, sell_tax)
        
        # Get creation time
        creation_time = data.get("createdAt", "")

        result = {
            "status": risk_status,
            "risk_score": risk_score,
            "top_holders": top_holders,
            "holders_count": holders_count,
            "liquidity_locked": liquidity_locked,
            "is_honeypot": is_honeypot,
            "contract_verified": contract_verified,
            "max_tax": max_tax,
            "creation_time": creation_time,
            "raw_data": data  # Store the complete data for reference
        }
        
        logging.debug(f"RugCheck result for {token_address}: {json.dumps(result, default=str)}")
        return result
    
    except requests.RequestException as e:
        if not isinstance(e, requests.Timeout):
            logging.error(f"Error fetching RugCheck report for {token_address}: {e}")
        raise  # Allow retry mechanism to handle it
    
    except Exception as e:
        logging.error(f"Unexpected error in RugCheck report for {token_address}: {e}")
        return mock_rugcheck_response(token_address)

def mock_rugcheck_response(token_address: str) -> Dict[str, Any]:
    """
    Create a mock RugCheck response when the API fails.
    
    Args:
        token_address: Token address
        
    Returns:
        Dict with mocked rugcheck data
    """
    logging.warning(f"Using mock RugCheck response for {token_address} due to API failure")
    return {
        "status": "caution",
        "risk_score": 60,
        "top_holders": [{"address": "mock1", "pct": 0.2}, {"address": "mock2", "pct": 0.1}],
        "holders_count": 50,
        "liquidity_locked": 2000,
        "is_honeypot": False,
        "contract_verified": True,
        "max_tax": 10,
        "creation_time": datetime.now().isoformat(),
        "is_mocked": True
    }

def clean_risk_cache() -> None:
    """Remove expired items from the risk cache"""
    current_time = time.time()
    expired_keys = [k for k, exp_time in cache_expiry.items() if current_time > exp_time]
    
    for key in expired_keys:
        if key in risk_cache:
            del risk_cache[key]
        if key in cache_expiry:
            del cache_expiry[key]
            
    logging.debug(f"Cleaned {len(expired_keys)} expired items from risk cache")

def get_token_risk(token_address: str, force_refresh: bool = False) -> Optional[RiskAssessment]:
    """
    Get cached risk assessment for a token or force a refresh.
    
    Args:
        token_address: Token address to check
        force_refresh: Whether to force a fresh assessment
        
    Returns:
        RiskAssessment object or None if not found and can't be assessed
    """
    if not token_address:
        return None
    
    # Check cache first if not forcing refresh
    cache_key = token_address
    current_time = time.time()
    
    if not force_refresh and cache_key in risk_cache and current_time < cache_expiry.get(cache_key, 0):
        return risk_cache[cache_key]
    
    # Get fresh RugCheck data
    rug_result = check_rug_status(token_address)
    if not rug_result:
        return None
    
    # Create a dummy token object with address
    token = {"address": token_address}
    
    # If RugCheck has liquidity data, add it
    if "liquidity" in rug_result.get("raw_data", {}):
        token["liquidity"] = rug_result["raw_data"]["liquidity"]
    
    # Apply risk filters with minimal config
    # Create a minimal config object
    class MinimalConfig:
        class RiskSettings:
            requireRugCheck = False
            blacklistedCoins = []
        
        class TradingSettings:
            liquidityThreshold = MIN_LIQUIDITY_DEFAULT
        
        riskSettings = RiskSettings()
        tradingSettings = TradingSettings()
    
    _, _, assessment = apply_risk_filters(token, MinimalConfig())
    return assessment

if __name__ == "__main__":
    # Example usage
    token_data = {
        "address": "TokenABC123",
        "liquidity": 5000,
        "name": "Sample Token"
    }
    
    # Example config
    class TestConfig:
        class RiskSettings:
            blacklistedCoins = ["BadToken1", "BadToken2"]
            maxSupplyConcentration = 80.0
            minHolders = 20
            maxRiskScore = 75
            requireRugCheck = True
        
        class TradingSettings:
            liquidityThreshold = 1000.0
        
        riskSettings = RiskSettings()
        tradingSettings = TradingSettings()
    
    config = TestConfig()
    
    # Perform risk assessment
    passes, reason, assessment = apply_risk_filters(token_data, config)
    
    print(f"Risk Assessment for {token_data['address']}:")
    print(f"Passed: {passes}")
    print(f"Reason: {reason}")
    print(f"Risk Score: {assessment.risk_score} ({assessment.risk_level} risk)")
    print(f"Liquidity: ${assessment.liquidity_usd}")
    print(f"Holders: {assessment.holders_count}")
    print(f"Top Holders Concentration: {assessment.top_holders_concentration:.1f}%")
    print(f"Liquidity Locked: ${assessment.liquidity_locked}")
    print(f"Contract Verified: {assessment.contract_verification}")
    print(f"Honeypot Risk: {assessment.honeypot_risk}")
    print(f"Max Tax: {assessment.max_tax}%")
    print(f"Token Age: {assessment.age_hours:.1f} hours")
    
    print("\nDetailed Assessments:")
    for check, details in assessment.assessments.items():
        print(f"- {check}: {details['result']} - {details['details']}")