USE unified_library;

CREATE TABLE IF NOT EXISTS source_sources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  adapter_type VARCHAR(50) NOT NULL DEFAULT 'mock',
  base_url VARCHAR(255) NULL,
  username VARCHAR(120) NOT NULL,
  password VARCHAR(255) NOT NULL,
  root_folder_id VARCHAR(120) NULL,
  config_json LONGTEXT NULL,
  status ENUM('active', 'disabled', 'error') NOT NULL DEFAULT 'active',
  is_enabled TINYINT(1) NOT NULL DEFAULT 1,
  rate_limit_per_minute INT NOT NULL DEFAULT 30,
  request_timeout_seconds INT NOT NULL DEFAULT 20,
  last_login_at DATETIME NULL,
  last_sync_at DATETIME NULL,
  last_error LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_folders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  source_id INT NOT NULL,
  parent_id INT NULL,
  provider_folder_id VARCHAR(120) NOT NULL,
  name VARCHAR(255) NOT NULL,
  full_path VARCHAR(1024) NOT NULL,
  share_url VARCHAR(1024) NULL,
  depth INT NOT NULL DEFAULT 0,
  last_scanned_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_source_folder_provider_id UNIQUE (source_id, provider_folder_id),
  CONSTRAINT fk_source_folders_source FOREIGN KEY (source_id) REFERENCES source_sources(id) ON DELETE CASCADE,
  CONSTRAINT fk_source_folders_parent FOREIGN KEY (parent_id) REFERENCES source_folders(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS files (
  id INT AUTO_INCREMENT PRIMARY KEY,
  source_id INT NOT NULL,
  folder_id INT NULL,
  provider_file_id VARCHAR(120) NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  normalized_name VARCHAR(255) NOT NULL,
  file_path VARCHAR(1024) NOT NULL,
  extension VARCHAR(32) NULL,
  size_bytes BIGINT NULL,
  share_url VARCHAR(1024) NULL,
  status ENUM('active', 'missing', 'deleted') NOT NULL DEFAULT 'active',
  source_updated_at DATETIME NULL,
  last_seen_at DATETIME NULL,
  hot_score INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_file_source_provider_id UNIQUE (source_id, provider_file_id),
  CONSTRAINT fk_files_source FOREIGN KEY (source_id) REFERENCES source_sources(id) ON DELETE CASCADE,
  CONSTRAINT fk_files_folder FOREIGN KEY (folder_id) REFERENCES source_folders(id) ON DELETE SET NULL,
  INDEX ix_files_name (file_name),
  INDEX ix_files_normalized_name (normalized_name),
  INDEX ix_files_source_extension (source_id, extension),
  INDEX ix_files_status (status)
);

CREATE TABLE IF NOT EXISTS direct_link_cache (
  id INT AUTO_INCREMENT PRIMARY KEY,
  file_id INT NOT NULL UNIQUE,
  direct_url VARCHAR(2048) NULL,
  resolved_at DATETIME NULL,
  expires_at DATETIME NULL,
  fail_count INT NOT NULL DEFAULT 0,
  hit_count INT NOT NULL DEFAULT 0,
  miss_count INT NOT NULL DEFAULT 0,
  last_error LONGTEXT NULL,
  next_retry_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_direct_link_cache_file FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
  INDEX ix_direct_link_cache_expires_at (expires_at)
);

CREATE TABLE IF NOT EXISTS file_stats (
  id INT AUTO_INCREMENT PRIMARY KEY,
  file_id INT NOT NULL UNIQUE,
  download_count INT NOT NULL DEFAULT 0,
  search_count INT NOT NULL DEFAULT 0,
  last_downloaded_at DATETIME NULL,
  last_searched_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_file_stats_file FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scan_jobs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  source_id INT NOT NULL,
  folder_id INT NULL,
  target_provider_folder_id VARCHAR(120) NULL,
  mode ENUM('full', 'incremental', 'rescan') NOT NULL DEFAULT 'incremental',
  status ENUM('pending', 'running', 'completed', 'failed', 'canceled') NOT NULL DEFAULT 'pending',
  requested_by VARCHAR(100) NULL,
  checkpoint_json LONGTEXT NULL,
  summary_json LONGTEXT NULL,
  progress_current INT NOT NULL DEFAULT 0,
  progress_total INT NULL,
  error_message LONGTEXT NULL,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_scan_jobs_source FOREIGN KEY (source_id) REFERENCES source_sources(id) ON DELETE CASCADE,
  CONSTRAINT fk_scan_jobs_folder FOREIGN KEY (folder_id) REFERENCES source_folders(id) ON DELETE SET NULL,
  INDEX ix_scan_jobs_status (status),
  INDEX ix_scan_jobs_source_status (source_id, status)
);
