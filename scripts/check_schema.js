const { Pool } = require('pg');
require('dotenv').config({ path: '.env.local' });

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

async function checkSchema() {
  try {
    const res = await pool.query(`
      SELECT column_name, data_type, character_maximum_length
      FROM information_schema.columns
      WHERE table_schema = 'leads' AND table_name = 'leads'
      ORDER BY ordinal_position
    `);

    console.log('Columns in leads.leads table:');
    res.rows.forEach(row => {
      console.log(`  ${row.column_name}: ${row.data_type}${row.character_maximum_length ? `(${row.character_maximum_length})` : ''}`);
    });

    // Also check a sample record
    const sample = await pool.query('SELECT * FROM leads.leads LIMIT 1');
    console.log('\nSample record structure:', Object.keys(sample.rows[0] || {}));

    await pool.end();
  } catch (err) {
    console.error('Error:', err.message);
    await pool.end();
  }
}

checkSchema();
