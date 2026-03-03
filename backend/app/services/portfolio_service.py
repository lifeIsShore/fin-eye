import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.portfolio import Portfolio, PortfolioItem
from app.services.technical_service import compute_technical_consensus
from app.services.market_data import OHLCVFetcher

fetcher = OHLCVFetcher()

async def calculate_portfolio_analysis(db: Session, portfolio_id: int) -> Dict[str, Any]:
    """
    Calculates the 3 core portfolio metrics defined in the PRD MVP:
    - Weighted Average GAS (Technical Consensus)
    - Sector Breakdown
    - Diversification Score (0-100 based on inter-asset correlation)
    """
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio or not portfolio.items:
        return {
            "weighted_gas": 0,
            "sector_breakdown": {},
            "diversification_score": 0,
            "error": "Portfolio is empty or does not exist."
        }

    items = portfolio.items
    
    # Validation: Ensure weights sum to 1.0 (100%) for accurate math
    total_weight = sum(item.weight for item in items)
    if total_weight == 0:
        return {"error": "Portfolio weights sum to 0."}
    
    normalized_items = [{"symbol": i.symbol, "weight": i.weight / total_weight} for i in items]

    # 1. Weighted Average GAS
    weighted_gas = 0.0
    for item in normalized_items:
        try:
            # Reusing the ML consensus generation
            consensus = await compute_technical_consensus(item['symbol'])
            weighted_gas += consensus['consensus_score'] * item['weight']
        except Exception:
            # If a symbol fails, we just add 0 weight contribution for now
            pass
            
    # 2. Sector Breakdown via Yahoo Finance Info
    sector_breakdown = {}
    tickers = [item['symbol'] for item in normalized_items]
    
    try:
        # yfinance caching or bulk fetching is ideal, but we loop for simplicity of MVP
        for item in normalized_items:
            ticker = yf.Ticker(item['symbol'])
            info = ticker.info
            sector = info.get('sector', 'Unknown')
            
            if sector in sector_breakdown:
                sector_breakdown[sector] += (item['weight'] * 100) # Convert to readable percentages
            else:
                sector_breakdown[sector] = (item['weight'] * 100)
    except Exception:
        pass

    # 3. Diversification Score (Correlation Matrix)
    # Lower correlation = higher diversification score
    div_score = 0
    if len(tickers) > 1:
        try:
            # Fetch 6-month daily return data to build a matrix
            price_data = {}
            for symbol in tickers:
                df = fetcher.fetch_ohlcv(symbol, period="6mo", interval="1d")
                if not df.empty:
                    df['Return'] = df['Close'].pct_change()
                    price_data[symbol] = df['Return']
            
            # Combine into a single pandas dataframe
            combined_df = pd.DataFrame(price_data).dropna()
            
            if not combined_df.empty:
                corr_matrix = combined_df.corr()
                
                # Extract upper triangle of matrix (excluding symmetric duplicate 1.0 diagonals)
                upper_tri_indices = np.triu_indices_from(corr_matrix, k=1)
                correlations = corr_matrix.values[upper_tri_indices]
                
                # If we have valid correlation points, average them
                if len(correlations) > 0:
                    avg_correlation = np.nanmean(correlations)
                    # Convert (-1 to +1) domain into (0 to 100) Diversification mapping
                    # -1 (Perfectly inversely correlated) = 100 Diversification Score
                    #  1 (Perfectly correlated) = 0 Diversification Score
                    # Math: (1 - correlation) / 2 * 100
                    div_score = ((1 - avg_correlation) / 2) * 100
        except Exception:
            pass # Fallback to 0 if data isn't available

    return {
        "weighted_gas": round(weighted_gas, 2),
        "sector_breakdown": {k: round(v, 2) for k, v in sector_breakdown.items()},
        "diversification_score": round(div_score, 2),
    }
