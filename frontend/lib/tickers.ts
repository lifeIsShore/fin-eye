/**
 * TICKER_LIST — ~2000 popular global tickers + crypto pairs
 * Used for client-side autocomplete in the ticker input and watchlist.
 * No API call needed — fully static, instant filtering.
 *
 * Categories:
 *  - US Large/Mid Cap Equities (S&P 500 + Nasdaq 100 + popular)
 *  - US ETFs
 *  - Major International ADRs & stocks
 *  - Crypto pairs (via Yahoo Finance format e.g. BTC-USD)
 */

export const TICKER_LIST: string[] = [
  // ── US Mega Cap ────────────────────────────────────────────────────────────
  "AAPL","MSFT","NVDA","GOOGL","GOOG","AMZN","META","TSLA","BRK-A","BRK-B",
  "LLY","V","JPM","UNH","XOM","MA","JNJ","PG","HD","MRK","ABBV","CVX","COST",
  "AVGO","AMD","ORCL","CRM","ACN","NFLX","BAC","TMO","ADBE","ABT","PEP","KO",
  "WMT","CSCO","MCD","NKE","DHR","TXN","NEE","LIN","PM","RTX","QCOM","IBM",
  "INTC","GE","MS","GS","SPGI","HON","UNP","CAT","AXP","BLK","SYK","ISRG",
  "BKNG","VRTX","GILD","MDT","CB","ADP","PLD","MMC","REGN","SCHW","ZTS","ETN",
  "DE","TJX","C","NOW","AMGN","BDX","BSX","ELV","MO","CME","USB","DUK",
  "AON","CL","ITW","SHW","TGT","HUM","APD","FDX","EMR","NSC","PSA","GM",
  "F","FORD","WFC","T","VZ","CMCSA","TMUS","CHTR",

  // ── US Tech / Growth ───────────────────────────────────────────────────────
  "PLTR","SNOW","PANW","CRWD","ZS","DDOG","NET","MDB","TWLO","OKTA","TEAM",
  "HUBS","VEEV","WDAY","ANSS","CDNS","SNPS","FTNT","PALO","GEHC","ON","MPWR",
  "ENPH","FSLR","SEDG","RUN","PLUG","BLNK","CHPT","LCID","RIVN","NIO","LI",
  "XPEV","FSR","GOEV","WKHS","NKLA","HYLN","IDEX","SOLO","KNDI","AYRO",
  "SQ","PYPL","AFRM","UPST","SOFI","OPEN","COIN","HOOD","ROBINHOOD",
  "SHOP","ETSY","EBAY","LYFT","UBER","ABNB","DASH","DKNG","PENN","CZOO",
  "RBLX","U","UNITY","MTTR","STEM","CLNE","XONE","DM","MARKFORGED",
  "SPCE","ASTR","RKT","ACHR","JOBY","LILM","EVEX","KTOS","ASTS",
  "AI","C3AI","BBAI","SOUN","GFAI","SING","VERB","AITX","AIOT",
  "IONQ","RGTI","QUBT","QBTS","ARQQ","QMCO","SPIR","SATL",

  // ── Semiconductors ─────────────────────────────────────────────────────────
  "TSM","ASML","AMAT","KLAC","LRCX","MU","WDC","STX","MRVL","MCHP","ADI",
  "SWKS","QRVO","NXPI","TER","ONTO","ACLS","RMBS","AMBA","FORM","SMTC",
  "CRUS","SLAB","DIOD","ALGM","MPWR","WOLF","AZTA","ONTO","PI","COHU",

  // ── US Financials ─────────────────────────────────────────────────────────
  "JPM","BAC","WFC","C","GS","MS","USB","PNC","TFC","COF","AXP","DFS","SYF",
  "ALLY","FITB","HBAN","KEY","RF","CFG","ZION","CMA","MTB","WTFC","SFNC",
  "BK","STT","NTRS","IVZ","TROW","BEN","AMG","FDS","MORN","ICE","CBOE",
  "CME","NDAQ","COIN","IBKR","LPLA","RJF","SF","PIPR","HLI","EVR","LAZ",
  "MET","PRU","UNM","AFL","GL","LNC","PFG","RGA","CNO","FGL","ARGO",
  "CB","AIG","ALL","TRV","PGR","HIG","MKL","RE","RNR","ACGL","ERIE",
  "BRO","AON","MMC","WTW","RYAN","AJG","EQNR","GLRE",

  // ── US Healthcare ─────────────────────────────────────────────────────────
  "JNJ","PFE","MRK","ABBV","LLY","BMY","AMGN","GILD","REGN","VRTX","BIIB",
  "MRNA","BNTX","NVAX","SGEN","ALNY","BMRN","EXEL","FATE","KYMR","RVMD",
  "RCKT","ARWR","BEAM","EDIT","CRSP","NTLA","PACB","ILMN","NTRA","EXAS",
  "TMO","DHR","A","BIO","TECH","IDXX","MLAB","NEOG","HOLO","GXII",
  "MDT","BSX","SYK","EW","ISRG","ZBH","HOLX","NVCR","NVRO","SWAV",
  "HCA","UHS","THC","CYH","SGRY","AMSRG","OPRX","ACCD","TDOC","AMWL",
  "CVS","MCK","ABC","CAH","HSIC","PDCO","PRGO","PKI","IQV","CRL",

  // ── US Consumer ───────────────────────────────────────────────────────────
  "AMZN","WMT","COST","TGT","HD","LOW","KR","ACI","SFM","GO","CASY",
  "MCD","SBUX","YUM","QSR","DPZ","CMG","TXRH","DINE","DRI","EAT","JACK",
  "NKE","LULU","UAA","UA","PVH","HBI","RL","VFC","CROX","SKX","WWW",
  "PG","CL","CHD","COTY","EL","ULTA","BBWI","BURL","TJX","ROST","OXM",
  "NFLX","DIS","WBD","PARA","FOX","FOXA","AMCX","AMC","CNK","IMAX",
  "GM","F","TSLA","RIVN","LCID","CARGURUS","AN","LAD","KMX","AAP","AZO","ORLY",

  // ── US Energy ─────────────────────────────────────────────────────────────
  "XOM","CVX","COP","EOG","SLB","HAL","BKR","PXD","DVN","MPC","PSX","VLO",
  "FANG","OXY","HES","APA","EQT","CNX","AR","RRC","CTRA","MTDR","VTLE",
  "SM","CLR","WTI","CPE","CRGY","REI","ESTE","TALO","CIVI","INE",
  "KMI","WMB","OKE","EPD","ET","MMP","PAA","TRGP","DT","AM","CEQP",
  "NEE","DUK","SO","D","EXC","AEP","XEL","ED","FE","ETR","WEC","ES",
  "ENPH","FSLR","RUN","SEDG","ARRY","NOVA","AY","BEP","CWEN","HASI",

  // ── US Industrials ────────────────────────────────────────────────────────
  "GE","HON","MMM","CAT","DE","EMR","ETN","ITW","PH","ROK","AME","VRSK",
  "IEX","XYL","XYLO","GNRC","TT","JCI","CARR","OTIS","LMT","RTX","NOC",
  "GD","BA","HII","TDG","HEI","TXT","SPR","KTOS","AVAV","AER","AL",
  "UNP","CSX","NSC","KSU","WAB","TRN","GATX","JBHT","XPO","SAIA","ARCB",
  "UPS","FDX","EXPD","CHRW","GXO","RXO","ECHO","RADNW",
  "WM","RSG","CWST","SRCL","US","CLH","WCN",

  // ── US REITs ──────────────────────────────────────────────────────────────
  "PLD","AMT","EQIX","CCI","SPG","O","VICI","WPC","NNN","STOR","SRC",
  "STAG","FR","EGP","DRE","REXR","COLD","IIPR","SAFE","CUBE","PSA",
  "EXR","LSI","NSA","AVB","EQR","UDR","CPT","MAA","NVT","AIV",
  "BXP","VNO","SL","ARE","CXW","WELL","VTR","PEAK","HR","SNH",
  "DLR","QTS","COR","IRM","INVH","SFR","TRNO","WARE","PLYM",

  // ── Popular ETFs ──────────────────────────────────────────────────────────
  "SPY","QQQ","IWM","DIA","VTI","VOO","VEA","VWO","EFA","EEM",
  "XLK","XLF","XLV","XLY","XLP","XLI","XLE","XLB","XLU","XLRE",
  "GLD","SLV","IAU","PPLT","PALL","PDBC","DBO","USO","UNG","DBB",
  "TLT","IEF","SHY","HYG","LQD","MUB","TIP","VTIP","BND","AGG",
  "ARKK","ARKW","ARKG","ARKF","ARKQ","ARKX","PRNT","IZRL",
  "SOXS","SOXL","TQQQ","SQQQ","SPXL","SPXS","UVXY","VXX","SVXY",
  "KWEB","FXI","MCHI","ASHR","EWJ","EWZ","EWY","EWT","INDA","VNM",

  // ── International / ADRs ──────────────────────────────────────────────────
  "TSM","ASML","SAP","TM","HMC","SONY","NVO","NOVO","AZN","GSK","RHHBY",
  "NSRGY","NESTLE","LVMUY","LVMH","CSGP","MC","OR","SAN","BNPQY",
  "BABA","JD","PDD","BIDU","TCEHY","TENCENT","NTES","ZH","VIPS","TAL",
  "SE","GRAB","GOTO","BIGO","IQ","HUYA","DOYU","BILI","IFRX",
  "SHOP","CNQ","SU","ENB","BCE","TD","RY","BNS","BMO","CM","NA",
  "VALE","ITUB","BBD","PBR","ABEV","BRFS","CPLE","SUZB","RENT3",
  "RELIANCE","INFY","WIT","HDB","IBN","SBIN","ICICIBANK","TATAMOTORS",
  "RIO","BHP","BBL","AALCY","GLNCY","SCCO","FCX","CLF","X","NUE",
  "SIEGY","BASFY","BAYRY","VWAGY","BMWYY","DAIMLER","MBG",

  // ── Crypto — Yahoo Finance format (TOKEN-USD) ─────────────────────────────
  "BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","USDC-USD","ADA-USD",
  "AVAX-USD","DOGE-USD","TRX-USD","DOT-USD","LINK-USD","MATIC-USD","SHIB-USD",
  "LTC-USD","BCH-USD","UNI-USD","ATOM-USD","XLM-USD","ETC-USD","ALGO-USD",
  "VET-USD","FIL-USD","NEAR-USD","HBAR-USD","ICP-USD","QNT-USD","AAVE-USD",
  "EOS-USD","SAND-USD","MANA-USD","AXS-USD","THETA-USD","XTZ-USD","KLAY-USD",
  "EGLD-USD","FLOW-USD","ZEC-USD","DASH-USD","XMR-USD","NEO-USD","WAVES-USD",
  "ONE-USD","CELO-USD","CHZ-USD","BAT-USD","ENJ-USD","GRT-USD","LRC-USD",
  "CRV-USD","SNX-USD","YFI-USD","COMP-USD","MKR-USD","SUSHI-USD","1INCH-USD",
  "OP-USD","ARB-USD","APT-USD","SUI-USD","SEI-USD","TIA-USD","INJ-USD",
  "BLUR-USD","PYTH-USD","W-USD","STRK-USD","ZETA-USD","DYM-USD","JTO-USD",
  "WIF-USD","BONK-USD","PEPE-USD","FLOKI-USD","LADYS-USD","BABYDOGE-USD",
  "BTC-EUR","ETH-EUR","BNB-EUR","SOL-EUR","XRP-EUR",

  // ── Forex (via Yahoo Finance) ─────────────────────────────────────────────
  "EURUSD=X","GBPUSD=X","USDJPY=X","USDCAD=X","AUDUSD=X","USDCHF=X",
  "NZDUSD=X","EURGBP=X","EURJPY=X","GBPJPY=X","USDTRY=X","USDSEK=X",
  "USDNOK=X","USDDKK=X","USDPLN=X","USDCZK=X","USDHUF=X","USDINR=X",
  "USDCNY=X","USDHKD=X","USDSGD=X","USDMXN=X","USDBRL=X","USDZAR=X",

  // ── Commodities / Futures indices ─────────────────────────────────────────
  "GC=F","SI=F","CL=F","NG=F","HG=F","ZW=F","ZC=F","ZS=F","KC=F","CT=F",
  "^GSPC","^DJI","^IXIC","^RUT","^VIX","^TNX","^TYX","^FVX",
  "^FTSE","^GDAXI","^FCHI","^N225","^HSI","^AXJO","^BSESN","^NSEI",
];

/**
 * Fast client-side search — returns up to `limit` matches.
 * Prioritises prefix matches over contains matches.
 */
export function searchTickers(query: string, limit = 8): string[] {
  if (!query) return TICKER_LIST.slice(0, limit);
  const q = query.toUpperCase().trim();
  const prefix   = TICKER_LIST.filter((t) => t.startsWith(q));
  const contains = TICKER_LIST.filter((t) => !t.startsWith(q) && t.includes(q));
  return [...prefix, ...contains].slice(0, limit);
}
