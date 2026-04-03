### Phishing Incident Playbook

**Trigger**: Employee reports a suspicious email or clicks a suspected phishing link.

**If the user only received/reported (did not click)**:
1. Thank the user for reporting
2. Analyze the email headers, links, and attachments in a sandbox
3. Block the sender domain/IP at the email gateway
4. Search for the same email across all mailboxes
5. Remove all instances of the phishing email
6. Update email filtering rules

**If the user clicked a link or opened an attachment**:
1. Immediately isolate the user's workstation from the network
2. Have the user change their password from a different, clean device
3. Check for credential harvesting — was a login page spoofed?
4. If credentials were entered: force password reset, revoke active sessions, check for MFA bypass
5. Run full endpoint scan on affected workstation
6. Check email rules for unauthorized forwarding rules
7. Review audit logs for the compromised account