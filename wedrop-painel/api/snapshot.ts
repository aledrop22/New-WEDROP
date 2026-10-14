/**
 * Lê categorias, produtos e movimentações do Supabase no servidor (Vercel).
 * A chave de serviço fica só nas variáveis de ambiente da Vercel, nunca no navegador.
 * A leitura é paginada igual ao SupabaseRepository.fetch_snapshot do Streamlit (Drop/wedrop).
 */

const FETCH_PAGE_SIZE = 1000;

type Row = Record<string, unknown>;

interface ApiRequest {
  method?: string;
}

interface ApiResponse {
  status(code: number): ApiResponse;
  json(body: unknown): void;
  setHeader(name: string, value: string): void;
}

async function fetchTable(baseUrl: string, apiKey: string, table: string, orderKey: string): Promise<Row[]> {
  const rows: Row[] = [];
  while (true) {
    const params = new URLSearchParams({
      select: '*',
      order: `${orderKey}.asc`,
      limit: String(FETCH_PAGE_SIZE),
      offset: String(rows.length),
    });
    const response = await fetch(`${baseUrl}/rest/v1/${table}?${params}`, {
      headers: { apikey: apiKey, Authorization: `Bearer ${apiKey}` },
    });
    if (!response.ok) {
      const detail = (await response.text()).slice(0, 300);
      throw new Error(`Supabase não respondeu a leitura de ${table} (HTTP ${response.status}): ${detail}`);
    }
    const page = (await response.json()) as Row[];
    if (page.length === 0) return rows;
    rows.push(...page);
  }
}

export default async function handler(req: ApiRequest, res: ApiResponse) {
  if (req.method && req.method !== 'GET') {
    res.status(405).json({ error: 'Método não permitido.' });
    return;
  }

  const baseUrl = (process.env.SUPABASE_URL || '').trim().replace(/\/+$/, '');
  const apiKey = (process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY || '').trim();
  if (!baseUrl || !apiKey) {
    res.status(500).json({
      error:
        'Supabase não configurado. Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY nas variáveis de ambiente da Vercel.',
    });
    return;
  }

  try {
    const [categories, products, stockEvents] = await Promise.all([
      fetchTable(baseUrl, apiKey, 'wedrop_categories', 'category_url'),
      fetchTable(baseUrl, apiKey, 'wedrop_products', 'product_id'),
      fetchTable(baseUrl, apiKey, 'wedrop_stock_events', 'event_id'),
    ]);
    // Mesmo tempo de vida do cache do Streamlit (5 min): a Vercel reaproveita a resposta nesse intervalo.
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=60');
    res.status(200).json({
      categories,
      products,
      stock_events: stockEvents,
      fetched_at: new Date().toISOString(),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Erro desconhecido ao ler o Supabase.';
    res.status(502).json({ error: message });
  }
}
