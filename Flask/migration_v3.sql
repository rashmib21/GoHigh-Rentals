-- ============================================================
-- GoHigh Rentals v3 Migration — Run ONCE after v2 migration
-- ============================================================

-- Admin accounts table
CREATE TABLE IF NOT EXISTS admin_accounts (
  admin_id   INT AUTO_INCREMENT PRIMARY KEY,
  username   VARCHAR(60)  NOT NULL UNIQUE,
  email      VARCHAR(100) NOT NULL UNIQUE,
  password   VARCHAR(256) NOT NULL,
  created_at DATETIME DEFAULT NOW()
);

-- Review categories
ALTER TABLE review ADD COLUMN category VARCHAR(20) DEFAULT 'travelling';
ALTER TABLE review ADD COLUMN vehicle_id INT DEFAULT NULL;

-- Document verification status
ALTER TABLE user_documents ADD COLUMN encrypted TINYINT(1) DEFAULT 0;
ALTER TABLE user_documents ADD COLUMN verified_at DATETIME DEFAULT NULL;
ALTER TABLE user_documents ADD COLUMN verification_status VARCHAR(20) DEFAULT 'pending';
