import os
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Constants
MAX_MESSAGE_LENGTH = 4096  # Telegram message length limit
DEFAULT_PARSE_MODE = "Markdown"  # or "HTML"
MESSAGE_QUEUE = []
LAST_MESSAGE_TIME = 0
RATE_LIMIT_SECONDS = 1  # Minimum seconds between messages
MAX_QUEUE_SIZE = 50  # Maximum size for message queue
TELEGRAM_API_BASE = "https://api.telegram.org/bot"

class TelegramError(Exception):
    """Base exception for Telegram-related errors"""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
def send_telegram_message(
    message: str, 
    chat_id: Union[str, int], 
    bot_token: str,
    parse_mode: Optional[str] = DEFAULT_PARSE_MODE,
    disable_web_page_preview: bool = True,
    disable_notification: bool = False
) -> bool:
    """
    Send a message via the Telegram Bot API.

    Args:
        message: The text message to send
        chat_id: The target Telegram chat ID
        bot_token: The Telegram Bot API token
        parse_mode: Message formatting mode ("Markdown" or "HTML")
        disable_web_page_preview: Whether to disable link previews
        disable_notification: Whether to send the message silently

    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    if not bot_token or not chat_id:
        logging.warning("Missing bot token or chat ID. Cannot send Telegram message.")
        return False
    
    # Ensure message is within length limits
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[:MAX_MESSAGE_LENGTH-100] + "...\n\n[Message truncated due to length]"
    
    try:
        # Respect rate limiting
        global LAST_MESSAGE_TIME
        current_time = time.time()
        if current_time - LAST_MESSAGE_TIME < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - (current_time - LAST_MESSAGE_TIME))
        
        url = f"{TELEGRAM_API_BASE}{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification
        }
        
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        
        # Update last message time
        LAST_MESSAGE_TIME = time.time()
        
        result = response.json()
        if result.get("ok"):
            logging.info(f"Sent Telegram message to {chat_id}")
            return True
        else:
            error_code = result.get("error_code")
            description = result.get("description", "Unknown error")
            logging.error(f"Telegram API error: {error_code} - {description}")
            
            # Handle specific error codes
            if error_code == 429:  # Too Many Requests
                retry_after = result.get("parameters", {}).get("retry_after", 5)
                logging.warning(f"Rate limited by Telegram. Retrying after {retry_after} seconds")
                time.sleep(retry_after)
                # Add to queue for retry
                queue_message(message, chat_id, bot_token, parse_mode, disable_web_page_preview, disable_notification)
            
            return False
    except requests.RequestException as e:
        logging.error(f"Request error sending Telegram message: {e}")
        # Add to queue for retry
        queue_message(message, chat_id, bot_token, parse_mode, disable_web_page_preview, disable_notification)
        raise  # Let tenacity handle retry
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")
        return False

def queue_message(
    message: str, 
    chat_id: Union[str, int], 
    bot_token: str,
    parse_mode: Optional[str] = DEFAULT_PARSE_MODE,
    disable_web_page_preview: bool = True,
    disable_notification: bool = False
) -> None:
    """
    Queue a message for later sending in case of rate limiting.
    
    Args:
        message: The text message to send
        chat_id: The target Telegram chat ID
        bot_token: The Telegram Bot API token
        parse_mode: Message formatting mode
        disable_web_page_preview: Whether to disable link previews
        disable_notification: Whether to send the message silently
    """
    global MESSAGE_QUEUE
    
    # Add to queue if not full
    if len(MESSAGE_QUEUE) < MAX_QUEUE_SIZE:
        MESSAGE_QUEUE.append({
            "message": message,
            "chat_id": chat_id,
            "bot_token": bot_token,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification,
            "timestamp": time.time()
        })
        logging.info(f"Message queued for later sending. Queue size: {len(MESSAGE_QUEUE)}")
    else:
        logging.warning("Message queue full. Dropping message.")

def process_message_queue() -> None:
    """Process queued messages"""
    global MESSAGE_QUEUE
    
    if not MESSAGE_QUEUE:
        return
    
    logging.info(f"Processing message queue. {len(MESSAGE_QUEUE)} messages queued.")
    
    # Process up to 5 messages at a time
    messages_to_process = MESSAGE_QUEUE[:5]
    MESSAGE_QUEUE = MESSAGE_QUEUE[5:]
    
    for msg_data in messages_to_process:
        try:
            send_telegram_message(
                msg_data["message"],
                msg_data["chat_id"],
                msg_data["bot_token"],
                msg_data["parse_mode"],
                msg_data["disable_web_page_preview"],
                msg_data["disable_notification"]
            )
            # Small delay between messages
            time.sleep(0.5)
        except Exception as e:
            logging.error(f"Error processing queued message: {e}")
            # If it's a recent message (< 1 hour), requeue it
            if time.time() - msg_data["timestamp"] < 3600:
                queue_message(
                    msg_data["message"],
                    msg_data["chat_id"],
                    msg_data["bot_token"],
                    msg_data["parse_mode"],
                    msg_data["disable_web_page_preview"],
                    msg_data["disable_notification"]
                )

def send_trade_alert(
    token_data: Dict[str, Any],
    action: str,
    amount: float,
    price: float,
    reasons: List[str],
    chat_id: Union[str, int],
    bot_token: str
) -> bool:
    """
    Send a formatted trade alert.
    
    Args:
        token_data: Token information
        action: Trade action (BUY, SELL, etc.)
        amount: Trade amount
        price: Token price
        reasons: Reasons for the trade
        chat_id: The target Telegram chat ID
        bot_token: The Telegram Bot API token
        
    Returns:
        bool: True if the message was sent successfully
    """
    token_name = token_data.get("name", "Unknown")
    token_symbol = token_data.get("symbol", "Unknown")
    token_address = token_data.get("address", "Unknown")
    
    # Format action emoji
    action_emoji = {
        "BUY": "🟢",
        "SELL": "🔴",
        "TAKE_PROFIT": "💰",
        "CUT_LOSS": "✂️",
        "HOLD": "⏳"
    }.get(action, "🔄")
    
    # Format amounts
    if action == "BUY":
        amount_text = f"{amount:.3f} SOL"
    else:
        amount_text = f"{amount} tokens"
    
    # Format top reasons (max 3)
    reasons_text = ""
    for i, reason in enumerate(reasons[:3]):
        reasons_text += f"- {reason}\n"
    
    message = (
        f"{action_emoji} *{action} {token_symbol}*\n\n"
        f"*Token:* {token_name} ({token_symbol})\n"
        f"*Amount:* {amount_text}\n"
        f"*Price:* ${price:.8f}\n"
        f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"*Reasons:*\n{reasons_text}\n"
        f"*Address:* `{token_address[:8]}...{token_address[-4:]}`"
    )
    
    return send_telegram_message(message, chat_id, bot_token)

def send_performance_report(
    performance_data: Dict[str, Any],
    chat_id: Union[str, int],
    bot_token: str
) -> bool:
    """
    Send a formatted performance report.
    
    Args:
        performance_data: Performance statistics
        chat_id: The target Telegram chat ID
        bot_token: The Telegram Bot API token
        
    Returns:
        bool: True if the message was sent successfully
    """
    # Extract time periods
    periods = performance_data.get("periods", {})
    day1 = periods.get("1d", {})
    day7 = periods.get("7d", {})
    day30 = periods.get("30d", {})
    
    # Extract portfolio data
    portfolio = performance_data.get("portfolio", {})
    open_positions = portfolio.get("open_positions", 0)
    total_invested = portfolio.get("total_invested", 0)
    
    message = (
        f"📊 *Performance Report*\n\n"
        
        f"📅 *24-Hour Performance:*\n"
        f"Trades: {day1.get('total_trades', 0)}\n"
        f"Profit/Loss: {day1.get('profit_loss', 0):.4f} SOL\n"
        f"Win Rate: {day1.get('win_rate', 0):.1f}%\n\n"
        
        f"📅 *7-Day Performance:*\n"
        f"Trades: {day7.get('total_trades', 0)}\n"
        f"Profit/Loss: {day7.get('profit_loss', 0):.4f} SOL\n"
        f"Win Rate: {day7.get('win_rate', 0):.1f}%\n\n"
        
        f"📅 *30-Day Performance:*\n"
        f"Trades: {day30.get('total_trades', 0)}\n"
        f"Profit/Loss: {day30.get('profit_loss', 0):.4f} SOL\n"
        f"Win Rate: {day30.get('win_rate', 0):.1f}%\n\n"
        
        f"💼 *Current Status:*\n"
        f"Open Positions: {open_positions}\n"
        f"Total Invested: {total_invested:.4f} SOL\n"
    )
    
    # Add best performing token if available
    best_token = performance_data.get('best_token')
    if best_token:
        message += (
            f"\n🏆 *Top Performer:* {best_token.get('name', 'Unknown')}\n"
            f"Symbol: {best_token.get('symbol', 'Unknown')}\n"
            f"Profit: {best_token.get('profit', 0):.4f} SOL\n"
            f"Trades: {best_token.get('trades', 0)}\n"
        )
    
    return send_telegram_message(message, chat_id, bot_token)

def send_market_update(
    market_data: Dict[str, Any],
    chat_id: Union[str, int],
    bot_token: str
) -> bool:
    """
    Send a formatted market update.
    
    Args:
        market_data: Market analysis data
        chat_id: The target Telegram chat ID
        bot_token: The Telegram Bot API token
        
    Returns:
        bool: True if the message was sent successfully
    """
    market_sentiment = market_data.get("market_sentiment", "neutral")
    risk_level = market_data.get("risk_level", "moderate")
    solana_outlook = market_data.get("solana_outlook", "neutral")
    opportunities = market_data.get("trading_opportunities", "selective")
    key_trends = market_data.get("key_trends", [])
    summary = market_data.get("market_summary", "No summary available.")
    
    # Format sentiment emoji
    sentiment_emoji = {
        "bullish": "📈",
        "neutral": "➡️",
        "bearish": "📉"
    }.get(market_sentiment, "➡️")
    
    # Format risk emoji
    risk_emoji = {
        "low": "🟢",
        "moderate": "🟡",
        "high": "🟠",
        "extreme": "🔴"
    }.get(risk_level, "🟡")
    
    # Format trends
    trends_text = ""
    for trend in key_trends[:3]:
        trends_text += f"- {trend}\n"
    
    message = (
        f"🌍 *Market Update* {sentiment_emoji}\n\n"
        f"*Market Sentiment:* {market_sentiment.capitalize()}\n"
        f"*Risk Level:* {risk_emoji} {risk_level.capitalize()}\n"
        f"*Solana Outlook:* {solana_outlook.capitalize()}\n"
        f"*Opportunities:* {opportunities.capitalize()}\n\n"
        
        f"*Key Trends:*\n{trends_text}\n"
        f"*Summary:*\n{summary}"
    )
    
    return send_telegram_message(message, chat_id, bot_token)

def send_system_alert(
    alert_type: str,
    details: str,
    chat_id: Union[str, int],
    bot_token: str,
    disable_notification: bool = False
) -> bool:
    """
    Send a system alert message.
    
    Args:
        alert_type: Type of alert (error, warning, info)
        details: Alert details
        chat_id: The target Telegram chat ID
        bot_token: The Telegram Bot API token
        disable_notification: Whether to send silently
        
    Returns:
        bool: True if the message was sent successfully
    """
    # Format alert emoji
    alert_emoji = {
        "error": "🚨",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅"
    }.get(alert_type.lower(), "ℹ️")
    
    message = (
        f"{alert_emoji} *System Alert: {alert_type.capitalize()}*\n\n"
        f"{details}\n\n"
        f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    return send_telegram_message(
        message, 
        chat_id, 
        bot_token, 
        disable_notification=disable_notification
    )

def send_new_token_alert(
    token_data: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    ai_evaluation: Dict[str, Any],
    chat_id: Union[str, int],
    bot_token: str
) -> bool:
    """
    Send an alert about a newly discovered interesting token.
    
    Args:
        token_data: Token information
        risk_assessment: Risk assessment data
        ai_evaluation: AI evaluation data
        chat_id: The target Telegram chat ID
        bot_token: The Telegram Bot API token
        
    Returns:
        bool: True if the message was sent successfully
    """
    token_name = token_data.get("name", "Unknown")
    token_symbol = token_data.get("symbol", "Unknown")
    token_address = token_data.get("address", "Unknown")
    
    # Extract key metrics
    liquidity = token_data.get("liquidity", 0)
    volume = token_data.get("v24hUSD", 0)
    price = token_data.get("priceUSD", 0)
    
    # Extract AI evaluation
    ai_confidence = ai_evaluation.get("ai_confidence", 0)
    risk_score = ai_evaluation.get("risk_score", 0)
    recommendation = ai_evaluation.get("recommendation", "HOLD")
    
    # Format recommendation emoji
    rec_emoji = {
        "BUY": "🟢",
        "HOLD": "🟡",
        "AVOID": "🔴"
    }.get(recommendation, "🟡")
    
    message = (
        f"🔎 *New Token Detected*\n\n"
        f"*Token:* {token_name} ({token_symbol})\n"
        f"*Price:* ${price:.8f}\n"
        f"*Liquidity:* ${liquidity:,.0f}\n"
        f"*24h Volume:* ${volume:,.0f}\n\n"
        
        f"*AI Evaluation:*\n"
        f"Confidence: {ai_confidence:.1f}/10\n"
        f"Risk Score: {risk_score:.1f}/10\n"
        f"Recommendation: {rec_emoji} {recommendation}\n\n"
        
        f"*Risk Assessment:*\n"
        f"Risk Level: {risk_assessment.get('risk_level', 'unknown')}\n"
        f"Passed Filters: {'Yes' if risk_assessment.get('passes_filters', False) else 'No'}\n\n"
        
        f"*Address:* `{token_address}`"
    )
    
    return send_telegram_message(message, chat_id, bot_token)

if __name__ == "__main__":
    # For testing purposes, retrieve values from environment variables or provide defaults
    bot_token = os.getenv("TELEGRAM_BOT_API_KEY", "YOUR_TELEGRAM_BOT_API_KEY")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")
    
    # Test regular message
    test_message = "🧪 Test message from the Solana AI Trading Bot."
    
    if send_telegram_message(test_message, chat_id, bot_token):
        print("Telegram message sent successfully.")
    else:
        print("Failed to send Telegram message.")
    
    # Process any queued messages
    process_message_queue()
    
    # Test trade alert
    sample_token = {
        "name": "Sample Token",
        "symbol": "SMPL",
        "address": "SampleTokenAddress123456789",
        "priceUSD": 0.00012345
    }
    
    sample_reasons = [
        "Strong AI confidence score: 8.5/10",
        "Positive social sentiment",
        "Low risk assessment"
    ]
    
    if send_trade_alert(sample_token, "BUY", 0.5, 0.00012345, sample_reasons, chat_id, bot_token):
        print("Trade alert sent successfully.")
    else:
        print("Failed to send trade alert.")