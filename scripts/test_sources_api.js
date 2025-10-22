const { Pool } = require('pg');
require('dotenv').config({ path: '.env.local' });

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

async function testSourcesAPI() {
  try {
    // This is the exact query from /api/sources/route.ts
    const result = await pool.query(`
      SELECT DISTINCT website as source
      FROM leads.leads
      WHERE website IS NOT NULL
      ORDER BY website
    `);

    const sources = result.rows.map(row => row.source);

    console.log('Sources returned by API query:');
    console.log(JSON.stringify({ sources }, null, 2));

    console.log('\nTotal sources:', sources.length);
    console.log('\nDoes it include repetitor.az?', sources.includes('repetitor.az'));

    await pool.end();
  } catch (error) {
    console.error('Error:', error);
    await pool.end();
  }
}

testSourcesAPI();
