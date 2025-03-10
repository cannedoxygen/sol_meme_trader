import sqlite3
import os
import logging
import json
import datetime
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple, Union, Generator

# Set the database file path from the environment variable or default to 'memecoin_trades.db'
DB_FILE = os.getenv("DB_FILE", "memecoin_trades.db")
BACKUP_DIR = os.getenv("DB_BACKUP_DIR", "db_backups")

# Configure logging for production
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class DatabaseError(Exception):
    """Base exception for database-related errors"""
    pass

@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Establish a connection to the SQLite database using a context manager.
    Returns a connection object with row_factory set for dict-like access.
    
    Usage:
        with get_connection() as conn:
            conn.execute("SELECT * FROM tokens")
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Ensure the journal mode is WAL for better performance and concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        
        yield conn
    except sqlite3.Error as e:
        logging.error(f"Error connecting to SQLite database: {e}")
        raise DatabaseError(f"Database connection error: {e}")
    finally:
        if conn:
            conn.close()

def init_db() -> None:
    """
    Initialize the database schema with tables for tokens, trades, AI analysis logs,
    and performance tracking.
    """
    with get_connection() as conn:
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tokens (
                    token_address TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    symbol TEXT,
                    listing_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS trades (
                    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT,
                    direction TEXT CHECK(direction IN ('BUY', 'SELL')),
                    amount_sold REAL,
                    amount_received REAL,
                    entry_price REAL,
                    exit_price REAL,
                    transaction_signature TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (token_address) REFERENCES tokens(token_address)
                );

                CREATE TABLE IF NOT EXISTS ai_analysis (
                    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT,
                    ai_confidence REAL,
                    risk_score REAL,
                    recommendation TEXT,
                    full_analysis TEXT,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (token_address) REFERENCES tokens(token_address)
                );
                
                CREATE TABLE IF NOT EXISTS performance (
                    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT,
                    entry_time TIMESTAMP,
                    exit_time TIMESTAMP,
                    entry_price REAL,
                    exit_price REAL,
                    amount_in REAL,
                    amount_out REAL,
                    profit_loss REAL,
                    profit_loss_percent REAL,
                    holding_period_hours REAL,
                    trade_status TEXT CHECK(trade_status IN ('OPEN', 'CLOSED')),
                    FOREIGN KEY (token_address) REFERENCES tokens(token_address)
                );
                
                CREATE TABLE IF NOT EXISTS bot_statistics (
                    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE,
                    tokens_analyzed INTEGER DEFAULT 0,
                    trades_executed INTEGER DEFAULT 0,
                    successful_trades INTEGER DEFAULT 0,
                    failed_trades INTEGER DEFAULT 0,
                    total_profit_loss REAL DEFAULT 0,
                    runtime_hours REAL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indexes for better query performance
            conn.executescript("""
                CREATE INDEX IF NOT EXISTS idx_trades_token ON trades(token_address);
                CREATE INDEX IF NOT EXISTS idx_trades_direction ON trades(direction);
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_token ON ai_analysis(token_address);
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_recommendation ON ai_analysis(recommendation);
                CREATE INDEX IF NOT EXISTS idx_performance_token ON performance(token_address);
                CREATE INDEX IF NOT EXISTS idx_performance_status ON performance(trade_status);
            """)
            
            logging.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logging.error(f"Error initializing database: {e}")
            raise DatabaseError(f"Database initialization error: {e}")

def backup_database() -> str:
    """
    Create a timestamped backup of the database.
    
    Returns:
        str: Path to the backup file
    """
    try:
        # Create backup directory if it doesn't exist
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # Generate timestamped backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
        
        # Create the backup
        with get_connection() as conn:
            backup_conn = sqlite3.connect(backup_file)
            conn.backup(backup_conn)
            backup_conn.close()
        
        logging.info(f"Database backup created at {backup_file}")
        return backup_file
    except Exception as e:
        logging.error(f"Error creating database backup: {e}")
        raise DatabaseError(f"Backup creation error: {e}")

def insert_token(token_address: str, name: str, symbol: str = None, listing_time: str = None, 
                metadata: Dict[str, Any] = None) -> bool:
    """
    Insert a token into the tokens table if it does not already exist.
    
    Args:
        token_address: The token's blockchain address
        name: Token name
        symbol: Token symbol (optional)
        listing_time: Timestamp of token listing (optional)
        metadata: Additional token metadata as a dictionary (optional)
    
    Returns:
        bool: True if insert was successful, False if token already exists
    """
    with get_connection() as conn:
        try:
            # Check if token already exists
            cursor = conn.execute("SELECT token_address FROM tokens WHERE token_address = ?", (token_address,))
            if cursor.fetchone():
                # Token exists, update metadata if provided
                if metadata:
                    conn.execute(
                        "UPDATE tokens SET metadata = ? WHERE token_address = ?", 
                        (json.dumps(metadata), token_address)
                    )
                    conn.commit()
                    logging.info(f"Updated metadata for existing token {token_address}")
                return False
            
            # Insert new token
            conn.execute(
                "INSERT INTO tokens (token_address, name, symbol, listing_time, metadata) VALUES (?, ?, ?, ?, ?)",
                (token_address, name, symbol, listing_time, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
            logging.info(f"Inserted token {token_address} with name '{name}' into database.")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error inserting token: {e}")
            raise DatabaseError(f"Token insertion error: {e}")

def log_trade(token_address: str, direction: str, amount_sold: float, amount_received: float, 
             entry_price: float, exit_price: float, tx_signature: str = None) -> int:
    """
    Log a trade execution into the trades table.
    
    Args:
        token_address: The token's blockchain address
        direction: Trade direction, either 'BUY' or 'SELL'
        amount_sold: Amount of token sold
        amount_received: Amount of token received
        entry_price: Entry price in USD
        exit_price: Exit price in USD
        tx_signature: Transaction signature (optional)
    
    Returns:
        int: ID of the inserted trade record
    """
    with get_connection() as conn:
        try:
            cursor = conn.execute("""
                INSERT INTO trades (
                    token_address, direction, amount_sold, amount_received, 
                    entry_price, exit_price, transaction_signature
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (token_address, direction, amount_sold, amount_received, 
                 entry_price, exit_price, tx_signature))
            conn.commit()
            
            # Update daily statistics
            update_bot_statistics(trades_executed=1)
            
            # For sell trades, update performance data
            if direction == "SELL":
                update_trade_performance(token_address, exit_price, amount_received)
            
            logging.info(f"Trade logged for token {token_address} as {direction}. TX: {tx_signature}")
            return cursor.lastrowid
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error logging trade: {e}")
            raise DatabaseError(f"Trade logging error: {e}")

def log_ai_analysis(token_address: str, ai_confidence: float, risk_score: float, 
                   recommendation: str, full_analysis: Dict[str, Any] = None) -> int:
    """
    Log AI evaluation results for a token into the ai_analysis table.
    
    Args:
        token_address: The token's blockchain address
        ai_confidence: AI confidence score (0-10)
        risk_score: Risk assessment score (0-10)
        recommendation: Trading recommendation ('BUY', 'HOLD', 'AVOID')
        full_analysis: Complete analysis data as a dictionary (optional)
    
    Returns:
        int: ID of the inserted analysis record
    """
    with get_connection() as conn:
        try:
            cursor = conn.execute("""
                INSERT INTO ai_analysis (
                    token_address, ai_confidence, risk_score, recommendation, full_analysis
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                token_address, ai_confidence, risk_score, recommendation,
                json.dumps(full_analysis) if full_analysis else None
            ))
            conn.commit()
            
            # Update daily statistics
            update_bot_statistics(tokens_analyzed=1)
            
            logging.info(f"AI analysis logged for token {token_address}: Confidence {ai_confidence}, Risk {risk_score}, Recommendation {recommendation}.")
            return cursor.lastrowid
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error logging AI analysis: {e}")
            raise DatabaseError(f"AI analysis logging error: {e}")

def get_token_data(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve token data from the database.
    
    Args:
        token_address: The token's blockchain address
    
    Returns:
        dict: Token data or None if not found
    """
    with get_connection() as conn:
        try:
            cursor = conn.execute("""
                SELECT * FROM tokens WHERE token_address = ?
            """, (token_address,))
            row = cursor.fetchone()
            
            if row:
                token_data = dict(row)
                # Parse JSON metadata if present
                if token_data.get('metadata'):
                    token_data['metadata'] = json.loads(token_data['metadata'])
                return token_data
            return None
        except sqlite3.Error as e:
            logging.error(f"Error retrieving token data: {e}")
            raise DatabaseError(f"Token data retrieval error: {e}")

def get_trade_history(token_address: str = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get trading history for a specific token or all tokens.
    
    Args:
        token_address: The token's blockchain address (optional, for filtering)
        limit: Maximum number of records to return
    
    Returns:
        list: List of trade records
    """
    with get_connection() as conn:
        try:
            if token_address:
                cursor = conn.execute("""
                    SELECT t.*, tk.name, tk.symbol
                    FROM trades t
                    JOIN tokens tk ON t.token_address = tk.token_address
                    WHERE t.token_address = ?
                    ORDER BY t.timestamp DESC
                    LIMIT ?
                """, (token_address, limit))
            else:
                cursor = conn.execute("""
                    SELECT t.*, tk.name, tk.symbol
                    FROM trades t
                    JOIN tokens tk ON t.token_address = tk.token_address
                    ORDER BY t.timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error retrieving trade history: {e}")
            raise DatabaseError(f"Trade history retrieval error: {e}")

def get_ai_analysis_history(token_address: str = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get AI analysis history for a specific token or all tokens.
    
    Args:
        token_address: The token's blockchain address (optional, for filtering)
        limit: Maximum number of records to return
    
    Returns:
        list: List of AI analysis records
    """
    with get_connection() as conn:
        try:
            if token_address:
                cursor = conn.execute("""
                    SELECT a.*, t.name, t.symbol
                    FROM ai_analysis a
                    JOIN tokens t ON a.token_address = t.token_address
                    WHERE a.token_address = ?
                    ORDER BY a.analyzed_at DESC
                    LIMIT ?
                """, (token_address, limit))
            else:
                cursor = conn.execute("""
                    SELECT a.*, t.name, t.symbol
                    FROM ai_analysis a
                    JOIN tokens t ON a.token_address = t.token_address
                    ORDER BY a.analyzed_at DESC
                    LIMIT ?
                """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # Parse JSON full_analysis if present
                if result.get('full_analysis'):
                    result['full_analysis'] = json.loads(result['full_analysis'])
                results.append(result)
            
            return results
        except sqlite3.Error as e:
            logging.error(f"Error retrieving AI analysis history: {e}")
            raise DatabaseError(f"AI analysis history retrieval error: {e}")

def update_trade_performance(token_address: str, exit_price: float, amount_received: float) -> None:
    """
    Update trade performance for a token after a sell.
    
    Args:
        token_address: The token's blockchain address
        exit_price: Exit price in USD
        amount_received: Amount received from sale
    """
    with get_connection() as conn:
        try:
            # Check for open positions
            cursor = conn.execute("""
                SELECT * FROM performance
                WHERE token_address = ? AND trade_status = 'OPEN'
            """, (token_address,))
            
            performance = cursor.fetchone()
            
            if performance:
                # This is a close of an existing position
                perf = dict(performance)
                entry_time = datetime.datetime.fromisoformat(perf['entry_time'])
                exit_time = datetime.datetime.now()
                
                # Calculate metrics
                holding_period = (exit_time - entry_time).total_seconds() / 3600  # hours
                profit_loss = amount_received - perf['amount_in']
                profit_loss_percent = (profit_loss / perf['amount_in']) * 100 if perf['amount_in'] > 0 else 0
                
                # Update the performance record
                conn.execute("""
                    UPDATE performance
                    SET exit_time = ?, exit_price = ?, amount_out = ?,
                        profit_loss = ?, profit_loss_percent = ?,
                        holding_period_hours = ?, trade_status = 'CLOSED'
                    WHERE performance_id = ?
                """, (
                    exit_time.isoformat(), exit_price, amount_received,
                    profit_loss, profit_loss_percent, holding_period,
                    perf['performance_id']
                ))
                conn.commit()
                
                # Update bot statistics
                successful = profit_loss > 0
                update_bot_statistics(
                    successful_trades=1 if successful else 0,
                    failed_trades=0 if successful else 1,
                    total_profit_loss=profit_loss
                )
                
                logging.info(f"Closed position for {token_address} with P/L: {profit_loss:.2f} ({profit_loss_percent:.2f}%)")
            else:
                logging.warning(f"No open position found for {token_address} when attempting to close")
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error updating trade performance: {e}")
            raise DatabaseError(f"Performance update error: {e}")

def open_position(token_address: str, entry_price: float, amount_in: float) -> int:
    """
    Record a new open position for a token.
    
    Args:
        token_address: The token's blockchain address
        entry_price: Entry price in USD
        amount_in: Amount invested
    
    Returns:
        int: ID of the inserted performance record
    """
    with get_connection() as conn:
        try:
            entry_time = datetime.datetime.now()
            
            cursor = conn.execute("""
                INSERT INTO performance (
                    token_address, entry_time, entry_price, amount_in, trade_status
                )
                VALUES (?, ?, ?, ?, 'OPEN')
            """, (token_address, entry_time.isoformat(), entry_price, amount_in))
            conn.commit()
            
            logging.info(f"Opened position for {token_address} at ${entry_price} with {amount_in} invested")
            return cursor.lastrowid
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error opening position: {e}")
            raise DatabaseError(f"Position opening error: {e}")

def get_performance_stats(days: int = 30) -> Dict[str, Any]:
    """
    Get bot performance statistics for a specified time period.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        dict: Performance statistics
    """
    with get_connection() as conn:
        try:
            # Calculate date cutoff
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
            
            # Get completed trades
            cursor = conn.execute("""
                SELECT COUNT(*) as total_trades,
                       SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                       SUM(CASE WHEN profit_loss <= 0 THEN 1 ELSE 0 END) as losing_trades,
                       SUM(profit_loss) as total_profit_loss,
                       AVG(profit_loss_percent) as avg_profit_loss_percent,
                       AVG(holding_period_hours) as avg_holding_period
                FROM performance
                WHERE exit_time > ? AND trade_status = 'CLOSED'
            """, (cutoff_date,))
            
            trade_stats = dict(cursor.fetchone())
            
            # Get most profitable token
            cursor = conn.execute("""
                SELECT p.token_address, t.name, t.symbol, 
                       SUM(p.profit_loss) as total_profit,
                       COUNT(*) as trade_count
                FROM performance p
                JOIN tokens t ON p.token_address = t.token_address
                WHERE p.exit_time > ? AND p.trade_status = 'CLOSED'
                GROUP BY p.token_address
                ORDER BY total_profit DESC
                LIMIT 1
            """, (cutoff_date,))
            
            most_profitable = cursor.fetchone()
            if most_profitable:
                most_profitable = dict(most_profitable)
            
            # Get current open positions
            cursor = conn.execute("""
                SELECT COUNT(*) as open_positions,
                       SUM(amount_in) as total_invested
                FROM performance
                WHERE trade_status = 'OPEN'
            """)
            
            position_stats = dict(cursor.fetchone())
            
            # Combine all stats
            win_rate = (trade_stats['winning_trades'] / trade_stats['total_trades'] * 100 
                       if trade_stats['total_trades'] > 0 else 0)
            
            return {
                "period_days": days,
                "total_trades": trade_stats['total_trades'],
                "winning_trades": trade_stats['winning_trades'],
                "losing_trades": trade_stats['losing_trades'],
                "win_rate": win_rate,
                "total_profit_loss": trade_stats['total_profit_loss'],
                "avg_profit_percent": trade_stats['avg_profit_loss_percent'],
                "avg_holding_hours": trade_stats['avg_holding_period'],
                "most_profitable_token": most_profitable,
                "open_positions": position_stats['open_positions'],
                "total_invested": position_stats['total_invested']
            }
        except sqlite3.Error as e:
            logging.error(f"Error retrieving performance stats: {e}")
            raise DatabaseError(f"Performance stats retrieval error: {e}")

def update_bot_statistics(tokens_analyzed: int = 0, trades_executed: int = 0,
                         successful_trades: int = 0, failed_trades: int = 0,
                         total_profit_loss: float = 0, runtime_hours: float = 0) -> None:
    """
    Update daily bot statistics.
    
    Args:
        tokens_analyzed: Number of tokens analyzed to add
        trades_executed: Number of trades executed to add
        successful_trades: Number of successful trades to add
        failed_trades: Number of failed trades to add
        total_profit_loss: Profit/loss amount to add
        runtime_hours: Runtime hours to add
    """
    with get_connection() as conn:
        try:
            today = datetime.date.today().isoformat()
            
            # Check if we have an entry for today
            cursor = conn.execute("SELECT * FROM bot_statistics WHERE date = ?", (today,))
            stats = cursor.fetchone()
            
            if stats:
                # Update existing entry
                conn.execute("""
                    UPDATE bot_statistics SET
                        tokens_analyzed = tokens_analyzed + ?,
                        trades_executed = trades_executed + ?,
                        successful_trades = successful_trades + ?,
                        failed_trades = failed_trades + ?,
                        total_profit_loss = total_profit_loss + ?,
                        runtime_hours = runtime_hours + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = ?
                """, (
                    tokens_analyzed, trades_executed, successful_trades,
                    failed_trades, total_profit_loss, runtime_hours, today
                ))
            else:
                # Create new entry for today
                conn.execute("""
                    INSERT INTO bot_statistics (
                        date, tokens_analyzed, trades_executed, successful_trades,
                        failed_trades, total_profit_loss, runtime_hours
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    today, tokens_analyzed, trades_executed, successful_trades,
                    failed_trades, total_profit_loss, runtime_hours
                ))
            
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error updating bot statistics: {e}")
            # Don't raise here to prevent disrupting main functionality

def execute_query(query: str, params: Tuple = None) -> List[Dict[str, Any]]:
    """
    Execute a custom SQL query with parameters.
    Use with caution - only for internal/admin use.
    
    Args:
        query: SQL query string
        params: Query parameters as tuple
    
    Returns:
        list: Query results as list of dictionaries
    """
    with get_connection() as conn:
        try:
            cursor = conn.execute(query, params or ())
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error executing custom query: {e}")
            raise DatabaseError(f"Custom query error: {e}")

if __name__ == "__main__":
    try:
        # Initialize database
        init_db()
        print("Database initialized successfully.")
        
        # Create a backup
        backup_file = backup_database()
        print(f"Database backup created at {backup_file}")
        
        # Example: Insert a test token
        test_token = "TokenABC123"
        insert_token(
            token_address=test_token,
            name="Test Token",
            symbol="TEST",
            metadata={"description": "A test token for database operations"}
        )
        
        # Example: Log a test trade
        trade_id = log_trade(
            token_address=test_token,
            direction="BUY",
            amount_sold=1.0,
            amount_received=100.0,
            entry_price=1.0,
            exit_price=0.0,
            tx_signature="test_signature_123"
        )
        print(f"Test trade logged with ID: {trade_id}")
        
        # Example: Log AI analysis
        analysis_id = log_ai_analysis(
            token_address=test_token,
            ai_confidence=7.5,
            risk_score=3.2,
            recommendation="BUY",
            full_analysis={"detail": "This is a test analysis"}
        )
        print(f"Test AI analysis logged with ID: {analysis_id}")
        
        # Example: Open a position
        position_id = open_position(
            token_address=test_token,
            entry_price=1.0,
            amount_in=100.0
        )
        print(f"Test position opened with ID: {position_id}")
        
        # Example: Print trade history
        trades = get_trade_history(limit=5)
        print(f"Recent trades: {len(trades)}")
        
        # Example: Print performance stats
        stats = get_performance_stats(days=7)
        print(f"7-day performance stats: {json.dumps(stats, indent=2)}")
    except Exception as e:
        print(f"Database test failed: {e}")