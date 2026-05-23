---
description: Describe when these instructions should be loaded by the agent based on task context
applyTo: '**/*'
---


# System Identity and Vision Document

## 1. System Name
**Theft Guard AI**

Alternative internal naming used in the codebase and repository context:
- Theft Detection System
- Retail Loss Prevention AI Platform

## 2. System Summary
Theft Guard AI is a real-time retail theft detection platform that combines multi-camera monitoring, AI-based pose and object analysis, zone-aware rules, and optional face recognition. It tracks suspicious behavior over time, evaluates cumulative risk, and generates alerts with visual evidence (image and video) only when configured behavioral conditions are met.

## 3. System Purpose
The system exists to reduce retail shrinkage and improve in-store security operations by automating suspicious behavior detection and incident documentation. It helps security teams move from reactive manual review to proactive, evidence-based intervention.

## 4. System Mission
The mission of the system is to automate and organize the full theft-monitoring cycle: camera ingestion, behavior analysis, risk scoring, alert generation, evidence recording, and operational review through APIs and dashboards.

## 5. System Vision
To become a reliable, scalable, and configurable visual intelligence layer for retail environments, enabling stores of different sizes to detect theft behavior earlier, reduce false positives, and improve operational response quality.

## 6. System Values and Principles
The system is guided by these principles:

- **Behavior over isolated events**: A single gesture should not define a theft event by itself.
- **Progressive risk scoring**: Suspicion grows through behavior chains and temporal evidence, not binary flags only.
- **Context-aware detection**: Zone type (merchandise, entry, forbidden) changes behavior interpretation.
- **Operational reliability**: Non-blocking processing, background tasks, and configurable thresholds support stable operation.
- **Evidence integrity**: Alerts should include timestamped data and media artifacts for later audit.
- **Configurability**: Detection policy and thresholds must be adjustable without code rewrites.
- **Practical fairness**: Optional whitelist logic and configurable face-hidden handling reduce unnecessary escalations.

## 7. Target Audience
The system serves:

- Retail security operators monitoring live incidents
- Store managers and loss prevention teams reviewing risk and alerts
- Administrators configuring cameras, zones, and detection policies
- Technical operators integrating the backend with dashboard workflows
- Stakeholders analyzing incident history and operational KPIs

## 8. Problems the System Solves
The system addresses the following problems:

- Delayed detection of suspicious in-store behavior
- High dependence on manual camera monitoring
- Excessive noise from simplistic, single-trigger alerting
- Lack of structured evidence for incident validation
- Difficulty correlating camera events with risk progression
- Inconsistent zone monitoring and object movement tracking
- Poor historical visibility into alert patterns and trends

## 9. Main System Functions
The system provides these major functions:

- Multi-camera ingestion and management (RTSP, webcam, DVR channel expansion)
- Real-time person, pose, and object detection
- Behavior-based risk tracking per person across frames
- ROI and multi-zone logic for context-specific scoring
- Configurable alert-chain and threshold policies
- Alert generation with image and video evidence persistence
- Notification dispatch through email and Telegram
- Face registry workflows (optional), including whitelist/blacklist handling
- History and statistics APIs for monitoring and reporting
- Detection configuration APIs for runtime tuning

## 10. System Duties
The system has the duty to:

- Continuously ingest and process active camera streams
- Evaluate suspicious behavior with temporal consistency
- Persist alerts and incident artifacts for audit and review
- Keep detection decisions traceable via stored event data
- Prevent alert flooding through cooldown and policy control
- Maintain configuration consistency for detection behavior
- Provide operational APIs for history, stats, and administration
- Protect processing continuity by isolating heavy operations in background execution

## 11. What the System Must Not Do
The system must not:

- Trigger high-severity incidents based only on isolated body movements when chain policy requires confirmation
- Treat all zones as behaviorally equivalent
- Assume face recognition is always available or mandatory
- Depend on manual-only incident registration when automatic persistence is available
- Block the detection pipeline while sending notifications or processing media conversion
- Expose unrestricted administrative behavior to ungoverned deployment environments
- Present risk as absolute certainty without contextual thresholds and temporal validation

## 12. Main Business Rules
Key business rules inferred from the backend implementation include:

1. Suspicious behavior is evaluated cumulatively through risk scoring with decay over time.
2. Zone context influences risk interpretation:
   - Merchandise zones: normal scoring.
   - Forbidden zones: higher weighting.
   - Entry zones: reduced or suppressed scoring based on configuration.
3. Alerting follows configurable chain logic, including confirmed behavior sequence and/or high-score overrides.
4. Alert triggering uses threshold gates and cooldown windows to avoid repeated spam.
5. Risk has an upper cap and does not grow indefinitely.
6. Detection policies and thresholds are persisted and can be updated via API.
7. Evidence creation is part of alerting, including image snapshots and time-window video clips.
8. Optional face typing affects interpretation (for example, whitelist trust or blacklist sensitivity) when face recognition is enabled.
9. Zone object events are tracked with timestamps and metadata to support event history and audits.

## 13. Success Indicators
The system is considered effective when it can demonstrate:

- Lower false-positive rate after policy tuning
- Faster time from suspicious behavior onset to actionable alert
- Consistent generation of usable evidence for triggered incidents
- Stable multi-camera operation with low processing interruption
- Better operational visibility through history and statistical endpoints
- Increased detection quality in critical merchandise and restricted zones
- Improved review workflows for security and management teams

## 14. System Guiding Phrase
**"Transform store video streams into structured, context-aware, and evidence-backed theft prevention decisions."**