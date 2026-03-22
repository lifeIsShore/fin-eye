
// ── Live price ────────────────────────────────────────────────────────────────

const DEFAULT_BASE_URL = "http://localhost:8000";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;

export interface LatestPriceDto {
  symbol: string;
  price:  number | null;
  source: string;
}

export async function fetchLatestPrice(
  symbol: string,
  init?: RequestInit,
): Promise<LatestPriceDto> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/technical/${encodeURIComponent(symbol.toUpperCase())}/price`,
    { ...init, cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to fetch price for ${symbol}: ${res.status}`);
  return res.json() as Promise<LatestPriceDto>;
}
