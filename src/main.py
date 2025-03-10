import logging
import time
import signal
import sys
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

# Import project modules
from config import load_config, is_trading_enabled, create_default_config, BotConfig
from db_manager import (init_db, insert_token, log_trade, log_ai_analysis,
                       get_performance_stats, update_bot_statistics, backup_database,
                       open_position, get_token_data, get_connection)
from dex_api import poll_solana_tokens, get_token_price_history, cleanup_cache as clean_dex_cache
from sentiment import clean_sentiment_cache
from risk_manager import apply_risk_filters, get_token_risk, clean_risk_cache
from ai_engine import evaluate_token, analyze_token_fundamentals, get_market_analysis, clean_evaluation_cache
from sentiment import analyze_tweets_for_token, get_sentiment_score
from strategy import decide_trade, get_exit_strategy, TradeAction
from trade_executor import execute_buy, execute_sell
from wallet import get_solana_client, load_wallet, get_all_balances
from telegram_alerts import send_telegram_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Global variables
running = True
known_token_addresses = set()
token_listing_times = {}  # Track when tokens were listed
market_context = {}
last_market_analysis = datetime.now() - timedelta(days=1)  # Force initial analysis
last_cleanup = datetime.now()
last_database_backup = datetime.now() - timedelta(days=1)  # Force initial backup
last_performance_report = datetime.now() - timedelta(hours=23)  # Force initial report soon
last_status_report = datetime.now() - timedelta(minutes=25)  # Start almost ready to send a report
runtime_start = datetime.now()

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    global running
    logging.info("Termination signal received. Shutting down gracefully...")
    running = False

def initialize():
    """Initialize the bot"""
    logging.info("Solana AI Trading Bot - Initializing...")
    
    # Load configuration or create default if it doesn't exist
    try:
        config = load_config()
    except Exception as e:
        logging.warning(f"Failed to load config: {e}. Creating default config...")
        config = create_default_config()
    
    # Initialize database
    try:
        init_db()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        return None
    
    # Connect to Solana network
    try:
        solana_client = get_solana_client()
        logging.info("Connected to Solana network")
    except Exception as e:
        logging.error(f"Failed to connect to Solana network: {e}")
        return None
    
    # Load wallet
    try:
        wallet = load_wallet()
        logging.info(f"Wallet loaded successfully: {wallet.pubkey()}")
    except Exception as e:
        logging.error(f"Failed to load wallet: {e}")
        return None
    
    # Check wallet balances
    sol_balance = 0  # Default value to prevent startup notification error
    try:
        balances = get_all_balances(solana_client, wallet)
        sol_balance = balances.get("So11111111111111111111111111111111111111112", 0)
        logging.info(f"Wallet SOL balance: {sol_balance} SOL")
        
        if sol_balance < 0.05:
            logging.warning("Low SOL balance. Trading may fail due to insufficient funds.")
    except Exception as e:
        logging.error(f"Failed to check wallet balances: {e}")
    
    # Send startup notification
    try:
        telegram_bot_token = config.apiKeys.telegramBot
        telegram_chat_id = config.socialSettings.telegramChatId
        
        if telegram_bot_token and telegram_chat_id:
            send_telegram_message(
                f"🚀 Solana AI Trading Bot started\n"
                f"💰 Wallet balance: {sol_balance:.4f} SOL\n"
                f"⚙️ Auto-trading: {'Enabled' if is_trading_enabled(config) else 'Disabled'}\n"
                f"🔍 Monitoring for new tokens...",
                telegram_chat_id,
                telegram_bot_token
            )
    except Exception as e:
        logging.error(f"Failed to send startup notification: {e}")
    
    return config, solana_client, wallet

def update_market_context(config: BotConfig) -> Dict[str, Any]:
    """Update market context periodically"""
    global market_context, last_market_analysis
    
    # Check if we need to update market analysis (every 8 hours)
    current_time = datetime.now()
    if (current_time - last_market_analysis).total_seconds() > 28800:  # 8 hours
        logging.info("Updating market context analysis...")
        
        # Fetch real data from a price API (example with Birdeye)
        try:
            # Get SOL price - you can use your dex_api module or add a direct call
            sol_price = 120  # Default price if can't fetch
            tvl = 2_000_000_000  # Default TVL
            vol_24h = 500_000_000  # Default volume
            
            # Example of getting SOL price from Birdeye
            if config.apiKeys.birdeye:
                sol_url = "https://public-api.birdeye.so/defi/v2/price?address=So11111111111111111111111111111111111111112"
                headers = {
                    "x-api-key": config.apiKeys.birdeye,
                    "x-chain": "solana"
                }
                
                price_response = requests.get(sol_url, headers=headers, timeout=10)
                if price_response.status_code == 200:
                    price_data = price_response.json()
                    if "data" in price_data and "value" in price_data["data"]:
                        sol_price = price_data["data"]["value"]
            
            # Get count of tokens in known_token_addresses collected in last 24h
            new_token_count = len([addr for addr in known_token_addresses 
                                 if addr in token_listing_times and 
                                 (current_time - token_listing_times[addr]).total_seconds() < 86400])
            
            market_data = {
                "timestamp": current_time.isoformat(),
                "sol_price": sol_price,
                "global_metrics": {
                    "total_solana_defi_tvl": tvl,
                    "sol_24h_volume": vol_24h,
                    "new_token_count_24h": new_token_count or 10
                }
            }
        except Exception as e:
            logging.error(f"Error fetching market data: {e}")
            # Fallback to better placeholders
            market_data = {
                "timestamp": current_time.isoformat(),
                "sol_price": 120,  # Approximate SOL price rather than 0
                "global_metrics": {
                    "total_solana_defi_tvl": 2_000_000_000,  # ~$2B TVL
                    "sol_24h_volume": 500_000_000,  # ~$500M volume
                    "new_token_count_24h": len(known_token_addresses)  # At least use our known count
                }
            }
        
        # Perform market analysis with AI
        try:
            analysis = get_market_analysis(market_data)
            market_context = analysis
            last_market_analysis = current_time
            
            # Log market context
            logging.info(f"Market analysis updated: {analysis.get('market_sentiment', 'unknown')} sentiment")
            
            # Send market update notification if enabled
            telegram_bot_token = config.apiKeys.telegramBot
            telegram_chat_id = config.socialSettings.telegramChatId
            
            if telegram_bot_token and telegram_chat_id:
                summary = analysis.get("market_summary", "")
                key_trends = ", ".join(analysis.get("key_trends", [])[:3])
                
                message = (
                    f"🌍 Market Update\n"
                    f"Sentiment: {analysis.get('market_sentiment', 'unknown')}\n"
                    f"Risk Level: {analysis.get('risk_level', 'unknown')}\n"
                    f"Key Trends: {key_trends}\n\n"
                    f"{summary}"
                )
                
                send_telegram_message(message, telegram_chat_id, telegram_bot_token)
        except Exception as e:
            logging.error(f"Failed to update market context: {e}")
    
    return market_context

def send_status_report(config: BotConfig) -> None:
    """Send a periodic status report to Telegram"""
    try:
        telegram_bot_token = config.apiKeys.telegramBot
        telegram_chat_id = config.socialSettings.telegramChatId
        
        if not telegram_bot_token or not telegram_chat_id:
            return
        
        # Get runtime duration
        uptime = datetime.now() - runtime_start
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Get database stats
        tokens_analyzed = len(known_token_addresses)
        
        # Get SOL price (if available)
        sol_price = "Unknown"
        try:
            # If you have a birdeye API key, fetch the current SOL price
            if config.apiKeys.birdeye:
                headers = {
                    "x-api-key": config.apiKeys.birdeye,
                    "x-chain": "solana"
                }
                sol_url = "https://public-api.birdeye.so/defi/v2/price?address=So11111111111111111111111111111111111111112"
                price_response = requests.get(sol_url, headers=headers, timeout=10)
                if price_response.status_code == 200:
                    price_data = price_response.json()
                    if "data" in price_data and "value" in price_data["data"]:
                        sol_price = f"${price_data['data']['value']:.2f}"
        except Exception as e:
            logging.error(f"Failed to fetch SOL price: {e}")
        
        # Get tokens that received BUY recommendations
        buy_tokens = []
        try:
            # Query up to 5 most recent AI analyses with BUY recommendations
            with get_connection() as conn:
                cursor = conn.execute("""
                    SELECT a.token_address, t.name, t.symbol, a.ai_confidence, a.risk_score
                    FROM ai_analysis a
                    JOIN tokens t ON a.token_address = t.token_address
                    WHERE a.recommendation = 'BUY'
                    ORDER BY a.analyzed_at DESC
                    LIMIT 5
                """)
                buy_tokens = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Failed to fetch recent buy recommendations: {e}")
        
        # Format the buy tokens section
        buy_tokens_text = ""
        if buy_tokens:
            buy_tokens_text = "\n\n*Recent Buy Recommendations:*\n"
            for i, token in enumerate(buy_tokens):
                buy_tokens_text += f"{i+1}. {token.get('name')} ({token.get('symbol', '?')})\n"
                buy_tokens_text += f"   Confidence: {token.get('ai_confidence', 0):.1f}/10, "
                buy_tokens_text += f"Risk: {token.get('risk_score', 0):.1f}/10\n"
        
        # Get current market data
        market_sentiment = market_context.get('market_sentiment', 'Unknown')
        risk_level = market_context.get('risk_level', 'Unknown')
        
        # Format the message
        message = (
            f"🤖 *Status Update*\n\n"
            f"*Uptime:* {int(hours)}h {int(minutes)}m\n"
            f"*Tokens Analyzed:* {tokens_analyzed}\n"
            f"*SOL Price:* {sol_price}\n"
            f"*Trading Mode:* {'Enabled' if is_trading_enabled(config) else 'Disabled'}\n\n"
            f"*Market Sentiment:* {market_sentiment}\n"
            f"*Risk Level:* {risk_level}\n"
            f"{buy_tokens_text}\n"
            f"*Status:* Monitoring for new tokens..."
        )
        
        send_telegram_message(message, telegram_chat_id, telegram_bot_token)
        logging.info("Sent periodic status report to Telegram")
    except Exception as e:
        logging.error(f"Failed to send status report: {e}")

def examine_positions(
    config: BotConfig,
    solana_client,
    wallet,
    market_context: Dict[str, Any]
) -> None:
    """Check existing positions for exit opportunities"""
    # This function would query the database for open positions
    # and evaluate exit strategies for each
    # For simplicity, we're using a placeholder implementation
    logging.info("Checking exit strategies for open positions...")
    
    # In a real implementation, you would:
    # 1. Query the database for all open positions
    # 2. Get current token data for each position
    # 3. Apply exit strategy logic
    # 4. Execute sells as needed
    
    # Placeholder example:
    """
    open_positions = get_open_positions()
    
    for position in open_positions:
        token_address = position.get("token_address")
        token_data = get_token_data(token_address)
        
        if not token_data:
            logging.warning(f"Could not retrieve data for token {token_address}")
            continue
        
        # Get AI evaluation and risk assessment
        ai_evaluation = evaluate_token(token_data)
        risk_assessment = get_token_risk(token_address)
        
        # Determine exit strategy
        exit_decision = get_exit_strategy(
            token_data, 
            position, 
            ai_evaluation, 
            risk_assessment,
            market_context
        )
        
        if exit_decision.action in [TradeAction.SELL, TradeAction.TAKE_PROFIT, TradeAction.CUT_LOSS]:
            # Execute sell
            amount_to_sell = exit_decision.position_size
            tx_sig = execute_sell(
                solana_client, 
                wallet,
                token_in=token_address,
                token_out="So11111111111111111111111111111111111111112",  # SOL
                amount_in=amount_to_sell
            )
            
            if tx_sig:
                log_trade(
                    token_address=token_address,
                    direction=exit_decision.action.value,
                    amount_sold=amount_to_sell,
                    amount_received=0,  # Will be updated when tx confirms
                    entry_price=position.get("entry_price", 0),
                    exit_price=token_data.get("priceUSD", 0),
                    tx_signature=tx_sig
                )
                
                # Send notification
                notify_trade(
                    config,
                    token_data,
                    exit_decision.action.value,
                    amount_to_sell,
                    token_data.get("priceUSD", 0),
                    exit_decision.reasons
                )
    """
    pass

def process_new_token(
    token: Dict[str, Any],
    config: BotConfig,
    solana_client,
    wallet,
    market_context: Dict[str, Any]
) -> None:
    """Process a single token"""
    token_address = token.get("address")
    token_name = token.get("name", "Unknown")
    
    if not token_address or not isinstance(token_address, str):
        logging.warning(f"Invalid token address in token: {token}")
        return
    
    # Insert token into database if new
    if token_address not in known_token_addresses:
        try:
            metadata = {
                "symbol": token.get("symbol", ""),
                "listing_time": token.get("listingTime", ""),
                "description": token.get("description", ""),
                "website": token.get("website", ""),
                "twitter": token.get("twitter", ""),
                "discord": token.get("discord", "")
            }
            
            insert_token(
                token_address=token_address,
                name=token_name,
                symbol=token.get("symbol", ""),
                listing_time=token.get("listingTime", ""),
                metadata=metadata
            )
            known_token_addresses.add(token_address)
            
            # Track listing time for market context
            if listing_time := token.get("listingTime"):
                try:
                    listing_datetime = datetime.fromisoformat(listing_time.replace("Z", "+00:00"))
                    token_listing_times[token_address] = listing_datetime
                except (ValueError, TypeError):
                    token_listing_times[token_address] = datetime.now()
        except Exception as e:
            logging.error(f"Failed to insert token {token_address}: {e}")
            return
    
    # Get token price history if available
    try:
        price_history = get_token_price_history(token_address)
        if price_history:
            token["price_history"] = price_history
    except Exception as e:
        logging.warning(f"Failed to get price history for {token_address}: {e}")
    
    # Apply risk filters
    try:
        passes, risk_reason, risk_assessment = apply_risk_filters(token, config)
        if not passes:
            logging.info(f"Token {token_address} ({token_name}) skipped due to risk: {risk_reason}")
            return
    except Exception as e:
        logging.error(f"Risk assessment failed for {token_address}: {e}")
        return
    
    # Get AI evaluation
    try:
        ai_evaluation = evaluate_token(token, market_context)
        
        # Log AI analysis to database
        log_ai_analysis(
            token_address=token_address,
            ai_confidence=ai_evaluation.ai_confidence,
            risk_score=ai_evaluation.risk_score,
            recommendation=ai_evaluation.recommendation,
            full_analysis=ai_evaluation.__dict__
        )
    except Exception as e:
        logging.error(f"AI evaluation failed for {token_address}: {e}")
        return
    
    # Get sentiment analysis
    try:
        twitter_bearer = config.socialSettings.twitterBearerToken
        sentiment_result = analyze_tweets_for_token(token, twitter_bearer) if twitter_bearer else None
        sentiment_score = get_sentiment_score(token, twitter_bearer) if twitter_bearer else 0.0
    except Exception as e:
        logging.error(f"Sentiment analysis failed for {token_address}: {e}")
        sentiment_result = None
        sentiment_score = 0.0
    
    # Make trading decision
    try:
        decision = decide_trade(
            ai_evaluation.__dict__,
            risk_assessment.__dict__,
            sentiment_result.__dict__ if sentiment_result else {"sentiment_score": 0, "confidence": 0.5},
            token,
            market_context
        )
        
        logging.info(
            f"Token {token_address} ({token_name}) evaluated: "
            f"AI {ai_evaluation.ai_confidence:.1f}/10, "
            f"Risk {ai_evaluation.risk_score:.1f}/10, "
            f"Sentiment {sentiment_score:.2f} => "
            f"Decision: {decision.action.value}"
        )
    except Exception as e:
        logging.error(f"Decision making failed for {token_address}: {e}")
        return
    
    # Execute trade if enabled
    if is_trading_enabled(config) and decision.action == TradeAction.BUY:
        try:
            # Calculate amount_in in lamports (SOL)
            amount_in_sol = decision.position_size
            amount_in = int(amount_in_sol * 10**9)  # Convert to lamports
            
            logging.info(f"Executing BUY for {token_name}: {amount_in_sol} SOL")
            
            tx_sig = execute_buy(
                solana_client,
                wallet,
                token_in="So11111111111111111111111111111111111111112",  # SOL
                token_out=token_address,
                amount_in=amount_in
            )
            
            if tx_sig:
                # Log trade to database
                entry_price = token.get("priceUSD", 0)
                trade_id = log_trade(
                    token_address=token_address,
                    direction="BUY",
                    amount_sold=amount_in_sol,
                    amount_received=0,  # Will be updated when tx confirms
                    entry_price=entry_price,
                    exit_price=0,
                    tx_signature=tx_sig
                )
                
                # Open position tracking
                open_position(
                    token_address=token_address,
                    entry_price=entry_price,
                    amount_in=amount_in_sol
                )
                
                # Send notification
                notify_trade(
                    config,
                    token,
                    "BUY",
                    amount_in_sol,
                    entry_price,
                    decision.reasons
                )
                
                logging.info(f"Buy executed for {token_name}: {tx_sig}")
        except Exception as e:
            logging.error(f"Trade execution failed for {token_address}: {e}")

def notify_trade(
    config: BotConfig,
    token: Dict[str, Any],
    action: str,
    amount: float,
    price: float,
    reasons: List[str]
) -> None:
    """Send trade notification"""
    try:
        telegram_bot_token = config.apiKeys.telegramBot
        telegram_chat_id = config.socialSettings.telegramChatId
        
        if not telegram_bot_token or not telegram_chat_id:
            return
        
        token_name = token.get("name", "Unknown")
        token_symbol = token.get("symbol", "Unknown")
        token_address = token.get("address", "Unknown")
        
        # Format action emoji
        action_emoji = "🟢" if action == "BUY" else "🔴"
        
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
            f"{action_emoji} {action} {token_symbol}\n\n"
            f"Token: {token_name} ({token_symbol})\n"
            f"Amount: {amount_text}\n"
            f"Price: ${price:.8f}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Reasons:\n{reasons_text}\n"
            f"Address: {token_address[:8]}...{token_address[-4:]}"
        )
        
        send_telegram_message(message, telegram_chat_id, telegram_bot_token)
    except Exception as e:
        logging.error(f"Failed to send trade notification: {e}")

def maintenance_tasks(config: BotConfig) -> None:
    """Perform routine maintenance tasks"""
    global last_cleanup, last_database_backup
    
    current_time = datetime.now()
    
    # Cleanup caches every hour
    if (current_time - last_cleanup).total_seconds() > 3600:  # 1 hour
        try:
            logging.info("Performing routine cache cleanup...")
            clean_evaluation_cache()
            clean_risk_cache()
            clean_sentiment_cache()
            clean_dex_cache()
            last_cleanup = current_time
        except Exception as e:
            logging.error(f"Cache cleanup failed: {e}")
    
    # Database backup every day
    if (current_time - last_database_backup).total_seconds() > 86400:  # 24 hours
        try:
            logging.info("Creating database backup...")
            backup_file = backup_database()
            logging.info(f"Database backup created: {backup_file}")
            last_database_backup = current_time
        except Exception as e:
            logging.error(f"Database backup failed: {e}")
    
    # Update bot statistics
    try:
        runtime_hours = (current_time - runtime_start).total_seconds() / 3600
        update_bot_statistics(runtime_hours=runtime_hours)
    except Exception as e:
        logging.error(f"Failed to update bot statistics: {e}")

def show_performance_summary(config: BotConfig) -> None:
    """Display performance summary and send report"""
    try:
        # Get performance stats for various time periods
        performance_1d = get_performance_stats(days=1) or {"total_trades": 0, "total_profit_loss": 0.0, "win_rate": 0.0}
        performance_7d = get_performance_stats(days=7) or {"total_trades": 0, "total_profit_loss": 0.0, "win_rate": 0.0}
        performance_30d = get_performance_stats(days=30) or {"total_trades": 0, "total_profit_loss": 0.0, "win_rate": 0.0}
        
        # Ensure all values have defaults to prevent None formatting errors
        for perf in [performance_1d, performance_7d, performance_30d]:
            for key in ["total_trades", "total_profit_loss", "win_rate", "open_positions", "total_invested"]:
                if key not in perf or perf[key] is None:
                    perf[key] = 0
        
        # Log performance summary
        logging.info("Performance Summary:")
        logging.info(f"24h: {performance_1d.get('total_trades', 0)} trades, "
                    f"P/L: {performance_1d.get('total_profit_loss', 0):.4f} SOL")
        logging.info(f"7d: {performance_7d.get('total_trades', 0)} trades, "
                    f"P/L: {performance_7d.get('total_profit_loss', 0):.4f} SOL")
        logging.info(f"30d: {performance_30d.get('total_trades', 0)} trades, "
                    f"P/L: {performance_30d.get('total_profit_loss', 0):.4f} SOL")
        
        # Send report via Telegram if enabled
        telegram_bot_token = config.apiKeys.telegramBot
        telegram_chat_id = config.socialSettings.telegramChatId
        
        if telegram_bot_token and telegram_chat_id:
            message = (
                f"📊 Performance Report\n\n"
                f"📅 24-Hour Performance:\n"
                f"Trades: {performance_1d.get('total_trades', 0)}\n"
                f"Profit/Loss: {performance_1d.get('total_profit_loss', 0):.4f} SOL\n"
                f"Win Rate: {performance_1d.get('win_rate', 0):.1f}%\n\n"
                
                f"📅 7-Day Performance:\n"
                f"Trades: {performance_7d.get('total_trades', 0)}\n"
                f"Profit/Loss: {performance_7d.get('total_profit_loss', 0):.4f} SOL\n"
                f"Win Rate: {performance_7d.get('win_rate', 0):.1f}%\n\n"
                
                f"📅 30-Day Performance:\n"
                f"Trades: {performance_30d.get('total_trades', 0)}\n"
                f"Profit/Loss: {performance_30d.get('total_profit_loss', 0):.4f} SOL\n"
                f"Win Rate: {performance_30d.get('win_rate', 0):.1f}%\n\n"
                
                f"💼 Current Status:\n"
                f"Open Positions: {performance_30d.get('open_positions', 0)}\n"
                f"Total Invested: {performance_30d.get('total_invested', 0):.4f} SOL\n"
            )
            
            # Add best performing token if available
            best_token = performance_30d.get('most_profitable_token')
            if best_token:
                message += (
                    f"\n🏆 Top Performer: {best_token.get('name', 'Unknown')}\n"
                    f"Symbol: {best_token.get('symbol', 'Unknown')}\n"
                    f"Profit: {best_token.get('total_profit', 0):.4f} SOL\n"
                    f"Trades: {best_token.get('trade_count', 0)}\n"
                )
            
            send_telegram_message(message, telegram_chat_id, telegram_bot_token)
    except Exception as e:
        logging.error(f"Failed to generate performance summary: {e}")

def main_loop():
    """Main bot loop"""
    global running, market_context, last_performance_report, last_status_report
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize the bot
    init_result = initialize()
    if not init_result:
        logging.error("Initialization failed. Exiting.")
        return
    
    config, solana_client, wallet = init_result
    
    # Setup token polling
    poller = poll_solana_tokens(
        num_requests=60,
        period=3600  # Poll every minute in production
    )
    
    poll_count = 0
    
    logging.info("Bot started successfully. Monitoring for new tokens...")
    
    try:
        while running:
            current_time = datetime.now()
            
            # Get new tokens from poller
            try:
                tokens = next(poller)
                poll_count += 1
                
                if tokens:
                    logging.info(f"Poll {poll_count}: Found {len(tokens)} tokens to analyze")
                    
                    # Update market context periodically
                    market_context = update_market_context(config)
                    
                    # Process each token
                    for token in tokens:
                        process_new_token(
                            token,
                            config,
                            solana_client,
                            wallet,
                            market_context
                        )
                    
                    # Check exit positions after processing new tokens
                    try:
                        examine_positions(
                            config,
                            solana_client,
                            wallet,
                            market_context
                        )
                    except Exception as e:
                        logging.error(f"Error checking exit positions: {e}")
            except Exception as e:
                logging.error(f"Error in polling cycle: {e}")
            
            # Performance report every 24 hours
            if (current_time - last_performance_report).total_seconds() > 86400:  # 24 hours
                show_performance_summary(config)
                last_performance_report = current_time
            
            # Status report every 30 minutes
            if (current_time - last_status_report).total_seconds() > 1800:  # 30 minutes
                send_status_report(config)
                last_status_report = current_time
            
            # Perform maintenance tasks
            maintenance_tasks(config)
            
            # Small delay to prevent tight looping
            time.sleep(1)
    
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}")
    finally:
        # Perform cleanup and final reporting
        logging.info("Bot shutting down...")
        
        # Final performance report
        show_performance_summary(config)
        
        # Final database backup
        try:
            backup_file = backup_database()
            logging.info(f"Final database backup created: {backup_file}")
        except Exception as e:
            logging.error(f"Final database backup failed: {e}")
        
        # Shutdown notification
        try:
            telegram_bot_token = config.apiKeys.telegramBot
            telegram_chat_id = config.socialSettings.telegramChatId
            
            if telegram_bot_token and telegram_chat_id:
                runtime = datetime.now() - runtime_start
                runtime_hours = runtime.total_seconds() / 3600
                
                send_telegram_message(
                    f"🛑 Solana AI Trading Bot shutting down\n"
                    f"⏱️ Runtime: {runtime_hours:.2f} hours\n"
                    f"⏰ Shutdown time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    telegram_chat_id,
                    telegram_bot_token
                )
        except Exception as e:
            logging.error(f"Failed to send shutdown notification: {e}")
        
        logging.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        sys.exit(1)