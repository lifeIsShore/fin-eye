from fastapi import APIRouter, Depends, HTTPException
from app.schemas.montecarlo_models import (
    MCAssetParams, 
    MCSimulationResult, 
    MCPortfolioParams, 
    MCPortfolioResult
)
from app.services.mc_engine import run_asset_simulation, run_portfolio_simulation

router = APIRouter()

@router.post("/asset", response_model=MCSimulationResult)
def run_asset_mc(params: MCAssetParams):
    """
    Run Monte Carlo simulation for a single asset or strategy given historical parameters.
    """
    try:
        # Prevent OOM attacks
        if params.paths > 50000:
            raise HTTPException(status_code=400, detail="Maximum paths allowed is 50000")
        if params.years * params.steps_per_year > 3650: # Max 10 years daily
            raise HTTPException(status_code=400, detail="Maximum time steps allowed is 3650")
            
        result = run_asset_simulation(params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portfolio", response_model=MCPortfolioResult)
def run_portfolio_mc(params: MCPortfolioParams):
    """
    Simulate combined portfolio matrix with covariances and cash flows.
    """
    try:
        # Prevent OOM attacks for portfolio matrix
        if params.paths > 50000:
            raise HTTPException(status_code=400, detail="Maximum paths allowed is 50000")
        if len(params.assets) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 assets allowed per portfolio simulation")
        if params.years * params.steps_per_year > 1200: # Max 100 years monthly
            raise HTTPException(status_code=400, detail="Maximum time steps allowed is 1200")
            
        result = run_portfolio_simulation(params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
