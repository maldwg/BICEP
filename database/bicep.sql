CREATE DATABASE IF NOT EXISTS bicep;


USE bicep;

CREATE TABLE IF NOT EXISTS ids_tool(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    ids_type VARCHAR(64) NOT NULL,
    analysis_method VARCHAR(64) NOT NULL,
    requires_ruleset BOOLEAN NOT NULL,
    image_name VARCHAR(128) NOT NULL,
    image_tag VARCHAR(64) NOT NULL,
    deployment_type VARCHAR(64) NOT NULL DEFAULT 'SINGLE_CONTAINER',
    required_env_vars VARCHAR(512) DEFAULT ''
);



CREATE TABLE IF NOT EXISTS docker_host_system(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(128) NOT NULL,
    -- can be dns name or plain IP
    host VARCHAR(1024) NOT NULL,
    docker_port INT NOT NULL,
    status VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_service(
    id INT AUTO_INCREMENT PRIMARY KEY,
    host_system_id INT NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    ip VARCHAR(255),
    port INT,
    status VARCHAR(64) NOT NULL,
    status_message VARCHAR(2048),
    last_registration_at VARCHAR(128),

    FOREIGN KEY (host_system_id) REFERENCES docker_host_system(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS configuration(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    description VARCHAR(2048) NOT NULL,
    config_type VARCHAR(32) NOT NULL DEFAULT 'CONFIGURATION'
);

CREATE TABLE IF NOT EXISTS dataset_type(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    description VARCHAR(2048) NOT NULL,
    function_prefix VARCHAR(128) NOT NULL
    
);

CREATE TABLE IF NOT EXISTS dataset(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    data_file_path VARCHAR(1024) NOT NULL,
    labels_file_path VARCHAR(1024) NOT NULL,
    description VARCHAR(2048) NOT NULL,
    ammount_benign INT NOT NULL,
    ammount_malicious INT NOT NULL,
    dataset_type_id INT NOT NULL,
    timestamp_precision VARCHAR(64) NOT NULL,
    FOREIGN KEY (dataset_type_id) REFERENCES dataset_type(id)
);




CREATE TABLE IF NOT EXISTS ensemble_technique(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    description VARCHAR(2048) NOT NULL,
    function_name VARCHAR(128) NOT NULL
);

CREATE TABLE IF NOT EXISTS ids_system (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name varchar(64) NOT NULL,
    port INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    deployment_status VARCHAR(32) NOT NULL DEFAULT 'deployed',
    description VARCHAR(2048) NOT NULL,
    host_system_id INT NOT NULL,
    configuration_id INT NOT NULL,
    ids_tool_id INT NOT NULL,
    ruleset_id INT,
    runtime_configuration_id INT,
    type VARCHAR(32) NOT NULL DEFAULT 'NIDS',

    FOREIGN KEY (host_system_id) REFERENCES docker_host_system(id),
    FOREIGN KEY (configuration_id) REFERENCES configuration(id),
    FOREIGN KEY (ids_tool_id) REFERENCES ids_tool(id),
    FOREIGN KEY (ruleset_id) REFERENCES configuration(id),
    FOREIGN KEY (runtime_configuration_id) REFERENCES configuration(id)

);

CREATE TABLE IF NOT EXISTS ensemble(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    description VARCHAR(2048) NOT NULL,
    technique_id INT NOT NULL,
    current_analysis_id VARCHAR(64),


    FOREIGN KEY (technique_id) REFERENCES ensemble_technique(id)
);


CREATE TABLE IF NOT EXISTS ensemble_ids(
    id INT AUTO_INCREMENT PRIMARY KEY,
    ensemble_id  INT NOT NULL,
    ids_system_id INT NOT NULL,
    status VARCHAR(32),

    FOREIGN KEY (ensemble_id) REFERENCES ensemble(id),
    FOREIGN KEY (ids_system_id) REFERENCES ids_system(id)
);


CREATE TABLE IF NOT EXISTS ids_component(
    id INT AUTO_INCREMENT PRIMARY KEY,
    ids_id INT NOT NULL,
    name VARCHAR(64) NOT NULL,
    service_name VARCHAR(64),
    role VARCHAR(32) NOT NULL,
    host_system_id INT,
    port INT,
    runtime_configuration_id INT,
    count INT DEFAULT 1,

    FOREIGN KEY (ids_id) REFERENCES ids_system(id),
    FOREIGN KEY (host_system_id) REFERENCES docker_host_system(id),
    FOREIGN KEY (runtime_configuration_id) REFERENCES configuration(id)
);


CREATE TABLE IF NOT EXISTS benchmarking_result (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_name VARCHAR(256),
    ids_name VARCHAR(256),
    ensembling_method VARCHAR(256),
    configuration_name VARCHAR(256),
    ruleset_name VARCHAR(256),
    start_time VARCHAR(256),
    stop_time VARCHAR(256),
    runtime FLOAT,
    prec FLOAT,
    detection_rate FLOAT,
    f1_score FLOAT,
    acc FLOAT,
    fpr FLOAT,
    fnr FLOAT,
    fdr FLOAT,
    avg_cpu_usage FLOAT,
    avg_memory_usage FLOAT,
    resource_query_mode VARCHAR(32),
    resource_query_targets TEXT
);

CREATE TABLE IF NOT EXISTS benchmarking_intermediate_result (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ensemble_name VARCHAR(256),
    ensemble_uuid VARCHAR(64),
    container_name VARCHAR(128),
    start_time VARCHAR(256),
    stop_time VARCHAR(256)
);


INSERT INTO dataset_type (name, description, function_prefix) VALUES ('Network Analysis Data', 'Network traffic data in form of PCAPs. The labels are in CSV file format', 'network_traffic_data');
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag, deployment_type, required_env_vars) VALUES ('Suricata', 'NIDS', 'Signature-based', true, 'maxldwg/bicep-suricata', 'latest', 'SINGLE_CONTAINER', '');
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag, deployment_type, required_env_vars) VALUES ('Slips', 'NIDS', 'Anomaly-based', false, 'maxldwg/bicep-slips', 'latest', 'SINGLE_CONTAINER', '');
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag, deployment_type, required_env_vars) VALUES ('Snort', 'NIDS', 'Signature-based', true, 'maxldwg/bicep-snort', 'latest', 'SINGLE_CONTAINER', '');
-- Sample CIDS Tool
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag, deployment_type, required_env_vars) VALUES ('Hamstring', 'CIDS', 'ML-based', false, 'hamstring/hamstring', 'latest', 'DOCKER_COMPOSE', 'HOST_IP,MOUNT_PATH');
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag, deployment_type, required_env_vars) VALUES ('Maltrail', 'NIDS', 'Threat-intel-based', false, 'ghcr.io/maldwg/bicep-maltrail', 'latest', 'SINGLE_CONTAINER', '');

INSERT INTO ensemble_technique (name, description, function_name) VALUES ('Majority Vote', 'A simply Majority vote approach where all IDS in the ensemble have the same weight', 'majority_vote');
INSERT INTO docker_host_system (name, host, docker_port, status) VALUES ("Core-server", "localhost", 2375, "unavailable");
INSERT INTO dataset (name, data_file_path, labels_file_path, description, ammount_benign, ammount_malicious, dataset_type_id, timestamp_precision) VALUES ('sample-data','/opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/dataset.pcap','/opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/dataset.csv','Sample data including 0,5% of all requests from the CICIDS Dataset',11367,2791, 1, 'minute');


INSERT INTO configuration VALUES
(1, 'suricata.yaml', '/opt/runtime_configurations/uuid2/suricata.yaml', 'RUNTIME', 'default suricata configuartion', 'RUNTIME');
INSERT INTO configuration VALUES
(2, 'snort.lua', '/opt/runtime_configurations/uuid1/snort.lua', 'RUNTIME', 'default snort configuartion', 'RUNTIME');
INSERT INTO configuration VALUES
(3, 'slips.yaml', '/opt/runtime_configurations/uuid3/slips.yaml', 'RUNTIME', 'default slips configuartion', 'RUNTIME');
INSERT INTO configuration VALUES
(4, 'hamstring_config.yaml', '/opt/runtime_configurations/uuid7/hamstring_config.yaml', 'RUNTIME', 'default hamstring configuartion', 'RUNTIME');
INSERT INTO configuration VALUES
(13, 'maltrail.conf', '/opt/runtime_configurations/uuid9/maltrail.conf', 'RUNTIME', 'default maltrail configuration', 'RUNTIME');

INSERT INTO configuration VALUES
(5, 'et-open.rules', '/opt/rulesets/uuid4/suricata-et-open.rules', 'RULESET', 'default et/open rules', 'RULESET');
INSERT INTO configuration VALUES
(6, 'snort-community.rules', '/opt/rulesets/uuid1/snort-community.rules', 'RULESET', 'default snort community rules', 'RULESET');
INSERT INTO configuration VALUES
(7, 'suricata-all.rules', '/opt/rulesets/uuid3/suricata-all.rules', 'RULESET', 'All opensource suricata rules', 'RULESET');
INSERT INTO configuration VALUES
(8, 'snort-max-detect.rules', '/opt/rulesets/uuid2/snort-max-detect.rules', 'RULESET', 'lightspd max detect + community rules', 'RULESET');
-- Sample CIDS Config
INSERT INTO configuration VALUES
(10, 'hamstring-compose.yaml', '/opt/deployment_configurations/uuid5/hamstring-compose.yaml', 'DEPLOYMENT', 'Hamstring Docker Compose Setup', 'DEPLOYMENT');
INSERT INTO configuration VALUES
(12, 'hamstring_clickhouse.sql', '/opt/runtime_configurations/uuid8/hamstring_clickhouse.sql', 'RUNTIME', 'Hamstring Clickhouse tables', 'RUNTIME');
