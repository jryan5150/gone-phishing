#!/usr/bin/env python3
"""
Incident scenario generator for the IRP (Incident Response Plan) engine.

Procedurally generates realistic MSP incident scenarios with rich combinatorial
variance across 10 categories. Designed to produce training data that feels
organic rather than templated.

Usage:
    python scripts/generate_scenarios.py                          # 2000 to stdout
    python scripts/generate_scenarios.py --count 500 --seed 42    # reproducible
    python scripts/generate_scenarios.py --output data/scenarios.json --seed 42

Pure Python — no external dependencies.
"""

import argparse
import json
import random
import sys
from typing import Any

# =============================================================================
# ENVIRONMENT POOLS
# =============================================================================

ENVIRONMENTS = [
    "mid-size law firm (80 users, hybrid cloud)",
    "small medical practice (15 users, 2 servers)",
    "school district (500 users, 12 campuses)",
    "county government (300 users, public services)",
    "manufacturing plant (200 users, OT/IT converged)",
    "accounting firm (45 users, seasonal contractors)",
    "church/religious org (20 users, volunteer-heavy)",
    "engineering firm (90 users, IP-heavy)",
    "dental group (40 users, 6 locations)",
    "real estate firm (35 users, mostly mobile)",
    "insurance agency (60 users, cloud-heavy)",
    "nonprofit (25 users, remote-first)",
    "retail chain (200 users, 15 POS locations)",
    "construction company (100 users, field + office)",
    "trucking/logistics company (75 users, GPS/IoT)",
    "regional bank (150 users, multiple branches)",
    "startup (20 users, AWS-native, zero legacy)",
    "hospice/home health (60 users, field nurses)",
    "veterinary hospital (30 users, 3 clinics)",
    "credit union (85 users, regulated)",
    "property management company (50 users, 120 properties)",
    "CPA firm (35 users, heavy tax season)",
    "funeral home group (20 users, 4 locations)",
    "auto dealership group (150 users, 6 lots)",
    "K-8 private school (40 users, BYOD policy)",
    "community college (250 users, adjunct-heavy)",
    "outpatient surgery center (55 users, HIPAA-critical)",
    "staffing agency (70 users, high turnover)",
    "pest control franchise (25 users, mobile-first)",
    "municipal water utility (60 users, SCADA + IT)",
    "architecture firm (35 users, large file storage)",
    "title company (30 users, wire transfer heavy)",
    "pediatric clinic group (45 users, 5 offices)",
    "warehousing company (80 users, WMS + barcode)",
    "tribal government (120 users, sovereignty considerations)",
]

# =============================================================================
# TIME CONTEXT POOLS
# =============================================================================

TIME_CONTEXTS = [
    "Friday 4:55 PM — end of week, skeleton crew",
    "Saturday 3:00 AM — weekend, no IT staff on-site",
    "Sunday 9:00 PM — night before major deadline",
    "Monday 8:15 AM — just after login rush",
    "Monday holiday (Memorial Day) — offices closed",
    "Monday holiday (Labor Day) — long weekend",
    "Christmas Eve — half staff, early close",
    "Wednesday 11:45 PM — overnight",
    "Tuesday 2:30 PM — middle of business day",
    "Thursday 6:00 AM — before first shift arrives",
    "during annual security audit",
    "during quarterly financial close",
    "during board meeting presentation",
    "during severe weather / power instability",
    "first day of a new employee",
    "day after IT admin gave two weeks notice",
    "during office move / network migration",
    "during open enrollment period",
    "30 minutes before court filing deadline",
    "during month-end payroll processing",
    "during a ransomware tabletop exercise (ironic)",
    "4th of July weekend — skeleton IT coverage",
    "day of a major client presentation",
    "right after deploying a major system update",
    "during back-to-school registration week",
    "during flu season — 40% of staff out sick",
    "day before state compliance audit",
    "Friday of a 3-day weekend",
    "Super Bowl Monday — half the office remote",
    "during tornado watch — staff sent home early",
    "2 hours after the backup window completed",
    "during annual all-hands meeting (everyone distracted)",
    "first Monday after daylight saving time change",
    "during a site visit from the insurance underwriter",
    "night of the company holiday party",
]

# =============================================================================
# MITRE ATT&CK TECHNIQUE POOLS (real IDs)
# =============================================================================

MITRE_TECHNIQUES = {
    "ransomware": [
        ("T1566.001", "Spearphishing Attachment"),
        ("T1486", "Data Encrypted for Impact"),
        ("T1490", "Inhibit System Recovery"),
        ("T1021.001", "Remote Desktop Protocol"),
        ("T1078", "Valid Accounts"),
        ("T1059.001", "PowerShell"),
        ("T1053.005", "Scheduled Task"),
        ("T1570", "Lateral Tool Transfer"),
        ("T1048", "Exfiltration Over Alternative Protocol"),
        ("T1562.001", "Disable or Modify Tools"),
    ],
    "phishing": [
        ("T1566.001", "Spearphishing Attachment"),
        ("T1566.002", "Spearphishing Link"),
        ("T1566.003", "Spearphishing via Service"),
        ("T1598.003", "Spearphishing Link (Recon)"),
        ("T1204.001", "Malicious Link"),
        ("T1204.002", "Malicious File"),
        ("T1534", "Internal Spearphishing"),
        ("T1114.003", "Email Forwarding Rule"),
        ("T1556.006", "Multi-Factor Authentication Interception"),
    ],
    "data_breach": [
        ("T1530", "Data from Cloud Storage"),
        ("T1567", "Exfiltration Over Web Service"),
        ("T1048", "Exfiltration Over Alternative Protocol"),
        ("T1537", "Transfer Data to Cloud Account"),
        ("T1005", "Data from Local System"),
        ("T1039", "Data from Network Shared Drive"),
        ("T1114", "Email Collection"),
        ("T1119", "Automated Collection"),
    ],
    "bec": [
        ("T1566.002", "Spearphishing Link"),
        ("T1534", "Internal Spearphishing"),
        ("T1114.003", "Email Forwarding Rule"),
        ("T1078.004", "Cloud Accounts"),
        ("T1098.005", "Device Registration"),
        ("T1556.006", "Multi-Factor Authentication Interception"),
    ],
    "insider_threat": [
        ("T1078", "Valid Accounts"),
        ("T1005", "Data from Local System"),
        ("T1074", "Data Staged"),
        ("T1567.002", "Exfiltration to Cloud Storage"),
        ("T1070.004", "File Deletion"),
        ("T1485", "Data Destruction"),
        ("T1531", "Account Access Removal"),
        ("T1098", "Account Manipulation"),
    ],
    "denial_of_service": [
        ("T1498", "Network Denial of Service"),
        ("T1499", "Endpoint Denial of Service"),
        ("T1499.002", "Service Exhaustion Flood"),
        ("T1498.001", "Direct Network Flood"),
        ("T1496", "Resource Hijacking"),
    ],
    "unauthorized_access": [
        ("T1110.003", "Password Spraying"),
        ("T1110.004", "Credential Stuffing"),
        ("T1558.003", "Kerberoasting"),
        ("T1558.001", "Golden Ticket"),
        ("T1078", "Valid Accounts"),
        ("T1021.001", "Remote Desktop Protocol"),
        ("T1021.006", "Windows Remote Management"),
        ("T1550.002", "Pass the Hash"),
    ],
    "supply_chain": [
        ("T1195.001", "Compromise Software Dependencies"),
        ("T1195.002", "Compromise Software Supply Chain"),
        ("T1199", "Trusted Relationship"),
        ("T1072", "Software Deployment Tools"),
        ("T1553.002", "Code Signing"),
    ],
    "physical_security": [
        ("T1200", "Hardware Additions"),
        ("T1091", "Replication Through Removable Media"),
        ("T1052.001", "Exfiltration over USB"),
    ],
    "web_app_attack": [
        ("T1190", "Exploit Public-Facing Application"),
        ("T1059.007", "JavaScript"),
        ("T1505.003", "Web Shell"),
        ("T1595.002", "Vulnerability Scanning"),
    ],
}

# =============================================================================
# RANSOMWARE VARIANT POOLS
# =============================================================================

RANSOMWARE_VARIANTS = [
    "LockBit 3.0", "BlackCat/ALPHV", "Clop", "Royal", "Akira", "Play",
    "Rhysida", "Hunters International", "NoEscape", "BlackSuit", "Qilin",
    "Medusa", "BianLian", "Hive", "Black Basta", "Vice Society",
    "8Base", "Cactus", "INC Ransom", "Trigona",
]

# =============================================================================
# CATEGORY-SPECIFIC COMPONENT POOLS
# =============================================================================

# --- Ransomware ---

RANSOMWARE_ENTRY_VECTORS = [
    "phishing email with macro-enabled attachment",
    "exposed RDP on port 3389",
    "exploited PrintNightmare vulnerability",
    "stolen VPN credentials from infostealer logs",
    "compromised MSP remote access tool",
    "brute-forced admin credentials on SonicWall",
    "supply chain compromise via software update",
    "malicious Google Ads redirecting to fake installer",
    "exploited CVE-2023-27997 in FortiGate SSL VPN",
    "compromised legitimate remote support session",
    "USB drive left in parking lot",
    "exploited unpatched Exchange Server (ProxyShell)",
    "callback phishing — user called fake IT support number",
    "Cobalt Strike beacon delivered via Discord CDN",
    "compromised third-party IT vendor credentials",
    "trojanized installer from watering hole site",
    "SEO-poisoned search result for common business software",
]

RANSOMWARE_TARGETS = [
    "domain controller", "file server", "SQL database server",
    "backup server (Veeam)", "SharePoint server", "print server",
    "SCADA workstation", "accounting server (QuickBooks host)",
    "EMR/EHR system", "RDS session host", "Exchange mailbox store",
    "NAS appliance with shared drives", "virtual host (ESXi)",
    "payroll processing system", "case management server",
    "document management system (iManage)", "imaging server (PACS)",
]

RANSOMWARE_IMPACTS = [
    "lateral movement to {n} network segments",
    "Active Directory compromised",
    "all files encrypted with .locked extension",
    "backup volumes deleted before encryption",
    "production line halted",
    "double extortion — data posted on leak site",
    "ESXi hosts encrypted, all VMs offline",
    "500+ endpoints showing ransom note",
    "network shares encrypted across {n} departments",
    "print spooler broadcasting ransom note to all printers",
    "encryption spreading via Group Policy push",
    "shadow copies and recovery partitions wiped",
    "domain admin account compromised — full network access",
    "ransomware dormant for {days} days before detonation",
]

RANSOMWARE_DEMANDS = [
    "$500,000 in Monero",
    "2 BTC ($180K)",
    "$1.2M with 72-hour countdown",
    "negotiation portal on Tor",
    "$250K with claim of 200GB exfiltrated data",
    "demand doubles after 3 days",
    "$75K — unusually low, suggests automated deployment",
    "$2.5M — mentions regulatory filing deadline as leverage",
    "15 BTC with proof-of-life file decryptor",
    "$800K, threatening to notify clients directly",
    "no set amount — 'contact us to discuss'",
    "$350K, countdown timer at 48 hours",
]

# --- Phishing ---

PHISHING_PRETEXTS = [
    "password expiration notice from IT",
    "fake Microsoft 365 login page",
    "package delivery notification (UPS/FedEx)",
    "voicemail notification with malicious link",
    "DocuSign request for urgent contract",
    "IRS tax refund notification",
    "board meeting document share from CEO",
    "fake Slack workspace invite",
    "urgent wire transfer approval from CFO",
    "shared OneDrive file from known vendor",
    "calendar invite with malicious Teams link",
    "QR code in physical mail piece",
    "fake IT helpdesk ticket update",
    "LinkedIn connection from recruiter with attachment",
    "W-2 request posing as HR director",
    "invoice from 'new' approved vendor",
    "MFA reset notification — 'verify your identity'",
    "fake browser update popup on legitimate site",
    "Zoom meeting invite with credential harvester link",
    "shared Google Doc that requests OAuth permissions",
]

PHISHING_USER_ACTIONS = [
    "user entered credentials on spoofed portal",
    "user opened macro-enabled Word attachment",
    "user downloaded and ran .exe disguised as PDF",
    "user entered MFA code on spoofed portal",
    "user called phone number in vishing attempt",
    "user scanned QR code with personal phone",
    "user approved OAuth consent for malicious app",
    "3 users clicked before anyone reported",
    "user forwarded to entire department before reporting",
    "user entered credentials, then provided MFA token via phone",
    "user opened HTML smuggling attachment in browser",
    "executive assistant entered CEO credentials on look-alike domain",
]

PHISHING_RESULTS = [
    "reverse shell established via PowerShell",
    "MFA fatigue attack succeeded — user approved push",
    "QBot loader deployed to workstation",
    "attacker established persistence via scheduled task",
    "email forwarding rule silently exfiltrating mail",
    "Emotet dropper installed, beaconing to C2",
    "OAuth token granted — attacker reading mailbox",
    "credentials harvested, sold on dark web within 6 hours",
    "browser session cookies stolen via AitM proxy",
    "attacker registered MFA device on compromised account",
    "IcedID payload delivered, lateral movement beginning",
    "no payload yet — credential phish only, account compromised",
    "Gootloader infection chain initiated",
    "remote access trojan (RAT) installed silently",
]

# --- Data Breach ---

DATA_TYPES = [
    "PHI (protected health information)",
    "PII — full SSNs + DOBs",
    "payment card data (PCI scope)",
    "student education records (FERPA)",
    "client legal files (privileged)",
    "employee HR records with salary data",
    "CUI (controlled unclassified information)",
    "tax returns and financial statements",
    "architectural blueprints and bid proposals",
    "customer credit applications with SSN",
    "donor records with payment methods",
    "proprietary manufacturing formulas",
    "patient dental imaging and records",
    "vehicle owner financial records",
    "law enforcement case files",
    "insurance claim records with medical details",
]

DATA_VOLUMES = [
    "47 records (executives only)",
    "2,300 records",
    "12,000 records spanning 3 years",
    "180,000 rows exported to CSV",
    "full database dump — estimated 500K records",
    "340 patient files",
    "unknown volume — still investigating scope",
    "7GB compressed archive",
    "entire accounts receivable database",
    "1,200 client files with attached documents",
    "38 records — targeted, not bulk",
]

DATA_BREACH_VECTORS = [
    "misconfigured S3 bucket — public since deployment",
    "SQL injection on patient portal",
    "former employee retained access post-termination",
    "third-party vendor compromised (shared credentials)",
    "insider copied to personal device",
    "API key exposed in public GitHub repo",
    "unencrypted laptop stolen from parked car",
    "backup tape lost during office relocation",
    "cloud storage sharing link set to 'anyone with link'",
    "phishing led to mailbox access, then data exfil",
    "print job left on shared printer overnight",
    "misconfigured firewall rule exposed database port",
    "screenshot of records posted on social media",
    "RMM tool credentials compromised, data extracted remotely",
]

# --- BEC ---

BEC_SCHEMES = [
    "vendor invoice with altered bank routing info",
    "CEO impersonation requesting emergency wire",
    "fake real estate closing wire instructions",
    "compromised vendor email thread — invoice swap mid-conversation",
    "W-2/payroll diversion request to HR",
    "gift card purchase request from 'executive'",
    "fake attorney demanding urgent settlement payment",
    "partner email compromised — fraudulent capital call",
    "thread hijack: reply inserted into real vendor conversation",
    "impersonation of client requesting refund to new account",
    "spoofed CFO email during M&A due diligence",
    "compromised email used to redirect payroll direct deposits",
]

BEC_FINANCIAL_EXPOSURES = [
    "$12,500", "$23,000", "$47,000", "$85,000",
    "$125,000", "$240,000", "$380,000", "$18,500",
    "$67,000 (wire already sent)", "$9,800 in gift cards",
    "$450,000 (real estate transaction)",
    "$55,000 — caught before wire completed",
    "$175,000 split across 3 transactions",
    "$32,000 in payroll diversion over 2 pay periods",
]

BEC_INDICATORS = [
    "forwarding rule sending copies to external address",
    "reply-to domain off by one character (typosquat)",
    "email originated from non-corporate IP",
    "MFA prompt approved at unusual hour",
    "new inbox rule hiding 'wire' and 'payment' emails",
    "sent folder shows emails user doesn't recognize",
    "email headers show different envelope sender",
    "victims email account sending internal spearphish to others",
    "account accessed from VPN exit node in different country",
    "display name matched but email domain was .co not .com",
]

# --- Insider Threat ---

INSIDER_ACTORS = [
    "disgruntled sysadmin after demotion",
    "employee in final 2 weeks after resignation",
    "contractor with excessive access permissions",
    "IT intern with domain admin (policy violation)",
    "bookkeeper with access to all financial systems",
    "terminated employee — account not yet disabled",
    "nurse with access to celebrity patient records",
    "developer copying source code before leaving for competitor",
    "executive assistant accessing files outside job scope",
    "warehouse manager manipulating inventory records",
    "part-time employee with full-time access",
    "vendor technician with unmonitored remote access",
    "temp worker hired through staffing agency",
    "long-tenured employee passed over for promotion",
]

INSIDER_ACTIONS = [
    "bulk download of client files to USB drive",
    "accessed systems outside of job scope",
    "emailed proprietary data to personal Gmail",
    "modified financial records to cover embezzlement",
    "deleted shared drives and changed admin passwords",
    "installed keylogger on supervisor's workstation",
    "exported CRM database to personal Dropbox",
    "created backdoor admin account",
    "accessed patient records without treatment relationship",
    "shared credentials with unauthorized third party",
    "copied source code repository to external drive",
    "disabled security monitoring on specific systems",
    "took photos of screen with personal phone",
    "ran unauthorized cryptocurrency miner on server",
    "forwarded confidential board minutes to external party",
    "modified access logs to cover tracks",
]

INSIDER_DATA_RISKS = [
    "50GB to Google Drive",
    "client list and pricing shared with competitor",
    "2 years of financial records",
    "entire customer database (15K records)",
    "source code for flagship product",
    "employee SSNs and salary information",
    "confidential merger documents",
    "patient records for 340 individuals",
    "security system credentials and documentation",
    "vendor contracts with pricing terms",
    "board meeting recordings and minutes",
    "trade secrets and manufacturing processes",
]

# --- Denial of Service ---

DOS_ATTACK_TYPES = [
    "volumetric DDoS — 45 Gbps UDP flood",
    "application-layer HTTP flood",
    "DNS amplification attack",
    "botnet-driven layer 7 attack",
    "SYN flood targeting web servers",
    "internal resource exhaustion from cryptominer",
    "slowloris attack tying up all HTTP connections",
    "NTP amplification — 60x traffic multiplier",
    "carpet bombing attack across /24 subnet",
    "SSL/TLS renegotiation flood",
    "memcached reflection attack",
    "ICMP flood from compromised IoT devices on network",
]

DOS_IMPACTS = [
    "client-facing portal unreachable",
    "email and VoIP systems offline",
    "payment processing system offline",
    "SaaS application latency increased 10x",
    "internet connection saturated — all services affected",
    "web application returning 503 to all users",
    "VPN concentrator overwhelmed — remote workers disconnected",
    "upstream ISP null-routing our IP block",
    "phone system (SIP) completely unusable",
    "online scheduling system down during peak booking hours",
    "e-commerce storefront offline during promotional event",
    "API gateway returning timeouts to all integrations",
    "DNS resolution failing intermittently",
]

# --- Unauthorized Access ---

UNAUTH_METHODS = [
    "credential stuffing with leaked database",
    "password spraying against OWA",
    "golden ticket attack using extracted krbtgt hash",
    "exploited default credentials on network appliance",
    "brute force on SSH — weak root password",
    "pass-the-hash using cached NTLM hashes",
    "Kerberoasting — cracked service account password",
    "stolen session cookie from compromised browser",
    "MFA bypass via SIM swap",
    "exploitation of misconfigured SAML SSO",
    "VPN credential reuse from prior breach",
    "compromised service account with no MFA",
    "social engineering of helpdesk for password reset",
    "LDAP injection against self-service portal",
    "OAuth token theft via redirect manipulation",
]

UNAUTH_DISCOVERIES = [
    "impossible travel alert in SIEM",
    "failed login spike followed by successful access",
    "lateral movement detected by EDR",
    "honeypot file accessed on file share",
    "unusual PowerShell execution flagged",
    "data exfiltration volume triggered DLP alert",
    "user reported account locked out unexpectedly",
    "new admin account created at 2:00 AM",
    "antivirus quarantined Mimikatz on domain controller",
    "VPN connection from country with no employees",
    "canary token triggered in sensitive directory",
    "IT noticed unfamiliar RDP sessions in event log",
    "cloud access security broker flagged bulk download",
]

# --- Supply Chain ---

SUPPLY_CHAIN_VECTORS = [
    "compromised update pushed through RMM tool",
    "trojanized npm package in build pipeline",
    "vendor's email system compromised — sent malicious links to all clients",
    "managed print service vendor backdoor found",
    "MSP's credential vault breached — client access exposed",
    "compromised WordPress plugin on vendor's managed site",
    "malware injected into vendor-provided firmware update",
    "HVAC vendor's remote access used as entry point",
    "payroll SaaS provider breach — customer data exposed",
    "legal document exchange portal compromised",
    "IT distributor shipped pre-infected hardware",
    "cloud backup vendor experienced ransomware — client backups encrypted",
    "compromised code-signing certificate used by software vendor",
    "MFA provider had authentication bypass vulnerability",
]

SUPPLY_CHAIN_IMPACTS = [
    "5 of our managed clients affected simultaneously",
    "attackers used trusted tool to bypass EDR",
    "malicious code ran with SYSTEM privileges",
    "unable to patch — vendor hasn't released fix yet",
    "client data exposed through vendor's infrastructure",
    "vendor denying breach — our telemetry says otherwise",
    "lateral spread to 3 clients via shared RMM session",
    "software update channel now untrusted — manual patching required",
    "backups potentially compromised — recovery plan uncertain",
    "need to rotate every credential the vendor had access to",
    "supply chain partner is also an MSP — cascading risk",
    "firmware integrity cannot be verified without vendor cooperation",
]

# --- Physical Security ---

PHYSICAL_INCIDENTS = [
    "former employee badge still active — accessed building",
    "tailgating into server room behind delivery driver",
    "USB drive with malware found plugged into lobby kiosk",
    "cleaning crew photographed whiteboard with credentials",
    "laptop stolen from unlocked car in parking lot",
    "server room door propped open — no alarm triggered",
    "unauthorized person found in wiring closet",
    "dumpster diver recovered unshredded documents",
    "social engineer posed as fire inspector — given full access",
    "security camera footage shows unknown person at server rack",
    "employee left building without locking classified file cabinet",
    "visitor badge not collected — person remained after hours",
    "construction crew cut fiber while drilling",
    "network switch found in ceiling tile (rogue device)",
    "someone removed hard drives from decommissioned PCs in storage",
    "water leak in server room — discovered 12 hours later",
    "AC failure in server closet — temps hit 105F before alert",
    "fire suppression system triggered by dust during renovation",
]

PHYSICAL_DATA_RISKS = [
    "server room contains unencrypted backup drives",
    "access to network jacks in unsecured areas",
    "physical keylogger could have been installed",
    "paper records with PHI visible on desks",
    "badge cloning is trivial — no smart card in use",
    "security cameras were offline for maintenance",
    "no visitor log — cannot determine who was in the building",
    "fire safe with backup tapes was left unlocked",
]

# --- Web Application ---

WEB_ATTACK_TYPES = [
    "SQL injection on login form",
    "stored XSS in customer portal",
    "IDOR allowing access to other users' records",
    "authentication bypass via JWT none algorithm",
    "remote code execution via file upload",
    "SSRF through PDF generation feature",
    "deserialization vulnerability in API endpoint",
    "path traversal accessing /etc/passwd",
    "brute force on API with no rate limiting",
    "XML external entity (XXE) injection",
    "CORS misconfiguration exposing API to any origin",
    "mass assignment vulnerability on user profile update",
    "broken access control — horizontal privilege escalation",
    "template injection in email generation feature",
    "exposed debug endpoint in production",
]

WEB_TARGETS = [
    "patient portal (internet-facing)",
    "client document sharing platform",
    "online payment gateway",
    "employee self-service HR portal",
    "customer scheduling application",
    "internal wiki/knowledge base",
    "vendor management portal",
    "WordPress marketing site with WooCommerce",
    "custom CRM web interface",
    "student information system (SIS)",
    "board meeting portal with financial documents",
    "online case filing system",
    "inventory management web app",
    "benefits enrollment portal",
]

WEB_CONSEQUENCES = [
    "full database dump downloaded by attacker",
    "session tokens of active users exposed",
    "web shell uploaded — persistent backdoor",
    "admin account created via API manipulation",
    "customer payment data exfiltrated",
    "defacement — homepage replaced with political message",
    "cryptominer injected into page JavaScript",
    "redirecting visitors to credential harvesting site",
    "data modification — records altered silently",
    "complete source code of application leaked",
]

# =============================================================================
# SEVERITY DISTRIBUTION
# =============================================================================

# Weighted distribution: S2/S3 are most common, S1/S4 are rare
# Approximation: S1 ~10%, S2 ~35%, S3 ~40%, S4 ~15%
SEVERITY_WEIGHTS = {
    "S1": 10,
    "S2": 35,
    "S3": 40,
    "S4": 15,
}

# Some categories skew severity up or down
CATEGORY_SEVERITY_ADJUSTMENTS: dict[str, dict[str, int]] = {
    "ransomware": {"S1": 20, "S2": 35, "S3": 30, "S4": 15},
    "data_breach": {"S1": 15, "S2": 40, "S3": 30, "S4": 15},
    "physical_security": {"S1": 5, "S2": 20, "S3": 50, "S4": 25},
    "phishing": {"S1": 5, "S2": 30, "S3": 45, "S4": 20},
}

# =============================================================================
# CATEGORY DISTRIBUTION (weighted — mirrors real MSP incident mix)
# =============================================================================

CATEGORY_WEIGHTS = {
    "ransomware": 15,
    "phishing": 18,
    "data_breach": 12,
    "bec": 12,
    "insider_threat": 10,
    "denial_of_service": 8,
    "unauthorized_access": 8,
    "supply_chain": 7,
    "physical_security": 5,
    "web_app_attack": 5,
}

# =============================================================================
# DESCRIPTION BUILDERS (multiple structures per category)
# =============================================================================


def _pick(pool: list) -> str:
    """Pick a random item from a pool."""
    return random.choice(pool)


def _maybe(prob: float, text: str) -> str:
    """Return text with given probability, empty string otherwise."""
    return text if random.random() < prob else ""


def _pick_mitre(category: str) -> str | None:
    """Maybe pick a MITRE technique reference (30% chance)."""
    if random.random() < 0.30 and category in MITRE_TECHNIQUES:
        tid, name = random.choice(MITRE_TECHNIQUES[category])
        return f"{tid} ({name})"
    return None


def _severity(category: str) -> str:
    """Pick a severity with weighted distribution, adjusted by category."""
    weights = CATEGORY_SEVERITY_ADJUSTMENTS.get(category, SEVERITY_WEIGHTS)
    population = list(weights.keys())
    w = list(weights.values())
    return random.choices(population, weights=w, k=1)[0]


def _fmt_impact_template(template: str) -> str:
    """Fill numeric placeholders in impact strings."""
    result = template
    if "{n}" in result:
        result = result.replace("{n}", str(random.randint(2, 8)))
    if "{days}" in result:
        result = result.replace("{days}", str(random.randint(7, 90)))
    return result


# --- Ransomware description builders ---

def _ransomware_desc_detailed(env: str) -> str:
    variant = _pick(RANSOMWARE_VARIANTS)
    entry = _pick(RANSOMWARE_ENTRY_VECTORS)
    target = _pick(RANSOMWARE_TARGETS)
    impact = _fmt_impact_template(_pick(RANSOMWARE_IMPACTS))
    demand = _pick(RANSOMWARE_DEMANDS)
    mitre = _pick_mitre("ransomware")

    base = f"{variant} ransomware detected at {env}."
    base += f" Entry vector: {entry}."
    base += f" Primary target: {target}."
    base += f" Current impact: {impact}."
    base += f" Ransom demand: {demand}."
    if mitre:
        base += f" MITRE ATT&CK: {mitre}."
    return base


def _ransomware_desc_terse(env: str) -> str:
    variant = _pick(RANSOMWARE_VARIANTS)
    target = _pick(RANSOMWARE_TARGETS)
    demand = _pick(RANSOMWARE_DEMANDS)

    return (
        f"Active {variant} infection — {target} encrypted. "
        f"Ransom demand: {demand}. Incident at {env}."
    )


def _ransomware_desc_narrative(env: str) -> str:
    variant = _pick(RANSOMWARE_VARIANTS)
    entry = _pick(RANSOMWARE_ENTRY_VECTORS)
    impact = _fmt_impact_template(_pick(RANSOMWARE_IMPACTS))
    demand = _pick(RANSOMWARE_DEMANDS)
    mitre = _pick_mitre("ransomware")

    parts = [
        f"At {env}, a {variant} ransomware attack is in progress.",
        f"Initial access was gained via {entry}.",
    ]
    if random.random() < 0.5:
        parts.append(f"Impact so far: {impact}.")
    else:
        parts.append(f"The attacker has achieved the following: {impact}.")
    parts.append(f"Demand: {demand}.")
    if mitre:
        parts.append(f"Technique aligns with {mitre}.")
    return " ".join(parts)


def _ransomware_desc_discovery(env: str) -> str:
    variant = _pick(RANSOMWARE_VARIANTS)
    target = _pick(RANSOMWARE_TARGETS)
    entry = _pick(RANSOMWARE_ENTRY_VECTORS)
    impact = _fmt_impact_template(_pick(RANSOMWARE_IMPACTS))

    openers = [
        f"SOC alert triggered: {variant} indicators detected at {env}.",
        f"Endpoint Detection flagged {variant} activity at {env}.",
        f"User reported ransom note on screen at {env} — confirmed {variant}.",
        f"Automated honeypot triggered at {env}. Analysis confirms {variant}.",
    ]
    base = _pick(openers)
    base += f" Likely entry: {entry}. Affected system: {target}."
    if random.random() < 0.6:
        base += f" Status: {impact}."
    return base


RANSOMWARE_BUILDERS = [
    _ransomware_desc_detailed,
    _ransomware_desc_terse,
    _ransomware_desc_narrative,
    _ransomware_desc_discovery,
]


# --- Phishing description builders ---

def _phishing_desc_standard(env: str) -> str:
    pretext = _pick(PHISHING_PRETEXTS)
    action = _pick(PHISHING_USER_ACTIONS)
    result = _pick(PHISHING_RESULTS)
    mitre = _pick_mitre("phishing")

    base = f"Phishing incident at {env}."
    base += f" Pretext: {pretext}."
    base += f" User action: {action}."
    base += f" Result: {result}."
    if mitre:
        base += f" MITRE: {mitre}."
    return base


def _phishing_desc_campaign(env: str) -> str:
    pretext = _pick(PHISHING_PRETEXTS)
    count = random.randint(5, 80)
    clicked = random.randint(1, max(1, count // 5))
    result = _pick(PHISHING_RESULTS)

    base = f"Phishing campaign targeting {env}: {count} users received emails."
    base += f" Lure: {pretext}. {clicked} user(s) interacted."
    if clicked > 1:
        base += f" At least one led to: {result}."
    else:
        base += f" Result: {result}."
    if random.random() < 0.3:
        base += " Additional recipients may have interacted — investigation ongoing."
    return base


def _phishing_desc_reported(env: str) -> str:
    pretext = _pick(PHISHING_PRETEXTS)
    action = _pick(PHISHING_USER_ACTIONS)

    openers = [
        f"User at {env} reported suspicious email — {pretext}.",
        f"Phish reported via Outlook button at {env}. Pretext: {pretext}.",
        f"Help desk ticket at {env}: 'I think I clicked a bad link.'",
    ]
    base = _pick(openers)
    if random.random() < 0.7:
        base += f" On investigation: {action}."
    result = _pick(PHISHING_RESULTS)
    base += f" Current status: {result}."
    return base


def _phishing_desc_spearphish(env: str) -> str:
    pretext = _pick(PHISHING_PRETEXTS)
    result = _pick(PHISHING_RESULTS)
    mitre = _pick_mitre("phishing")

    targets = [
        "CFO", "office manager", "HR director", "managing partner",
        "accounts payable clerk", "practice administrator", "superintendent",
    ]
    target = _pick(targets)
    base = f"Targeted spearphishing at {env} — {target} was the intended victim."
    base += f" Lure: {pretext}."
    if random.random() < 0.5:
        base += f" Outcome: {result}."
    else:
        base += " User engaged with the email but has not confirmed credential entry."
    if mitre:
        base += f" Technique: {mitre}."
    return base


PHISHING_BUILDERS = [
    _phishing_desc_standard,
    _phishing_desc_campaign,
    _phishing_desc_reported,
    _phishing_desc_spearphish,
]


# --- Data Breach description builders ---

def _breach_desc_standard(env: str) -> str:
    dtype = _pick(DATA_TYPES)
    volume = _pick(DATA_VOLUMES)
    vector = _pick(DATA_BREACH_VECTORS)
    mitre = _pick_mitre("data_breach")

    base = f"Data breach at {env}."
    base += f" Data type: {dtype}."
    base += f" Estimated volume: {volume}."
    base += f" Attack vector: {vector}."
    if mitre:
        base += f" Technique: {mitre}."
    return base


def _breach_desc_discovered(env: str) -> str:
    dtype = _pick(DATA_TYPES)
    volume = _pick(DATA_VOLUMES)
    vector = _pick(DATA_BREACH_VECTORS)

    discoveries = [
        "Breach discovered by third-party notification",
        "Dark web monitoring service flagged exposed data",
        "Client reported receiving suspicious contact referencing their records",
        "Routine access log review revealed anomalous export",
        "Penetration tester found the exposure during scheduled assessment",
    ]
    base = f"{_pick(discoveries)} at {env}."
    base += f" Compromised: {dtype} — approximately {volume}."
    base += f" Root cause: {vector}."
    if random.random() < 0.4:
        base += " Regulatory notification deadline may apply."
    return base


def _breach_desc_regulatory(env: str) -> str:
    dtype = _pick(DATA_TYPES)
    volume = _pick(DATA_VOLUMES)
    vector = _pick(DATA_BREACH_VECTORS)

    regs = {
        "PHI (protected health information)": "HIPAA breach notification required within 60 days",
        "PII — full SSNs + DOBs": "State breach notification laws triggered in 3+ states",
        "payment card data (PCI scope)": "PCI DSS incident response procedures activated",
        "student education records (FERPA)": "FERPA notification requirements apply",
        "CUI (controlled unclassified information)": "CMMC/DFARS reporting requirements in play",
    }
    reg_note = regs.get(dtype, "Regulatory impact assessment needed")

    base = f"Confirmed data breach at {env}. Exposed: {dtype} ({volume})."
    base += f" Cause: {vector}."
    base += f" Compliance note: {reg_note}."
    return base


BREACH_BUILDERS = [
    _breach_desc_standard,
    _breach_desc_discovered,
    _breach_desc_regulatory,
]


# --- BEC description builders ---

def _bec_desc_standard(env: str) -> str:
    scheme = _pick(BEC_SCHEMES)
    exposure = _pick(BEC_FINANCIAL_EXPOSURES)
    indicator = _pick(BEC_INDICATORS)
    mitre = _pick_mitre("bec")

    base = f"BEC incident at {env}."
    base += f" Scheme: {scheme}."
    base += f" Financial exposure: {exposure}."
    base += f" Detection indicator: {indicator}."
    if mitre:
        base += f" MITRE: {mitre}."
    return base


def _bec_desc_narrative(env: str) -> str:
    scheme = _pick(BEC_SCHEMES)
    exposure = _pick(BEC_FINANCIAL_EXPOSURES)
    indicator = _pick(BEC_INDICATORS)

    base = f"Finance team at {env} flagged a suspicious transaction."
    base += f" Investigation reveals: {scheme}."
    base += f" Estimated loss: {exposure}."
    if random.random() < 0.6:
        base += f" How it was caught: {indicator}."
    if random.random() < 0.3:
        base += " Wire recall has been initiated with the receiving bank."
    return base


def _bec_desc_compromise_chain(env: str) -> str:
    scheme = _pick(BEC_SCHEMES)
    exposure = _pick(BEC_FINANCIAL_EXPOSURES)
    indicator = _pick(BEC_INDICATORS)
    phish = _pick(PHISHING_PRETEXTS)

    base = f"Multi-stage BEC attack at {env}."
    base += f" Stage 1: initial phishing — {phish}."
    base += f" Stage 2: {scheme}."
    base += f" Financial impact: {exposure}."
    base += f" Signal: {indicator}."
    return base


BEC_BUILDERS = [
    _bec_desc_standard,
    _bec_desc_narrative,
    _bec_desc_compromise_chain,
]


# --- Insider Threat description builders ---

def _insider_desc_standard(env: str) -> str:
    actor = _pick(INSIDER_ACTORS)
    action = _pick(INSIDER_ACTIONS)
    risk = _pick(INSIDER_DATA_RISKS)
    mitre = _pick_mitre("insider_threat")

    base = f"Insider threat at {env}."
    base += f" Actor: {actor}."
    base += f" Action detected: {action}."
    base += f" Data at risk: {risk}."
    if mitre:
        base += f" Technique: {mitre}."
    return base


def _insider_desc_behavioral(env: str) -> str:
    actor = _pick(INSIDER_ACTORS)
    action = _pick(INSIDER_ACTIONS)
    risk = _pick(INSIDER_DATA_RISKS)

    signals = [
        "after-hours access patterns increased 400% this week",
        "DLP flagged 3 policy violations in 48 hours",
        "manager reported unusual behavior changes",
        "SIEM correlation identified access anomaly",
        "peer reported suspicious conversation about data access",
    ]
    base = f"Behavioral alert at {env}: {_pick(signals)}."
    base += f" Subject: {actor}."
    base += f" Observed activity: {action}."
    if random.random() < 0.6:
        base += f" Potential exposure: {risk}."
    return base


def _insider_desc_exfil(env: str) -> str:
    actor = _pick(INSIDER_ACTORS)
    risk = _pick(INSIDER_DATA_RISKS)

    methods = [
        "USB mass storage device connected to workstation",
        "personal email sent with large attachment",
        "cloud sync client installed without authorization",
        "screen recording software found running",
        "large print job to personal printer detected",
        "AirDrop transfer detected on corporate Mac",
    ]
    base = f"Data exfiltration detected at {env}."
    base += f" Actor: {actor}."
    base += f" Method: {_pick(methods)}."
    base += f" Data: {risk}."
    return base


INSIDER_BUILDERS = [
    _insider_desc_standard,
    _insider_desc_behavioral,
    _insider_desc_exfil,
]


# --- Denial of Service description builders ---

def _dos_desc_standard(env: str) -> str:
    attack = _pick(DOS_ATTACK_TYPES)
    impact = _pick(DOS_IMPACTS)
    mitre = _pick_mitre("denial_of_service")

    base = f"Denial of service at {env}."
    base += f" Attack type: {attack}."
    base += f" Impact: {impact}."
    if mitre:
        base += f" MITRE: {mitre}."
    return base


def _dos_desc_timeline(env: str) -> str:
    attack = _pick(DOS_ATTACK_TYPES)
    impact = _pick(DOS_IMPACTS)
    minutes = random.choice([5, 10, 15, 20, 30, 45, 60, 90])

    base = f"DDoS attack ongoing at {env} for approximately {minutes} minutes."
    base += f" Classification: {attack}."
    base += f" Business impact: {impact}."
    if random.random() < 0.4:
        base += " Upstream mitigation has been requested but not yet active."
    if random.random() < 0.3:
        base += " Attack volume is increasing."
    return base


def _dos_desc_internal(env: str) -> str:
    impact = _pick(DOS_IMPACTS)

    causes = [
        "runaway database query consuming all CPU",
        "cryptominer consuming 95% of server resources",
        "recursive script filling disk to capacity",
        "broadcast storm from misconfigured switch",
        "memory leak in custom application crashed host",
        "backup job and virus scan running simultaneously overwhelmed storage I/O",
    ]
    base = f"Internal denial of service condition at {env}."
    base += f" Cause: {_pick(causes)}."
    base += f" Result: {impact}."
    return base


DOS_BUILDERS = [
    _dos_desc_standard,
    _dos_desc_timeline,
    _dos_desc_internal,
]


# --- Unauthorized Access description builders ---

def _unauth_desc_standard(env: str) -> str:
    method = _pick(UNAUTH_METHODS)
    discovery = _pick(UNAUTH_DISCOVERIES)
    mitre = _pick_mitre("unauthorized_access")

    base = f"Unauthorized access at {env}."
    base += f" Method: {method}."
    base += f" Discovery: {discovery}."
    if mitre:
        base += f" MITRE: {mitre}."
    return base


def _unauth_desc_active(env: str) -> str:
    method = _pick(UNAUTH_METHODS)
    discovery = _pick(UNAUTH_DISCOVERIES)

    base = f"Active unauthorized access at {env} — attacker may still be in the network."
    base += f" Initial access via {method}."
    base += f" Detected when: {discovery}."
    if random.random() < 0.5:
        systems = random.randint(1, 6)
        base += f" {systems} system(s) confirmed accessed so far."
    return base


def _unauth_desc_historical(env: str) -> str:
    method = _pick(UNAUTH_METHODS)
    days = random.randint(3, 120)

    base = f"Unauthorized access discovered at {env} — evidence suggests access for {days} days."
    base += f" Method: {method}."
    if random.random() < 0.5:
        base += " Scope of data accessed is still being determined."
    else:
        base += f" Discovery trigger: {_pick(UNAUTH_DISCOVERIES)}."
    return base


UNAUTH_BUILDERS = [
    _unauth_desc_standard,
    _unauth_desc_active,
    _unauth_desc_historical,
]


# --- Supply Chain description builders ---

def _supply_chain_desc_standard(env: str) -> str:
    vector = _pick(SUPPLY_CHAIN_VECTORS)
    impact = _pick(SUPPLY_CHAIN_IMPACTS)
    mitre = _pick_mitre("supply_chain")

    base = f"Supply chain compromise affecting {env}."
    base += f" Vector: {vector}."
    base += f" Impact: {impact}."
    if mitre:
        base += f" MITRE: {mitre}."
    return base


def _supply_chain_desc_vendor(env: str) -> str:
    vector = _pick(SUPPLY_CHAIN_VECTORS)
    impact = _pick(SUPPLY_CHAIN_IMPACTS)

    base = f"Vendor-originated security incident at {env}."
    base += f" Root cause: {vector}."
    base += f" Current status: {impact}."
    if random.random() < 0.4:
        base += " Vendor has been notified and is not yet responsive."
    elif random.random() < 0.5:
        base += " Vendor acknowledged the issue and is deploying a patch."
    return base


def _supply_chain_desc_cascade(env: str) -> str:
    vector = _pick(SUPPLY_CHAIN_VECTORS)
    affected = random.randint(2, 12)

    base = f"Cascading supply chain incident originating from {vector}."
    base += f" {env} is one of {affected} confirmed affected organizations."
    if random.random() < 0.5:
        base += " Shared infrastructure makes isolation difficult."
    else:
        base += " Full scope of compromise unknown — other clients may be at risk."
    return base


SUPPLY_CHAIN_BUILDERS = [
    _supply_chain_desc_standard,
    _supply_chain_desc_vendor,
    _supply_chain_desc_cascade,
]


# --- Physical Security description builders ---

def _physical_desc_standard(env: str) -> str:
    incident = _pick(PHYSICAL_INCIDENTS)
    mitre = _pick_mitre("physical_security")

    base = f"Physical security incident at {env}."
    base += f" Details: {incident}."
    if random.random() < 0.5:
        base += f" Additional risk: {_pick(PHYSICAL_DATA_RISKS)}."
    if mitre:
        base += f" MITRE: {mitre}."
    return base


def _physical_desc_discovered(env: str) -> str:
    incident = _pick(PHYSICAL_INCIDENTS)

    how = [
        "Discovered during routine security walk-through",
        "Security camera review revealed the incident",
        "Employee reported the situation to office manager",
        "Badge access logs showed the anomaly",
        "Building alarm triggered investigation",
        "Cleaning staff notified management",
    ]
    base = f"{_pick(how)} at {env}: {incident}."
    if random.random() < 0.5:
        base += f" Concern: {_pick(PHYSICAL_DATA_RISKS)}."
    return base


def _physical_desc_environmental(env: str) -> str:
    incident = _pick(PHYSICAL_INCIDENTS)

    base = f"Environmental/physical incident at {env}: {incident}."
    if random.random() < 0.6:
        hours = random.choice([2, 4, 6, 8, 12, 24])
        base += f" Estimated time before resolution: {hours} hours."
    if random.random() < 0.4:
        base += " Business continuity plan activation may be needed."
    return base


PHYSICAL_BUILDERS = [
    _physical_desc_standard,
    _physical_desc_discovered,
    _physical_desc_environmental,
]


# --- Web App Attack description builders ---

def _webapp_desc_standard(env: str) -> str:
    attack = _pick(WEB_ATTACK_TYPES)
    target = _pick(WEB_TARGETS)
    mitre = _pick_mitre("web_app_attack")

    base = f"Web application attack at {env}."
    base += f" Attack: {attack}."
    base += f" Target: {target}."
    if random.random() < 0.5:
        base += f" Consequence: {_pick(WEB_CONSEQUENCES)}."
    if mitre:
        base += f" MITRE: {mitre}."
    return base


def _webapp_desc_waf(env: str) -> str:
    attack = _pick(WEB_ATTACK_TYPES)
    target = _pick(WEB_TARGETS)

    base = f"WAF/IDS alert at {env}: {attack} against {target}."
    if random.random() < 0.5:
        count = random.randint(50, 5000)
        base += f" {count} malicious requests observed in the last hour."
    if random.random() < 0.6:
        base += f" Confirmed impact: {_pick(WEB_CONSEQUENCES)}."
    else:
        base += " Impact under investigation — attack may have been blocked."
    return base


def _webapp_desc_pentest(env: str) -> str:
    attack = _pick(WEB_ATTACK_TYPES)
    target = _pick(WEB_TARGETS)
    consequence = _pick(WEB_CONSEQUENCES)

    base = (
        f"Vulnerability exploited in production at {env} — "
        f"this was NOT a scheduled pentest."
    )
    base += f" Attack type: {attack} on {target}."
    base += f" Result: {consequence}."
    return base


WEBAPP_BUILDERS = [
    _webapp_desc_standard,
    _webapp_desc_waf,
    _webapp_desc_pentest,
]


# =============================================================================
# CATEGORY BUILDER REGISTRY
# =============================================================================

CATEGORY_BUILDERS: dict[str, list] = {
    "ransomware": RANSOMWARE_BUILDERS,
    "phishing": PHISHING_BUILDERS,
    "data_breach": BREACH_BUILDERS,
    "bec": BEC_BUILDERS,
    "insider_threat": INSIDER_BUILDERS,
    "denial_of_service": DOS_BUILDERS,
    "unauthorized_access": UNAUTH_BUILDERS,
    "supply_chain": SUPPLY_CHAIN_BUILDERS,
    "physical_security": PHYSICAL_BUILDERS,
    "web_app_attack": WEBAPP_BUILDERS,
}


# =============================================================================
# SCENARIO GENERATOR
# =============================================================================


def generate_scenario(scenario_id: int) -> dict[str, Any]:
    """Generate a single incident scenario with full combinatorial variance."""
    # Pick category (weighted)
    categories = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())
    category = random.choices(categories, weights=weights, k=1)[0]

    # Pick environment and time
    environment = _pick(ENVIRONMENTS)
    time_context = _pick(TIME_CONTEXTS)

    # Pick severity (weighted, category-adjusted)
    severity = _severity(category)

    # Build description using a random builder for this category
    builder = _pick(CATEGORY_BUILDERS[category])
    description = builder(environment)

    return {
        "id": f"SCN-{scenario_id:04d}",
        "category": category,
        "severity": severity,
        "environment": environment,
        "time_context": time_context,
        "description": description,
    }


def generate_scenarios(count: int) -> dict[str, Any]:
    """Generate a full scenario dataset."""
    # Generate IDs and shuffle them so they aren't sequential by category
    ids = list(range(1, count + 1))
    random.shuffle(ids)

    scenarios = []
    for scenario_id in ids:
        scenarios.append(generate_scenario(scenario_id))

    # Sort by ID for clean output
    scenarios.sort(key=lambda s: s["id"])

    return {
        "total": count,
        "scenarios": scenarios,
    }


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate incident response training scenarios for MSPs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/generate_scenarios.py --seed 42\n"
            "  python scripts/generate_scenarios.py --count 500 --output scenarios.json\n"
            "  python scripts/generate_scenarios.py --seed 42 | jq '.scenarios[0]'\n"
        ),
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=2000,
        help="Number of scenarios to generate (default: 2000)",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    data = generate_scenarios(args.count)

    output = json.dumps(data, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
            f.write("\n")
        # Print summary to stderr so it doesn't pollute piped output
        print(f"Generated {args.count} scenarios → {args.output}", file=sys.stderr)

        # Print category distribution
        from collections import Counter
        cats = Counter(s["category"] for s in data["scenarios"])
        sevs = Counter(s["severity"] for s in data["scenarios"])
        print("\nCategory distribution:", file=sys.stderr)
        for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {cat:25s} {n:4d} ({n/args.count*100:5.1f}%)", file=sys.stderr)
        print("\nSeverity distribution:", file=sys.stderr)
        for sev, n in sorted(sevs.items()):
            print(f"  {sev}: {n:4d} ({n/args.count*100:5.1f}%)", file=sys.stderr)
    else:
        sys.stdout.write(output)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
