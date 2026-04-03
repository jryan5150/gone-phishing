### Business Email Compromise (BEC) Playbook

**Trigger**: Email account takeover, fraudulent wire transfer request, or vendor impersonation detected.

**Immediate Actions**:
1. If a wire transfer was initiated: contact the bank immediately to halt/reverse the transfer
2. Disable the compromised email account
3. Check for email forwarding rules added by the attacker
4. Review sent items for fraudulent messages
5. Alert finance/accounting team of the compromise

**Investigation**:
1. Determine how the account was compromised (credential theft, token theft, etc.)
2. Review email access logs for unauthorized access from unusual IPs/locations
3. Check for OAuth app consent grants
4. Identify all contacts who received fraudulent emails
5. Assess financial impact

**Recovery**:
1. Reset the account password and revoke all active sessions
2. Remove unauthorized forwarding rules and app permissions
3. Notify recipients of fraudulent emails
4. Review and strengthen MFA configuration
5. Implement additional BEC protections (DMARC, impersonation protection)