/**
 * Initialize users table in database
 * Run with: npx ts-node scripts/init_users.ts
 */
import { Pool } from 'pg';
import bcrypt from 'bcryptjs';
import * as dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
});

async function initializeUsers() {
  console.log('🔧 Initializing users database...');

  try {
    // Create users table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER REFERENCES users(id),
        last_login TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE,
        CONSTRAINT role_check CHECK (role IN ('admin', 'user'))
      );
    `);

    console.log('✓ Users table created');

    // Create indexes
    await pool.query(`
      CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
      CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
    `);

    console.log('✓ Indexes created');

    // Check if admin exists
    const adminCheck = await pool.query(
      'SELECT id FROM users WHERE username = $1',
      ['admin']
    );

    if (adminCheck.rows.length === 0) {
      // Create admin user
      const adminPassword = process.env.ADMIN_PASSWORD || 'admin123';
      const passwordHash = await bcrypt.hash(adminPassword, 10);

      await pool.query(
        `INSERT INTO users (username, password_hash, role, is_active)
         VALUES ($1, $2, $3, TRUE)`,
        ['admin', passwordHash, 'admin']
      );

      console.log('✓ Admin user created');
      console.log(`  Username: admin`);
      console.log(`  Password: ${adminPassword}`);
    } else {
      console.log('ℹ Admin user already exists');
    }

    // Create sessions table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_token VARCHAR(255) UNIQUE NOT NULL,
        expires TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    console.log('✓ Sessions table created');

    // Create session indexes
    await pool.query(`
      CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
      CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
      CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires);
    `);

    console.log('✓ Session indexes created');

    console.log('\n✅ Database initialization complete!');
  } catch (error) {
    console.error('❌ Error initializing database:', error);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

initializeUsers();
