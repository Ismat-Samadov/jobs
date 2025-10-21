/**
 * Authentication utilities and helpers
 */
import bcrypt from 'bcryptjs';
import pool from './db';

export interface User {
  id: number;
  username: string;
  role: 'admin' | 'user';
  created_at: Date;
  last_login?: Date;
  is_active: boolean;
}

export interface UserWithPassword extends User {
  password_hash: string;
}

/**
 * Hash a password using bcrypt
 */
export async function hashPassword(password: string): Promise<string> {
  const salt = await bcrypt.genSalt(10);
  return bcrypt.hash(password, salt);
}

/**
 * Verify a password against a hash
 */
export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

/**
 * Get user by username
 */
export async function getUserByUsername(username: string): Promise<UserWithPassword | null> {
  const result = await pool.query(
    'SELECT id, username, password_hash, role, created_at, last_login, is_active FROM users WHERE username = $1',
    [username]
  );

  if (result.rows.length === 0) {
    return null;
  }

  return result.rows[0] as UserWithPassword;
}

/**
 * Get user by ID (without password hash)
 */
export async function getUserById(id: number): Promise<User | null> {
  const result = await pool.query(
    'SELECT id, username, role, created_at, last_login, is_active FROM users WHERE id = $1',
    [id]
  );

  if (result.rows.length === 0) {
    return null;
  }

  return result.rows[0] as User;
}

/**
 * Update user's last login timestamp
 */
export async function updateLastLogin(userId: number): Promise<void> {
  await pool.query(
    'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
    [userId]
  );
}

/**
 * Create a new user
 */
export async function createUser(
  username: string,
  password: string,
  role: 'admin' | 'user',
  createdBy: number
): Promise<User> {
  const passwordHash = await hashPassword(password);

  const result = await pool.query(
    `INSERT INTO users (username, password_hash, role, created_by, is_active)
     VALUES ($1, $2, $3, $4, TRUE)
     RETURNING id, username, role, created_at, is_active`,
    [username, passwordHash, role, createdBy]
  );

  return result.rows[0] as User;
}

/**
 * Get all users (admin only)
 */
export async function getAllUsers(): Promise<User[]> {
  const result = await pool.query(
    `SELECT id, username, role, created_at, last_login, is_active
     FROM users
     ORDER BY created_at DESC`
  );

  return result.rows as User[];
}

/**
 * Update user
 */
export async function updateUser(
  id: number,
  updates: {
    username?: string;
    password?: string;
    is_active?: boolean;
  }
): Promise<User> {
  const setClauses: string[] = [];
  const values: any[] = [];
  let paramIndex = 1;

  if (updates.username !== undefined) {
    setClauses.push(`username = $${paramIndex++}`);
    values.push(updates.username);
  }

  if (updates.password !== undefined) {
    const passwordHash = await hashPassword(updates.password);
    setClauses.push(`password_hash = $${paramIndex++}`);
    values.push(passwordHash);
  }

  if (updates.is_active !== undefined) {
    setClauses.push(`is_active = $${paramIndex++}`);
    values.push(updates.is_active);
  }

  if (setClauses.length === 0) {
    throw new Error('No updates provided');
  }

  values.push(id);

  const result = await pool.query(
    `UPDATE users
     SET ${setClauses.join(', ')}
     WHERE id = $${paramIndex}
     RETURNING id, username, role, created_at, last_login, is_active`,
    values
  );

  if (result.rows.length === 0) {
    throw new Error('User not found');
  }

  return result.rows[0] as User;
}

/**
 * Delete user
 */
export async function deleteUser(id: number): Promise<void> {
  const result = await pool.query('DELETE FROM users WHERE id = $1 AND role != $2', [id, 'admin']);

  if (result.rowCount === 0) {
    throw new Error('User not found or cannot delete admin');
  }
}
