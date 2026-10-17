CREATE DATABASE civicsense_db;
USE civicsense_db;
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    raw_image_name VARCHAR(255) NOT NULL,
    analyzed_image_path VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    confidence_score DECIMAL(5, 2),
    report_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);