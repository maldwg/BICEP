CREATE TABLE IF NOT EXISTS suspicious_batches_to_batch (
    suspicious_batch_id UUID NOT NULL,
    batch_id UUID NOT NULL
)
ENGINE = MergeTree
PRIMARY KEY (suspicious_batch_id);

CREATE TABLE IF NOT EXISTS suspicious_batch_timestamps (
    suspicious_batch_id UUID NOT NULL,
    src_ip String NOT NULL,
    instance_name String NOT NULL,
    stage String NOT NULL,
    status String NOT NULL,
    timestamp DateTime64(6) NOT NULL,
    message_count UInt32,
    is_active Bool NOT NULL
)
ENGINE = MergeTree
-- keep the PK as the UUID even thogh it is not uinque for indexing reasons
PRIMARY KEY (suspicious_batch_id);

CREATE TABLE IF NOT EXISTS server_logs (
    message_id UUID NOT NULL,
    timestamp_in DateTime64(6) NOT NULL,
    message_text String NOT NULL
)
ENGINE = MergeTree
PRIMARY KEY(message_id);

CREATE TABLE IF NOT EXISTS server_logs_timestamps (
    message_id UUID NOT NULL,
    event String NOT NULL,
    event_timestamp DateTime64(6) NOT NULL
)
ENGINE = MergeTree
PRIMARY KEY(message_id);

CREATE TABLE IF NOT EXISTS loglines (
    logline_id UUID NOT NULL,
    timestamp DateTime64(6) NOT NULL,
    subnet_id String NOT NULL,
    src_ip String NOT NULL,
    additional_fields String
)
ENGINE = MergeTree
PRIMARY KEY (logline_id);

CREATE TABLE IF NOT EXISTS logline_to_batches (
    logline_id UUID NOT NULL,
    batch_id UUID NOT NULL
)
ENGINE = MergeTree
PRIMARY KEY (logline_id);

CREATE TABLE IF NOT EXISTS logline_timestamps (
    logline_id UUID NOT NULL,
    stage String NOT NULL,
    status String NOT NULL,
    timestamp DateTime64(6) NOT NULL,
    is_active Bool NOT NULL
)
ENGINE = MergeTree
PRIMARY KEY (logline_id);

CREATE TABLE IF NOT EXISTS fill_levels (
    timestamp DateTime64(6) NOT NULL,
    stage String NOT NULL,
    entry_type String NOT NULL,
    entry_count UInt32 DEFAULT 0
)
ENGINE = MergeTree
PRIMARY KEY (timestamp, stage, entry_type);

CREATE TABLE IF NOT EXISTS failed_loglines (
    message_text String NOT NULL,
    timestamp_in DateTime64(6) NOT NULL,
    timestamp_failed DateTime64(6) NOT NULL,
    reason_for_failure Nullable(String)
)
ENGINE = MergeTree
PRIMARY KEY(message_text, timestamp_in);

-- Table to be able to reconstruct where the batch was processed in
-- used in grafana to calculate the elapsed time between stages
CREATE TABLE IF NOT EXISTS batch_tree (
    batch_row_id String NOT NULL,
    batch_id UUID NOT NULL,
    parent_batch_row_id Nullable(String), -- Default of Null indicates a root element
    instance_name String NOT NULL,
    stage String NOT NULL,
    status String NOT NULL,
    timestamp DateTime64(6) NOT NULL,
)
ENGINE = MergeTree
-- keep the PK as the UUID even thogh it is not uinque for indexing reasons
PRIMARY KEY (batch_row_id);

CREATE TABLE IF NOT EXISTS batch_timestamps (
    batch_id UUID NOT NULL,
    instance_name String NOT NULL,
    stage String NOT NULL,
    status String NOT NULL,
    timestamp DateTime64(6) NOT NULL,
    message_count UInt32,
    is_active Bool NOT NULL
)
ENGINE = MergeTree
-- keep the PK as the UUID even thogh it is not uinque for indexing reasons
PRIMARY KEY (batch_id);

CREATE TABLE IF NOT EXISTS alerts (
    src_ip String NOT NULL,
    alert_timestamp DateTime64(6) NOT NULL,
    suspicious_batch_id UUID NOT NULL,
    overall_score Float32 NOT NULL,
    domain_names String NOT NULL,
    result String,
)
ENGINE = MergeTree
PRIMARY KEY(src_ip, alert_timestamp);

