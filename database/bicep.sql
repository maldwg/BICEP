CREATE DATABASE IF NOT EXISTS bicep;


USE bicep;

CREATE TABLE IF NOT EXISTS ids_tool(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    ids_type VARCHAR(64) NOT NULL,
    analysis_method VARCHAR(64) NOT NULL,
    requires_ruleset BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS configuration(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    configuration LONGBLOB NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    description VARCHAR(2048) NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    pcap_file LONGBLOB NOT NULL,
    labels_file LONGBLOB NOT NULL,
    description VARCHAR(2048) NOT NULL,
    ammount_benign INT NOT NULL,
    ammount_malicious INT NOT NULL
);

CREATE TABLE IF NOT EXISTS ensemble_technique(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    description VARCHAR(2048) NOT NULL
    -- TODO 0: function_name varchar(128) NOT NULL
);

CREATE TABLE IF NOT EXISTS ids_container (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name varchar(64) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    description VARCHAR(2048),
    configuration_id INT NOT NULL,
    ids_tool_id INT NOT NULL,
    ruleset_id INT,
    stream_metric_task_id VARCHAR(64),


    FOREIGN KEY (configuration_id) REFERENCES configuration(id),
    FOREIGN KEY (ids_tool_id) REFERENCES ids_tool(id),
    FOREIGN KEY (ruleset_id) REFERENCES configuration(id)

);

CREATE TABLE IF NOT EXISTS ensemble(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    description VARCHAR(2048),
    technique_id INT NOT NULL,

    FOREIGN KEY (technique_id) REFERENCES ensemble_technique(id)
);


CREATE TABLE IF NOT EXISTS ensemble_ids(
    id INT AUTO_INCREMENT PRIMARY KEY,
    ensemble_id  INT NOT NULL,
    ids_container_id INT NOT NULL,

    FOREIGN KEY (ensemble_id) REFERENCES ensemble(id),
    FOREIGN KEY (ids_container_id) REFERENCES ids_container(id)
);


INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset) VALUES ('Suricata', 'NIDS', 'Signature-based', true);
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset) VALUES ('Slips', 'NIDS', 'Anomaly-based', false);

INSERT INTO ensemble_technique (name, description) VALUES ('Majority Vote', 'A simply Majority vote approach where all IDS in the ensemble have the same weight');