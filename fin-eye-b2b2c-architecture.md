

**FIN-EYE**

**B2B2C Platform-as-a-Service**

Architecture Pivot — Implementation Playbook


|**This document translates the B2B2C pivot question into concrete code patterns, schema changes, and service-layer designs — all grounded in the actual Fin-Eye codebase (FastAPI + SQLAlchemy + PostgreSQL). Every code snippet shown is written to slot into the existing architecture with minimal breaking changes.**|
| :- |


|**Section**|**Topic**|
| :- | :- |
|**Part 1**|The Mental Model — Platform / Advisor / Client|
|**Part 2**|Multi-Tenancy Schema — PostgreSQL & SQLAlchemy|
|**Part 3**|Data Isolation — Row-Level Security vs App Filtering|
|**Part 4**|AI Narrator White-Labeling — Tone per Tenant|
|**Part 5**|GAS Weight Engine — Advisor-Adjustable Scoring|
|**Part 6**|Compliance Audit Logs|
|**Part 7**|Auth Changes — JWT Claims & Dependency Injection|
|**Part 8**|Migration Strategy — Breaking Nothing|
|**Part 9**|Bonus Patterns — Billing, Feature Flags, Rate Limits|



**Part 1 — The Mental Model: Three Tiers, Three Responsibilities**

|**Tier**|**Who**|**What They Do**|**What They Own in the DB**|
| :- | :- | :- | :- |
|**🏢  Platform Admin<br>(You — The Landlord)**|Fin-Eye operator|Manages all tenants, billing, feature flags, global ML models, market data pipelines.|Platform settings, tenant accounts, global models, audit logs|
|**👔  Advisor<br>(The Tenant)**|Financial advisor or RIA firm|Onboards clients, customises GAS weights and AI tone, views client dashboards, uses compliance logs.|Advisor profile, GAS weight profiles, AI tone config, client roster|
|**👤  Client<br>(End User)**|Retail investor managed by advisor|Views their dashboard, watchlist, portfolios. Receives AI narrations. Cannot see other clients.|Portfolio, watchlist, alerts — all scoped under their advisor|

**The Regulatory Shield — Why This Model Works**

The key legal insight: Fin-Eye provides market intelligence data and educational analysis (the engine). Advisors provide financial advice based on their professional judgment (the interpretation). This separation is what shields Fin-Eye from acting as an investment advisor under regulations like the SEC Investment Advisers Act, MiFID II, or equivalent.

|**Fin-Eye provides (data/tools)**|**Advisor provides (advice)**|
| :- | :- |
|GAS Score (0–100) with methodology|Interpretation of what the score means for this specific client|
|AI Market Narration (educational, factual)|Personalised advice built on top of the narration|
|Historical backtests (statistical patterns)|Recommendation to act or not act based on the backtest|
|**CRITICAL: Every screen the client sees must carry the disclaimer: 'This analysis is provided by Fin-Eye as educational market intelligence. [Advisor Name] provides all financial advice. This is not investment advice from Fin-Eye.' This needs to be baked into the white-label rendering layer.**||



**Part 2 — Multi-Tenancy Schema**

**The Core Insight: Add tenant\_id to Every Row, Not a New Database**

The two main multi-tenancy strategies are (A) separate databases per tenant or (B) shared database with a tenant\_id column. For Fin-Eye at this stage, shared database with application-level isolation is correct. Here's why:

|**Strategy**|**Pros**|**Cons**|
| :- | :- | :- |
|**Separate DB per tenant**|Perfect isolation. Simple compliance.|Expensive at scale. Impossible to run cross-tenant analytics. Schema migrations run N times.|
|**Shared DB + tenant\_id ✅ RECOMMENDED**|Single Alembic migration. Cross-tenant analytics possible for you. Cost-efficient.|Isolation enforced at app level — bugs could leak data. Requires disciplined query patterns.|

**Step 1 — Add the Tenant (Advisor) Model**

An Advisor is a special User. The cleanest pattern is a dedicated tenants table rather than adding a role to the users table. This gives Advisors their own configuration space without polluting the User model.

`  `**app/models/tenant.py**

|# app/models/tenant.py<br># NEW FILE — add to app/models/\_\_init\_\_.py<br> <br>import uuid<br>from datetime import datetime<br>from sqlalchemy import Boolean, Column, DateTime, String, Text, JSON<br>from sqlalchemy.dialects.postgresql import UUID<br>from sqlalchemy.orm import relationship<br>from sqlalchemy.sql import func<br>from app.db.database import Base<br> <br>class Tenant(Base):<br>`    `"""<br>`    `Represents a Financial Advisor / RIA firm — a paying B2B customer.<br>`    `One Tenant can have many clients (Users linked via TenantMembership).<br>`    `"""<br>`    `\_\_tablename\_\_ = "tenants"<br> <br>`    `id = Column(UUID(as\_uuid=True), primary\_key=True, default=uuid.uuid4)<br>`    `name = Column(String(256), nullable=False)           # 'Smith Financial Advisory'<br>`    `slug = Column(String(64), unique=True, nullable=False, index=True)  # 'smith-advisory'<br>`    `is\_active = Column(Boolean, default=True)<br> <br>`    `# White-label display<br>`    `brand\_name       = Column(String(128), nullable=True)   # 'Smith Insights'<br>`    `logo\_url         = Column(String(512), nullable=True)<br>`    `primary\_color    = Column(String(7),   nullable=True, default='#1F4E79')  # hex<br>`    `disclaimer\_text  = Column(Text,        nullable=True)   # custom legal footer<br> <br>`    `# Billing / subscription<br>`    `subscription\_tier = Column(String(32), default='advisor\_basic')<br>`    `max\_clients       = Column(Integer,    default=50)      # license limit<br> <br>`    `# AI Narrator config (Part 4)<br>`    `ai\_narrator\_config = Column(JSON, nullable=True)        # tone, persona, forbidden words<br> <br>`    `# GAS weight profile link (Part 5)<br>`    `gas\_weight\_profile\_id = Column(UUID(as\_uuid=True), nullable=True)<br> <br>`    `created\_at = Column(DateTime(timezone=True), server\_default=func.now())<br>`    `updated\_at = Column(DateTime(timezone=True), onupdate=func.now())<br> <br>`    `# Relationships<br>`    `memberships = relationship('TenantMembership', back\_populates='tenant',<br>`                               `cascade='all, delete-orphan')<br>`    `gas\_profiles = relationship('GASWeightProfile', back\_populates='tenant')|
| :- |


**Step 2 — TenantMembership: The Link Table**

A TenantMembership row says 'User X belongs to Tenant Y with role Z'. This is better than adding advisor\_id to the User model because one advisor could theoretically belong to multiple firms, and roles are explicit.

`  `**TenantMembership**

|# app/models/tenant.py  (continued)<br> <br>class TenantMembership(Base):<br>`    `"""<br>`    `Links a User to a Tenant with a role.<br>`    `Roles: 'advisor' (the tenant owner/admin) | 'client' (end user)<br>`    `"""<br>`    `\_\_tablename\_\_ = "tenant\_memberships"<br> <br>`    `id         = Column(Integer, primary\_key=True)<br>`    `tenant\_id  = Column(UUID(as\_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'),<br>`                         `nullable=False, index=True)<br>`    `user\_id    = Column(UUID(as\_uuid=True), ForeignKey('users.id', ondelete='CASCADE'),<br>`                         `nullable=False, index=True)<br>`    `role       = Column(String(32), nullable=False)   # 'advisor' | 'client'<br>`    `is\_active  = Column(Boolean, default=True)<br>`    `invited\_by = Column(UUID(as\_uuid=True), ForeignKey('users.id'), nullable=True)<br>`    `joined\_at  = Column(DateTime(timezone=True), server\_default=func.now())<br> <br>`    `\_\_table\_args\_\_ = (<br>`        `UniqueConstraint('tenant\_id', 'user\_id', name='uq\_tenant\_user'),<br>`    `)<br> <br>`    `tenant = relationship('Tenant', back\_populates='memberships')<br>`    `user   = relationship('User', foreign\_keys=[user\_id], back\_populates='memberships')|
| :- |


**Step 3 — Add tenant\_id to Owned Resources**

Every row that belongs to a client must carry a tenant\_id. This enables you to filter by tenant in every query. The change to Portfolio is minimal — just add one column and one FK.

`  `**Modified Portfolio model**

|# app/models/portfolio.py  — MODIFIED (minimal change)<br> <br>class Portfolio(Base):<br>`    `\_\_tablename\_\_ = "portfolios"<br> <br>`    `id        = Column(Integer, primary\_key=True, index=True)<br>`    `user\_id   = Column(UUID(as\_uuid=True), ForeignKey('users.id', ondelete='CASCADE'),<br>`                        `nullable=False)<br> <br>`    `# ── NEW: tenant scope ──────────────────────────────────────────────────<br>`    `tenant\_id = Column(UUID(as\_uuid=True), ForeignKey('tenants.id', ondelete='SET NULL'),<br>`                        `nullable=True, index=True)   # null = direct B2C user (no advisor)<br>`    `# ──────────────────────────────────────────────────────────────────────<br> <br>`    `name        = Column(String(128), nullable=False)<br>`    `description = Column(String(512), nullable=True)<br>`    `created\_at  = Column(DateTime, default=datetime.utcnow)<br>`    `updated\_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)<br> <br>`    `owner  = relationship('User',   back\_populates='portfolios')<br>`    `tenant = relationship('Tenant', back\_populates='portfolios')  # NEW<br>`    `items  = relationship('PortfolioItem', back\_populates='portfolio',<br>`                           `cascade='all, delete-orphan')<br> <br># Apply the same pattern to WatchlistItem and Alert:<br># Add:  tenant\_id = Column(UUID, ForeignKey('tenants.id'), nullable=True, index=True)|
| :- |


**Step 4 — User Model: Add Membership Relationship**

Add one line to the existing User model. This is non-breaking — it just adds a relationship.

`  `**user.py addition**

|# app/models/user.py  — ADD THESE TWO LINES to the User class<br> <br># In relationships section:<br>memberships = relationship('TenantMembership', foreign\_keys='TenantMembership.user\_id',<br>`                            `back\_populates='user', cascade='all, delete-orphan')<br> <br># Optional: convenience property to get active tenant<br>@property<br>def active\_tenant\_id(self):<br>`    `active = next((m.tenant\_id for m in self.memberships if m.is\_active), None)<br>`    `return active|
| :- |



**Part 3 — Data Isolation: RLS vs Application Filtering**

**Recommendation: Application-Level Filtering with a TenantContext**

PostgreSQL Row-Level Security (RLS) is powerful but has a critical flaw for your stack: SQLAlchemy's async engine does not easily support setting session-level variables (like SET app.current\_tenant\_id = ...) that RLS policies depend on. Application-level filtering is more practical here.

|**DECISION: Use application-level filtering via a TenantContext dependency injected into every FastAPI endpoint. Every database query that touches client-owned data MUST include a .where(Model.tenant\_id == ctx.tenant\_id) filter. This is enforced by convention and code review, not by the DB engine.**|
| :- |


**The TenantContext Pattern — Core Building Block**

This is the most important pattern in the entire pivot. Every endpoint that handles tenant-scoped data receives a TenantContext object that proves the caller's identity and tenant membership.

`  `**app/core/tenant\_context.py**

|# app/core/tenant\_context.py  — NEW FILE<br> <br>from dataclasses import dataclass<br>from uuid import UUID<br>from typing import Literal, Optional<br> <br>@dataclass(frozen=True)<br>class TenantContext:<br>`    `"""<br>`    `Immutable context injected into every tenant-scoped endpoint.<br>`    `Created by FastAPI dependencies — never constructed manually in service code.<br>`    `"""<br>`    `user\_id:   UUID<br>`    `tenant\_id: UUID<br>`    `role:      Literal['advisor', 'client']<br>`    `is\_platform\_admin: bool = False<br> <br>`    `def assert\_advisor(self) -> None:<br>`        `if self.role != 'advisor' and not self.is\_platform\_admin:<br>`            `from fastapi import HTTPException<br>`            `raise HTTPException(403, "Advisor role required")<br> <br>`    `def assert\_can\_access\_client(self, client\_user\_id: UUID) -> None:<br>`        `"""Advisor can access any client in their tenant. Client can only access themselves."""<br>`        `if self.is\_platform\_admin:<br>`            `return<br>`        `if self.role == 'advisor':<br>`            `return  # advisor sees all clients in their tenant<br>`        `if str(self.user\_id) != str(client\_user\_id):<br>`            `from fastapi import HTTPException<br>`            `raise HTTPException(403, "Access denied")|
| :- |


**FastAPI Dependency — Injecting TenantContext**

`  `**app/api/deps.py — get\_tenant\_context**

|# app/api/deps.py  — ADD THIS<br> <br>from fastapi import Depends, HTTPException, status<br>from sqlalchemy.ext.asyncio import AsyncSession<br>from sqlalchemy import select<br>from app.core.security import decode\_access\_token<br>from app.models.tenant import TenantMembership<br>from app.core.tenant\_context import TenantContext<br>from app.api.deps import get\_current\_user, get\_db   # existing deps<br> <br>async def get\_tenant\_context(<br>`    `current\_user = Depends(get\_current\_user),<br>`    `db: AsyncSession = Depends(get\_db),<br>) -> TenantContext:<br>`    `"""<br>`    `Resolves the caller's active tenant membership.<br>`    `Injected into all tenant-scoped endpoints.<br>`    `"""<br>`    `if current\_user.is\_admin:<br>`        `# Platform admins can pass ?tenant\_id=... as a query param to act on behalf<br>`        `return TenantContext(user\_id=current\_user.id, tenant\_id=None,<br>`                             `role='advisor', is\_platform\_admin=True)<br> <br>`    `result = await db.execute(<br>`        `select(TenantMembership).where(<br>`            `TenantMembership.user\_id == current\_user.id,<br>`            `TenantMembership.is\_active == True,<br>`        `).limit(1)  # use most recent active membership<br>`    `)<br>`    `membership = result.scalar\_one\_or\_none()<br>`    `if not membership:<br>`        `# No tenant membership = legacy direct B2C user — allow with null tenant\_id<br>`        `return TenantContext(user\_id=current\_user.id, tenant\_id=None,<br>`                             `role='client', is\_platform\_admin=False)<br> <br>`    `return TenantContext(<br>`        `user\_id=current\_user.id,<br>`        `tenant\_id=membership.tenant\_id,<br>`        `role=membership.role,<br>`        `is\_platform\_admin=False,<br>`    `)|
| :- |


**Using TenantContext in an Endpoint**

Here's how a portfolio endpoint uses TenantContext. The advisor sees all clients' portfolios in their tenant. A client only sees their own.

`  `**Endpoint using TenantContext**

|# app/api/v1/endpoints/portfolio.py  — MODIFIED<br> <br>@router.get('/portfolios')<br>async def list\_portfolios(<br>`    `ctx: TenantContext = Depends(get\_tenant\_context),<br>`    `db: AsyncSession = Depends(get\_db),<br>):<br>`    `stmt = select(Portfolio)<br> <br>`    `if ctx.is\_platform\_admin:<br>`        `pass  # platform admin sees everything (for support/debugging)<br>`    `elif ctx.role == 'advisor':<br>`        `# Advisor sees ALL portfolios belonging to clients in their tenant<br>`        `stmt = stmt.where(Portfolio.tenant\_id == ctx.tenant\_id)<br>`    `else:<br>`        `# Client sees only THEIR OWN portfolios<br>`        `stmt = stmt.where(Portfolio.user\_id == ctx.user\_id)<br> <br>`    `result = await db.execute(stmt)<br>`    `return result.scalars().all()<br> <br> <br>@router.get('/portfolios/{portfolio\_id}')<br>async def get\_portfolio(<br>`    `portfolio\_id: int,<br>`    `ctx: TenantContext = Depends(get\_tenant\_context),<br>`    `db: AsyncSession = Depends(get\_db),<br>):<br>`    `result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio\_id))<br>`    `portfolio = result.scalar\_one\_or\_none()<br>`    `if not portfolio:<br>`        `raise HTTPException(404)<br> <br>`    `# The key isolation check:<br>`    `ctx.assert\_can\_access\_client(portfolio.user\_id)<br>`    `if not ctx.is\_platform\_admin and portfolio.tenant\_id != ctx.tenant\_id:<br>`        `raise HTTPException(403, 'Cross-tenant access denied')<br> <br>`    `return portfolio|
| :- |


**PostgreSQL Index Strategy**

Add composite indexes on (tenant\_id, user\_id) for all owned tables. This is critical for performance — without it, every advisor query does a full table scan.

`  `**Composite index pattern**

|# In each model's \_\_table\_args\_\_:<br>from sqlalchemy import Index<br> <br>\_\_table\_args\_\_ = (<br>`    `Index('ix\_portfolios\_tenant\_user', 'tenant\_id', 'user\_id'),<br>`    `UniqueConstraint(...),   # existing constraints<br>)<br> <br># And in the Alembic migration:<br># op.create\_index('ix\_portfolios\_tenant\_user', 'portfolios', ['tenant\_id', 'user\_id'])<br># op.create\_index('ix\_watchlist\_tenant\_user',  'watchlist\_items', ['tenant\_id', 'user\_id'])<br># op.create\_index('ix\_alerts\_tenant\_user',     'alerts', ['tenant\_id', 'user\_id'])|
| :- |



**Part 4 — AI Narrator White-Labeling: Tone per Tenant**

**The Pattern: Prompt Templates with Tenant-Injected Variables**

The core idea is that the AI service logic stays the same — it collects data, builds a context dict, calls the Claude API. What changes is the system prompt, which is rendered from a template using per-tenant configuration stored in the tenants.ai\_narrator\_config JSON column.

`  `**ai\_narrator\_service.py — Config + Prompt Builder**

|# app/services/ai\_narrator\_service.py  — NEW FILE<br> <br>from dataclasses import dataclass, field<br>from typing import Optional<br>import httpx, json, logging<br> <br>logger = logging.getLogger(\_\_name\_\_)<br> <br>@dataclass<br>class NarratorConfig:<br>`    `"""<br>`    `Per-tenant AI Narrator configuration.<br>`    `Stored as JSON in tenants.ai\_narrator\_config.<br>`    `Defaults produce the same output as the original direct-to-consumer version.<br>`    `"""<br>`    `tone: str = 'educational'         # 'educational' | 'professional' | 'concise' | 'detailed'<br>`    `persona: str = 'market analyst'   # e.g. 'senior portfolio strategist'<br>`    `brand\_name: str = 'Fin-Eye'       # inserted into disclaimer line<br>`    `advisor\_name: str = 'your advisor' # 'Smith Financial Advisory'<br>`    `forbidden\_topics: list = field(default\_factory=list)  # ['crypto', 'options']<br>`    `max\_words: int = 350<br>`    `focus\_areas: list = field(default\_factory=list)  # ['macro', 'tech'] — empty = all<br>`    `custom\_footnote: str = ''         # Extra legal text the advisor wants at the bottom<br> <br> <br>SYSTEM\_PROMPT\_TEMPLATE = '''<br>You are a {persona} writing a {tone} daily market briefing for clients of {advisor\_name},<br>powered by {brand\_name}'s market intelligence engine.<br> <br>TONE GUIDELINES:<br>- educational: Explain every term. Use analogies. Assume no financial background.<br>- professional: Clear, precise, institutional-grade. Minimal jargon but assume literacy.<br>- concise: Maximum 150 words. Bullet points only. No preamble.<br>- detailed: Comprehensive. 400+ words. Include methodology notes.<br> <br>ABSOLUTE RULES:<br>1\. NEVER say 'you should buy', 'sell', or recommend any action.<br>2\. ALWAYS end with: 'This briefing is market intelligence data provided by {brand\_name}.<br>`   `Speak with {advisor\_name} for advice specific to your situation.'<br>{forbidden\_block}<br>3\. Maximum {max\_words} words.<br>{focus\_block}<br>{custom\_footnote}<br>'''<br> <br> <br>def build\_system\_prompt(cfg: NarratorConfig) -> str:<br>`    `forbidden\_block = ''<br>`    `if cfg.forbidden\_topics:<br>`        `topics = ', '.join(cfg.forbidden\_topics)<br>`        `forbidden\_block = f'3. Do NOT mention or analyse: {topics}.'<br> <br>`    `focus\_block = ''<br>`    `if cfg.focus\_areas:<br>`        `focus\_block = f'Focus heavily on: {', '.join(cfg.focus\_areas)}.'<br> <br>`    `return SYSTEM\_PROMPT\_TEMPLATE.format(<br>`        `persona=cfg.persona, tone=cfg.tone,<br>`        `brand\_name=cfg.brand\_name, advisor\_name=cfg.advisor\_name,<br>`        `forbidden\_block=forbidden\_block, focus\_block=focus\_block,<br>`        `max\_words=cfg.max\_words, custom\_footnote=cfg.custom\_footnote,<br>`    `)|
| :- |


`  `**Core generate function + endpoint usage**

|# ai\_narrator\_service.py  (continued) — The core generate function<br> <br>async def generate\_daily\_briefing(<br>`    `market\_context: dict,<br>`    `narrator\_config: Optional[NarratorConfig] = None,<br>) -> str:<br>`    `"""<br>`    `market\_context is the structured data dict from existing Fin-Eye pipelines:<br>`      `{ 'macro': {...}, 'sentiment': {...}, 'sectors': [...], 'events': [...] }<br> <br>`    `narrator\_config is None for direct B2C users (uses defaults).<br>`    `Pass a tenant's NarratorConfig for white-labeled output.<br>`    `"""<br>`    `cfg = narrator\_config or NarratorConfig()<br>`    `system\_prompt = build\_system\_prompt(cfg)<br> <br>`    `user\_message = f'''<br>`    `Generate a daily briefing using this structured market data:<br>`    `{json.dumps(market\_context, indent=2)}<br>`    `'''<br> <br>`    `async with httpx.AsyncClient(timeout=30.0) as client:<br>`        `resp = await client.post(<br>`            `'https://api.anthropic.com/v1/messages',<br>`            `headers={'Content-Type': 'application/json'},<br>`            `json={<br>`                `'model': 'claude-sonnet-4-20250514',<br>`                `'max\_tokens': 800,<br>`                `'system': system\_prompt,<br>`                `'messages': [{'role': 'user', 'content': user\_message}],<br>`            `}<br>`        `)<br>`        `resp.raise\_for\_status()<br>`        `data = resp.json()<br>`        `return data['content'][0]['text']<br> <br> <br># In your endpoint — get config from tenant:<br>async def get\_daily\_briefing\_endpoint(<br>`    `ctx: TenantContext = Depends(get\_tenant\_context),<br>`    `db: AsyncSession = Depends(get\_db),<br>):<br>`    `tenant = await db.get(Tenant, ctx.tenant\_id) if ctx.tenant\_id else None<br>`    `cfg = None<br>`    `if tenant and tenant.ai\_narrator\_config:<br>`        `cfg = NarratorConfig(\*\*tenant.ai\_narrator\_config)<br> <br>`    `market\_ctx = await build\_market\_context(ctx.user\_id, db)  # existing function<br>`    `briefing = await generate\_daily\_briefing(market\_ctx, cfg)<br>`    `return {'briefing': briefing, 'generated\_at': datetime.utcnow().isoformat()}|
| :- |


**Advisor API to Update Their Tone Configuration**

`  `**Advisor self-service tone config endpoint**

|# app/api/v1/endpoints/tenant\_config.py  — NEW ENDPOINT<br> <br>from pydantic import BaseModel<br>from typing import Optional, List<br> <br>class NarratorConfigUpdate(BaseModel):<br>`    `tone: Optional[str] = None<br>`    `persona: Optional[str] = None<br>`    `forbidden\_topics: Optional[List[str]] = None<br>`    `focus\_areas: Optional[List[str]] = None<br>`    `max\_words: Optional[int] = None<br>`    `custom\_footnote: Optional[str] = None<br> <br>@router.patch('/tenant/narrator-config')<br>async def update\_narrator\_config(<br>`    `update: NarratorConfigUpdate,<br>`    `ctx: TenantContext = Depends(get\_tenant\_context),<br>`    `db: AsyncSession = Depends(get\_db),<br>):<br>`    `ctx.assert\_advisor()  # only advisors can change their tenant config<br>`    `tenant = await db.get(Tenant, ctx.tenant\_id)<br> <br>`    `current = tenant.ai\_narrator\_config or {}<br>`    `patch = update.model\_dump(exclude\_none=True)<br>`    `tenant.ai\_narrator\_config = {\*\*current, \*\*patch}<br> <br>`    `await db.commit()<br>`    `return {'status': 'updated', 'config': tenant.ai\_narrator\_config}|
| :- |



**Part 5 — GAS Weight Engine: Advisor-Adjustable Scoring**

**The Pattern: Inject a WeightProfile into compute\_macro\_score()**

The existing compute\_macro\_score() in macro\_scoring.py uses hardcoded weights. The change is elegant: extract all weights into a GASWeightProfile dataclass, pass it as a parameter, and persist profiles per tenant. The function signature changes but the internal logic does not.

`  `**app/models/gas\_weight\_profile.py**

|# app/models/gas\_weight\_profile.py  — NEW FILE<br> <br>import uuid<br>from sqlalchemy import Column, String, Float, ForeignKey, Boolean<br>from sqlalchemy.dialects.postgresql import UUID<br>from sqlalchemy.orm import relationship<br>from app.db.database import Base<br> <br>class GASWeightProfile(Base):<br>`    `"""<br>`    `Per-tenant GAS weight configuration.<br>`    `A tenant can have multiple profiles (e.g. 'Conservative' vs 'Growth').<br>`    `The active profile is referenced by tenants.gas\_weight\_profile\_id.<br>`    `"""<br>`    `\_\_tablename\_\_ = "gas\_weight\_profiles"<br> <br>`    `id        = Column(UUID(as\_uuid=True), primary\_key=True, default=uuid.uuid4)<br>`    `tenant\_id = Column(UUID(as\_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'),<br>`                        `nullable=True)   # null = platform default profile<br>`    `name      = Column(String(128), nullable=False)  # 'Macro-Focused', 'Tech Momentum'<br>`    `is\_default = Column(Boolean, default=False)<br> <br>`    `# Layer weights — must sum to 1.0 (validated in Pydantic schema)<br>`    `weight\_technical = Column(Float, default=0.40)   # 40% default<br>`    `weight\_macro     = Column(Float, default=0.30)   # 30% default<br>`    `weight\_sentiment = Column(Float, default=0.30)   # 30% default<br> <br>`    `# Sub-weights within the macro layer<br>`    `macro\_yield\_curve\_weight    = Column(Float, default=1.0)<br>`    `macro\_inflation\_weight      = Column(Float, default=1.0)<br>`    `macro\_unemployment\_weight   = Column(Float, default=1.0)<br>`    `macro\_vix\_weight            = Column(Float, default=1.0)<br> <br>`    `# Sub-weights within the technical layer<br>`    `tech\_weight\_1h   = Column(Float, default=0.10)<br>`    `tech\_weight\_4h   = Column(Float, default=0.15)<br>`    `tech\_weight\_1d   = Column(Float, default=0.40)<br>`    `tech\_weight\_1w   = Column(Float, default=0.25)<br>`    `tech\_weight\_1mo  = Column(Float, default=0.10)<br> <br>`    `tenant = relationship('Tenant', back\_populates='gas\_profiles')|
| :- |


`  `**GASWeights Pydantic schema with validator**

|# app/schemas/gas\_models.py  — NEW: Pydantic validators<br> <br>from pydantic import BaseModel, model\_validator<br>from typing import Optional<br> <br>class GASWeights(BaseModel):<br>`    `"""Pydantic version of GASWeightProfile — used in service layer."""<br>`    `weight\_technical: float = 0.40<br>`    `weight\_macro:     float = 0.30<br>`    `weight\_sentiment: float = 0.30<br> <br>`    `macro\_yield\_curve\_weight:  float = 1.0<br>`    `macro\_inflation\_weight:    float = 1.0<br>`    `macro\_unemployment\_weight: float = 1.0<br>`    `macro\_vix\_weight:          float = 1.0<br> <br>`    `tech\_weight\_1h:  float = 0.10<br>`    `tech\_weight\_4h:  float = 0.15<br>`    `tech\_weight\_1d:  float = 0.40<br>`    `tech\_weight\_1w:  float = 0.25<br>`    `tech\_weight\_1mo: float = 0.10<br> <br>`    `@model\_validator(mode='after')<br>`    `def validate\_weights\_sum(self) -> 'GASWeights':<br>`        `total = self.weight\_technical + self.weight\_macro + self.weight\_sentiment<br>`        `if abs(total - 1.0) > 0.001:<br>`            `raise ValueError(<br>`                `f'Layer weights must sum to 1.0, got {total:.3f}. '<br>`                `f'Adjust technical ({self.weight\_technical}), macro ({self.weight\_macro}), '<br>`                `f'or sentiment ({self.weight\_sentiment}).'<br>`            `)<br>`        `return self<br> <br>`    `@classmethod<br>`    `def macro\_advisor\_preset(cls) -> 'GASWeights':<br>`        `'''Preset for advisors who prioritise macro signals.'''<br>`        `return cls(weight\_technical=0.20, weight\_macro=0.55, weight\_sentiment=0.25)<br> <br>`    `@classmethod<br>`    `def momentum\_trader\_preset(cls) -> 'GASWeights':<br>`        `'''Preset for technical momentum-focused advisors.'''<br>`        `return cls(weight\_technical=0.60, weight\_macro=0.20, weight\_sentiment=0.20)<br> <br>`    `@classmethod<br>`    `def balanced\_preset(cls) -> 'GASWeights':<br>`        `'''Default balanced weights (existing behaviour).'''<br>`        `return cls()|
| :- |


`  `**compute\_macro\_score modified + GAS aggregation**

|# app/services/macro\_scoring.py  — MODIFIED signature only<br># The internal logic is UNCHANGED. Just add the weights parameter.<br> <br>from app.schemas.gas\_models import GASWeights<br> <br>def compute\_macro\_score(<br>`    `indicators: Indicators,<br>`    `weights: Optional[GASWeights] = None,   # ← NEW optional param<br>) -> MacroScoreDto:<br>`    `w = weights or GASWeights()  # falls back to defaults — backward compatible<br> <br>`    `score = 50.0<br>`    `# ...<br> <br>`    `# Where you previously had hardcoded -20 for yield curve inversion,<br>`    `# multiply by the weight:<br>`    `spread = indicators.get('yield\_spread\_10y\_2y')<br>`    `if spread is not None:<br>`        `if spread < -0.5:<br>`            `\_adj('yield\_curve\_deeply\_inverted', -20.0 \* w.macro\_yield\_curve\_weight)<br>`        `elif spread < 0:<br>`            `\_adj('yield\_curve\_inverted', -12.0 \* w.macro\_yield\_curve\_weight)<br>`        `# ... etc<br> <br>`    `# Same pattern for inflation, unemployment, VIX — each uses its weight multiplier<br>`    `# ...<br> <br>`    `return MacroScoreDto(score=round(score, 1), label=label)<br> <br> <br># app/services/gas\_service.py — final GAS aggregation<br>def compute\_global\_alignment\_score(<br>`    `technical\_score: float,   # 0-100 from technical\_consensus.py<br>`    `macro\_score: float,       # 0-100 from compute\_macro\_score()<br>`    `sentiment\_score: float,   # 0-100 from sentiment\_service.py<br>`    `weights: Optional[GASWeights] = None,<br>) -> float:<br>`    `w = weights or GASWeights()<br>`    `gas = (<br>`        `technical\_score  \* w.weight\_technical +<br>`        `macro\_score      \* w.weight\_macro +<br>`        `sentiment\_score  \* w.weight\_sentiment<br>`    `)<br>`    `return round(max(0.0, min(100.0, gas)), 1)|
| :- |


**Advisor Weight Management Endpoint**

`  `**Weight profile endpoint + usage in GAS compute**

|# POST /tenant/gas-profile — Advisor creates/updates a weight profile<br> <br>class GASProfileCreate(BaseModel):<br>`    `name: str<br>`    `weights: GASWeights<br>`    `set\_as\_active: bool = False<br> <br>@router.post('/tenant/gas-profile')<br>async def create\_gas\_profile(<br>`    `body: GASProfileCreate,<br>`    `ctx: TenantContext = Depends(get\_tenant\_context),<br>`    `db: AsyncSession = Depends(get\_db),<br>):<br>`    `ctx.assert\_advisor()<br> <br>`    `profile = GASWeightProfile(<br>`        `tenant\_id=ctx.tenant\_id,<br>`        `name=body.name,<br>`        `weight\_technical=body.weights.weight\_technical,<br>`        `weight\_macro=body.weights.weight\_macro,<br>`        `weight\_sentiment=body.weights.weight\_sentiment,<br>`        `# ... all other weight fields<br>`    `)<br>`    `db.add(profile)<br>`    `await db.flush()<br> <br>`    `if body.set\_as\_active:<br>`        `tenant = await db.get(Tenant, ctx.tenant\_id)<br>`        `tenant.gas\_weight\_profile\_id = profile.id<br> <br>`    `await db.commit()<br>`    `return profile<br> <br> <br># In the GAS compute endpoint — load weights by tenant:<br>async def get\_gas\_for\_symbol(symbol, ctx, db):<br>`    `weights = None<br>`    `if ctx.tenant\_id:<br>`        `tenant = await db.get(Tenant, ctx.tenant\_id)<br>`        `if tenant.gas\_weight\_profile\_id:<br>`            `profile = await db.get(GASWeightProfile, tenant.gas\_weight\_profile\_id)<br>`            `weights = GASWeights(<br>`                `weight\_technical=profile.weight\_technical,<br>`                `weight\_macro=profile.weight\_macro,<br>`                `weight\_sentiment=profile.weight\_sentiment,<br>`                `# ... map all fields<br>`            `)<br> <br>`    `# Now pass weights into the scoring functions:<br>`    `macro\_score\_dto = compute\_macro\_score(indicators, weights=weights)<br>`    `gas = compute\_global\_alignment\_score(<br>`        `technical\_score, macro\_score\_dto.score, sentiment\_score, weights<br>`    `)<br>`    `return gas|
| :- |



**Part 6 — Compliance Audit Logs**

**What to Log, Why, and How**

Financial advisors operating under regulations (SEC, FINRA, MiFID II, FCA) are required to maintain records of what information was shown to clients and when. Your compliance log is the evidence trail that proves Fin-Eye served data, not advice.

|**The rule: log EVERY time a GAS score, AI narration, backtest result, or macro insight is served to a client. Include: who saw it, when, what values were shown, which AI prompt version was used, and which weight profile was active. This log should be append-only and never deleted.**|
| :- |


`  `**ComplianceAuditLog model**

|# app/models/compliance.py  — NEW FILE<br> <br>import uuid<br>from datetime import datetime<br>from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, JSON, Index<br>from sqlalchemy.dialects.postgresql import UUID<br>from app.db.database import Base<br> <br>class ComplianceAuditLog(Base):<br>`    `"""<br>`    `Append-only audit log. NEVER update or delete rows.<br>`    `Primary interface for advisor compliance reporting.<br>`    `"""<br>`    `\_\_tablename\_\_ = "compliance\_audit\_logs"<br> <br>`    `id         = Column(UUID(as\_uuid=True), primary\_key=True, default=uuid.uuid4)<br>`    `tenant\_id  = Column(UUID(as\_uuid=True), ForeignKey('tenants.id'), nullable=True, index=True)<br>`    `advisor\_id = Column(UUID(as\_uuid=True), ForeignKey('users.id'), nullable=True)<br>`    `client\_id  = Column(UUID(as\_uuid=True), ForeignKey('users.id'), nullable=True, index=True)<br> <br>`    `# What was shown<br>`    `event\_type = Column(String(64), nullable=False, index=True)<br>`    `# event\_type values:<br>`    `# 'gas\_score\_viewed'     — client/advisor viewed GAS dashboard<br>`    `# 'narration\_generated'  — AI narration was generated and shown<br>`    `# 'backtest\_viewed'      — backtest results were displayed<br>`    `# 'macro\_dashboard\_viewed' — macro indicators were shown<br>`    `# 'alert\_triggered'      — an alert fired and was delivered<br>`    `# 'report\_generated'     — PDF/CSV report was downloaded<br> <br>`    `symbol       = Column(String(20), nullable=True)       # ticker if applicable<br> <br>`    `# Snapshot of what was shown — stored as JSON for flexibility<br>`    `payload = Column(JSON, nullable=False)<br>`    `# For gas\_score\_viewed:    {'gas': 67.3, 'regime': 'Risk-On', 'weights': {...}}<br>`    `# For narration\_generated: {'word\_count': 342, 'tone': 'educational',<br>`    `#                           'prompt\_version': 'v2.1', 'model': 'claude-sonnet...'}<br>`    `# For backtest\_viewed:     {'strategy': 'momentum', 'sharpe': 1.2, 'period': '5y'}<br> <br>`    `# Request metadata (for debugging + compliance)<br>`    `ip\_address    = Column(String(45), nullable=True)     # IPv4 or IPv6<br>`    `user\_agent    = Column(String(256), nullable=True)<br>`    `session\_id    = Column(String(128), nullable=True)<br>`    `request\_id    = Column(String(64), nullable=True)     # FastAPI request ID<br> <br>`    `# Immutable timestamp<br>`    `created\_at = Column(DateTime(timezone=True),<br>`                         `default=datetime.utcnow, nullable=False, index=True)<br> <br>`    `\_\_table\_args\_\_ = (<br>`        `Index('ix\_audit\_tenant\_client\_event', 'tenant\_id', 'client\_id', 'event\_type'),<br>`        `Index('ix\_audit\_tenant\_created',      'tenant\_id', 'created\_at'),<br>`    `)|
| :- |


`  `**compliance\_service.py**

|# app/services/compliance\_service.py  — NEW FILE<br> <br>import logging<br>from datetime import datetime<br>from typing import Optional<br>from uuid import UUID<br>from fastapi import Request<br>from sqlalchemy.ext.asyncio import AsyncSession<br>from app.models.compliance import ComplianceAuditLog<br>from app.core.tenant\_context import TenantContext<br> <br>logger = logging.getLogger(\_\_name\_\_)<br> <br>async def log\_event(<br>`    `db: AsyncSession,<br>`    `ctx: TenantContext,<br>`    `event\_type: str,<br>`    `payload: dict,<br>`    `symbol: Optional[str] = None,<br>`    `client\_id: Optional[UUID] = None,<br>`    `request: Optional[Request] = None,<br>) -> None:<br>`    `"""<br>`    `Fire-and-forget compliance log writer.<br>`    `Call this after every data-serving event. Never raises — log failures<br>`    `are caught and logged as errors, never allowed to break the main request.<br>`    `"""<br>`    `try:<br>`        `log\_entry = ComplianceAuditLog(<br>`            `tenant\_id   = ctx.tenant\_id,<br>`            `advisor\_id  = ctx.user\_id if ctx.role == 'advisor' else None,<br>`            `client\_id   = client\_id or (ctx.user\_id if ctx.role == 'client' else None),<br>`            `event\_type  = event\_type,<br>`            `symbol      = symbol,<br>`            `payload     = payload,<br>`            `ip\_address  = request.client.host if request else None,<br>`            `user\_agent  = request.headers.get('user-agent') if request else None,<br>`            `session\_id  = request.headers.get('x-session-id') if request else None,<br>`            `request\_id  = request.headers.get('x-request-id') if request else None,<br>`        `)<br>`        `db.add(log\_entry)<br>`        `await db.flush()   # don't commit — the caller's transaction handles that<br>`    `except Exception as exc:<br>`        `logger.error('Compliance log write failed: %s', exc, exc\_info=True)<br>`        `# Intentionally do NOT re-raise — a logging failure must not fail a client request<br> <br> <br># Usage in a GAS endpoint:<br># await log\_event(db, ctx, 'gas\_score\_viewed',<br>#     payload={'gas': 67.3, 'regime': regime, 'weights': weights.model\_dump()},<br>#     symbol='TSLA', request=request)|
| :- |


`  `**Compliance report endpoints**

|# app/api/v1/endpoints/compliance.py  — Advisor audit report endpoint<br> <br>from datetime import date<br>from sqlalchemy import select, and\_<br> <br>@router.get('/compliance/audit-log')<br>async def get\_audit\_log(<br>`    `start\_date: date,<br>`    `end\_date: date,<br>`    `client\_id: Optional[UUID] = None,<br>`    `event\_type: Optional[str] = None,<br>`    `ctx: TenantContext = Depends(get\_tenant\_context),<br>`    `db: AsyncSession = Depends(get\_db),<br>):<br>`    `ctx.assert\_advisor()<br> <br>`    `filters = [<br>`        `ComplianceAuditLog.tenant\_id == ctx.tenant\_id,  # ALWAYS filter by tenant<br>`        `ComplianceAuditLog.created\_at >= start\_date,<br>`        `ComplianceAuditLog.created\_at <= end\_date,<br>`    `]<br>`    `if client\_id:<br>`        `filters.append(ComplianceAuditLog.client\_id == client\_id)<br>`    `if event\_type:<br>`        `filters.append(ComplianceAuditLog.event\_type == event\_type)<br> <br>`    `result = await db.execute(<br>`        `select(ComplianceAuditLog).where(and\_(\*filters))<br>        .order\_by(ComplianceAuditLog.created\_at.desc())<br>        .limit(1000)<br>`    `)<br>`    `logs = result.scalars().all()<br>`    `return {'count': len(logs), 'logs': logs}<br> <br> <br># CSV/PDF export endpoint for regulatory submission:<br>@router.get('/compliance/audit-log/export')<br>async def export\_audit\_log(<br>`    `start\_date: date, end\_date: date,<br>`    `format: Literal['csv', 'json'] = 'csv',<br>`    `ctx: TenantContext = Depends(get\_tenant\_context),<br>`    `db: AsyncSession = Depends(get\_db),<br>):<br>`    `ctx.assert\_advisor()<br>`    `# ... fetch logs, stream as CSV or JSON<br>`    `# Use Python csv module or openpyxl for Excel<br>`    `pass|
| :- |



**Part 7 — Auth Changes: JWT Claims & Tenant-Aware Login**

**Extend the JWT Payload to Include Tenant Info**

The cleanest approach is to embed tenant\_id and role in the JWT at login time. This avoids a DB lookup on every request while still being secure.

`  `**JWT with tenant claims**

|# app/core/security.py  — MODIFIED<br> <br>from typing import Optional<br>from uuid import UUID<br> <br>def create\_access\_token(<br>`    `user\_id: UUID,<br>`    `tenant\_id: Optional[UUID] = None,    # ← NEW<br>`    `role: Optional[str] = None,           # ← NEW: 'advisor' | 'client' | None (B2C)<br>`    `is\_admin: bool = False,<br>`    `expires\_delta: Optional[timedelta] = None,<br>) -> str:<br>`    `data = {<br>`        `'sub': str(user\_id),<br>`        `'tenant\_id': str(tenant\_id) if tenant\_id else None,   # NEW<br>`        `'role': role,                                           # NEW<br>`        `'is\_admin': is\_admin,<br>`        `'exp': ...<br>`    `}<br>`    `return jwt.encode(data, settings.jwt\_secret, algorithm='HS256')<br> <br> <br># In the login endpoint — find membership and put it in the token:<br>async def login(<br>`    `credentials: OAuth2PasswordRequestForm = Depends(),<br>`    `db: AsyncSession = Depends(get\_db),<br>):<br>`    `user = await authenticate\_user(db, credentials.username, credentials.password)<br>`    `if not user: raise HTTPException(401)<br> <br>`    `# Find active membership<br>`    `result = await db.execute(select(TenantMembership).where(<br>`        `TenantMembership.user\_id == user.id, TenantMembership.is\_active == True<br>`    `).limit(1))<br>`    `membership = result.scalar\_one\_or\_none()<br> <br>`    `token = create\_access\_token(<br>`        `user\_id=user.id,<br>`        `tenant\_id=membership.tenant\_id if membership else None,<br>`        `role=membership.role if membership else None,<br>`        `is\_admin=user.is\_admin,<br>`    `)<br>`    `return {'access\_token': token, 'token\_type': 'bearer'}|
| :- |


**Updated get\_tenant\_context — Fast Path from JWT**

`  `**Optimised TenantContext with JWT fast path**

|# app/api/deps.py  — OPTIMISED get\_tenant\_context<br># No DB lookup if JWT already has tenant\_id and role<br> <br>async def get\_tenant\_context(<br>`    `token\_data = Depends(decode\_token),  # returns the JWT payload dict<br>`    `db: AsyncSession = Depends(get\_db),<br>) -> TenantContext:<br> <br>`    `if token\_data.get('tenant\_id') and token\_data.get('role'):<br>`        `# Fast path: JWT has everything we need — no DB query<br>`        `return TenantContext(<br>`            `user\_id=UUID(token\_data['sub']),<br>`            `tenant\_id=UUID(token\_data['tenant\_id']),<br>`            `role=token\_data['role'],<br>`            `is\_platform\_admin=token\_data.get('is\_admin', False),<br>`        `)<br> <br>`    `# Slow path: B2C user or JWT without tenant claim — check DB<br>`    `# (same logic as before...)<br>`    `return TenantContext(<br>`        `user\_id=UUID(token\_data['sub']),<br>`        `tenant\_id=None, role='client', is\_platform\_admin=False,<br>`    `)|
| :- |



**Part 8 — Migration Strategy: Zero Breaking Changes**

**The key: tenant\_id is nullable. Direct B2C users keep working with null tenant\_id.**

The entire pivot is non-breaking because tenant\_id is nullable. Every existing user, portfolio, watchlist, and alert continues to work exactly as before. The B2B2C feature is opt-in — it activates only when a TenantMembership row exists.

`  `**Alembic migration**

|# alembic migration — add\_tenant\_tables.py<br> <br>def upgrade() -> None:<br>`    `# 1. Create tenants table<br>`    `op.create\_table('tenants',<br>`        `sa.Column('id', postgresql.UUID(as\_uuid=True), primary\_key=True),<br>`        `sa.Column('name', sa.String(256), nullable=False),<br>`        `sa.Column('slug', sa.String(64), unique=True, nullable=False),<br>`        `sa.Column('brand\_name', sa.String(128), nullable=True),<br>`        `sa.Column('logo\_url', sa.String(512), nullable=True),<br>`        `sa.Column('primary\_color', sa.String(7), nullable=True),<br>`        `sa.Column('disclaimer\_text', sa.Text, nullable=True),<br>`        `sa.Column('subscription\_tier', sa.String(32), default='advisor\_basic'),<br>`        `sa.Column('max\_clients', sa.Integer, default=50),<br>`        `sa.Column('ai\_narrator\_config', postgresql.JSONB, nullable=True),<br>`        `sa.Column('gas\_weight\_profile\_id', postgresql.UUID(as\_uuid=True), nullable=True),<br>`        `sa.Column('created\_at', sa.DateTime(timezone=True), server\_default=sa.func.now()),<br>`        `sa.Column('updated\_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),<br>`    `)<br> <br>`    `# 2. Create tenant\_memberships table<br>`    `op.create\_table('tenant\_memberships', ...)<br> <br>`    `# 3. Create gas\_weight\_profiles table<br>`    `op.create\_table('gas\_weight\_profiles', ...)<br> <br>`    `# 4. Create compliance\_audit\_logs table<br>`    `op.create\_table('compliance\_audit\_logs', ...)<br> <br>`    `# 5. Add nullable tenant\_id to existing tables (NON-BREAKING)<br>`    `op.add\_column('portfolios',     sa.Column('tenant\_id',<br>`        `postgresql.UUID(as\_uuid=True), sa.ForeignKey('tenants.id'),<br>`        `nullable=True))   # ← NULLABLE = backward compatible<br>`    `op.add\_column('watchlist\_items', sa.Column('tenant\_id', ..., nullable=True))<br>`    `op.add\_column('alerts',          sa.Column('tenant\_id', ..., nullable=True))<br> <br>`    `# 6. Add composite indexes<br>`    `op.create\_index('ix\_portfolios\_tenant\_user',<br>`                     `'portfolios', ['tenant\_id', 'user\_id'])<br> <br>def downgrade() -> None:<br>`    `op.drop\_column('portfolios', 'tenant\_id')<br>`    `# ... drop in reverse order<br>`    `op.drop\_table('compliance\_audit\_logs')<br>`    `op.drop\_table('gas\_weight\_profiles')<br>`    `op.drop\_table('tenant\_memberships')<br>`    `op.drop\_table('tenants')|
| :- |


**Rollout Order (No Downtime)**

- **Step 1:** Run the Alembic migration. All existing users keep working — tenant\_id is null for everyone.
- **Step 2:** Deploy the new code. The get\_tenant\_context dependency returns null tenant\_id for all existing users. No behaviour change.
- **Step 3:** Create your first Tenant row (e.g. a test advisory firm) and a TenantMembership for a test user.
- **Step 4:** Test the advisor login flow, GAS weight profiles, and AI narrator config with the test tenant.
- **Step 5:** Build the Advisor onboarding UI: invite clients, set GAS profile, configure AI tone.
- **Step 6:** When satisfied, open to your first real advisor tenant. B2C users continue unaffected.



**Part 9 — Bonus Patterns: Billing, Feature Flags, Rate Limits**

**Tenant-Level Feature Flags**

Use a JSON column on the Tenant model (features: JSONB) to gate premium features per advisor without code changes.

`  `**Feature flag pattern**

|# In Tenant model:<br>features = Column(JSONB, nullable=True, default=dict)<br># Example value: {'ai\_narrator': True, 'advanced\_macro': True, 'custom\_gas\_weights': False}<br> <br># Dependency:<br>async def require\_feature(feature: str, ctx: TenantContext, db: AsyncSession):<br>`    `if ctx.is\_platform\_admin: return  # admins bypass all feature flags<br>`    `if not ctx.tenant\_id: raise HTTPException(402, 'Upgrade to advisor plan')<br>`    `tenant = await db.get(Tenant, ctx.tenant\_id)<br>`    `if not (tenant.features or {}).get(feature):<br>`        `raise HTTPException(402, f'Feature {feature!r} not included in your plan.')<br> <br># In endpoint:<br>@router.post('/tenant/gas-profile')<br>async def create\_gas\_profile(ctx=Depends(get\_tenant\_context), db=Depends(get\_db)):<br>`    `await require\_feature('custom\_gas\_weights', ctx, db)<br>`    `# ...proceed|
| :- |


**Per-Tenant API Rate Limiting**

`  `**Per-tenant rate limiting**

|# Use slowapi or a Redis-based counter keyed by tenant\_id, not IP<br># This prevents one advisor's API-heavy clients from affecting others<br> <br>from fastapi import Request<br>import redis.asyncio as redis<br> <br>async def check\_tenant\_rate\_limit(<br>`    `ctx: TenantContext,<br>`    `cache: redis.Redis,<br>`    `limit: int = 100,     # requests per minute<br>):<br>`    `key = f'rate:{ctx.tenant\_id}:{datetime.utcnow().strftime("%Y%m%d%H%M")}'<br>`    `count = await cache.incr(key)<br>`    `if count == 1:<br>`        `await cache.expire(key, 60)<br>`    `if count > limit:<br>`        `raise HTTPException(429, f'Tenant rate limit exceeded ({limit}/min)')|
| :- |


**The Advisor Onboarding API Sequence**

Here is the complete sequence of API calls to onboard a new advisor tenant from scratch:

|**Step**|**API Call**|**Who Calls**|
| :- | :- | :- |
|**1**|POST /admin/tenants — create Tenant record|Platform admin (you)|
|**2**|POST /admin/tenants/{id}/invite-advisor — create advisor User + TenantMembership (role='advisor')|Platform admin|
|**3**|Advisor logs in → receives JWT with tenant\_id + role='advisor'|Advisor|
|**4**|PATCH /tenant/narrator-config — set tone, persona, brand\_name|Advisor|
|**5**|POST /tenant/gas-profile — create weight profile (e.g. 'Macro-Focused')|Advisor|
|**6**|POST /tenant/invite-client — create client User + TenantMembership (role='client')|Advisor|
|**7**|Client logs in → sees dashboard with advisor's GAS weights + branded AI narrations|Client|




**Quick Reference — Files to Create / Modify**

|**File**|**Create or Modify**|**What Changes**|
| :- | :- | :- |
|app/models/tenant.py|**CREATE**|Tenant + TenantMembership models|
|app/models/gas\_weight\_profile.py|**CREATE**|GASWeightProfile model|
|app/models/compliance.py|**CREATE**|ComplianceAuditLog model|
|app/core/tenant\_context.py|**CREATE**|TenantContext frozen dataclass|
|app/services/ai\_narrator\_service.py|**CREATE**|NarratorConfig + generate\_daily\_briefing()|
|app/services/compliance\_service.py|**CREATE**|log\_event() helper|
|app/schemas/gas\_models.py|**CREATE**|GASWeights Pydantic model with validator|
|app/models/user.py|**MODIFY**|Add memberships relationship (2 lines)|
|app/models/portfolio.py|**MODIFY**|Add nullable tenant\_id column|
|app/models/watchlist.py|**MODIFY**|Add nullable tenant\_id column|
|app/models/alert.py|**MODIFY**|Add nullable tenant\_id column|
|app/core/security.py|**MODIFY**|create\_access\_token() adds tenant\_id + role|
|app/api/deps.py|**MODIFY**|Add get\_tenant\_context() dependency|
|app/services/macro\_scoring.py|**MODIFY**|compute\_macro\_score() adds weights param|
|alembic/versions/add\_tenants.py|**CREATE**|Migration: 4 new tables + 3 new columns|


*End of Document  ·  Fin-Eye B2B2C Architecture Playbook  ·  March 2026*
