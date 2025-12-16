"""
Analytics Engine
Computes quantitative analytics on market data
"""

import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from sklearn.linear_model import LinearRegression, HuberRegressor
import logging
from typing import Dict
import os

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    def compute_analytics(self, symbol: str, timeframe: str = '1m', window: int = 20) -> Dict:
        """Compute analytics for a single symbol"""
        try:
            df = self.db_manager.get_dataframe(symbol, timeframe, limit=1000)
            
            if len(df) < window:
                return {
                    'error': 'Insufficient data',
                    'required': window,
                    'available': len(df)
                }
            
            # Price statistics
            current_price = df['close'].iloc[-1]
            price_change = ((current_price - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
            
            # Rolling statistics
            df['sma'] = df['close'].rolling(window=window).mean()
            df['std'] = df['close'].rolling(window=window).std()
            df['returns'] = df['close'].pct_change()
            
            # Z-score
            df['zscore'] = (df['close'] - df['sma']) / df['std']
            
            # Volatility
            volatility = df['returns'].std() * np.sqrt(252)  # Annualized
            
            # Volume analysis
            avg_volume = df['volume'].mean()
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Momentum indicators
            rsi = self._calculate_rsi(df['close'], 14)
            
            # ADF test for stationarity
            adf_result = self._adf_test(df['close'])
            
            analytics = {
                'symbol': symbol,
                'timestamp': df['timestamp'].iloc[-1].isoformat() if 'timestamp' in df.columns else None,
                'price': {
                    'current': float(current_price),
                    'change_percent': float(price_change),
                    'high': float(df['close'].max()),
                    'low': float(df['close'].min()),
                    'avg': float(df['close'].mean())
                },
                'statistics': {
                    'volatility': float(volatility),
                    'zscore': float(df['zscore'].iloc[-1]) if not pd.isna(df['zscore'].iloc[-1]) else 0,
                    'rsi': float(rsi),
                    'sharpe_approx': float(df['returns'].mean() / df['returns'].std()) if df['returns'].std() > 0 else 0
                },
                'volume': {
                    'current': float(current_volume),
                    'average': float(avg_volume),
                    'ratio': float(volume_ratio)
                },
                'stationarity': adf_result,
                'data_points': len(df)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error computing analytics for {symbol}: {e}")
            return {'error': str(e)}
    
    def compute_pair_analytics(self, symbol1: str, symbol2: str, timeframe: str = '1m', window: int = 20) -> Dict:
        """Compute pair analytics (spread, hedge ratio, correlation, etc.)"""
        try:
            df1 = self.db_manager.get_dataframe(symbol1, timeframe, limit=1000)
            df2 = self.db_manager.get_dataframe(symbol2, timeframe, limit=1000)
            
            if len(df1) < window or len(df2) < window:
                return {'error': 'Insufficient data for pair analytics'}
            
            # Merge on timestamp
            df1 = df1.rename(columns={'close': 'price1'})
            df2 = df2.rename(columns={'close': 'price2'})
            
            merged = pd.merge(df1[['timestamp', 'price1']], 
                            df2[['timestamp', 'price2']], 
                            on='timestamp', 
                            how='inner')
            
            if len(merged) < window:
                return {'error': 'Insufficient aligned data'}
            
            # OLS Regression for hedge ratio
            X = merged['price2'].values.reshape(-1, 1)
            y = merged['price1'].values
            
            model = LinearRegression()
            model.fit(X, y)
            hedge_ratio = float(model.coef_[0])
            intercept = float(model.intercept_)
            
            # Spread
            merged['spread'] = merged['price1'] - (hedge_ratio * merged['price2'])
            
            # Rolling statistics on spread
            merged['spread_mean'] = merged['spread'].rolling(window=window).mean()
            merged['spread_std'] = merged['spread'].rolling(window=window).std()
            merged['spread_zscore'] = (merged['spread'] - merged['spread_mean']) / merged['spread_std']
            
            # Correlation
            correlation = merged[['price1', 'price2']].corr().iloc[0, 1]
            rolling_corr = merged['price1'].rolling(window=window).corr(merged['price2'])
            
            # ADF test on spread
            spread_adf = self._adf_test(merged['spread'])
            
            # Huber regression for robust estimation
            huber = HuberRegressor()
            huber.fit(X, y)
            robust_hedge_ratio = float(huber.coef_[0])
            
            analytics = {
                'symbols': [symbol1, symbol2],
                'hedge_ratio': {
                    'ols': hedge_ratio,
                    'robust': robust_hedge_ratio,
                    'intercept': intercept
                },
                'spread': {
                    'current': float(merged['spread'].iloc[-1]),
                    'mean': float(merged['spread_mean'].iloc[-1]) if not pd.isna(merged['spread_mean'].iloc[-1]) else 0,
                    'std': float(merged['spread_std'].iloc[-1]) if not pd.isna(merged['spread_std'].iloc[-1]) else 0,
                    'zscore': float(merged['spread_zscore'].iloc[-1]) if not pd.isna(merged['spread_zscore'].iloc[-1]) else 0,
                    'min': float(merged['spread'].min()),
                    'max': float(merged['spread'].max())
                },
                'correlation': {
                    'pearson': float(correlation),
                    'rolling': float(rolling_corr.iloc[-1]) if not pd.isna(rolling_corr.iloc[-1]) else 0
                },
                'stationarity': spread_adf,
                'data_points': len(merged),
                'series': {
                    'timestamps': [ts.isoformat() for ts in merged['timestamp'].tail(100).tolist()],
                    'spread': merged['spread'].tail(100).tolist(),
                    'zscore': merged['spread_zscore'].tail(100).fillna(0).tolist()
                }
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error computing pair analytics: {e}")
            return {'error': str(e)}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _adf_test(self, series: pd.Series) -> Dict:
        """Perform Augmented Dickey-Fuller test"""
        try:
            result = adfuller(series.dropna())
            
            return {
                'statistic': float(result[0]),
                'pvalue': float(result[1]),
                'is_stationary': result[1] < 0.05,
                'critical_values': {k: float(v) for k, v in result[4].items()}
            }
        except Exception as e:
            logger.error(f"ADF test error: {e}")
            return {
                'statistic': 0,
                'pvalue': 1,
                'is_stationary': False,
                'error': str(e)
            }
    
    def export_to_csv(self, symbol: str, timeframe: str = '1m') -> str:
        """Export analytics data to CSV"""
        df = self.db_manager.get_dataframe(symbol, timeframe, limit=10000)
        
        # Add computed columns
        df['returns'] = df['close'].pct_change()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['std_20'] = df['close'].rolling(window=20).std()
        df['zscore'] = (df['close'] - df['sma_20']) / df['std_20']
        
        # Export
        os.makedirs('exports', exist_ok=True)
        filename = f'exports/{symbol}_{timeframe}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(filename, index=False)
        
        logger.info(f"Exported data to {filename}")
        return filename
    
    def backtest_mean_reversion(self, symbol1: str, symbol2: str, timeframe: str = '1m') -> Dict:
        """Simple mean reversion backtest: enter when z>2, exit when z<0"""
        try:
            pair_analytics = self.compute_pair_analytics(symbol1, symbol2, timeframe)
            
            if 'error' in pair_analytics:
                return pair_analytics
            
            # Get historical z-scores
            df1 = self.db_manager.get_dataframe(symbol1, timeframe, limit=1000)
            df2 = self.db_manager.get_dataframe(symbol2, timeframe, limit=1000)
            
            merged = pd.merge(
                df1[['timestamp', 'close']].rename(columns={'close': 'price1'}),
                df2[['timestamp', 'close']].rename(columns={'close': 'price2'}),
                on='timestamp',
                how='inner'
            )
            
            hedge_ratio = pair_analytics['hedge_ratio']['ols']
            merged['spread'] = merged['price1'] - (hedge_ratio * merged['price2'])
            merged['spread_mean'] = merged['spread'].rolling(window=20).mean()
            merged['spread_std'] = merged['spread'].rolling(window=20).std()
            merged['zscore'] = (merged['spread'] - merged['spread_mean']) / merged['spread_std']
            
            # Simple strategy: Long when z > 2, close when z < 0
            positions = []
            in_position = False
            entry_price = 0
            
            for i, row in merged.iterrows():
                if not in_position and row['zscore'] > 2:
                    in_position = True
                    entry_price = row['spread']
                    positions.append({'entry': entry_price, 'entry_time': row['timestamp']})
                    
                elif in_position and row['zscore'] < 0:
                    in_position = False
                    exit_price = row['spread']
                    pnl = entry_price - exit_price  # Short spread
                    positions[-1]['exit'] = exit_price
                    positions[-1]['exit_time'] = row['timestamp']
                    positions[-1]['pnl'] = pnl
            
            # Calculate stats
            completed_trades = [p for p in positions if 'pnl' in p]
            
            if completed_trades:
                total_pnl = sum(p['pnl'] for p in completed_trades)
                win_rate = len([p for p in completed_trades if p['pnl'] > 0]) / len(completed_trades)
                avg_pnl = total_pnl / len(completed_trades)
            else:
                total_pnl = 0
                win_rate = 0
                avg_pnl = 0
            
            return {
                'total_trades': len(completed_trades),
                'total_pnl': float(total_pnl),
                'win_rate': float(win_rate),
                'avg_pnl_per_trade': float(avg_pnl),
                'trades': completed_trades[:10]  # Return first 10 trades
            }
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {'error': str(e)}