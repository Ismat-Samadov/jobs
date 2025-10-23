const { Pool } = require('pg');

// Load .env.local if it exists
try {
  require('dotenv').config({ path: '.env.local' });
} catch (e) {
  // dotenv not installed, environment variable should be set
}

// Parse DATABASE_URL and handle SSL based on the URL parameter
const dbUrl = process.env.DATABASE_URL;
let poolConfig = { connectionString: dbUrl };

// If sslmode is in the URL, let pg handle it automatically
// Otherwise, set SSL config manually
if (!dbUrl?.includes('sslmode')) {
  poolConfig.ssl = dbUrl?.includes('localhost') ? false : { rejectUnauthorized: false };
}

const pool = new Pool(poolConfig);

async function analyzeLeadsTable() {
  const client = await pool.connect();
  try {
    // Get table schema
    console.log('=== TABLE SCHEMA ===');
    const schema = await client.query(`
      SELECT column_name, data_type, character_maximum_length, is_nullable
      FROM information_schema.columns
      WHERE table_schema = 'leads' AND table_name = 'leads'
      ORDER BY ordinal_position
    `);
    console.table(schema.rows);

    // Get indexes
    console.log('\n=== INDEXES ===');
    const indexes = await client.query(`
      SELECT indexname, indexdef
      FROM pg_indexes
      WHERE schemaname = 'leads' AND tablename = 'leads'
    `);
    console.table(indexes.rows);

    // Get total count
    console.log('\n=== DATA STATISTICS ===');
    const count = await client.query('SELECT COUNT(*) as total FROM leads.leads');
    console.log('Total leads:', count.rows[0].total);

    // Get count by website
    const byWebsite = await client.query(`
      SELECT website, COUNT(*) as count
      FROM leads.leads
      GROUP BY website
      ORDER BY count DESC
    `);
    console.log('\nLeads by website:');
    console.table(byWebsite.rows);

    // Get recent leads stats
    console.log('\n=== DATE RANGE ===');
    const dateRange = await client.query(`
      SELECT
        MIN(created_at) as earliest,
        MAX(created_at) as latest,
        COUNT(*) as total
      FROM leads.leads
    `);
    console.table(dateRange.rows);

    // Check if full_data column exists
    console.log('\n=== CHECKING FULL_DATA COLUMN ===');
    const hasFullData = await client.query(`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_schema = 'leads'
        AND table_name = 'leads'
        AND column_name = 'full_data'
    `);
    console.log('full_data column exists:', hasFullData.rows.length > 0);

    // Sample leads
    console.log('\n=== SAMPLE LEADS (5 most recent) ===');
    const sample = await client.query(`
      SELECT id, phone_number, website,
             LEFT(source, 60) as source_preview,
             created_at
      FROM leads.leads
      ORDER BY created_at DESC
      LIMIT 5
    `);
    console.table(sample.rows);

    // If full_data exists, show structure
    if (hasFullData.rows.length > 0) {
      console.log('\n=== SAMPLE FULL_DATA STRUCTURE ===');
      const fullDataSample = await client.query(`
        SELECT phone_number, jsonb_pretty(full_data) as full_data_preview
        FROM leads.leads
        WHERE full_data IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 1
      `);
      if (fullDataSample.rows.length > 0) {
        console.log('Phone:', fullDataSample.rows[0].phone_number);
        console.log('\nFull Data:');
        console.log(fullDataSample.rows[0].full_data_preview);
      } else {
        console.log('No leads with full_data found');
      }

      // Count leads with and without full_data
      const fullDataStats = await client.query(`
        SELECT
          COUNT(*) FILTER (WHERE full_data IS NOT NULL) as with_full_data,
          COUNT(*) FILTER (WHERE full_data IS NULL) as without_full_data
        FROM leads.leads
      `);
      console.log('\n=== FULL_DATA STATISTICS ===');
      console.table(fullDataStats.rows);
    }

  } finally {
    client.release();
    await pool.end();
  }
}

analyzeLeadsTable().catch(console.error);
