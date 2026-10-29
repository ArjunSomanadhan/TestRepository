# Security Incident Response SOP (SEC-SOP-01)

Effective: 2024-09-01 | Owner: InfoSec

## Severity levels

- **SEV-1**: Confirmed breach involving customer data or ransomware affecting production.
- **SEV-2**: Suspected compromise, widespread malware, or critical vulnerability actively exploited.
- **SEV-3**: Phishing reports, isolated endpoint alerts, policy violations without data exposure.

## Initial response

1. Detecting party opens an incident in the Security Portal within **15 minutes** of discovery.
2. On-call security analyst triages and assigns severity within **30 minutes**.
3. SEV-1 incidents page the CISO and Legal automatically.

## Containment

- Isolate affected hosts via EDR.
- Rotate credentials for impacted accounts within **1 hour** for SEV-1/2.
- Preserve forensic images before rebuilding systems when feasible.

## Notification

Customer notification for confirmed PII exposure follows Legal guidance and must begin within **72 hours** of confirmation, consistent with contractual SLAs. Internal all-hands notes require Communications approval.

## Post-incident

A blameless retrospective is required within **5 business days** for SEV-1 and SEV-2. Action items are tracked in Jira with owners and due dates.
