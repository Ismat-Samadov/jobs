/**
 * Database connection utilities
 */
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : undefined,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Set search path to leads schema
pool.on('connect', (client) => {
  client.query('SET search_path TO leads, public', (err) => {
    if (err) {
      console.error('Error setting search_path:', err);
    }
  });
});

export default pool;

pool.on('error', (err) => {
  console.error('❌ Unexpected database error:', err);
  process.exit(-1);
});
