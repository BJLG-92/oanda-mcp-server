# Oanda MCP Server

A REST API server for Oanda trading operations, deployed on Railway and compatible with Model Context Protocol (MCP).

## Features

- Account information retrieval
- Position management
- Order placement (market and limit orders)
- Current price data
- Historical data
- Order cancellation

## API Endpoints

- `GET /` - Health check
- `GET /account` - Get account information
- `GET /positions` - Get current positions
- `GET /orders` - Get pending orders
- `GET /price/{instrument}` - Get current price for instrument
- `GET /historical/{instrument}` - Get historical data
- `POST /order/market` - Place market order
- `POST /order/limit` - Place limit order
- `DELETE /order/{order_id}` - Cancel order
- `POST /position/close/{instrument}` - Close position

## Environment Variables

- `OANDA_API_KEY` - Your Oanda API key
- `OANDA_ACCOUNT_ID` - Your Oanda account ID
- `OANDA_ENVIRONMENT` - 'practice' or 'live'
- `PORT` - Server port (set automatically by Railway)
