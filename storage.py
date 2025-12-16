"""
Database Manager
Handles data storage and retrieval using SQLite
"""

import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import os

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path='data/trading_data.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
    def initialize(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tick data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                trade_id INTEGER
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_time 
            ON ticks(symbol, timestamp DESC)
        ''')
        
        # OHLC data table (for resampled data)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ohlc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(symbol, timeframe, timestamp)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def insert_tick(self, tick: Dict):
        """Insert a single tick into the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ticks (timestamp, symbol, price, quantity, trade_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                tick['timestamp'],
                tick['symbol'],
                tick['price'],
                tick['quantity'],
                tick.get('trade_id')
            ))
            
            conn.commit()
            conn.close()
            
            # Also update OHLC in background
            self.update_ohlc(tick['symbol'], tick['timestamp'])
            
        except Exception as e:
            logger.error(f"Error inserting tick: {e}")
    
    def update_ohlc(self, symbol: str, timestamp: datetime):
        """Update OHLC data for different timeframes"""
        timeframes = {
            '1s': 1,
            '1m': 60,
            '5m': 300
        }
        
        for tf_name, seconds in timeframes.items():
            try:
                self._resample_to_ohlc(symbol, tf_name, seconds, timestamp)
            except Exception as e:
                logger.error(f"Error updating OHLC for {tf_name}: {e}")
    
    def _resample_to_ohlc(self, symbol: str, timeframe: str, seconds: int, current_time: datetime):
        """Resample tick data to OHLC"""
        conn = sqlite3.connect(self.db_path)
        
        # Get the current timeframe bucket
        bucket_start = current_time.replace(second=0, microsecond=0)
        if timeframe == '1s':
            bucket_start = current_time.replace(microsecond=0)
        elif timeframe == '1m':
            pass  # Already at minute level
        elif timeframe == '5m':
            bucket_start = bucket_start.replace(minute=(bucket_start.minute // 5) * 5)
        
        bucket_end = bucket_start + timedelta(seconds=seconds)
        
        # Query ticks in this bucket
        query = '''
            SELECT price, quantity
            FROM ticks
            WHERE symbol = ? AND timestamp >= ? AND timestamp < ?
            ORDER BY timestamp
        '''
        
        df = pd.read_sql_query(query, conn, params=(symbol, bucket_start, bucket_end))
        
        if len(df) > 0:
            ohlc_data = {
                'timestamp': bucket_start,
                'symbol': symbol,
                'timeframe': timeframe,
                'open': df['price'].iloc[0],
                'high': df['price'].max(),
                'low': df['price'].min(),
                'close': df['price'].iloc[-1],
                'volume': df['quantity'].sum()
            }
            
            # Insert or replace OHLC
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO ohlc (timestamp, symbol, timeframe, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ohlc_data['timestamp'],
                ohlc_data['symbol'],
                ohlc_data['timeframe'],
                ohlc_data['open'],
                ohlc_data['high'],
                ohlc_data['low'],
                ohlc_data['close'],
                ohlc_data['volume']
            ))
            conn.commit()
        
        conn.close()
    
    def get_recent_ticks(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent tick data"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT timestamp, symbol, price, quantity
            FROM ticks
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        '''
        df = pd.read_sql_query(query, conn, params=(symbol, limit))
        conn.close()
        
        # Convert timestamp to string for JSON serialization
        df['timestamp'] = df['timestamp'].astype(str)
        return df.to_dict('records')
    
    def get_ohlc_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict]:
        """Get OHLC data"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT timestamp, open, high, low, close, volume
            FROM ohlc
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        '''
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
        conn.close()
        
        # Convert timestamp to string for JSON serialization
        df['timestamp'] = df['timestamp'].astype(str)
        return df.to_dict('records')
    
    def get_dataframe(self, symbol: str, timeframe: str = '1m', limit: int = 1000) -> pd.DataFrame:
        """Get data as pandas DataFrame for analytics"""
        conn = sqlite3.connect(self.db_path)
        
        if timeframe == 'tick':
            query = '''
                SELECT timestamp, price as close, quantity as volume
                FROM ticks
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            '''
            df = pd.read_sql_query(query, conn, params=(symbol, limit))
        else:
            query = '''
                SELECT timestamp, open, high, low, close, volume
                FROM ohlc
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            '''
            df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
        
        conn.close()
        
        if len(df) > 0:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def get_total_tick_count(self) -> int:
        """Get total number of ticks stored"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM ticks')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def import_ohlc_csv(self, file):
        """Import OHLC data from CSV file"""
        df = pd.read_csv(file)
        
        # Expected columns: timestamp, symbol, open, high, low, close, volume
        required_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"CSV must contain columns: {required_cols}")
        
        df['timeframe'] = '1m'  # Default to 1m
        
        conn = sqlite3.connect(self.db_path)
        df.to_sql('ohlc', conn, if_exists='append', index=False)
        conn.close()
        
        logger.info(f"Imported {len(df)} OHLC records from CSV")