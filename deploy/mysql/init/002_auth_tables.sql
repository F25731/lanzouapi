USE unified_library;

CREATE TABLE IF NOT EXISTS api_clients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  client_name VARCHAR(120) NOT NULL UNIQUE,
  client_type VARCHAR(50) NOT NULL DEFAULT 'robot',
  key_prefix VARCHAR(40) NOT NULL UNIQUE,
  api_key_hash VARCHAR(255) NOT NULL,
  status ENUM('active', 'disabled') NOT NULL DEFAULT 'active',
  scopes LONGTEXT NULL,
  rate_limit_per_min INT NOT NULL DEFAULT 60,
  ip_whitelist LONGTEXT NULL,
  last_used_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_api_clients_status (status),
  INDEX ix_api_clients_key_prefix (key_prefix)
);

CREATE TABLE IF NOT EXISTS admin_users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  status ENUM('active', 'disabled') NOT NULL DEFAULT 'active',
  last_login_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_admin_users_status (status)
);

CREATE TABLE IF NOT EXISTS api_request_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  client_id INT NULL,
  request_path VARCHAR(1024) NOT NULL,
  request_method VARCHAR(16) NOT NULL,
  request_ip VARCHAR(64) NULL,
  status_code INT NOT NULL,
  latency_ms INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_api_request_logs_client FOREIGN KEY (client_id) REFERENCES api_clients(id) ON DELETE SET NULL,
  INDEX ix_api_request_logs_created_at (created_at),
  INDEX ix_api_request_logs_client_id (client_id),
  INDEX ix_api_request_logs_request_path (request_path)
);
