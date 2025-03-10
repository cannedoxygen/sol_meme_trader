# Solana Meme Coin Trading Bot

An advanced, production-ready trading bot for Solana meme coins. This system integrates AI analysis, risk management, and real-time market data to identify, evaluate, and trade meme coins with sophisticated decision-making capabilities.

## Features

### Core Infrastructure
- **Enhanced Configuration System:** Loads settings from `config.json` with fallbacks and environment variable overrides via `.env`.
- **Robust Database Management:** Records token information, trade history, AI analysis data, and performance metrics with automatic backups.
- **Advanced Error Handling:** Comprehensive error recovery, retry mechanisms, and graceful degradation.

### Data Integration
- **Birdeye API Integration:** Fetches new listings, trending tokens, and detailed token data from the Birdeye API.
- **Jupiter API Integration:** Performs price quotes and transaction simulations for accurate swap estimations.
- **Risk Assessment:** Multi-dimensional risk evaluation including liquidity checks, RugCheck integration, holder analysis, and contract verification.

### AI and Analysis
- **Advanced AI Evaluation:** Uses OpenAI's GPT models for comprehensive token analysis with short and medium-term price projections.
- **Multi-factor Decision Making:** Weighted decision system integrating AI analysis, risk assessment, and market context.
- **Sentiment Analysis:** Sophisticated social media sentiment evaluation with theme identification and engagement metrics.

### Trading Capabilities
- **Strategic Position Management:** Dynamic position sizing based on confidence and risk factors.
- **Exit Strategy Optimization:** AI-assisted exit planning with take-profit and stop-loss management.
- **Portfolio Risk Management:** Position limits, diversification rules, and exposure controls.

### Monitoring and Alerts
- **Comprehensive Telegram Notifications:** Real-time alerts for trades, discoveries, performance, and system status.
- **Performance Analytics:** Detailed metrics on trading performance across multiple timeframes.
- **Market Context Awareness:** Regular analysis of broader market conditions to adapt trading strategies.

## System Requirements

- Python 3.8 or higher
- Internet connection
- API keys for OpenAI, Birdeye, Twitter, Telegram
- Solana wallet with sufficient SOL for trading

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd solana-trading-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API keys:**
   
   Create a `.env` file with the following variables:
   ```
   # OpenAI API Key for AI analysis
   OPENAI_API_KEY=your_openai_api_key
   
   # Telegram settings for notifications
   TELEGRAM_BOT_API_KEY=your_telegram_bot_api_key
   TELEGRAM_CHAT_ID=your_chat_id
   
   # Twitter for sentiment analysis
   TWITTER_BEARER_TOKEN=your_twitter_token
   
   # Solana configuration
   SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
   SOLANA_WALLET_PRIVATE_KEY=[your_private_key_bytes]
   
   # Data providers
   BIRDEYE_API_KEY=your_birdeye_api_key
   ```

4. **Configure trading settings:**
   
   Edit `config.json` to set your trading parameters, risk limits, and other configuration options.

5. **Initialize the database:**
   ```bash
   python db_manager.py
   ```

6. **Start the bot:**
   ```bash
   python main.py
   ```

## Configuration Options

The bot can be configured through the `config.json` file with the following sections:

### API Keys
Configure external service connections (most can be overridden via `.env`).

### Trading Settings
- `liquidityThreshold`: Minimum liquidity required (USD)
- `maxSlippageBps`: Maximum acceptable slippage in basis points
- `tradeSize`: Default position size in SOL
- `maxDailyTrades`: Daily trade limit
- `enableAutoTrading`: Master toggle for auto-trading

### Risk Settings
- `maxPortfolioRisk`: Maximum portfolio exposure percentage
- `blacklistedCoins`: List of tokens to avoid
- `requireRugCheck`: Whether RugCheck validation is mandatory
- `maxSupplyConcentration`: Maximum acceptable top holder concentration

### Network Settings
Configure RPC endpoints, connection parameters, and transaction settings.

## Monitoring

The bot provides several ways to monitor its operation:

- **Telegram notifications** for real-time updates on trades and important events
- **Database queries** for historical performance analysis
- **Logging** for detailed operation tracking and debugging

## Safety Features

- Auto-trading disabled by default (must be explicitly enabled)
- Balance verification before trades
- Slippage protection
- Comprehensive pre-trade risk checks
- Emergency stop-loss capability

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


## Disclaimer

Trading cryptocurrencies involves significant risk. This software is provided for educational and informational purposes only. Use at your own risk.
