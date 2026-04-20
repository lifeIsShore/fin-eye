import numpy as np
from typing import Tuple, List
from app.schemas.montecarlo_models import MCAssetParams, MCSimulationResult, MCPercentileResult, MCPortfolioParams, MCPortfolioResult

def compute_log_returns(prices: List[float]) -> np.ndarray:
    """Compute daily logarithmic returns from an array of prices."""
    if len(prices) < 2:
        return np.array([])
    prices_array = np.array(prices)
    return np.diff(np.log(prices_array))

def run_gbm_paths(S0: float, mu: float, sigma: float, T: float, steps: int, paths: int) -> np.ndarray:
    """
    Generate paths using Geometric Brownian Motion.
    Returns array of shape (steps+1, paths)
    """
    if steps == 0:
        val = np.zeros((1, paths))
        val[0] = S0
        return val
        
    dt = T / steps
    
    # Generate random standard normal variables
    Z = np.random.standard_normal((steps, paths))
    
    drift = (mu - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt) * Z
    
    daily_returns = np.exp(drift + diffusion)
    
    paths_array = np.zeros((steps + 1, paths))
    paths_array[0] = S0
    paths_array[1:] = S0 * np.cumprod(daily_returns, axis=0)
    
    return paths_array

def run_merton_jump_diffusion_paths(S0: float, mu: float, sigma: float, T: float, steps: int, paths: int, 
                                    lambda_j: float, mu_j: float, sigma_j: float) -> np.ndarray:
    """
    Generate paths using Merton's Jump Diffusion model.
    """
    if steps == 0:
        val = np.zeros((1, paths))
        val[0] = S0
        return val
        
    dt = T / steps
    
    Z = np.random.standard_normal((steps, paths))
    N = np.random.poisson(lambda_j * dt, (steps, paths))
    
    J = np.zeros((steps, paths))
    mask = N > 0
    if np.any(mask):
        J[mask] = np.random.normal(N[mask] * mu_j, np.sqrt(N[mask]) * sigma_j)
    
    k = np.exp(mu_j + 0.5 * sigma_j**2) - 1
    
    drift = (mu - lambda_j * k - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt) * Z
    
    daily_returns = np.exp(drift + diffusion + J)
    
    paths_array = np.zeros((steps + 1, paths))
    paths_array[0] = S0
    paths_array[1:] = S0 * np.cumprod(daily_returns, axis=0)
    
    return paths_array

def calculate_percentiles(paths_array: np.ndarray, dt: float) -> list[MCPercentileResult]:
    """
    Calculate percentiles across all paths at each time step.
    paths_array shape: (steps+1, paths)
    """
    percentiles = [5, 25, 50, 75, 95]
    res_percentiles = np.percentile(paths_array, percentiles, axis=1)
    res_mean = np.mean(paths_array, axis=1)
    
    steps = paths_array.shape[0]
    
    trajectory = []
    for step in range(steps):
        # convert step index to approximate day
        day = int(step * dt * 252) # Assuming T is in years, and 252 days per year
        
        trajectory.append(MCPercentileResult(
            step=step,
            day=day,
            p5=res_percentiles[0][step],
            p25=res_percentiles[1][step],
            p50=res_percentiles[2][step],
            p75=res_percentiles[3][step],
            p95=res_percentiles[4][step],
            mean=res_mean[step]
        ))
    
    return trajectory

def run_asset_simulation(params: MCAssetParams) -> MCSimulationResult:
    """
    Main entry point to run simulation for a single asset and extract all requested KPIs.
    """
    T = params.years
    steps = params.years * params.steps_per_year
    dt = T / steps if steps > 0 else 0
    
    if params.model_type.upper() == "JUMP_DIFFUSION":
        paths_array = run_merton_jump_diffusion_paths(
            S0=params.starting_value,
            mu=params.mu,
            sigma=params.sigma,
            T=T,
            steps=steps,
            paths=params.paths,
            lambda_j=params.jump_intensity,
            mu_j=params.jump_mean,
            sigma_j=params.jump_std
        )
    else:
        paths_array = run_gbm_paths(
            S0=params.starting_value,
            mu=params.mu,
            sigma=params.sigma,
            T=T,
            steps=steps,
            paths=params.paths
        )
        
    trajectory = calculate_percentiles(paths_array, dt)
    
    if steps > 0:
        peaks = np.maximum.accumulate(paths_array, axis=0)
        drawdowns = (peaks - paths_array) / peaks
        max_drawdowns = np.max(drawdowns, axis=0)
        mdd_95 = np.percentile(max_drawdowns, 95)
    else:
        mdd_95 = 0.0
    
    final_values = paths_array[-1]
    returns = (final_values - params.starting_value) / params.starting_value if params.starting_value > 0 else final_values
    sorted_returns = np.sort(returns)
    cutoff_index = max(1, int(0.05 * params.paths))
    cvar_95 = np.mean(sorted_returns[:cutoff_index]) * -1.0 # Positive number representing loss
    
    return MCSimulationResult(
        symbol=params.symbol,
        final_median=float(np.median(final_values)),
        final_p5=float(np.percentile(final_values, 5)),
        final_p95=float(np.percentile(final_values, 95)),
        max_drawdown_p95=float(mdd_95),
        cvar_95=float(cvar_95),
        paths_generated=params.paths,
        trajectory=trajectory
    )

def run_portfolio_simulation(params: MCPortfolioParams) -> MCPortfolioResult:
    """
    Simulate a portfolio of assets with potential correlations and cash flows.
    """
    T = params.years
    steps = params.years * params.steps_per_year
    dt = T / steps if steps > 0 else 0
    num_assets = len(params.assets)
    paths = params.paths
    
    if steps == 0 or num_assets == 0:
        return MCPortfolioResult(
            final_median=params.starting_capital,
            final_p5=params.starting_capital,
            final_p95=params.starting_capital,
            success_rate=100.0 if params.starting_capital > 0 else 0.0,
            trajectory=[MCPercentileResult(step=0, day=0, p5=params.starting_capital, p25=params.starting_capital, p50=params.starting_capital, p75=params.starting_capital, p95=params.starting_capital, mean=params.starting_capital)]
        )
    
    # Extract mus and sigmas
    mus = np.array([a.mu for a in params.assets]) # shape: (num_assets,)
    sigmas = np.array([a.sigma for a in params.assets]) # shape: (num_assets,)
    
    if params.correlation_matrix is not None and len(params.correlation_matrix) == num_assets:
        corr_mat = np.array(params.correlation_matrix)
        outer_sigmas = np.outer(sigmas, sigmas)
        cov_mat = corr_mat * outer_sigmas
    else:
        cov_mat = np.diag(sigmas**2)
        
    # We add a small regularization term to the diagonal to ensure the matrix is uniquely positive definite
    # Sometimes due to floating point precision, cholesky might fail.
    try:
        L = np.linalg.cholesky(cov_mat) # shape: (num_assets, num_assets)
    except np.linalg.LinAlgError:
        cov_mat += np.eye(num_assets) * 1e-8
        L = np.linalg.cholesky(cov_mat)
    
    Z = np.random.standard_normal((num_assets, steps * paths))
    W = L.dot(Z) # shape: (num_assets, steps * paths)
    W = W.reshape((num_assets, steps, paths))
    
    asset_returns = np.zeros((num_assets, steps, paths))
    for i in range(num_assets):
        drift = (mus[i] - 0.5 * sigmas[i]**2) * dt
        diffusion = W[i] * np.sqrt(dt)
        asset_returns[i] = np.exp(drift + diffusion)
    
    total_starting_value = sum(a.starting_value for a in params.assets)
    if total_starting_value > 0:
        weights = np.array([a.starting_value / total_starting_value for a in params.assets])
    else:
        weights = np.ones(num_assets) / num_assets
        
    port_vals = np.zeros((steps + 1, paths))
    port_vals[0] = params.starting_capital
    
    step_contribution = params.monthly_contribution * (12.0 / params.steps_per_year)
    port_returns = np.tensordot(weights, asset_returns, axes=([0], [0])) # shape (steps, paths)
    
    for t in range(steps):
        port_vals[t+1] = port_vals[t] * port_returns[t] + step_contribution
        if step_contribution < 0:
            port_vals[t+1] = np.maximum(0, port_vals[t+1])
            
    trajectory = calculate_percentiles(port_vals, dt)
    final_values = port_vals[-1]
    success_rate = float(np.mean(final_values > 0) * 100) # Percentage
    
    return MCPortfolioResult(
        final_median=float(np.median(final_values)),
        final_p5=float(np.percentile(final_values, 5)),
        final_p95=float(np.percentile(final_values, 95)),
        success_rate=success_rate,
        trajectory=trajectory
    )
