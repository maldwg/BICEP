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
    docker_port INT NOT NULL,
    status VARCHAR(64)
);


CREATE TABLE IF NOT EXISTS configuration(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    description VARCHAR(2048) NOT NULL
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

CREATE TABLE IF NOT EXISTS ids_container (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name varchar(64) NOT NULL,
    port INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    description VARCHAR(2048) NOT NULL,
    host_system_id INT NOT NULL,
    configuration_id INT NOT NULL,
    ids_tool_id INT NOT NULL,
    ruleset_id INT,

    FOREIGN KEY (host_system_id) REFERENCES docker_host_system(id),
    FOREIGN KEY (configuration_id) REFERENCES configuration(id),
    FOREIGN KEY (ids_tool_id) REFERENCES ids_tool(id),
    FOREIGN KEY (ruleset_id) REFERENCES configuration(id)

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
    ids_container_id INT NOT NULL,
    status VARCHAR(32),

    FOREIGN KEY (ensemble_id) REFERENCES ensemble(id),
    FOREIGN KEY (ids_container_id) REFERENCES ids_container(id)
);



INSERT INTO dataset_type (name, description, function_prefix) VALUES ('Network Analysis Data', 'Network traffic data in form of PCAPs. The labels are in CSV file format', 'network_traffic_data');
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag) VALUES ('Suricata', 'NIDS', 'Signature-based', true, 'maxldwg/bicep-suricata', 'latest');
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag) VALUES ('Slips', 'NIDS', 'Anomaly-based', false, 'maxldwg/bicep-slips', 'latest');
INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag) VALUES ('Snort', 'NIDS', 'Signature-based', true, 'maxldwg/bicep-snort', 'latest');

INSERT INTO ensemble_technique (name, description, function_name) VALUES ('Majority Vote', 'A simply Majority vote approach where all IDS in the ensemble have the same weight', 'majority_vote');


INSERT INTO docker_host_system (name, host, docker_port) VALUES ("Core-server", "localhost", 2375);

INSERT INTO dataset (name, data_file_path, labels_file_path, description, ammount_benign, ammount_malicious, dataset_type_id, timestamp_precision) VALUES ('sample-data','/opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/dataset.pcap','/opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/dataset.csv','Sample data including 0,5% of all requests from the CICIDS Dataset',11367,2791, 1, 'minute');


INSERT INTO configuration VALUES
(1, 'suricata.yaml', '/opt/configuration_data/uuid2/suricata.yaml', 'configuration', 'default suricata configuartion');
INSERT INTO configuration VALUES
(2, 'snort.lua', '/opt/configuration_data/uuid1/snort.lua', 'configuration', 'default snort configuartion');
INSERT INTO configuration VALUES
(3, 'slips.yaml', '/opt/configuration_data/uuid3/slips.yaml', 'configuration', 'default slips configuartion');
INSERT INTO configuration VALUES
(4, 'et-open.rules', '/opt/rulesets/uuid4/suricata-et-open.rules', 'rule-set', 'default et/open rules');
INSERT INTO configuration VALUES
(5, 'snort-community.rules', '/opt/rulesets/uuid1/snort-community.rules', 'rule-set', 'default snort community rules');
INSERT INTO configuration VALUES
(6, 'suricata-all.rules', '/opt/rulesets/uuid3/suricata-all.rules', 'rule-set', 'All opensource suricata rules');
INSERT INTO configuration VALUES
(7, 'snort-all.rules', '/opt/rulesets/uuid2/snort-all.rules', 'rule-set', 'lightspd max detect + community rules');