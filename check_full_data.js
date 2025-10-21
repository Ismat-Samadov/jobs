/**
 * Script to verify the full_data column is populated correctly
 */
const { Pool } = require('pg');
require('dotenv/config');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL?.includes('localhost') ? false : {
    rejectUnauthorized: false
  }
});

async function checkFullData() {
  try {
    console.log('Checking latest lead with full_data...\n');

    const result = await pool.query(`
      SELECT
        phone_number,
        website,
        source,
        created_at,
        full_data
      FROM leads.leads
      WHERE full_data IS NOT NULL
      ORDER BY created_at DESC
      LIMIT 1
    `);

    if (result.rows.length === 0) {
      console.log('No leads with full_data found in database.');
      return;
    }

    const lead = result.rows[0];

    console.log('='.repeat(70));
    console.log('LATEST LEAD WITH FULL_DATA');
    console.log('='.repeat(70));
    console.log(`Phone Number: ${lead.phone_number}`);
    console.log(`Website: ${lead.website}`);
    console.log(`Source: ${lead.source}`);
    console.log(`Created At: ${lead.created_at}`);
    console.log('\nFull Data JSON:');
    console.log('='.repeat(70));
    console.log(JSON.stringify(lead.full_data, null, 2));
    console.log('='.repeat(70));

    // Validate the structure
    const data = lead.full_data;
    console.log('\n✓ Structure Validation:');
    console.log(`  - listing_type: ${data.listing_type || 'MISSING'}`);
    console.log(`  - title: ${data.title ? 'Present' : 'MISSING'}`);
    console.log(`  - price: ${data.price ? JSON.stringify(data.price) : 'MISSING'}`);
    console.log(`  - property_details: ${Object.keys(data.property_details || {}).length} fields`);
    console.log(`  - description: ${data.description ? 'Present (' + data.description.length + ' chars)' : 'MISSING'}`);
    console.log(`  - seller: ${data.seller ? JSON.stringify(data.seller) : 'MISSING'}`);
    console.log(`  - listing_info: ${data.listing_info ? JSON.stringify(data.listing_info) : 'MISSING'}`);
    console.log(`  - images: ${data.images ? data.images.length + ' images' : 'MISSING'}`);

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkFullData();
