-- ============================================================
-- GoHigh Rentals  –  v2 Migration
-- Run this on your MySQL database ONCE before restarting Flask
-- ============================================================

-- 1. Vehicle: add rating, photo, model, condition, faults & price per vehicle
ALTER TABLE vehicle
  ADD COLUMN IF NOT EXISTS model_number     VARCHAR(100)  DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS vehicle_condition ENUM('Excellent','Good','Fair','Needs Repair') DEFAULT 'Good',
  ADD COLUMN IF NOT EXISTS known_faults     TEXT          DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS photo_url        VARCHAR(300)  DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS rating           DECIMAL(3,2)  DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS rating_count     INT           DEFAULT 0,
  ADD COLUMN IF NOT EXISTS price_per_day    DECIMAL(10,2) DEFAULT NULL  COMMENT 'Vehicle-level price overrides destination price',
  ADD COLUMN IF NOT EXISTS price_per_hour   DECIMAL(10,2) DEFAULT NULL;

-- 2. Vehicle ratings table
CREATE TABLE IF NOT EXISTS vehicle_rating (
  rating_id    INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id   INT NOT NULL,
  user_id      INT NOT NULL,
  booking_id   INT NOT NULL,
  rating       TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  review_text  TEXT,
  created_at   DATETIME DEFAULT NOW(),
  UNIQUE KEY uniq_booking_rating (booking_id),
  FOREIGN KEY (vehicle_id)  REFERENCES vehicle(vehicle_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)     REFERENCES users(user_id)      ON DELETE CASCADE,
  FOREIGN KEY (booking_id)  REFERENCES booking(booking_id) ON DELETE CASCADE
);

-- 3. User documents table  (Aadhaar + Driving Licence)
CREATE TABLE IF NOT EXISTS user_documents (
  doc_id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id        INT NOT NULL UNIQUE,
  full_name      VARCHAR(200) NOT NULL,
  aadhar_number  VARCHAR(12)  NOT NULL,
  aadhar_file    VARCHAR(300) DEFAULT NULL   COMMENT 'Stored filename',
  dl_number      VARCHAR(20)  NOT NULL,
  dl_file        VARCHAR(300) DEFAULT NULL,
  verified       TINYINT(1)   DEFAULT 0,
  submitted_at   DATETIME     DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 4. Booking agreement / digital signature
ALTER TABLE booking
  ADD COLUMN IF NOT EXISTS security_deposit   DECIMAL(10,2) DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS agreement_signed   TINYINT(1)    DEFAULT 0,
  ADD COLUMN IF NOT EXISTS signature_data     TEXT          DEFAULT NULL  COMMENT 'Base64 canvas signature',
  ADD COLUMN IF NOT EXISTS agreement_signed_at DATETIME     DEFAULT NULL;

-- 5. Pricing: add payment_mode
ALTER TABLE pricing
  ADD COLUMN IF NOT EXISTS payment_mode       ENUM('Online','Cash','UPI','Card','Net Banking') DEFAULT 'Online',
  ADD COLUMN IF NOT EXISTS cancellation_deduction DECIMAL(10,2) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS refund_amount          DECIMAL(10,2) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS cancellation_pct       TINYINT       DEFAULT NULL;

-- 6. Upload folder reference (no DB change needed – files saved to static/uploads/)

-- 7. Sample vehicle prices (adjust to your actual data)
UPDATE vehicle SET
  price_per_day  = CASE vehicle_type
    WHEN 'Bike'       THEN 500
    WHEN 'Scooter'    THEN 400
    WHEN 'Car'        THEN 1500
    WHEN 'SUV'        THEN 2500
    WHEN 'Tempo'      THEN 3000
    WHEN 'Bus'        THEN 5000
    ELSE 800
  END,
  price_per_hour = CASE vehicle_type
    WHEN 'Bike'       THEN 80
    WHEN 'Scooter'    THEN 60
    WHEN 'Car'        THEN 200
    WHEN 'SUV'        THEN 350
    WHEN 'Tempo'      THEN 450
    WHEN 'Bus'        THEN 700
    ELSE 120
  END
WHERE price_per_day IS NULL;
