"""
Agent 3: Classification Agent

Reads preprocessed cloud_logs from PostgreSQL, sends them to Gemini for
incident type detection, intent classification, and severity scoring.
Falls back to rule-based classification if Gemini is unavailable.
"""

import logging
from typing import Any

from sqlalchemy import select, update

from app.database import async_session
from app.models.cloud_log import CloudLog
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


def _extract_service_name(logs: list[dict]) -> str:
    """Extract the real Azure service name from resource_id in log data."""
    resource_providers = {}
    for log in logs:
        rid = (log.get("resource_id") or "").upper()
        if "/PROVIDERS/" in rid:
            provider_part = rid.split("/PROVIDERS/")[1]
            provider = provider_part.split("/")[0]
            resource_type = provider_part.split("/")[1] if "/" in provider_part else ""
            key = f"{provider}/{resource_type}" if resource_type else provider
            resource_providers[key] = resource_providers.get(key, 0) + 1

    PROVIDER_MAP = {
        "MICROSOFT.CDN": "Azure Front Door (CDN)",
        "MICROSOFT.NETWORK": "Azure Application Gateway / Network",
        "MICROSOFT.WEB": "Azure App Service",
        "MICROSOFT.COMPUTE": "Azure Virtual Machine",
        "MICROSOFT.SQL": "Azure SQL Database",
        "MICROSOFT.KEYVAULT": "Azure Key Vault",
        "MICROSOFT.APIMANAGEMENT": "Azure API Management",
        "MICROSOFT.SERVICEBUS": "Azure Service Bus",
        "MICROSOFT.STORAGE": "Azure Storage",
    }

    if resource_providers:
        top_provider = max(resource_providers, key=resource_providers.get)
        base_provider = top_provider.split("/")[0]
        return PROVIDER_MAP.get(base_provider, base_provider.replace("MICROSOFT.", "Azure "))
    return "Azure Front Door"


def _collect_error_samples(logs: list[dict], max_samples: int = 10) -> list[str]:
    """Collect unique, meaningful error message samples from logs.
    
    Digs deep into raw_data/raw_payload to extract actual error content:
    HTTP status codes, endpoints, hostnames, stack traces, SQL errors,
    WAF actions, rule names, and client IPs.
    """
    import json as _json
    seen = set()
    samples = []

    for log in logs:
        text_candidates = []

        # Get the raw payload (stored as raw_data in DB, passed as raw_payload)
        raw_payload = log.get("raw_payload") or log.get("raw_data")
        if raw_payload:
            payload = raw_payload
            if isinstance(payload, str):
                try:
                    payload = _json.loads(payload)
                except Exception:
                    payload = {}
            if isinstance(payload, dict):
                # resultDescription — contains Python stack traces, error details
                rd = (payload.get("resultDescription") or payload.get("ResultDescription") or "").strip()
                if rd and len(rd) > 10:
                    text_candidates.append(rd[:400])

                # ── WAF-specific fields (Front Door / App Gateway WAF logs) ──
                waf_action = payload.get("action") or payload.get("action_s") or ""
                waf_rule = payload.get("ruleName") or payload.get("ruleName_s") or ""
                waf_policy = payload.get("policyMode") or payload.get("policy") or ""
                waf_host = payload.get("host") or payload.get("hostName") or payload.get("host_s") or ""
                waf_uri = payload.get("requestUri") or payload.get("requestUri_s") or ""
                waf_client = payload.get("clientIP") or payload.get("clientIp") or payload.get("clientIp_s") or ""
                waf_details = payload.get("details", {})
                if isinstance(waf_details, str):
                    try:
                        waf_details = _json.loads(waf_details)
                    except Exception:
                        waf_details = {}
                waf_msg = ""
                if isinstance(waf_details, dict):
                    waf_msg = waf_details.get("msg", "") or waf_details.get("message", "")
                elif isinstance(waf_details, list) and waf_details:
                    waf_msg = str(waf_details[0].get("msg", "")) if isinstance(waf_details[0], dict) else str(waf_details[0])[:200]

                if waf_action or waf_rule:
                    parts = []
                    if waf_action:
                        parts.append(f"WAF Action: {waf_action}")
                    if waf_rule:
                        parts.append(f"Rule: {waf_rule}")
                    if waf_host:
                        parts.append(f"Host: {waf_host}")
                    if waf_uri:
                        parts.append(f"URI: {waf_uri}")
                    if waf_client:
                        parts.append(f"ClientIP: {waf_client}")
                    if waf_policy:
                        parts.append(f"Policy: {waf_policy}")
                    if waf_msg:
                        parts.append(f"Details: {waf_msg[:200]}")
                    text_candidates.append(" | ".join(parts))

                # properties block — HTTP details, SQL errors, etc.
                props = payload.get("properties", {})
                if isinstance(props, str):
                    try:
                        props = _json.loads(props)
                    except Exception:
                        props = {}
                if isinstance(props, dict):
                    sc_status = str(props.get("ScStatus", ""))
                    cs_method = props.get("CsMethod", "")
                    cs_uri = props.get("CsUriStem", "")
                    cs_host = props.get("CsHost", "")
                    time_taken = props.get("TimeTaken", "")

                    # Build rich HTTP error description
                    if sc_status and (sc_status.startswith("4") or sc_status.startswith("5")):
                        parts = [f"HTTP {sc_status}"]
                        if cs_method:
                            parts.append(cs_method)
                        if cs_uri:
                            parts.append(cs_uri)
                        if cs_host:
                            parts.append(f"on {cs_host}")
                        if time_taken:
                            parts.append(f"(TimeTaken: {time_taken}ms)")
                        text_candidates.append(" ".join(parts))
                    elif sc_status and cs_uri:
                        # Even for 200s that got flagged as errors
                        parts = [f"HTTP {sc_status} {cs_method} {cs_uri}"]
                        if cs_host:
                            parts.append(f"on {cs_host}")
                        if time_taken:
                            parts.append(f"(TimeTaken: {time_taken}ms)")
                        text_candidates.append(" ".join(parts))

                    # SQL error message
                    sql_msg = props.get("message") or props.get("error_message", "")
                    err_num = props.get("error_number", "")
                    if sql_msg:
                        prefix = f"SQL Error {err_num}: " if err_num else ""
                        text_candidates.append(f"{prefix}{sql_msg[:300]}")

        # Standard message field — more permissive filtering
        msg = (log.get("message") or "").strip()
        if msg and len(msg) > 15:
            # Skip messages that are just "Category: X | Operation: Y" without real info
            if "Microsoft.Web/sites/log" not in msg and "SELECT" not in msg.upper():
                # Include messages with HTTP errors, exceptions, warnings, SSL issues, timeouts
                msg_lower = msg.lower()
                if any(k in msg_lower for k in [
                    "http 5", "http 4", "error", "exception", "timeout",
                    "warning", "ssl", "certificate", "insecure", "fail",
                    "denied", "refused", "block", "waf", "unauthorized"
                ]):
                    text_candidates.append(msg[:300])

        # Fallback: use the full message even if it has Operation info (better than nothing)
        if not text_candidates:
            msg = (log.get("message") or "").strip()
            if msg and len(msg) > 15 and "|" in msg:
                # Extract the useful part after the last pipe
                parts = msg.split("|")
                useful_part = parts[-1].strip() if len(parts) > 1 else msg
                if len(useful_part) > 10:
                    text_candidates.append(msg[:400])
            elif msg and len(msg) > 15:
                text_candidates.append(msg[:300])

        # Last resort fallback: category + operation
        if not text_candidates:
            op = (log.get("operation_name") or "").strip()
            cat = (log.get("category") or "")
            if op:
                text_candidates.append(f"[{cat}] {op}")

        # Pick the best (most informative) candidate
        for text in text_candidates:
            normalized = text[:200]
            if normalized not in seen and len(normalized) > 10:
                seen.add(normalized)
                samples.append(text[:400])
                break

        if len(samples) >= max_samples:
            break

    return samples


def _extract_affected_urls(logs: list[dict], max_urls: int = 5) -> list[str]:
    """Extract exact website page URLs from log data (requestUri, CsUriStem, hostName, etc.)
    
    Specifically targets icicipruamc.com and Azure-hosted endpoints.
    Returns list of full URLs like 'https://www.icicipruamc.com/mail/send'
    """
    import json as _json
    seen = set()
    urls = []

    for log in logs:
        raw_payload = log.get("raw_payload") or log.get("raw_data")
        if not raw_payload:
            continue

        payload = raw_payload
        if isinstance(payload, str):
            try:
                payload = _json.loads(payload)
            except Exception:
                continue

        if not isinstance(payload, dict):
            continue

        # Check multiple possible fields for host and URI
        host = ""
        uri = ""

        # Top-level fields (Front Door / App Gateway logs)
        for hf in ["hostName", "httpHost", "host", "cs-host", "serverName"]:
            h = (payload.get(hf) or "").strip()
            if h and "." in h:
                host = h
                break

        for uf in ["requestUri", "originalRequestUriWithArgs", "cs-uri-stem", "url", "requestUrl"]:
            u = (payload.get(uf) or "").strip()
            if u:
                uri = u
                break

        # Also check nested 'properties' block (IIS / App Service logs)
        props = payload.get("properties", {})
        if isinstance(props, str):
            try:
                props = _json.loads(props)
            except Exception:
                props = {}

        if isinstance(props, dict):
            if not host:
                for hf in ["CsHost", "cs-host", "hostName", "httpHost"]:
                    h = (props.get(hf) or "").strip()
                    if h and "." in h:
                        host = h
                        break
            if not uri:
                for uf in ["CsUriStem", "cs-uri-stem", "requestUri", "originalRequestUriWithArgs"]:
                    u = (props.get(uf) or "").strip()
                    if u:
                        uri = u
                        break

        if not uri:
            continue

        # Build full URL
        if host:
            # Normalize: add https:// if not present
            if not host.startswith("http"):
                full_url = f"https://{host}{uri}"
            else:
                full_url = f"{host}{uri}"
        else:
            full_url = uri

        # Normalize and deduplicate
        normalized = full_url.split("?")[0]  # Remove query params for dedup
        if normalized not in seen:
            seen.add(normalized)
            urls.append(full_url[:300])

        if len(urls) >= max_urls:
            break

    return urls


def _build_issue(logs: list[dict], title: str, desc_prefix: str, category: str, severity: int) -> dict:
    """Build an issue dict with real service names, error samples, and affected URLs."""
    service_name = _extract_service_name(logs)
    error_samples = _collect_error_samples(logs)
    affected_urls = _extract_affected_urls(logs)

    samples_text = ""
    if error_samples:
        samples_text = "\n\nActual error samples:\n" + "\n".join(f"  • {s}" for s in error_samples)

    # Use the first URL as the primary endpoint
    sample_endpoint = affected_urls[0] if affected_urls else ""

    return {
        "title": title,
        "description": f"{desc_prefix}{samples_text}",
        "category": category,
        "source_service": service_name,
        "affected_service": service_name,
        "log_ids": [l["id"] for l in logs],
        "log_count": len(logs),
        "severity_score": severity,
        "sample_logs": error_samples,
        "sample_endpoint": sample_endpoint,
        "affected_urls": affected_urls,
    }


def _rule_based_classify(structured_logs: list[dict]) -> dict[str, Any]:
    """
    Fallback: rule-based classification when Gemini is unavailable.
    Groups logs by pattern and creates incidents.
    """
    issues = []
    waf_blocks = []
    high_latency = []
    http_errors = []
    health_probe_failures = []

    for log in structured_logs:
        msg = (log.get("message") or "").lower()
        category = (log.get("category") or "").lower()
        level = (log.get("level") or "").upper()

        # WAF blocks
        if "block" in msg or ("waf" in category and level == "ERROR"):
            waf_blocks.append(log)
        elif "redirect" in msg:
            waf_blocks.append(log)
        elif "latency" in msg or "timetaken" in msg or "slow" in msg:
            high_latency.append(log)
        elif any(s in msg for s in ["500", "502", "503", "504", "error", "failed"]):
            http_errors.append(log)
        elif "healthprobe" in category or "health" in msg:
            health_probe_failures.append(log)
        elif level == "ERROR":
            http_errors.append(log)
        elif level == "WARNING":
            high_latency.append(log)

    # Create grouped incidents
    if waf_blocks:
        ips = set()
        for log in waf_blocks:
            msg = log.get("message") or ""
            for part in msg.split():
                if part.count(".") == 3 and all(p.isdigit() for p in part.split(".")):
                    ips.add(part)
        issues.append(_build_issue(
            waf_blocks,
            f"WAF Blocked Requests Detected ({len(waf_blocks)} events)",
            f"Azure Front Door WAF blocked {len(waf_blocks)} requests. "
            f"These include potential automated scans, brute force attempts, "
            f"or geo-restricted traffic from non-authorized regions. "
            f"Unique source IPs: {len(ips) if ips else 'N/A'}.",
            "WAF Security", 7,
        ))

    if high_latency:
        issues.append(_build_issue(
            high_latency,
            f"High Latency / Slow Responses ({len(high_latency)} events)",
            f"Detected {len(high_latency)} logs indicating high latency or slow "
            f"response times. This may indicate backend performance issues, "
            f"origin timeouts, or resource exhaustion.",
            "Performance", 5,
        ))

    if http_errors:
        issues.append(_build_issue(
            http_errors,
            f"HTTP Error Responses ({len(http_errors)} events)",
            f"Detected {len(http_errors)} HTTP error responses (4xx/5xx). "
            f"These may indicate backend failures, misconfigurations, "
            f"or application errors.",
            "Availability", 8,
        ))

    if health_probe_failures:
        issues.append(_build_issue(
            health_probe_failures,
            f"Health Probe Issues ({len(health_probe_failures)} events)",
            f"Detected {len(health_probe_failures)} health probe anomalies. "
            f"This may indicate backend services are unhealthy or unreachable.",
            "Health", 9,
        ))

    return {"issues": issues, "model": "rule-based-classifier"}


async def classification_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Classify preprocessed logs for incidents.

    Steps:
    1. Query unprocessed cloud_logs from DB
    2. Send structured data to Gemini for classification
    3. If Gemini fails, use rule-based fallback
    4. Mark logs as processed
    5. Return detected issues
    """
    logger.info("Agent 3 [Classification]: Starting log classification...")

    try:
        async with async_session() as session:
            cloud_log_ids = state.get("cloud_log_ids", [])

            if cloud_log_ids:
                query = select(CloudLog).where(CloudLog.id.in_(cloud_log_ids))
            else:
                query = (
                    select(CloudLog)
                    .where(CloudLog.is_processed == False)
                    .where(CloudLog.is_duplicate == False)
                    .order_by(CloudLog.timestamp.desc())
                    .limit(200)
                )

            result = await session.execute(query)
            db_logs = result.scalars().all()

            if not db_logs:
                logger.info("Agent 3 [Classification]: No logs to classify")
                return {
                    "issues_found": [],
                    "has_issues": False,
                    "logs_analyzed": 0,
                    "current_agent": "classification_agent",
                }

            # Prepare structured data for Gemini
            structured_logs = []
            log_ids = []
            for log in db_logs:
                log_ids.append(log.id)
                structured_logs.append({
                    "id": str(log.id),
                    "timestamp": str(log.timestamp),
                    "level": log.level,
                    "source": log.source,
                    "category": log.category,
                    "message": log.message,
                    "resource_id": log.resource_id,
                    "resource_group": log.resource_group,
                    "correlation_id": log.correlation_id,
                    "operation_name": log.operation_name,
                    "raw_data": log.raw_data,
                    "raw_payload": log.raw_data,
                })

            logger.info(f"Agent 3 [Classification]: Classifying {len(structured_logs)} logs")

            # Try Gemini first, fall back to rule-based
            try:
                analysis_result = await gemini_service.classify_logs(structured_logs)
                logger.info("Agent 3 [Classification]: Gemini classification succeeded")
            except Exception as gemini_err:
                logger.warning(f"Agent 3 [Classification]: Gemini unavailable ({gemini_err}), using rule-based fallback")
                analysis_result = _rule_based_classify(structured_logs)

            issues = analysis_result.get("issues", [])

            # If Gemini returned 0 issues but we have ERROR/CRITICAL logs,
            # fall back to rule-based classification to avoid silent misses
            error_logs = [l for l in structured_logs if (l.get("level") or "").upper() in ("ERROR", "CRITICAL")]
            if len(issues) == 0 and len(error_logs) > 0:
                logger.info(f"Agent 3 [Classification]: Gemini found 0 issues but {len(error_logs)} ERROR/CRITICAL logs exist — running rule-based fallback")
                rule_result = _rule_based_classify(structured_logs)
                issues = rule_result.get("issues", [])

            # ─── Post-Classification Quality Filter ───
            # Remove issues that have no real error evidence
            filtered_issues = []
            for issue in issues:
                # Enrich with sample_logs if missing (Gemini issues won't have them)
                if not issue.get("sample_logs"):
                    related_indices = issue.get("related_log_indices", [])
                    if related_indices:
                        related_logs_subset = [structured_logs[idx] for idx in related_indices if idx < len(structured_logs)]
                    else:
                        related_logs_subset = structured_logs
                    issue["sample_logs"] = _collect_error_samples(related_logs_subset)
                    issue["log_ids"] = [l["id"] for l in related_logs_subset[:50]]
                    issue["log_count"] = len(related_logs_subset)

                    # Extract service name if not set
                    if not issue.get("source_service"):
                        issue["source_service"] = _extract_service_name(related_logs_subset)
                        issue["affected_service"] = issue["source_service"]

                # Extract the website URL / endpoint from logs or Gemini output
                sample_endpoint = issue.get("sample_endpoint", "")
                if not sample_endpoint:
                    # Try to find URL from log messages
                    for log in structured_logs[:50]:
                        msg = (log.get("message") or "").lower()
                        raw = log.get("raw_data") or {}
                        if isinstance(raw, dict):
                            uri = raw.get("requestUri") or raw.get("originalRequestUriWithArgs") or raw.get("cs-uri-stem") or ""
                            host = raw.get("hostName") or raw.get("httpHost") or raw.get("cs-host") or ""
                            if uri and "." in host:
                                sample_endpoint = f"https://{host}{uri}"
                                break
                            elif uri:
                                sample_endpoint = uri
                                break
                issue["sample_endpoint"] = sample_endpoint

                # Filter: reject issues that are purely speculative (no error samples, 
                # no related_log_indices, and title contains "masked" or "hidden")
                title_lower = (issue.get("title") or "").lower()
                desc_lower = (issue.get("description") or "").lower()
                
                is_speculative = (
                    "masked" in title_lower or "hidden" in title_lower or
                    "silent failure" in title_lower or
                    "no specific error" in desc_lower or
                    "no error samples" in desc_lower
                )
                
                has_evidence = (
                    len(issue.get("sample_logs", [])) > 0 or
                    len(issue.get("related_log_indices", [])) > 0 or
                    any(kw in desc_lower for kw in ["500", "502", "503", "504", "404", "timeout", "exception", "failed"])
                )

                if is_speculative and not has_evidence:
                    logger.info(f"Agent 3 [Classification]: Filtered out speculative issue: '{issue.get('title', '?')[:50]}'")
                    continue

                filtered_issues.append(issue)

            issues = filtered_issues
            has_issues = len(issues) > 0

            # Mark logs as processed (use fresh session to avoid transaction timeout)
            try:
                await session.execute(
                    update(CloudLog)
                    .where(CloudLog.id.in_(log_ids))
                    .values(is_processed=True)
                )
                await session.commit()
            except Exception as commit_err:
                logger.warning(f"Agent 3 [Classification]: Commit failed ({commit_err}), retrying with fresh session")
                await session.rollback()
                try:
                    async with async_session() as session2:
                        await session2.execute(
                            update(CloudLog)
                            .where(CloudLog.id.in_(log_ids))
                            .values(is_processed=True)
                        )
                        await session2.commit()
                except Exception as retry_err:
                    logger.error(f"Agent 3 [Classification]: Retry commit also failed: {retry_err}")

            logger.info(f"Agent 3 [Classification]: Found {len(issues)} issues from {len(structured_logs)} logs")

            return {
                "issues_found": issues,
                "has_issues": has_issues,
                "logs_analyzed": len(structured_logs),
                "current_agent": "classification_agent",
            }

    except Exception as e:
        logger.error(f"Agent 3 [Classification] failed: {e}")
        return {
            "issues_found": [],
            "has_issues": False,
            "logs_analyzed": 0,
            "errors": [f"Classification failed: {str(e)}"],
            "current_agent": "classification_agent",
        }

