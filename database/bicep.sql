CREATE DATABASE IF NOT EXISTS bicep;


USE bicep;

CREATE TABLE IF NOT EXISTS ids_tool(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    ids_type VARCHAR(64) NOT NULL,
    analysis_method VARCHAR(64) NOT NULL,
    requires_ruleset BOOLEAN NOT NULL,
    image_name VARCHAR(128) NOT NULL,
    image_tag VARCHAR(64) NOT NULL
);


CREATE TABLE IF NOT EXISTS docker_host_system(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(128) NOT NULL,
    -- can be dns name or plain IP
    host VARCHAR(1024) NOT NULL,
    docker_port INT NOT NULL
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
    pcap_file_path VARCHAR(1024) NOT NULL,
    labels_file_path VARCHAR(1024) NOT NULL,
    description VARCHAR(2048) NOT NULL,
    ammount_benign INT NOT NULL,
    ammount_malicious INT NOT NULL
);

CREATE TABLE IF NOT EXISTS ensemble_technique(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    description VARCHAR(2048) NOT NULL,
    function_name VARCHAR(128) NOT NULL
);

CREATE TABLE IF NOT EXISTS ids_container (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name varchar(64) NOT NULL,
    port INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    description VARCHAR(2048),
    host_system_id INT NOT NULL,
    configuration_id INT NOT NULL,
    ids_tool_id INT NOT NULL,
    ruleset_id INT,
    stream_metric_task_id VARCHAR(64),


    FOREIGN KEY (host_system_id) REFERENCES docker_host_system(id),
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
    current_analysis_id VARCHAR(64),


    FOREIGN KEY (technique_id) REFERENCES ensemble_technique(id)
);


CREATE TABLE IF NOT EXISTS ensemble_ids(
    id INT AUTO_INCREMENT PRIMARY KEY,
    ensemble_id  INT NOT NULL,
    ids_container_id INT NOT NULL,
    status VARCHAR(32),

    FOREIGN KEY (ensemble_id) REFERENCES ensemble(id),
    FOREIGN KEY (ids_container_id) REFERENCES ids_container(id)
);




INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag) VALUES ('Suricata', 'NIDS', 'Signature-based', true, 'maxldwg/bicep-suricata', 'latest');
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag) VALUES ('Slips', 'NIDS', 'Anomaly-based', false, 'maxldwg/bicep-slips', 'latest');

INSERT INTO ensemble_technique (name, description, function_name) VALUES ('Majority Vote', 'A simply Majority vote approach where all IDS in the ensemble have the same weight', 'majority_vote');


INSERT INTO docker_host_system (name, host, docker_port) VALUES ("Core-server", "localhost", 2375)