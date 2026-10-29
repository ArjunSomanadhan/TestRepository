# IT Access Request SOP (IT-SOP-04)

Effective: 2024-11-15 | Owner: IT Service Desk

## Purpose

Define how employees request, approve, and revoke access to enterprise applications.

## Standard access request

1. Employee submits a ticket in ServiceNow using the **Access Request** form.
2. Manager must approve within **2 business days**.
3. For systems classified **Confidential** or higher, Security reviews the request within **1 business day** after manager approval.
4. Service Desk provisions access and notifies the requester.

## Privileged access

Privileged (admin) access requires:
- Justified business need documented in the ticket
- Approval from the system owner **and** InfoSec
- Quarterly access review by the system owner

Emergency break-glass accounts are logged and must be reviewed within **24 hours**.

## Offboarding

When an employee leaves:
- HR triggers the offboarding workflow on the last working day.
- IT must revoke all accounts within **4 hours** of the HR trigger.
- Shared mailbox ownership transfers to the manager within **1 business day**.

## Escalation

SLA breaches escalate to the IT Operations Manager. Critical production access outages escalate to the on-call SRE via PagerDuty.
