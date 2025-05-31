import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import oandapyV20
from oandapyV20 import API
from oandapyV20.endpoints import accounts, orders, positions, pricing, instruments
from oandapyV20.exceptions import V20Error
import uvicorn
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Oanda MCP Server",
    description="REST API for Oanda trading operations compatible with MCP",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Oanda client
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")

if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
    logger.error("Missing Oanda API credentials")
    raise ValueError("Oanda API credentials not found in environment variables.")

try:
    oanda_client = API(access_token=OANDA_API_KEY, environment=OANDA_ENVIRONMENT)
    logger.info(f"Oanda client initialized for {OANDA_ENVIRONMENT} environment")
except Exception as e:
    logger.error(f"Failed to initialize Oanda client: {e}")
    raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Oanda MCP Server is running!",
        "environment": OANDA_ENVIRONMENT,
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test Oanda connection
        r = accounts.AccountDetails(accountID=OANDA_ACCOUNT_ID)
        oanda_client.request(r)
        return {
            "status": "healthy",
            "oanda_connection": "ok",
            "account_id": OANDA_ACCOUNT_ID,
            "environment": OANDA_ENVIRONMENT
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "oanda_connection": "failed"
        }

@app.get("/account")
async def get_account_info():
    """Get account information including balance, equity, and margin details."""
    try:
        r = accounts.AccountDetails(accountID=OANDA_ACCOUNT_ID)
        oanda_client.request(r)
        account_info = r.response['account']
        
        return {
            "success": True,
            "data": {
                "id": account_info['id'],
                "currency": account_info['currency'],
                "balance": account_info['balance'],
                "nav": account_info['NAV'],
                "unrealized_pl": account_info['unrealizedPL'],
                "margin_used": account_info['marginUsed'],
                "margin_available": account_info['marginAvailable'],
                "margin_rate": account_info['marginRate'],
                "open_trade_count": account_info['openTradeCount'],
                "open_position_count": account_info['openPositionCount'],
                "pending_order_count": account_info['pendingOrderCount']
            }
        }
    except V20Error as e:
        logger.error(f"Oanda API error in get_account_info: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_account_info: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/positions")
async def get_positions():
    """Get all current positions."""
    try:
        r = positions.OpenPositions(accountID=OANDA_ACCOUNT_ID)
        oanda_client.request(r)
        positions_data = r.response.get('positions', [])
        
        return {
            "success": True,
            "data": positions_data,
            "count": len(positions_data)
        }
    except V20Error as e:
        logger.error(f"Oanda API error in get_positions: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_positions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/orders")
async def get_orders():
    """Get all pending orders."""
    try:
        r = orders.OrderList(accountID=OANDA_ACCOUNT_ID)
        oanda_client.request(r)
        orders_data = r.response.get('orders', [])
        
        return {
            "success": True,
            "data": orders_data,
            "count": len(orders_data)
        }
    except V20Error as e:
        logger.error(f"Oanda API error in get_orders: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_orders: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/price/{instrument}")
async def get_current_price(instrument: str):
    """Get current bid/ask prices for an instrument."""
    try:
        params = {"instruments": instrument}
        r = pricing.PricingInfo(accountID=OANDA_ACCOUNT_ID, params=params)
        oanda_client.request(r)
        prices = r.response.get('prices', [])
        
        if not prices:
            raise HTTPException(status_code=404, detail=f"No price data found for {instrument}")
        
        price_data = prices[0]
        
        return {
            "success": True,
            "data": {
                "instrument": instrument,
                "bid": price_data.get('bids', [{}])[0].get('price', 'N/A'),
                "ask": price_data.get('asks', [{}])[0].get('price', 'N/A'),
                "spread": float(price_data.get('asks', [{}])[0].get('price', 0)) - float(price_data.get('bids', [{}])[0].get('price', 0)),
                "time": price_data.get('time')
            }
        }
    except V20Error as e:
        logger.error(f"Oanda API error in get_current_price: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_current_price: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/historical/{instrument}")
async def get_historical_data(instrument: str, granularity: str = "D", count: int = 100):
    """Get historical candle data for an instrument."""
    try:
        params = {
            "granularity": granularity,
            "count": min(count, 5000)
        }
        
        r = instruments.InstrumentsCandles(instrument=instrument, params=params)
        oanda_client.request(r)
        candles = r.response.get('candles', [])
        
        return {
            "success": True,
            "data": {
                "instrument": instrument,
                "granularity": granularity,
                "candles": candles,
                "count": len(candles)
            }
        }
    except V20Error as e:
        logger.error(f"Oanda API error in get_historical_data: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_historical_data: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/order/market")
async def place_market_order(order_request: Dict[str, Any]):
    """Place a market order."""
    try:
        required_fields = ["instrument", "units"]
        for field in required_fields:
            if field not in order_request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": order_request["instrument"],
                "units": str(order_request["units"])
            }
        }
        
        # Add optional stop loss
        if order_request.get("stop_loss"):
            order_data["order"]["stopLossOnFill"] = {
                "price": str(order_request["stop_loss"])
            }
        
        # Add optional take profit
        if order_request.get("take_profit"):
            order_data["order"]["takeProfitOnFill"] = {
                "price": str(order_request["take_profit"])
            }
        
        r = orders.OrderCreate(accountID=OANDA_ACCOUNT_ID, data=order_data)
        oanda_client.request(r)
        
        return {
            "success": True,
            "data": r.response
        }
    except V20Error as e:
        logger.error(f"Oanda API error in place_market_order: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in place_market_order: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/order/limit")
async def place_limit_order(order_request: Dict[str, Any]):
    """Place a limit order."""
    try:
        required_fields = ["instrument", "units", "price"]
        for field in required_fields:
            if field not in order_request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        order_data = {
            "order": {
                "type": "LIMIT",
                "instrument": order_request["instrument"],
                "units": str(order_request["units"]),
                "price": str(order_request["price"])
            }
        }
        
        # Add optional stop loss
        if order_request.get("stop_loss"):
            order_data["order"]["stopLossOnFill"] = {
                "price": str(order_request["stop_loss"])
            }
        
        # Add optional take profit
        if order_request.get("take_profit"):
            order_data["order"]["takeProfitOnFill"] = {
                "price": str(order_request["take_profit"])
            }
        
        r = orders.OrderCreate(accountID=OANDA_ACCOUNT_ID, data=order_data)
        oanda_client.request(r)
        
        return {
            "success": True,
            "data": r.response
        }
    except V20Error as e:
        logger.error(f"Oanda API error in place_limit_order: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in place_limit_order: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.delete("/order/{order_id}")
async def cancel_order(order_id: str):
    """Cancel a pending order."""
    try:
        r = orders.OrderCancel(accountID=OANDA_ACCOUNT_ID, orderID=order_id)
        oanda_client.request(r)
        
        return {
            "success": True,
            "data": r.response
        }
    except V20Error as e:
        logger.error(f"Oanda API error in cancel_order: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in cancel_order: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/position/close/{instrument}")
async def close_position(instrument: str, units: str = "ALL"):
    """Close a position for an instrument."""
    try:
        if units == "ALL":
            close_data = {
                "longUnits": "ALL",
                "shortUnits": "ALL"
            }
        else:
            if int(units) > 0:
                close_data = {"longUnits": units}
            else:
                close_data = {"shortUnits": str(abs(int(units)))}
        
        r = positions.PositionClose(accountID=OANDA_ACCOUNT_ID, instrument=instrument, data=close_data)
        oanda_client.request(r)
        
        return {
            "success": True,
            "data": r.response
        }
    except V20Error as e:
        logger.error(f"Oanda API error in close_position: {e}")
        raise HTTPException(status_code=400, detail=f"Oanda API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in close_position: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
