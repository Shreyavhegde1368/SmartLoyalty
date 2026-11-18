CREATE DATABASE IF NOT EXISTS smartloyalty
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smartloyalty;

CREATE TABLE IF NOT EXISTS businesses (
    business_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    business_type VARCHAR(80) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('owner','staff') NOT NULL DEFAULT 'owner',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_business FOREIGN KEY (business_id)
      REFERENCES businesses(business_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    phone VARCHAR(30),
    marketing_consent BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loyalty_accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    business_id INT NOT NULL,
    points_balance INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_customer_business (customer_id, business_id),
    CONSTRAINT fk_accounts_customer FOREIGN KEY (customer_id)
      REFERENCES customers(customer_id) ON DELETE CASCADE,
    CONSTRAINT fk_accounts_business FOREIGN KEY (business_id)
      REFERENCES businesses(business_id) ON DELETE CASCADE,
    CONSTRAINT chk_points_nonnegative CHECK (points_balance >= 0)
);

CREATE TABLE IF NOT EXISTS purchases (
    purchase_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    qr_token CHAR(64) NOT NULL UNIQUE,
    feedback_submitted BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_purchases_account FOREIGN KEY (account_id)
      REFERENCES loyalty_accounts(account_id) ON DELETE CASCADE,
    CONSTRAINT chk_purchase_amount CHECK (amount > 0)
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_id INT NOT NULL UNIQUE,
    rating TINYINT NOT NULL,
    comments TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_feedback_purchase FOREIGN KEY (purchase_id)
      REFERENCES purchases(purchase_id) ON DELETE CASCADE,
    CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS points_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    purchase_id INT NULL,
    transaction_type ENUM('earned','spent','bonus','adjustment') NOT NULL,
    points INT NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_transactions_account FOREIGN KEY (account_id)
      REFERENCES loyalty_accounts(account_id) ON DELETE CASCADE,
    CONSTRAINT fk_transactions_purchase FOREIGN KEY (purchase_id)
      REFERENCES purchases(purchase_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS rewards (
    reward_id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    reward_name VARCHAR(120) NOT NULL,
    description VARCHAR(255),
    points_required INT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_rewards_business FOREIGN KEY (business_id)
      REFERENCES businesses(business_id) ON DELETE CASCADE,
    CONSTRAINT chk_reward_points CHECK (points_required > 0)
);

CREATE TABLE IF NOT EXISTS redemptions (
    redemption_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    reward_id INT NOT NULL,
    points_spent INT NOT NULL,
    redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('requested','approved','used','cancelled') NOT NULL DEFAULT 'requested',
    CONSTRAINT fk_redemptions_account FOREIGN KEY (account_id)
      REFERENCES loyalty_accounts(account_id) ON DELETE CASCADE,
    CONSTRAINT fk_redemptions_reward FOREIGN KEY (reward_id)
      REFERENCES rewards(reward_id) ON DELETE RESTRICT
);

CREATE INDEX idx_purchases_date ON purchases(purchase_date);
CREATE INDEX idx_feedback_rating ON feedback(rating);
CREATE INDEX idx_transactions_account_date ON points_transactions(account_id, created_at);
