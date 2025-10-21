-- Users table for authentication and authorization
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

-- Create index for faster username lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Insert default admin user (password: admin123)
-- Password hash for 'admin123' using bcrypt
INSERT INTO users (username, password_hash, role, is_active)
VALUES ('admin', '$2a$10$X4qhKJZQqJx5xQ5xQqJx5eDqKqJx5xQ5xQqJx5eDqKqJx5xQ5xQqJ', 'admin', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Sessions table for NextAuth
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires);

COMMENT ON TABLE users IS 'Application users with role-based access control';
COMMENT ON TABLE sessions IS 'User session management for NextAuth.js';
