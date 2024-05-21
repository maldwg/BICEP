CREATE DATABASE IF NOT EXISTS bicep;

USE bicep;

CREATE TABLE IF NOT EXISTS ids_tool(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    ids_type VARCHAR(64) NOT NULL,
    analysis_method VARCHAR(64) NOT NULL 
);

CREATE TABLE IF NOT EXISTS configuration(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(32) NOT NULL,
    configuration LONGBLOB NOT NULL,
    description VARCHAR(2048) NOT NULL
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


    FOREIGN KEY (configuration_id) REFERENCES configuration(id),
    FOREIGN KEY (ids_tool_id) REFERENCES ids_tool(id)

);

CREATE TABLE IF NOT EXISTS data_set(
    id INT AUTO_INCREMENT PRIMARY KEY,
    dataset BLOB NOT NULL,
    description VARCHAR(2048)
);

CREATE TABLE IF NOT EXISTS ensemble(
    id INT AUTO_INCREMENT PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    description VARCHAR(2048) 
);


CREATE TABLE IF NOT EXISTS ensemble_ids(
    id INT AUTO_INCREMENT PRIMARY KEY,
    ensemble_id  INT NOT NULL,
    ids_container_id INT NOT NULL,

    FOREIGN KEY (ensemble_id) REFERENCES ensemble(id),
    FOREIGN KEY (ids_container_id) REFERENCES ids_container(id)
);


INSERT INTO ids_tool (name, ids_type, analysis_method) VALUES ('suricata', 'NIDS', 'Signature-based');
INSERT INTO ids_tool (name, ids_type, analysis_method) VALUES ('slips', 'NIDS', 'Anomaly-based');