### 5. Incident Response Phases

#### Phase 1: Preparation

**Objective**: Ensure the organization is ready to respond to incidents.

- [ ] Maintain this incident response plan and review at least annually
- [ ] Conduct security awareness training for all employees
- [ ] Deploy and maintain security monitoring tools (SIEM, EDR, IDS/IPS)
- [ ] Establish and test backup and recovery procedures
- [ ] Maintain incident response toolkit and forensic tools
- [ ] Conduct tabletop exercises at least annually
- [ ] Maintain current contact lists and escalation procedures
- [ ] Review and test communication channels (out-of-band if primary is compromised)
- [ ] Ensure legal review of notification obligations
- [ ] Maintain cyber insurance policy and understand coverage

#### Phase 2: Identification

**Objective**: Detect, validate, and classify the incident.

**Detection Sources**:
- Security Information and Event Management (SIEM) alerts
- Endpoint Detection and Response (EDR) alerts
- Intrusion Detection/Prevention System (IDS/IPS) alerts
- User reports (phishing, suspicious activity)
- Third-party notifications (vendors, partners, law enforcement)
- Threat intelligence feeds
- External vulnerability scanning

**Initial Triage Checklist**:
- [ ] Date and time of detection
- [ ] Source of detection (who/what identified it)
- [ ] Description of the event
- [ ] Systems, networks, and data affected
- [ ] Current status (ongoing, contained, resolved)
- [ ] Initial severity classification
- [ ] Assign incident tracking number
- [ ] Begin incident log documentation
- [ ] Notify IR Lead if severity warrants

#### Phase 3: Containment

**Objective**: Limit the scope and impact of the incident.

**Short-Term Containment** (immediate actions):
- [ ] Isolate affected systems from the network (do NOT power off if forensics needed)
- [ ] Block malicious IPs, domains, or email addresses
- [ ] Disable compromised user accounts
- [ ] Change credentials for affected accounts
- [ ] Preserve evidence (memory dumps, disk images, logs)
- [ ] Activate out-of-band communications if primary channels compromised
- [ ] Document all containment actions taken

**Long-Term Containment** (temporary fixes):
- [ ] Apply temporary security controls
- [ ] Implement network segmentation changes
- [ ] Set up enhanced monitoring of affected areas
- [ ] Coordinate with third-party providers as needed
- [ ] Brief management on containment status

#### Phase 4: Eradication

**Objective**: Remove the threat and close the attack vector.

- [ ] Identify root cause and attack vector
- [ ] Remove malware from all affected systems
- [ ] Close exploited vulnerabilities (patch, configuration change)
- [ ] Reset all potentially compromised credentials
- [ ] Review and update firewall/IDS rules
- [ ] Scan all systems for additional compromise (lateral movement)
- [ ] Verify eradication through re-scanning and monitoring
- [ ] Document eradication activities

#### Phase 5: Recovery

**Objective**: Restore systems to normal operations securely.

- [ ] Develop a recovery plan with prioritized system restoration order
- [ ] Restore systems from known-good backups (verify backup integrity)
- [ ] Rebuild compromised systems from clean images if necessary
- [ ] Re-enable disabled services and accounts
- [ ] Implement enhanced monitoring during recovery period
- [ ] Validate system functionality and data integrity
- [ ] Confirm with system owners that operations are restored
- [ ] Monitor for signs of re-compromise for at least 30 days
- [ ] Document recovery activities and timeline

#### Phase 6: Lessons Learned

**Objective**: Improve future incident response capabilities.

- [ ] Conduct post-incident review meeting within 2 weeks
- [ ] Document timeline of events, actions taken, and outcomes
- [ ] Identify what worked well and what needs improvement
- [ ] Update incident response plan based on findings
- [ ] Update detection rules and monitoring based on attack indicators
- [ ] Implement preventive measures to address root cause
- [ ] Share anonymized lessons learned with relevant teams
- [ ] Update training materials if human factors contributed
- [ ] Archive incident documentation per retention policy