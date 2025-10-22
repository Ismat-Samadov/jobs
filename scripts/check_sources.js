const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

async function checkSources() {
  try {
    const result = await pool.query(`
      SELECT website, COUNT(*) as count
      FROM leads.leads
      GROUP BY website
      ORDER BY website
    `);

    console.log('Sources in database:');
    console.log('==================');
    result.rows.forEach(row => {
      console.log(`${row.website}: ${row.count} leads`);
    });

    // Also check if there's any data with 'bina' in it
    const binaCheck = await pool.query(`
      SELECT website, COUNT(*) as count
      FROM leads.leads
      WHERE website ILIKE '%bina%'
      GROUP BY website
    `);

    console.log('\nSources containing "bina":');
    console.log('=========================');
    if (binaCheck.rows.length > 0) {
      binaCheck.rows.forEach(row => {
        console.log(`${row.website}: ${row.count} leads`);
      });
    } else {
      console.log('No sources found containing "bina"');
    }

    await pool.end();
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

checkSources();
