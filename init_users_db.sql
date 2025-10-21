-- Users table for authentication and authorization
CREATE TABLE IF NOT EXISTS leads.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES leads.users(id),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT role_check CHECK (role IN ('admin', 'user'))
);

-- Create index for faster username lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON leads.users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON leads.users(role);

-- Insert default admin user (password: admin123)
-- Password hash for 'admin123' using bcrypt
INSERT INTO leads.users (username, password_hash, role, is_active)
VALUES ('admin', '$2b$12$oaFdidvqh03o1BC3o86.dOpQpFFSURY5ZHfKlfXVf7S5i8Jolbuk.', 'admin', TRUE)
ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash;

-- Sessions table for NextAuth
CREATE TABLE IF NOT EXISTS leads.sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES leads.users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON leads.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON leads.sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON leads.sessions(expires);

COMMENT ON TABLE leads.users IS 'Application users with role-based access control';
COMMENT ON TABLE leads.sessions IS 'User session management for NextAuth.js';
