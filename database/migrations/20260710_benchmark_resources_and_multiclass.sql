ALTER TABLE dataset
    ADD COLUMN IF NOT EXISTS evaluation_mode VARCHAR(32) NOT NULL DEFAULT 'binary',
    ADD COLUMN IF NOT EXISTS class_counts TEXT;

ALTER TABLE benchmarking_result
    ADD COLUMN IF NOT EXISTS evaluation_mode VARCHAR(32) NOT NULL DEFAULT 'binary';

ALTER TABLE benchmarking_job_item
    ADD COLUMN IF NOT EXISTS avg_cpu_usage FLOAT,
    ADD COLUMN IF NOT EXISTS avg_memory_usage FLOAT,
    ADD COLUMN IF NOT EXISTS resource_query_mode VARCHAR(32),
    ADD COLUMN IF NOT EXISTS resource_query_targets TEXT;

CREATE TABLE IF NOT EXISTS benchmarking_class_result (
    id INT AUTO_INCREMENT PRIMARY KEY,
    benchmarking_result_id INT NOT NULL,
    class_label VARCHAR(256) NOT NULL,
    support INT NOT NULL,
    detected INT NOT NULL,
    missed INT NOT NULL,
    detection_rate FLOAT NOT NULL,
    FOREIGN KEY (benchmarking_result_id) REFERENCES benchmarking_result(id) ON DELETE CASCADE
);
