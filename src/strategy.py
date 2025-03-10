import logging
import json
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Define trading action types
class TradeAction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    TAKE_PROFIT = "TAKE_PROFIT"
    CUT_LOSS = "CUT_LOSS"
    NO_ACTION = "NO_ACTION"

@dataclass
class TradingDecision:
    """Structured trading decision with reasoning"""
    action: TradeAction
    confidence: float  # 0-1 scale
    reasons: List[str]
    position_size: float  # In SOL
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    time_horizon: str = "short_term"  # "short_term", "medium_term", "long_term"
    strategy_name: str = "ai_consensus"
    token_address: str = ""
    token_name: str = ""
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "action": self.action.value,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "position_size": self.position_size,
            "price_target": self.price_target,
            "stop_loss": self.stop_loss,
            "time_horizon": self.time_horizon,
            "strategy_name": self.strategy_name,
            "token_address": self.token_address,
            "token_name": self.token_name,
            "timestamp": self.timestamp
        }

def decide_trade(
    ai_evaluation: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    sentiment_data: Dict[str, Any],
    token_data: Dict[str, Any],
    market_context: Optional[Dict[str, Any]] = None,
    portfolio_state: Optional[Dict[str, Any]] = None
) -> TradingDecision:
    """
    Make a comprehensive trading decision based on multiple data sources.
    
    Args:
        ai_evaluation: AI analysis results
        risk_assessment: Risk evaluation results
        sentiment_data: Social sentiment analysis
        token_data: Token market data
        market_context: Broader market conditions (optional)
        portfolio_state: Current portfolio state (optional)
        
    Returns:
        TradingDecision object with action and details
    """
    logging.info(f"Evaluating trade decision for {token_data.get('name', 'unknown token')}")
    
    # Extract key decision factors
    token_address = token_data.get("address", "")
    token_name = token_data.get("name", "Unknown Token")
    
    # Default to smaller position size for safety
    default_position_size = float(os.getenv("DEFAULT_POSITION_SIZE", "0.1"))  # SOL
    max_position_size = float(os.getenv("MAX_POSITION_SIZE", "1.0"))  # SOL
    
    # IMPROVED: Check for explicit AI recommendation first
    ai_recommendation = ai_evaluation.get("recommendation", "HOLD")
    ai_confidence = ai_evaluation.get("ai_confidence", 5.0)
    ai_risk_score = ai_evaluation.get("risk_score", 5.0)
    
    # If AI explicitly recommends AVOID and has high risk or low confidence, respect that
    if ai_recommendation == "AVOID" and (ai_risk_score > 6.0 or ai_confidence < 4.0):
        reasons = [
            f"AI explicitly recommends avoiding this token (confidence: {ai_confidence}/10)",
            f"High risk assessment from AI ({ai_risk_score}/10)",
        ]
        
        # Add risk factors if available
        risk_factors = ai_evaluation.get("risk_reasons", [])
        if risk_factors:
            reasons.extend(risk_factors[:2])  # Add top 2 risk factors
            
        return TradingDecision(
            action=TradeAction.HOLD,
            confidence=0.8,
            reasons=reasons,
            position_size=0.0,
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    # Evaluate various signals
    ai_signal = evaluate_ai_signal(ai_evaluation)
    risk_signal = evaluate_risk_signal(risk_assessment)
    sentiment_signal = evaluate_sentiment_signal(sentiment_data)
    market_signal = evaluate_market_signal(market_context) if market_context else 0.0
    
    # Calculate weighted consensus signal
    weighted_signal = calculate_weighted_consensus(
        ai_signal, 
        risk_signal, 
        sentiment_signal, 
        market_signal
    )
    
    # IMPROVED: Minimum buy threshold
    # Only consider buying if signal is at least 0.4
    BUY_THRESHOLD = 0.4
    
    # Determine base action from consensus
    action, confidence, reasons = determine_base_action(
        weighted_signal, 
        ai_evaluation, 
        risk_assessment,
        sentiment_data,
        buy_threshold=BUY_THRESHOLD
    )
    
    # Apply portfolio constraints if available
    if portfolio_state:
        action, confidence, reasons, position_size = apply_portfolio_constraints(
            action,
            confidence,
            reasons,
            portfolio_state,
            token_address,
            default_position_size,
            max_position_size
        )
    else:
        # Scale position size based on confidence
        position_size = default_position_size * min(confidence * 2, 1.0)
        position_size = min(position_size, max_position_size)
    
    # Determine price targets and stop loss
    price_target, stop_loss = calculate_price_levels(
        action, 
        token_data, 
        ai_evaluation
    )
    
    # Create the final decision
    decision = TradingDecision(
        action=action,
        confidence=confidence,
        reasons=reasons,
        position_size=position_size,
        price_target=price_target,
        stop_loss=stop_loss,
        time_horizon="short_term",  # Default to short-term
        strategy_name="ai_consensus",
        token_address=token_address,
        token_name=token_name,
        timestamp=datetime.now().isoformat()
    )
    
    logging.info(f"Trade decision: {action.value} {token_name} with {confidence:.2f} confidence")
    for reason in reasons[:2]:  # Log first two reasons
        logging.info(f"- {reason}")
    
    return decision

def evaluate_ai_signal(ai_evaluation: Dict[str, Any]) -> float:
    """
    Convert AI evaluation to a normalized signal between -1 and 1.
    
    Args:
        ai_evaluation: AI analysis results
        
    Returns:
        float: Signal from -1 (strong sell) to 1 (strong buy)
    """
    # Extract the key metrics from AI evaluation
    try:
        ai_confidence = ai_evaluation.get("ai_confidence", 5.0)
        risk_score = ai_evaluation.get("risk_score", 5.0)
        recommendation = ai_evaluation.get("recommendation", "HOLD")
        
        # IMPROVED: More nuanced recommendation modifier
        rec_modifier = {
            "BUY": 1.0,
            "HOLD": 0.0,
            "AVOID": -1.0
        }.get(recommendation, 0.0)
        
        # IMPROVED: Higher weight to recommendation
        # Normalize AI confidence to -1 to 1 scale
        normalized_confidence = (ai_confidence - 5.0) / 5.0
        
        # Adjust by risk (higher risk reduces signal)
        risk_adjustment = 1.0 - (risk_score / 10.0)
        
        # Calculate final signal with more weight on explicit recommendation
        signal = (normalized_confidence * 0.4 + rec_modifier * 0.6) * risk_adjustment
        
        # Ensure it's within bounds
        return max(-1.0, min(1.0, signal))
    
    except Exception as e:
        logging.error(f"Error evaluating AI signal: {e}")
        return 0.0

def evaluate_risk_signal(risk_assessment: Dict[str, Any]) -> float:
    """
    Convert risk assessment to a normalized signal.
    
    Args:
        risk_assessment: Risk evaluation results
        
    Returns:
        float: Signal from -1 (very risky) to 1 (very safe)
    """
    try:
        # Extract risk factors
        passes_filters = risk_assessment.get("passes_filters", False)
        risk_score = risk_assessment.get("risk_score", 50)
        risk_level = risk_assessment.get("risk_level", "high")
        
        # Failed filters is an immediate strong negative
        if not passes_filters:
            return -1.0
        
        # Convert risk score (0-100 scale) to signal (-1 to 1 scale)
        # Lower risk score is better, so invert and normalize
        signal = 1.0 - (risk_score / 50.0)
        
        # IMPROVED: Add additional penalty for high risk levels
        if risk_level == "extreme":
            signal -= 0.3
        elif risk_level == "high":
            signal -= 0.15
        
        # Ensure it's within bounds
        return max(-1.0, min(1.0, signal))
    
    except Exception as e:
        logging.error(f"Error evaluating risk signal: {e}")
        return -0.5  # Default to cautious on error

def evaluate_sentiment_signal(sentiment_data: Dict[str, Any]) -> float:
    """
    Convert sentiment data to a normalized signal.
    
    Args:
        sentiment_data: Social sentiment analysis
        
    Returns:
        float: Signal from -1 (very negative) to 1 (very positive)
    """
    try:
        # Extract sentiment score and confidence
        sentiment_score = sentiment_data.get("sentiment_score", 0.0)
        confidence = sentiment_data.get("confidence", 0.5)
        
        # Adjust by confidence
        weighted_sentiment = sentiment_score * confidence
        
        # Return the weighted signal (already in -1 to 1 scale)
        return weighted_sentiment
    
    except Exception as e:
        logging.error(f"Error evaluating sentiment signal: {e}")
        return 0.0

def evaluate_market_signal(market_context: Dict[str, Any]) -> float:
    """
    Convert market context to a normalized signal.
    
    Args:
        market_context: Broader market conditions
        
    Returns:
        float: Signal from -1 (very bearish) to 1 (very bullish)
    """
    try:
        # Extract market sentiment
        market_sentiment = market_context.get("market_sentiment", "neutral")
        solana_outlook = market_context.get("solana_outlook", "neutral")
        risk_level = market_context.get("risk_level", "moderate")
        
        # Convert sentiment to numeric signal
        market_modifier = {
            "bullish": 0.8,
            "neutral": 0.0,
            "bearish": -0.8
        }.get(market_sentiment, 0.0)
        
        # Convert Solana outlook to numeric signal
        solana_modifier = {
            "positive": 0.5,
            "neutral": 0.0,
            "negative": -0.5
        }.get(solana_outlook, 0.0)
        
        # Convert risk level to numeric signal (higher risk = lower signal)
        risk_modifier = {
            "low": 0.3,
            "moderate": 0.0,
            "high": -0.3,
            "extreme": -0.6
        }.get(risk_level, 0.0)
        
        # Calculate overall market signal
        signal = market_modifier + solana_modifier + risk_modifier
        
        # Ensure it's within bounds
        return max(-1.0, min(1.0, signal))
    
    except Exception as e:
        logging.error(f"Error evaluating market signal: {e}")
        return 0.0

def calculate_weighted_consensus(
    ai_signal: float,
    risk_signal: float,
    sentiment_signal: float,
    market_signal: float
) -> float:
    """
    Calculate a weighted consensus from multiple signals.
    
    Args:
        ai_signal: AI evaluation signal (-1 to 1)
        risk_signal: Risk assessment signal (-1 to 1)
        sentiment_signal: Sentiment analysis signal (-1 to 1)
        market_signal: Market context signal (-1 to 1)
        
    Returns:
        float: Consensus signal from -1 to 1
    """
    # IMPROVED: Updated weights with more emphasis on AI and risk
    ai_weight = 0.50  # Highest weight on AI analysis
    risk_weight = 0.30  # Significant weight on risk
    sentiment_weight = 0.10  # Moderate weight on sentiment
    market_weight = 0.10  # Moderate weight on market
    
    # Calculate weighted consensus
    consensus = (
        ai_signal * ai_weight +
        risk_signal * risk_weight +
        sentiment_signal * sentiment_weight +
        market_signal * market_weight
    )
    
    return consensus

def determine_base_action(
    consensus_signal: float,
    ai_evaluation: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    sentiment_data: Dict[str, Any],
    buy_threshold: float = 0.4
) -> Tuple[TradeAction, float, List[str]]:
    """
    Determine the base trading action based on consensus signal.
    
    Args:
        consensus_signal: Weighted consensus signal (-1 to 1)
        ai_evaluation: AI analysis results
        risk_assessment: Risk evaluation results
        sentiment_data: Social sentiment analysis
        buy_threshold: Minimum signal required for BUY decision
        
    Returns:
        Tuple of (TradeAction, confidence, reasons)
    """
    reasons = []
    
    # IMPROVED: Higher threshold for buy (0.6 -> 0.7)
    # Strong buy signal
    if consensus_signal >= 0.7:
        action = TradeAction.BUY
        confidence = min(abs(consensus_signal) + 0.2, 1.0)
        reasons.append(f"Strong positive consensus signal: {consensus_signal:.2f}")
        
        # Add specific reasons from evaluations
        if ai_evaluation.get("recommendation") == "BUY":
            reasons.append(f"AI recommends BUY with confidence {ai_evaluation.get('ai_confidence', 0):.1f}/10")
        if risk_assessment.get("passes_filters", False):
            reasons.append(f"Passed all risk filters with score {risk_assessment.get('risk_score', 0)}")
    
    # Moderate buy signal - with higher threshold
    elif consensus_signal >= buy_threshold:
        action = TradeAction.BUY
        confidence = abs(consensus_signal)
        reasons.append(f"Positive consensus signal: {consensus_signal:.2f}")
        
        # Add specific reasons
        if sentiment_data.get("sentiment_label") == "positive":
            reasons.append("Positive social sentiment")
        if risk_assessment.get("risk_level") in ["low", "medium"]:
            reasons.append(f"Acceptable risk level: {risk_assessment.get('risk_level', 'unknown')}")
    
    # Weak buy signal - now made into HOLD due to higher threshold
    elif consensus_signal > 0.1:
        # IMPROVED: Changed from BUY to HOLD for weak signals
        action = TradeAction.HOLD
        confidence = 0.5 + abs(consensus_signal) * 0.5
        reasons.append(f"Weak positive signal: {consensus_signal:.2f}")
        reasons.append("Signal too weak for confident buy decision")
    
    # Strong sell signal
    elif consensus_signal <= -0.6:
        action = TradeAction.SELL
        confidence = min(abs(consensus_signal) + 0.2, 1.0)
        reasons.append(f"Strong negative consensus signal: {consensus_signal:.2f}")
        
        if ai_evaluation.get("recommendation") == "AVOID":
            reasons.append("AI explicitly recommends avoiding this token")
        if not risk_assessment.get("passes_filters", True):
            reasons.append(f"Failed risk assessment: {risk_assessment.get('risk_reason', 'Unknown risk')}")
    
    # Moderate sell signal
    elif consensus_signal <= -0.3:
        action = TradeAction.SELL
        confidence = abs(consensus_signal)
        reasons.append(f"Negative consensus signal: {consensus_signal:.2f}")
        
        if sentiment_data.get("sentiment_label") == "negative":
            reasons.append("Negative social sentiment")
        if risk_assessment.get("risk_level") in ["high", "extreme"]:
            reasons.append(f"High risk level: {risk_assessment.get('risk_level', 'unknown')}")
    
    # Weak sell signal
    elif consensus_signal < -0.1:
        action = TradeAction.SELL
        confidence = abs(consensus_signal) * 0.8
        reasons.append(f"Mild negative signal: {consensus_signal:.2f}")
        reasons.append("Consider partial position exit due to weaker signal")
    
    # Neutral signal
    else:
        action = TradeAction.HOLD
        confidence = 0.5 + abs(consensus_signal) * 2
        reasons.append(f"Neutral consensus signal: {consensus_signal:.2f}")
        reasons.append("Insufficient conviction for new position")
    
    return action, confidence, reasons

def apply_portfolio_constraints(
    action: TradeAction,
    confidence: float,
    reasons: List[str],
    portfolio_state: Dict[str, Any],
    token_address: str,
    default_position_size: float,
    max_position_size: float
) -> Tuple[TradeAction, float, List[str], float]:
    """
    Apply portfolio constraints to the trading decision.
    
    Args:
        action: Base trade action
        confidence: Confidence level
        reasons: Reasons for the action
        portfolio_state: Current portfolio state
        token_address: Token address
        default_position_size: Default position size in SOL
        max_position_size: Maximum position size in SOL
        
    Returns:
        Tuple of (action, confidence, reasons, position_size)
    """
    # Extract portfolio information
    current_positions = portfolio_state.get("positions", {})
    daily_trades = portfolio_state.get("daily_trades", 0)
    max_daily_trades = portfolio_state.get("max_daily_trades", 10)
    available_sol = portfolio_state.get("available_sol", 0.0)
    max_portfolio_risk = portfolio_state.get("max_portfolio_risk", 5.0)
    total_portfolio_value = portfolio_state.get("total_portfolio_value", 0.0)
    
    # Check for existing position in this token
    has_position = token_address in current_positions
    
    # Check daily trade limit
    if daily_trades >= max_daily_trades and action == TradeAction.BUY and not has_position:
        action = TradeAction.NO_ACTION
        reasons.append(f"Daily trade limit reached ({daily_trades}/{max_daily_trades})")
        confidence = min(confidence, 0.3)
        return action, confidence, reasons, 0.0
    
    # Check available SOL for buying
    if action == TradeAction.BUY and available_sol < default_position_size:
        if available_sol > default_position_size * 0.5:
            # Adjust position size down
            position_size = available_sol * 0.9  # Leave a small buffer
            reasons.append(f"Reduced position size due to available SOL ({available_sol:.3f})")
        else:
            # Not enough SOL
            action = TradeAction.NO_ACTION
            reasons.append(f"Insufficient SOL available ({available_sol:.3f})")
            confidence = min(confidence, 0.2)
            return action, confidence, reasons, 0.0
    
    # Scale position size based on confidence
    position_size = default_position_size * min(confidence * 1.5, 1.0)
    
    # Constrain position size to available SOL and max position
    if action == TradeAction.BUY:
        position_size = min(position_size, available_sol * 0.9, max_position_size)
    
    # Check portfolio risk concentration
    if action == TradeAction.BUY and total_portfolio_value > 0:
        position_percentage = (position_size / total_portfolio_value) * 100
        if position_percentage > max_portfolio_risk:
            # Reduce position size to meet risk limit
            position_size = (total_portfolio_value * max_portfolio_risk / 100) * 0.9
            reasons.append(f"Position size constrained by risk limit ({max_portfolio_risk}%)")
    
    # For selling, check if we have a position
    if action in [TradeAction.SELL, TradeAction.TAKE_PROFIT, TradeAction.CUT_LOSS]:
        if not has_position:
            action = TradeAction.NO_ACTION
            reasons.append("No existing position to sell")
            confidence = min(confidence, 0.2)
            return action, confidence, reasons, 0.0
    
    return action, confidence, reasons, position_size

def calculate_price_levels(
    action: TradeAction,
    token_data: Dict[str, Any],
    ai_evaluation: Dict[str, Any]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate price targets and stop loss levels.
    
    Args:
        action: Trading action
        token_data: Token market data
        ai_evaluation: AI analysis results
        
    Returns:
        Tuple of (price_target, stop_loss)
    """
    # Default to None
    price_target = None
    stop_loss = None
    
    # Get current price
    current_price = token_data.get("priceUSD", 0)
    if not current_price:
        return price_target, stop_loss
    
    if action == TradeAction.BUY:
        # Calculate price target based on AI evaluation
        ai_confidence = ai_evaluation.get("ai_confidence", 5)
        
        # Higher confidence = higher price target
        confidence_factor = min(ai_confidence / 5, 2)
        price_target = current_price * (1 + (0.2 * confidence_factor))
        
        # Set stop loss based on risk score
        risk_score = ai_evaluation.get("risk_score", 5)
        risk_factor = max(risk_score / 10, 0.1)
        stop_loss = current_price * (1 - (0.1 + risk_factor * 0.2))
    
    elif action in [TradeAction.SELL, TradeAction.TAKE_PROFIT, TradeAction.CUT_LOSS]:
        # For sells, target and stop loss are less relevant
        # But can still set them for monitoring
        price_target = current_price * 0.95  # 5% below current for sell
        stop_loss = current_price * 1.05  # 5% above current to abort sell
    
    return price_target, stop_loss

def get_exit_strategy(
    token_data: Dict[str, Any],
    position_data: Dict[str, Any],
    ai_evaluation: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    market_context: Optional[Dict[str, Any]] = None
) -> TradingDecision:
    """
    Determine exit strategy for an existing position.
    
    Args:
        token_data: Current token data
        position_data: Position information
        ai_evaluation: AI analysis results
        risk_assessment: Risk evaluation results
        market_context: Broader market conditions (optional)
        
    Returns:
        TradingDecision for position exit
    """
    # Extract position details
    token_address = token_data.get("address", "")
    token_name = token_data.get("name", "Unknown Token")
    entry_price = position_data.get("entry_price", 0)
    position_size = position_data.get("position_size", 0)
    entry_time = position_data.get("entry_time", "")
    stop_loss = position_data.get("stop_loss", 0)
    take_profit = position_data.get("take_profit", 0)
    
    # Current price
    current_price = token_data.get("priceUSD", 0)
    
    if not current_price or not entry_price:
        # Can't evaluate without prices
        return TradingDecision(
            action=TradeAction.HOLD,
            confidence=0.5,
            reasons=["Insufficient price data for exit evaluation"],
            position_size=position_size,
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    # Calculate profit/loss
    profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
    
    # Initialize reasons
    reasons = []
    
    # Check for stop loss and take profit
    if stop_loss and current_price <= stop_loss:
        return TradingDecision(
            action=TradeAction.CUT_LOSS,
            confidence=0.9,
            reasons=[f"Stop loss triggered at {stop_loss}", f"Current loss: {profit_loss_pct:.2f}%"],
            position_size=position_size,
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    if take_profit and current_price >= take_profit:
        return TradingDecision(
            action=TradeAction.TAKE_PROFIT,
            confidence=0.9,
            reasons=[f"Take profit target reached: {take_profit}", f"Current profit: {profit_loss_pct:.2f}%"],
            position_size=position_size,
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    # Calculate holding period
    holding_period = "unknown"
    holding_hours = 0
    
    if entry_time:
        try:
            entry_dt = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
            now = datetime.now().astimezone()
            holding_hours = (now - entry_dt).total_seconds() / 3600
            holding_period = f"{holding_hours:.1f} hours"
        except Exception as e:
            logging.error(f"Error calculating holding period: {e}")
    
    # Check for severe losses
    if profit_loss_pct <= -20:
        return TradingDecision(
            action=TradeAction.CUT_LOSS,
            confidence=0.85,
            reasons=[
                f"Severe loss detected: {profit_loss_pct:.2f}%",
                "Emergency exit to prevent further losses"
            ],
            position_size=position_size,
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    # Check for strong profits
    if profit_loss_pct >= 50:
        return TradingDecision(
            action=TradeAction.TAKE_PROFIT,
            confidence=0.8,
            reasons=[
                f"Strong profit secured: {profit_loss_pct:.2f}%",
                "Booking profits to reduce exposure"
            ],
            position_size=position_size * 0.75,  # Take partial profits
            price_target=current_price * 1.1,  # Target additional 10% for remainder
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    # Check for risk factors that suggest exit
    if not risk_assessment.get("passes_filters", True):
        return TradingDecision(
            action=TradeAction.SELL,
            confidence=0.75,
            reasons=[
                f"Risk assessment failed: {risk_assessment.get('risk_reason', 'Unknown risk')}",
                "Exiting position due to increased risk"
            ],
            position_size=position_size,
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    # Check for negative AI recommendation
    if ai_evaluation.get("recommendation") == "AVOID":
        return TradingDecision(
            action=TradeAction.SELL,
            confidence=0.7,
            reasons=[
                "AI analysis recommends avoiding this token",
                f"Current P/L: {profit_loss_pct:.2f}%"
            ],
            position_size=position_size,
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    # Check for expiration of holding period (if set in position)
    target_holding_period = position_data.get("target_holding_period", 168)  # Default 7 days
    if holding_hours > target_holding_period and profit_loss_pct > 0:
        return TradingDecision(
            action=TradeAction.TAKE_PROFIT,
            confidence=0.65,
            reasons=[
                f"Target holding period reached: {holding_period}",
                f"Positive return achieved: {profit_loss_pct:.2f}%"
            ],
            position_size=position_size,
            token_address=token_address,
            token_name=token_name,
            timestamp=datetime.now().isoformat()
        )
    
    # Default to hold if no exit conditions met
    return TradingDecision(
        action=TradeAction.HOLD,
        confidence=0.6,
        reasons=[
            f"No exit conditions met. Current P/L: {profit_loss_pct:.2f}%",
            f"Holding period: {holding_period}"
        ],
        position_size=position_size,
        token_address=token_address,
        token_name=token_name,
        timestamp=datetime.now().isoformat()
    )

if __name__ == "__main__":
    # Example usage
    # Sample AI evaluation
    ai_eval = {
        "ai_confidence": 8,
        "risk_score": 3,
        "recommendation": "BUY"
    }
    
    # Sample risk assessment
    risk_assess = {
        "passes_filters": True,
        "risk_score": 30,
        "risk_level": "medium",
        "risk_reason": "OK"
    }
    
    # Sample sentiment data
    sentiment = {
        "sentiment_score": 0.6,
        "sentiment_label": "positive",
        "confidence": 0.8
    }
    
    # Sample token data
    token = {
        "address": "TokenXYZ123",
        "name": "Example Token",
        "symbol": "XYZ",
        "priceUSD": 0.0005,
        "liquidity": 50000,
        "v24hUSD": 25000
    }
    
    # Test decision
    decision = decide_trade(ai_eval, risk_assess, sentiment, token)
    
    print("Trading Decision:")
    print(f"Action: {decision.action.value}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Position Size: {decision.position_size} SOL")
    print("\nReasons:")
    for reason in decision.reasons:
        print(f"- {reason}")
    
    if decision.price_target:
        print(f"\nPrice Target: ${decision.price_target:.6f}")
    if decision.stop_loss:
        print(f"Stop Loss: ${decision.stop_loss:.6f}")
    
    # Test with AVOID recommendation
    ai_eval_avoid = {
        "ai_confidence": 2.5,
        "risk_score": 7.5,
        "recommendation": "AVOID",
        "risk_reasons": ["Low liquidity raises manipulation risk", "Token has suspicious holder distribution"]
    }
    
    decision_avoid = decide_trade(ai_eval_avoid, risk_assess, sentiment, token)
    
    print("\n\nTesting with AVOID recommendation:")
    print(f"Action: {decision_avoid.action.value}")
    print(f"Confidence: {decision_avoid.confidence:.2f}")
    print("\nReasons:")
    for reason in decision_avoid.reasons:
        print(f"- {reason}")