"""
Root Cause Analysis Agent — Determines probable root causes for classified incident groups.

Provides:
- Root cause identification with confidence scores
- Evidence collection and supporting log references
- Historical incident matching
- Component affected (UI/Frontend, Backend, Network, WAF, etc.)

Sits between Classification Agent and Priority Agent in the pipeline.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from app.database import async_session
from app.models.root_cause import RootCauseAnalysis
from app.models.incident_group import IncidentGroup

logger = logging.getLogger(__name__)


# --- Root Cause Pattern Database ---
# Each pattern maps error signatures to known root causes

RCA_PATTERNS = {
    # Backend/Origin Issues
    "backend_timeout": {
        "keywords": ["timeout", "timed out", "time_taken", "latency", "slow", "504", "origin"],
        "http_codes": [504, 502, 0],
        "root_cause": "Backend service timeout — origin server not responding within configured timeout period",
        "category": "Backend Timeout",
        "component": "Backend — Origin Server",
        "confidence": 0.85,
        "immediate_resolution": "1. Check backend service health and restart if unresponsive\n2. Increase origin timeout in Front Door/App Gateway configuration\n3. Scale up backend instances if under resource pressure\n4. Check database connectivity from backend servers",
        "preventive_action": "1. Configure health probes with appropriate intervals\n2. Set up auto-scaling rules for backend services\n3. Add retry policies with exponential backoff\n4. Implement circuit breaker pattern",
        "owner_team": "Backend / DevOps",
        "business_impact": "Users experience slow page loads or timeouts. May cause transaction failures.",
        "est_resolution_min": 30,
    },
    "backend_unavailable": {
        "keywords": ["502", "bad gateway", "backend", "unavailable", "connection refused", "connect failure"],
        "http_codes": [502, 503],
        "root_cause": "Backend service unavailable — origin server cannot be reached or is returning errors",
        "category": "Backend Unavailable",
        "component": "Backend — Application Server",
        "confidence": 0.90,
        "immediate_resolution": "1. Verify backend service is running and healthy\n2. Check App Service / VM status in Azure Portal\n3. Review recent deployments that may have caused failure\n4. Verify backend pool configuration in Front Door/App Gateway",
        "preventive_action": "1. Enable monitoring alerts for backend health\n2. Configure redundant backend instances\n3. Implement blue-green deployments\n4. Add health check endpoints",
        "owner_team": "Infrastructure / DevOps",
        "business_impact": "Complete service outage for affected endpoints. Critical business impact.",
        "est_resolution_min": 15,
    },
    "ssl_certificate": {
        "keywords": ["ssl", "certificate", "tls", "handshake", "cert", "x509"],
        "http_codes": [502, 525, 526],
        "root_cause": "SSL/TLS certificate issue — expired, invalid, or misconfigured certificate",
        "category": "SSL Certificate Error",
        "component": "Network — SSL/TLS",
        "confidence": 0.92,
        "immediate_resolution": "1. Check certificate expiry date\n2. Renew SSL certificate if expired\n3. Verify certificate chain is complete\n4. Ensure certificate matches the domain",
        "preventive_action": "1. Set up certificate expiry monitoring alerts (30-day warning)\n2. Enable auto-renewal with Azure Key Vault\n3. Use managed SSL certificates where possible\n4. Monitor certificate health in Front Door",
        "owner_team": "Security / Infrastructure",
        "business_impact": "Users see security warnings or cannot access the site. Trust impact.",
        "est_resolution_min": 60,
    },
    "dns_resolution": {
        "keywords": ["dns", "name resolution", "nxdomain", "resolve", "hostname"],
        "http_codes": [502],
        "root_cause": "DNS resolution failure — backend hostname cannot be resolved",
        "category": "DNS Resolution Failure",
        "component": "Network — DNS",
        "confidence": 0.88,
        "immediate_resolution": "1. Verify DNS records for backend endpoints\n2. Check Azure DNS zone configuration\n3. Verify custom domain CNAME/A records\n4. Test DNS resolution from backend subnet",
        "preventive_action": "1. Use Azure Private DNS zones for internal resolution\n2. Set appropriate DNS TTL values\n3. Configure DNS health monitoring\n4. Add redundant DNS providers",
        "owner_team": "Infrastructure / Network",
        "business_impact": "Complete routing failure. All traffic to affected endpoints fails.",
        "est_resolution_min": 20,
    },
    "waf_geo_block": {
        "keywords": ["block", "blockcountries", "geo", "geofencing", "waf"],
        "waf_actions": ["Block"],
        "root_cause": "WAF geo-restriction — traffic blocked from non-whitelisted countries by firewall policy",
        "category": "WAF Geo-Restriction Block",
        "component": "WAF / Network Security",
        "confidence": 0.95,
        "immediate_resolution": "1. Verify if blocked traffic is legitimate\n2. Check WAF policy rules for correct country list\n3. If legitimate, add the country to allow-list\n4. Review blocked IP addresses for attack patterns",
        "preventive_action": "1. Regularly review WAF blocked traffic reports\n2. Maintain updated geo-allow list for partners\n3. Set up alerts for spike in WAF blocks\n4. Consider IP-based allow-listing for known partners",
        "owner_team": "Security / Network",
        "business_impact": "Foreign users/partners cannot access the service. Minimal impact if by design.",
        "est_resolution_min": 10,
    },
    "waf_attack": {
        "keywords": ["sqli", "xss", "injection", "cross-site", "attack", "bot", "scanner", "crawler"],
        "waf_actions": ["Block", "Redirect"],
        "root_cause": "WAF detected and blocked a potential security attack (SQL injection, XSS, or bot activity)",
        "category": "Security Attack Blocked",
        "component": "WAF / Application Security",
        "confidence": 0.90,
        "immediate_resolution": "1. Review attack details and determine if true positive\n2. Check if application has input validation vulnerabilities\n3. Add offending IPs to permanent block list if malicious\n4. Review WAF rule for false positive rate",
        "preventive_action": "1. Implement input validation and output encoding in application\n2. Add Content-Security-Policy headers\n3. Enable bot management features\n4. Conduct periodic security assessments",
        "owner_team": "Security / Application Development",
        "business_impact": "Attack mitigated. No business impact if WAF is working correctly.",
        "est_resolution_min": 5,
    },
    "rate_limiting": {
        "keywords": ["rate limit", "throttl", "429", "too many requests"],
        "http_codes": [429],
        "root_cause": "Rate limiting triggered — client exceeded configured request rate",
        "category": "Rate Limiting",
        "component": "WAF / API Gateway",
        "confidence": 0.90,
        "immediate_resolution": "1. Identify the client causing rate limit breaches\n2. Check if legitimate traffic or DDoS/abuse\n3. Adjust rate limit thresholds if too restrictive\n4. Whitelist known API consumers if needed",
        "preventive_action": "1. Implement progressive rate limiting\n2. Add API key-based quotas\n3. Enable DDoS protection (Azure DDoS Standard)\n4. Monitor rate limit metrics",
        "owner_team": "API Platform / Security",
        "business_impact": "Legitimate users may be throttled during peak traffic.",
        "est_resolution_min": 15,
    },
    "high_latency_blob": {
        "keywords": ["blob", "download", "storage", "pdf", "file", "document", "knowledgecentre", "factsheet"],
        "root_cause": "High latency on file downloads from Azure Blob Storage — CDN cache miss or storage throttling",
        "category": "Blob Storage Latency",
        "component": "Backend — Azure Blob Storage",
        "confidence": 0.85,
        "immediate_resolution": "1. Check Azure Storage account performance metrics\n2. Verify CDN caching rules for blob paths\n3. Check if storage account is being throttled\n4. Move hot files to premium storage tier",
        "preventive_action": "1. Enable CDN caching for /blob/ paths with appropriate TTL\n2. Set Cache-Control headers on Blob Storage\n3. Compress large files (PDFs) before upload\n4. Consider Azure CDN pre-warming for popular content",
        "owner_team": "Infrastructure / Content Management",
        "business_impact": "Users experience slow document downloads. Poor UX for factsheet/report access.",
        "est_resolution_min": 45,
    },
    "high_latency_frontend": {
        "keywords": ["static", "/js/", "/css/", "/media/", "chunk", "bundle", "service-worker", "webpack"],
        "root_cause": "Frontend static assets (JS/CSS) loading slowly due to CDN cache misses or large bundle sizes",
        "category": "Frontend Asset Latency",
        "component": "UI / Frontend",
        "confidence": 0.82,
        "immediate_resolution": "1. Verify CDN caching rules for /static/ paths\n2. Set Cache-Control: immutable for hashed files\n3. Enable Brotli/Gzip compression on Front Door\n4. Check if service worker is interfering",
        "preventive_action": "1. Implement aggressive caching with immutable headers\n2. Optimize webpack code-splitting strategy\n3. Reduce JS bundle sizes\n4. Use lazy loading for non-critical components",
        "owner_team": "Frontend Development",
        "business_impact": "Slow page loads degrade user experience. May increase bounce rate.",
        "est_resolution_min": 60,
    },
    "authentication_failure": {
        "keywords": ["401", "unauthorized", "authentication", "auth", "token", "jwt", "bearer", "forbidden"],
        "http_codes": [401, 403],
        "root_cause": "Authentication/authorization failure — invalid or expired credentials",
        "category": "Authentication Failure",
        "component": "Backend — Auth Service",
        "confidence": 0.88,
        "immediate_resolution": "1. Check if auth token is expired\n2. Verify OAuth/JWT configuration\n3. Check if API keys need rotation\n4. Verify CORS and allowed origins",
        "preventive_action": "1. Implement token refresh mechanism\n2. Set up auth service monitoring\n3. Configure token expiry alerts\n4. Use managed identities where possible",
        "owner_team": "Identity / Backend Development",
        "business_impact": "Users cannot login or access protected resources.",
        "est_resolution_min": 20,
    },
    "application_error": {
        "keywords": ["500", "internal server error", "exception", "crash", "unhandled", "stack trace", "null"],
        "http_codes": [500],
        "root_cause": "Application error — unhandled exception or crash in the backend application",
        "category": "Application Error",
        "component": "Backend — Application Code",
        "confidence": 0.80,
        "immediate_resolution": "1. Check application logs for stack traces\n2. Review recent code deployments\n3. Restart the application if crashed\n4. Roll back to last known good version if needed",
        "preventive_action": "1. Add comprehensive error handling\n2. Implement structured logging\n3. Set up Application Insights\n4. Add unit tests for edge cases",
        "owner_team": "Application Development",
        "business_impact": "Application errors may cause partial or complete service disruption.",
        "est_resolution_min": 30,
    },
    "routing_misconfiguration": {
        "keywords": ["404", "not found", "routing", "route", "path", "endpoint", "invalid"],
        "http_codes": [404],
        "root_cause": "Routing misconfiguration — requested resource not found due to invalid routing rules",
        "category": "Routing/Configuration Error",
        "component": "Network — Front Door / App Gateway",
        "confidence": 0.75,
        "immediate_resolution": "1. Verify Front Door / App Gateway routing rules\n2. Check backend health probes\n3. Verify the requested endpoint exists\n4. Check for recent configuration changes",
        "preventive_action": "1. Implement routing rule validation in CI/CD\n2. Use configuration-as-code for routing\n3. Add smoke tests after routing changes\n4. Document all routing rules",
        "owner_team": "Infrastructure / DevOps",
        "business_impact": "Users get 404 errors. Specific pages or API endpoints unavailable.",
        "est_resolution_min": 15,
    },
    "client_disconnect": {
        "keywords": ["clientdisconnect", "client disconnect", "reset", "aborted", "connection closed"],
        "root_cause": "Client disconnected before server response — usually caused by slow backend response making users navigate away",
        "category": "Client Disconnect",
        "component": "Network / UX",
        "confidence": 0.70,
        "immediate_resolution": "1. Fix underlying backend latency causing users to abandon\n2. Check for network issues between CDN and clients\n3. Review if large responses are causing timeouts",
        "preventive_action": "1. Implement loading indicators in UI\n2. Optimize backend response times\n3. Add progressive content loading\n4. Set appropriate client-side timeouts",
        "owner_team": "Frontend / Backend Development",
        "business_impact": "Users abandon slow pages. Impacts engagement and conversion.",
        "est_resolution_min": 60,
    },
}


def _match_pattern(issue: dict) -> tuple[str, dict]:
    """Match an issue against known RCA patterns. Returns (pattern_key, pattern_data)."""
    title = (issue.get("title", "") or "").lower()
    description = (issue.get("description", "") or "").lower()
    combined_text = f"{title} {description}"
    http_code = issue.get("http_status_code")
    waf_action = (issue.get("waf_action", "") or "").lower()

    best_match = None
    best_score = 0

    for key, pattern in RCA_PATTERNS.items():
        score = 0

        # Keyword matching
        keywords = pattern.get("keywords", [])
        for kw in keywords:
            if kw.lower() in combined_text:
                score += 2

        # HTTP code matching
        if http_code and http_code in pattern.get("http_codes", []):
            score += 3

        # WAF action matching
        if waf_action and waf_action in [a.lower() for a in pattern.get("waf_actions", [])]:
            score += 4

        if score > best_score:
            best_score = score
            best_match = (key, pattern)

    if best_match and best_score >= 2:
        return best_match

    # Fallback: generic pattern
    return "unknown", {
        "root_cause": f"Unclassified issue: {issue.get('title', 'Unknown')}. Requires manual investigation.",
        "category": "Unclassified",
        "component": "Unknown",
        "confidence": 0.40,
        "immediate_resolution": "1. Review the incident details in Azure Portal\n2. Check related service health dashboards\n3. Escalate to the appropriate team",
        "preventive_action": "1. Improve log classification rules\n2. Add monitoring for this pattern\n3. Document findings for future reference",
        "owner_team": "Operations",
        "business_impact": "Impact unknown — requires investigation.",
        "est_resolution_min": 60,
    }


async def rca_agent_node(state: dict) -> dict:
    """
    Root Cause Analysis Agent — analyzes classified issues and determines root causes.
    
    Strategy:
    1. FIRST try Gemini AI for dynamic, log-specific RCA
    2. If Gemini fails, fall back to rule-based pattern matching

    Inputs from state:
        - issues_found: list of classified issues from Classification Agent
        - run_id: pipeline run ID

    Outputs to state:
        - rca_results: list of issues enriched with root cause analysis
    """
    issues = state.get("issues_found", [])
    run_id = state.get("run_id", "")

    logger.info(f"Agent 3.5 [RCA]: Analyzing {len(issues)} classified issues")

    if not issues:
        logger.info("Agent 3.5 [RCA]: No issues to analyze")
        return {"rca_results": [], "current_agent": "rca_agent"}

    # Try to initialize Gemini service
    gemini = None
    try:
        from app.services.gemini_service import GeminiService
        gemini = GeminiService()
        logger.info("Agent 3.5 [RCA]: Gemini AI available — will generate dynamic root causes")
    except Exception as e:
        logger.warning(f"Agent 3.5 [RCA]: Gemini unavailable ({e}) — using rule-based fallback")

    rca_results = []

    # Pre-compute Gemini RCA for ALL issues concurrently (if available)
    gemini_results = {}
    if gemini and issues:
        import asyncio as _aio
        sem = _aio.Semaphore(3)  # Max 3 concurrent Gemini calls

        async def _rca_for_issue(idx, iss):
            async with sem:
                try:
                    return idx, await gemini.generate_root_cause(iss)
                except Exception as e:
                    logger.warning(f"Agent 3.5 [RCA]: Gemini failed for #{idx}: {e}")
                    return idx, None

        tasks = [_rca_for_issue(i, iss) for i, iss in enumerate(issues)]
        results = await _aio.gather(*tasks)
        for idx, rca_data in results:
            if rca_data and rca_data.get("root_cause"):
                gemini_results[idx] = rca_data

    for i, issue in enumerate(issues):
        try:
            # Build evidence (used by both paths)
            evidence = []
            if issue.get("title"):
                evidence.append({"type": "incident_title", "value": issue["title"]})
            if issue.get("description"):
                evidence.append({"type": "incident_description", "value": issue["description"][:500]})
            if issue.get("http_status_code"):
                evidence.append({"type": "http_status_code", "value": str(issue["http_status_code"])})
            if issue.get("log_count", 0) > 0:
                evidence.append({"type": "occurrence_count", "value": str(issue["log_count"])})
            if issue.get("waf_action"):
                evidence.append({"type": "waf_action", "value": issue["waf_action"]})
            if issue.get("sample_logs"):
                for sl in issue["sample_logs"][:3]:
                    evidence.append({"type": "sample_log", "value": str(sl)[:300]})

            gemini_rca = gemini_results.get(i)

            if gemini_rca and gemini_rca.get("root_cause"):
                # Use Gemini's dynamic RCA
                rca = {
                    "issue": issue,
                    "root_cause": gemini_rca["root_cause"],
                    "root_cause_category": gemini_rca.get("root_cause_category", "AI-Analyzed"),
                    "confidence_score": gemini_rca.get("confidence_score", 0.85),
                    "evidence": evidence,
                    "evidence_summary": f"AI-generated RCA based on {len(evidence)} evidence items and {len(issue.get('sample_logs', []))} error samples",
                    "affected_component": gemini_rca.get("affected_component", issue.get("source_service", "Unknown")),
                    "immediate_resolution": gemini_rca.get("immediate_resolution", ""),
                    "preventive_action": gemini_rca.get("preventive_action", ""),
                    "owner_team": gemini_rca.get("owner_team", "Operations"),
                    "business_impact": gemini_rca.get("business_impact", ""),
                    "est_resolution_min": gemini_rca.get("est_resolution_min", 30),
                    "analysis_method": "gemini_ai",
                    "source_service": issue.get("source_service") or issue.get("affected_service", ""),
                    "affected_service": issue.get("affected_service") or issue.get("source_service", ""),
                }
                logger.info(
                    f"Agent 3.5 [RCA]: 🤖 Gemini: '{issue.get('title', '?')[:40]}' → "
                    f"{gemini_rca.get('root_cause_category', '?')} (AI confidence: {gemini_rca.get('confidence_score', '?')})"
                )
            else:
                # === Strategy 2: Rule-based fallback (enriched with log samples) ===
                pattern_key, pattern = _match_pattern(issue)
                
                # Build enriched root cause from actual log samples
                base_root_cause = pattern["root_cause"]
                sample_logs = issue.get("sample_logs", [])
                source_service = issue.get("source_service") or issue.get("affected_service", "Unknown")
                
                if sample_logs:
                    # Deduplicate and clean up samples
                    unique_samples = list(dict.fromkeys(s.strip() for s in sample_logs if s.strip()))[:5]
                    if unique_samples:
                        enriched_root_cause = (
                            f"{base_root_cause}\n\n"
                            f"Service Affected: {source_service}\n\n"
                            f"Evidence from error logs ({issue.get('log_count', 0)} occurrences):\n" +
                            "\n".join(f"  • {s[:250]}" for s in unique_samples)
                        )
                    else:
                        enriched_root_cause = base_root_cause
                else:
                    enriched_root_cause = base_root_cause

                rca = {
                    "issue": issue,
                    "root_cause": enriched_root_cause,
                    "root_cause_category": pattern["category"],
                    "confidence_score": pattern["confidence"],
                    "evidence": evidence,
                    "evidence_summary": f"Matched pattern '{pattern_key}' based on {len(evidence)} evidence items",
                    "affected_component": f"{pattern['component']} ({source_service})" if source_service != "Unknown" else pattern["component"],
                    "immediate_resolution": pattern.get("immediate_resolution", ""),
                    "preventive_action": pattern.get("preventive_action", ""),
                    "owner_team": pattern.get("owner_team", "Operations"),
                    "business_impact": pattern.get("business_impact", ""),
                    "est_resolution_min": pattern.get("est_resolution_min", 30),
                    "analysis_method": "rule_based",
                    "source_service": issue.get("source_service") or issue.get("affected_service", ""),
                    "affected_service": issue.get("affected_service") or issue.get("source_service", ""),
                }
                logger.info(
                    f"Agent 3.5 [RCA]: 📋 Rule-based: '{issue.get('title', '?')[:40]}' → "
                    f"{pattern['category']} (confidence: {pattern['confidence']})"
                )

            rca_results.append(rca)

            # Persist RCA to database
            try:
                async with async_session() as session:
                    # Create IncidentGroup
                    group = IncidentGroup(
                        id=str(uuid.uuid4()),
                        category_name=rca["root_cause_category"],
                        error_signature=rca.get("analysis_method", "unknown"),
                        description=rca["root_cause"],
                        source_service=issue.get("source_service"),
                        error_type=rca["root_cause_category"],
                        total_occurrences=issue.get("log_count", 0),
                        first_seen=datetime.utcnow(),
                        last_seen=datetime.utcnow(),
                        log_ids=issue.get("log_ids", []),
                        agent_run_id=run_id,
                    )
                    session.add(group)

                    # Create RCA record
                    rca_record = RootCauseAnalysis(
                        id=str(uuid.uuid4()),
                        incident_group_id=group.id,
                        root_cause=rca["root_cause"],
                        root_cause_category=rca["root_cause_category"],
                        confidence_score=rca["confidence_score"],
                        evidence=evidence,
                        evidence_summary=rca["evidence_summary"],
                        supporting_log_ids=issue.get("log_ids", [])[:10],
                        supporting_log_count=issue.get("log_count", 0),
                        affected_component=rca["affected_component"],
                        analysis_method=rca.get("analysis_method", "rule_based"),
                        agent_run_id=run_id,
                    )
                    session.add(rca_record)
                    await session.commit()

                    # Store IDs for downstream agents
                    rca["incident_group_id"] = group.id
                    rca["rca_id"] = rca_record.id

            except Exception as e:
                logger.warning(f"Agent 3.5 [RCA]: DB persist failed: {e}")

        except Exception as e:
            logger.error(f"Agent 3.5 [RCA]: Error analyzing issue: {e}")
            rca_results.append({
                "issue": issue,
                "root_cause": "Analysis failed — manual review required",
                "root_cause_category": "Analysis Error",
                "confidence_score": 0.0,
                "evidence": [],
                "affected_component": "Unknown",
                "analysis_method": "error",
            })

    logger.info(f"Agent 3.5 [RCA]: Completed {len(rca_results)} root cause analyses")

    return {
        "rca_results": rca_results,
        "current_agent": "rca_agent",
    }
