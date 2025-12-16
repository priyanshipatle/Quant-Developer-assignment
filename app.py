"""
Real-Time Trading Analytics Platform
Main application entry point
"""

import asyncio
import threading
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
from datetime import datetime
import json

from backend.data_ingestion import DataIngestionService
from backend.analytics_engine import AnalyticsEngine
from backend.storage import DatabaseManager
from backend.alert_manager import AlertManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'quant_dev_secret_key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize components
db_manager = DatabaseManager()
alert_manager = AlertManager()
analytics_engine = AnalyticsEngine(db_manager)
data_ingestion = DataIngestionService(db_manager, socketio, alert_manager)

# Global state
active_symbols = ['BTCUSDT', 'ETHUSDT']


@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')


@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    """Get list of active symbols"""
    return jsonify({'symbols': active_symbols})


@app.route('/api/symbols', methods=['POST'])
def update_symbols():
    """Update active symbols for streaming"""
    global active_symbols
    data = request.json
    new_symbols = data.get('symbols', [])
    
    if new_symbols:
        active_symbols = new_symbols
        # Restart ingestion with new symbols
        threading.Thread(target=data_ingestion.restart_with_symbols, args=(new_symbols,), daemon=True).start()
        logger.info(f"Updated symbols to: {new_symbols}")
        return jsonify({'status': 'success', 'symbols': active_symbols})
    
    return jsonify({'status': 'error', 'message': 'No symbols provided'}), 400


@app.route('/api/analytics/<symbol>', methods=['GET'])
def get_analytics(symbol):
    """Get analytics for a specific symbol"""
    timeframe = request.args.get('timeframe', '1m')
    window = int(request.args.get('window', 20))
    
    try:
        analytics = analytics_engine.compute_analytics(symbol, timeframe, window)
        return jsonify(analytics)
    except Exception as e:
        logger.error(f"Error computing analytics for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pair_analytics', methods=['GET'])
def get_pair_analytics():
    """Get pair analytics (spread, hedge ratio, etc.)"""
    symbol1 = request.args.get('symbol1', 'BTCUSDT')
    symbol2 = request.args.get('symbol2', 'ETHUSDT')
    timeframe = request.args.get('timeframe', '1m')
    window = int(request.args.get('window', 20))
    
    try:
        analytics = analytics_engine.compute_pair_analytics(symbol1, symbol2, timeframe, window)
        return jsonify(analytics)
    except Exception as e:
        logger.error(f"Error computing pair analytics: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/live_data/<symbol>', methods=['GET'])
def get_live_data(symbol):
    """Get recent live tick data"""
    limit = int(request.args.get('limit', 100))
    
    try:
        data = db_manager.get_recent_ticks(symbol, limit)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching live data for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ohlc/<symbol>', methods=['GET'])
def get_ohlc(symbol):
    """Get OHLC data"""
    timeframe = request.args.get('timeframe', '1m')
    limit = int(request.args.get('limit', 100))
    
    try:
        data = db_manager.get_ohlc_data(symbol, timeframe, limit)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching OHLC for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all active alerts"""
    return jsonify({'alerts': alert_manager.get_all_alerts()})


@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """Create a new alert"""
    data = request.json
    alert_id = alert_manager.add_alert(
        symbol=data.get('symbol'),
        metric=data.get('metric'),
        condition=data.get('condition'),
        threshold=float(data.get('threshold')),
        message=data.get('message', '')
    )
    return jsonify({'status': 'success', 'alert_id': alert_id})


@app.route('/api/alerts/<alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Delete an alert"""
    alert_manager.remove_alert(alert_id)
    return jsonify({'status': 'success'})


@app.route('/api/export/<symbol>', methods=['GET'])
def export_data(symbol):
    """Export processed data as CSV"""
    timeframe = request.args.get('timeframe', '1m')
    
    try:
        filepath = analytics_engine.export_to_csv(symbol, timeframe)
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        logger.error(f"Error exporting data for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload_ohlc', methods=['POST'])
def upload_ohlc():
    """Upload OHLC data from CSV"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        db_manager.import_ohlc_csv(file)
        return jsonify({'status': 'success', 'message': 'Data uploaded successfully'})
    except Exception as e:
        logger.error(f"Error uploading OHLC data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    stats = {
        'total_ticks': db_manager.get_total_tick_count(),
        'active_symbols': active_symbols,
        'ingestion_status': data_ingestion.get_status(),
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(stats)


# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')


@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe to specific symbol updates"""
    symbol = data.get('symbol')
    logger.info(f'Client subscribed to {symbol}')


def run_data_ingestion():
    """Run data ingestion in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(data_ingestion.start(active_symbols))


if __name__ == '__main__':
    logger.info("Starting Real-Time Trading Analytics Platform...")
    
    # Initialize database
    db_manager.initialize()
    logger.info("Database initialized")
    
    # Start data ingestion in background thread
    ingestion_thread = threading.Thread(target=run_data_ingestion, daemon=True)
    ingestion_thread.start()
    logger.info("Data ingestion started")
    
    # Start Flask app with SocketIO
    logger.info("Starting Flask server on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)