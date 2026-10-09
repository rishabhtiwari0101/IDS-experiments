# CIC-IDS-2017 Raw Dataset Forensic Audit
Generated: 2026-10-06T04:03:01.697408+00:00  
Status: PASS  

## Summary
- Total Shards: 8
- Total Raw Rows: 2,830,743
- Total Columns: 79
- Total Labels: 15

## Shard Breakdown

### `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`
- Rows: 225,745
- Duplicate rows: 2,633
- Labels: `{'DDoS': 128027, 'BENIGN': 97718}`

### `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`
- Rows: 286,467
- Duplicate rows: 72,353
- Labels: `{'PortScan': 158930, 'BENIGN': 127537}`

### `Friday-WorkingHours-Morning.pcap_ISCX.csv`
- Rows: 191,033
- Duplicate rows: 6,888
- Labels: `{'BENIGN': 189067, 'Bot': 1966}`

### `Monday-WorkingHours.pcap_ISCX.csv`
- Rows: 529,918
- Duplicate rows: 26,935
- Labels: `{'BENIGN': 529918}`

### `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv`
- Rows: 288,602
- Duplicate rows: 35,630
- Labels: `{'BENIGN': 288566, 'Infiltration': 36}`

### `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`
- Rows: 170,366
- Duplicate rows: 6,066
- Labels: `{'BENIGN': 168186, 'Web Attack � Brute Force': 1507, 'Web Attack � XSS': 652, 'Web Attack � Sql Injection': 21}`

### `Tuesday-WorkingHours.pcap_ISCX.csv`
- Rows: 445,909
- Duplicate rows: 24,065
- Labels: `{'BENIGN': 432074, 'FTP-Patator': 7938, 'SSH-Patator': 5897}`

### `Wednesday-workingHours.pcap_ISCX.csv`
- Rows: 692,703
- Duplicate rows: 81,909
- Labels: `{'BENIGN': 440031, 'DoS Hulk': 231073, 'DoS GoldenEye': 10293, 'DoS slowloris': 5796, 'DoS Slowhttptest': 5499, 'Heartbleed': 11}`

## Dataset-Wide Label Inventory
- `BENIGN`: 2,273,097 (80.3004%)
- `DoS Hulk`: 231,073 (8.1630%)
- `PortScan`: 158,930 (5.6144%)
- `DDoS`: 128,027 (4.5227%)
- `DoS GoldenEye`: 10,293 (0.3636%)
- `FTP-Patator`: 7,938 (0.2804%)
- `SSH-Patator`: 5,897 (0.2083%)
- `DoS slowloris`: 5,796 (0.2048%)
- `DoS Slowhttptest`: 5,499 (0.1943%)
- `Bot`: 1,966 (0.0695%)
- `Web Attack � Brute Force`: 1,507 (0.0532%)
- `Web Attack � XSS`: 652 (0.0230%)
- `Infiltration`: 36 (0.0013%)
- `Web Attack � Sql Injection`: 21 (0.0007%)
- `Heartbleed`: 11 (0.0004%)
