# Quant-Developer-assignment
A comprehensive end-to-end analytics application for real-time cryptocurrency trading data, featuring WebSocket ingestion, quantitative analytics, and interactive visualization.
This platform demonstrates a complete data pipeline from real-time data ingestion through to advanced analytics and visualization, designed for traders and researchers at high-frequency trading firms.
Key Features

Real-time Data Ingestion: WebSocket connection to Binance for live tick data
Multi-timeframe Support: 1s, 1m, 5m aggregations
Advanced Analytics:

Price statistics and technical indicators (RSI, SMA, volatility)
Pair analytics (hedge ratios, spread analysis, correlation)
Statistical tests (ADF test for stationarity)
Z-score calculations for mean reversion strategies
OLS and Huber regression for robust hedge estimation


Interactive Dashboard: Real-time charts with zoom, pan, and hover capabilities
Alert System: User-defined custom alerts with real-time notifications
Data Export: CSV export functionality for further analysis

🏗️ Architecture
┌─────────────────┐
│  Binance        │
│  WebSocket API  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│ Data Ingestion  │────►│   SQLite DB  │
│   Service       │     │  (Storage)   │
└────────┬────────┘     └──────┬───────┘
         │                     │
         │                     │
         ▼                     ▼
┌─────────────────┐     ┌──────────────┐
│ Alert Manager   │     │  Analytics   │
│                 │     │   Engine     │
└────────┬────────┘     └──────┬───────┘
         │                     │
         └──────────┬──────────┘
                    ▼
         ┌──────────────────┐
         │   Flask API      │
         │   + SocketIO     │
         └─────────┬────────┘
                   │
                   ▼
         ┌──────────────────┐
         │  Web Dashboard   │
         │  (HTML/JS/Plotly)│
         └──────────────────┘
Component Design

Data Ingestion Layer (backend/data_ingestion.py)

Establishes WebSocket connection to Binance
Processes incoming tick data
Handles reconnection logic
Emits real-time updates via SocketIO


Storage Layer (backend/storage.py)

SQLite database for persistence
Separate tables for ticks and OHLC data
Automatic resampling to multiple timeframes
Efficient querying with indexed columns


Analytics Engine (backend/analytics_engine.py)

Single-symbol analytics (price stats, volatility, RSI, z-score)
Pair analytics (hedge ratios, spread, correlation)
Statistical tests (ADF for stationarity)
Robust regression implementations
Mean reversion backtesting


Alert Manager (backend/alert_manager.py)

Rule-based alert system
Multiple metric support (price, z-score, RSI, volume)
Condition evaluation engine
Real-time notification system


API Layer (app.py)

RESTful endpoints for analytics and data
WebSocket events for real-time updates
File upload/download capabilities


Frontend (templates/index.html)

Real-time dashboard with live updates
Interactive Plotly charts
Control panel for symbol/timeframe selection
Alert creation interface
