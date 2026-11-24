import { neon } from '@neondatabase/serverless';

export default async (req, context) => {
  const dbUrl = process.env.DATABASE_URL || '';

  try {
    // Faz o parse da URL sem expor a senha
    const parsed = new URL(dbUrl);
    const info = {
      protocol: parsed.protocol,
      user: parsed.username,
      host: parsed.hostname,
      port: parsed.port || 'padrão',
      db: parsed.pathname,
      params: parsed.search
    };

    const sql = neon(dbUrl);
    const rows = await sql`
      SELECT categoria, valor, atualizado_em 
      FROM analytics.metricas_realtime 
      ORDER BY id ASC
    `;

    return new Response(JSON.stringify(rows), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store, no-cache, must-revalidate'
      }
    });
  } catch (error) {
    let urlInfo = 'URL inválida (não passou no new URL())';
    try {
      const p = new URL(dbUrl);
      urlInfo = { host: p.hostname, user: p.username, db: p.pathname, params: p.search };
    } catch (_) {}

    return new Response(JSON.stringify({
      erro: error.message,
      node: process.version,
      url_lida: urlInfo
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};