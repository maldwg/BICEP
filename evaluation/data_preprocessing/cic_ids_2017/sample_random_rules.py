import random 

"""
Script to sample random rules from a suricata rules file.
Was not used througout the thesis.
"""

def sample_random_rules(rules_file, output_file, ratio=.1):
    total_rules = []
    with open(rules_file) as rules:
        for rule in rules:
            total_rules.append(rule)
    wanted_sample_count = int(len(total_rules) * ratio)
    sampled_rules = random.sample(total_rules, k=wanted_sample_count)
    with open(output_file, "w") as f:
        f.writelines(sampled_rules)


rules_file = "/mnt/d/master/suricata.rules"
output_file = "/mnt/d/master/suricata_tenth.rules"

sample_random_rules(rules_file=rules_file, output_file=output_file, ratio=0.1)