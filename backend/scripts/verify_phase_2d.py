import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import AsyncSessionLocal, async_engine
from app.services.gas_precompute import compute_gas_for_symbol
from app.models.gas_snapshot import GasSnapshot
from sqlalchemy import select

async def verify():
    print("--- Phase 2D Verification: Signal Grade Persistence ---")
    
    symbol = "AAPL"
    
    async with AsyncSessionLocal() as db:
        print(f"Triggering precompute for {symbol}...")
        result = await compute_gas_for_symbol(symbol, db)
        await db.commit()
        
        print(f"Computed Grade: {result.get('signal_grade')} ({result.get('signal_grade_score')})")
        
        print("Querying database to verify persistence...")
        stmt = select(GasSnapshot).where(GasSnapshot.symbol == symbol).order_by(GasSnapshot.computed_at.desc()).limit(1)
        db_res = await db.execute(stmt)
        snap = db_res.scalar_one_or_none()
        
        if snap:
            print(f"FOUND in DB: ID={snap.id}")
            print(f"  signal_grade:         {snap.signal_grade}")
            print(f"  signal_grade_score:   {snap.signal_grade_score}")
            print(f"  signal_tradeable:     {snap.signal_tradeable}")
            print(f"  signal_grade_desc:    {snap.signal_grade_desc}")
            print(f"  signal_grade_reasons: {snap.signal_grade_reasons}")
            
            if snap.signal_grade is not None:
                print("\nSUCCESS: Signal grade columns are working and persisting!")
            else:
                print("\nFAILURE: Columns exist but are NULL.")
        else:
            print("\nFAILURE: No snapshot found in DB.")
            
    await async_engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify())
