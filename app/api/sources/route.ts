import { NextResponse } from 'next/server';
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

export async function GET() {
  try {
    // Query distinct website sources from the database
    const result = await pool.query(`
      SELECT DISTINCT website as source
      FROM leads.leads
      WHERE website IS NOT NULL
      ORDER BY website
    `);

    const sources = result.rows.map(row => row.source);

    return NextResponse.json({ sources });
  } catch (error) {
    console.error('Error fetching sources:', error);
    return NextResponse.json(
      { error: 'Failed to fetch sources' },
      { status: 500 }
    );
  }
}
