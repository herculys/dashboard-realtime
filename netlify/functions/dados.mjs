import { neon } from '@neondatabase/serverless';

export default async (req, context) => {
  try {
    const dbUrl = process.env.DATABASE_URL;

    if (!dbUrl) {
      return new Response(JSON.stringify({ erro: 'DATABASE_URL não configurada neste site!' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }

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
    return new Response(JSON.stringify({ 
      erro: error.message,
      detalhe: error.cause ? String(error.cause) : null
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};