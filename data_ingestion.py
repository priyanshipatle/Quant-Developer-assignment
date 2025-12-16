"""
Data Ingestion Service
Handles WebSocket connections to Binance and streams tick data
"""

import asyncio
import json
import logging
from datetime import datetime
import websockets
from typing import List

logger = logging.getLogger(__name__)


class DataIngestionService:
    def __init__(self, db_manager, socketio, alert_manager):
        self.db_manager = db_manager
        self.socketio = socketio
        self.alert_manager = alert_manager
        self.active = False
        self.websocket = None
        self.current_symbols = []
        
    async def start(self, symbols: List[str]):
        """Start WebSocket connection and data ingestion"""
        self.current_symbols = symbols
        self.active = True
        
        # Convert symbols to lowercase for Binance API
        streams = [f"{symbol.lower()}@trade" for symbol in symbols]
        stream_string = "/".join(streams)
        
        ws_url = f"wss://stream.binance.com:9443/stream?streams={stream_string}"
        
        logger.info(f"Connecting to Binance WebSocket: {ws_url}")
        
        while self.active:
            try:
                async with websockets.connect(ws_url) as websocket:
                    self.websocket = websocket
                    logger.info("WebSocket connected successfully")
                    
                    async for message in websocket:
                        if not self.active:
                            break
                            
                        await self.process_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)
    
    async def process_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            if 'data' not in data:
                return
            
            trade_data = data['data']
            
            # Extract tick information
            tick = {
                'timestamp': datetime.fromtimestamp(trade_data['T'] / 1000),
                'symbol': trade_data['s'],
                'price': float(trade_data['p']),
                'quantity': float(trade_data['q']),
                'trade_id': trade_data['t']
            }
            
            # Store in database
            self.db_manager.insert_tick(tick)
            
            # Emit to connected clients via SocketIO
            self.socketio.emit('tick_update', {
                'timestamp': tick['timestamp'].isoformat(),
                'symbol': tick['symbol'],
                'price': tick['price'],
                'quantity': tick['quantity']
            })
            
            # Check alerts
            self.check_alerts(tick)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def check_alerts(self, tick):
        """Check if any alerts are triggered"""
        triggered = self.alert_manager.check_tick(tick)
        if triggered:
            for alert in triggered:
                self.socketio.emit('alert_triggered', alert)
                logger.info(f"Alert triggered: {alert}")
    
    def restart_with_symbols(self, symbols: List[str]):
        """Restart ingestion with new symbols"""
        self.active = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        
        # Wait a bit then restart
        asyncio.run(asyncio.sleep(2))
        asyncio.run(self.start(symbols))
    
    def get_status(self):
        """Get ingestion status"""
        return {
            'active': self.active,
            'symbols': self.current_symbols,
            'connected': self.websocket is not None and not self.websocket.closed
        }
    
    def stop(self):
        """Stop data ingestion"""
        self.active = False
        logger.info("Data ingestion stopped")