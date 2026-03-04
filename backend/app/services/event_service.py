import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from app.schemas.event_models import MarketEvent
import random

class EventService:
    def __init__(self):
        # In the future, API keys (e.g. from FINNHUB_API_KEY) and httpx clients would be initialized here
        pass

    async def get_upcoming_events(self, country: Optional[str] = None, impact: Optional[str] = None) -> List[MarketEvent]:
        """
        Fetches upcoming macroeconomic and political events.
        Currently uses a robust mock generation system.
        """
        events = self._generate_mock_events()
        
        # Apply filters
        if country:
            events = [e for e in events if e.country.upper() == country.upper()]
        
        if impact:
            events = [e for e in events if e.impact.capitalize() == impact.capitalize()]
            
        return sorted(events, key=lambda x: x.date)

    def _generate_mock_events(self) -> List[MarketEvent]:
        """Generates realistic mock macro events spanning the next two weeks."""
        today = datetime.now()
        events = []
        
        event_blueprints = [
            {"title": "Fed Interest Rate Decision", "description": "FOMC dictates the federal funds rate.", "impact": "High", "country": "US", "delay": 2, "time": "14:00", "estimate": "5.25%", "previous": "5.50%"},
            {"title": "Core CPI (MoM)", "description": "Consumer Price Index excluding food and energy.", "impact": "High", "country": "US", "delay": 5, "time": "08:30", "estimate": "0.3%", "previous": "0.4%"},
            {"title": "Non Farm Payrolls", "description": "Total number of paid workers in the U.S.", "impact": "High", "country": "US", "delay": 7, "time": "08:30", "estimate": "180K", "previous": "210K"},
            {"title": "ECB Press Conference", "description": "European Central Bank details monetary policy.", "impact": "High", "country": "EU", "delay": 1, "time": "14:45", "estimate": None, "previous": None},
            {"title": "CPI (YoY)", "description": "Annual inflation rate in the UK.", "impact": "Medium", "country": "UK", "delay": 8, "time": "07:00", "estimate": "3.8%", "previous": "4.0%"},
            {"title": "GDP Growth Rate", "description": "Quarterly economic growth indicator.", "impact": "High", "country": "CN", "delay": 12, "time": "02:00", "estimate": "4.5%", "previous": "4.7%"},
            {"title": "Initial Jobless Claims", "description": "Number of individuals filing for unemployment.", "impact": "Medium", "country": "US", "delay": 3, "time": "08:30", "estimate": "215K", "previous": "212K"},
            {"title": "Retail Sales (MoM)", "description": "Measurement of sales at retail level.", "impact": "Medium", "country": "US", "delay": 10, "time": "08:30", "estimate": "0.5%", "previous": "0.6%"},
            {"title": "Manufacturing PMI", "description": "Managers Index indicating manufacturing sector health.", "impact": "Low", "country": "EU", "delay": 4, "time": "10:00", "estimate": "48.5", "previous": "49.0"},
            {"title": "Presidential Policy Speech", "description": "Address outlining new economic stimulus plans.", "impact": "High", "country": "US", "delay": 14, "time": "20:00", "estimate": None, "previous": None},
        ]
        
        for bp in event_blueprints:
            event_date = today + timedelta(days=bp["delay"])
            events.append(MarketEvent(
                id=str(uuid.uuid4()),
                date=event_date.strftime("%Y-%m-%d"),
                time=bp["time"],
                title=bp["title"],
                description=bp["description"],
                impact=bp["impact"],
                country=bp["country"],
                estimate=bp["estimate"],
                previous=bp["previous"]
            ))
            
        return events
