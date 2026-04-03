### Ransomware Response Playbook

**Trigger**: Ransomware detected or suspected on any system.

**Immediate Actions (First 15 Minutes)**:
1. **DO NOT** pay the ransom without executive and legal approval
2. **DO NOT** power off affected systems (preserve evidence in memory)
3. Disconnect affected systems from the network (pull ethernet, disable WiFi)
4. Alert the IR Lead and initiate S1 response
5. Activate out-of-band communication (personal phones, separate email)
6. Take photos of any ransom notes displayed on screens

**Containment (First Hour)**:
1. Identify the scope — how many systems are affected?
2. Determine the ransomware variant (ransom note, file extension, IOCs)
3. Check for available decryptors at [No More Ransom Project](https://www.nomoreransom.org/)
4. Block known C2 (command and control) domains and IPs at the firewall
5. Disable file sharing services (SMB, NFS)
6. Isolate network segments containing affected systems
7. Preserve at least one encrypted system for forensic analysis

**Assessment**:
1. Determine the entry point (phishing, RDP, vulnerability, supply chain)
2. Assess data exfiltration — check for double extortion indicators
3. Evaluate backup integrity — are backups intact and uncompromised?
4. Notify cyber insurance carrier
5. Engage forensics firm if needed

**Recovery**:
1. Rebuild affected systems from clean images
2. Restore data from verified clean backups
3. Reset all credentials (domain admin, service accounts, user accounts)
4. Apply patches that address the entry point vulnerability
5. Implement enhanced monitoring before reconnecting systems
6. Monitor for re-infection for 90 days