"""
Configurable Symbolic AI Rule Engine Parameters.

All threshold variables and rule metadata are defined here to keep 
symbolic reasoning transparent, explainable, and tunable without hardcoded inline constants.
"""

# Relationship Rules Config
RULE_COOCCUR_SAME_PAGE_ID = "RULE-COOCCUR-PAGE-001"
RULE_COOCCUR_SAME_PAGE_NAME = "Same Page Co-occurrence Association"
RULE_COOCCUR_MIN_CONFIDENCE = 0.70

# Finding Rules Config
RULE_CLUSTER_PAGE_ID = "RULE-CLUSTER-PAGE-001"
RULE_CLUSTER_PAGE_NAME = "Page Evidence Co-occurrence Cluster"
RULE_CLUSTER_MIN_ENTITIES = 3  # Minimum distinct evidence items on the same page to flag a cluster

RULE_LOCATION_FREQ_ID = "RULE-FREQ-LOC-001"
RULE_LOCATION_FREQ_NAME = "High-Frequency Location Finding"
RULE_LOCATION_MIN_COUNT = 2    # Minimum occurrences of the same location across report pages to flag

RULE_COMM_CLUSTER_ID = "RULE-COMM-CLUSTER-001"
RULE_COMM_CLUSTER_NAME = "Communication Window Cluster"
RULE_COMM_TIME_WINDOW_MINUTES = 30
RULE_COMM_MIN_EVENTS = 3
