"""Input validation utilities."""
import re
from urllib.parse import urlparse
from typing import Optional
import structlog

logger = structlog.get_logger()


def validate_url(url: str, max_length: int = 2000) -> bool:
    """
    Validate URL format and length.
    
    Args:
        url: URL string to validate
        max_length: Maximum allowed URL length
        
    Returns:
        True if URL is valid, False otherwise
    """
    if not url or len(url) > max_length:
        return False
    
    try:
        parsed = urlparse(url)
        
        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Basic domain validation
        if not _is_valid_domain(parsed.netloc):
            return False
        
        return True
        
    except Exception as e:
        logger.debug("URL validation failed", url=url, error=str(e))
        return False


def validate_tracking_id(tracking_id: str, max_length: int = 100) -> bool:
    """
    Validate tracking ID format.
    
    Args:
        tracking_id: Tracking ID to validate
        max_length: Maximum allowed length
        
    Returns:
        True if valid, False otherwise
    """
    if not tracking_id or len(tracking_id) > max_length:
        return False
    
    # Allow alphanumeric, hyphens, underscores, and dots
    pattern = r'^[a-zA-Z0-9\-_.]+$'
    return bool(re.match(pattern, tracking_id))


def validate_user_agent(user_agent: str, max_length: int = 1000) -> bool:
    """
    Validate user agent string.
    
    Args:
        user_agent: User agent string to validate
        max_length: Maximum allowed length
        
    Returns:
        True if valid, False otherwise
    """
    if not user_agent or len(user_agent) > max_length:
        return False
    
    # Check for suspicious patterns that might indicate injection attempts
    suspicious_patterns = [
        r'<script',
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'onload=',
        r'onerror=',
        r'eval\(',
        r'expression\(',
    ]
    
    user_agent_lower = user_agent.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, user_agent_lower):
            logger.warning("Suspicious user agent detected", user_agent=user_agent)
            return False
    
    return True


def validate_ip_address(ip_address: str) -> bool:
    """
    Validate IP address format (IPv4 or IPv6).
    
    Args:
        ip_address: IP address string to validate
        
    Returns:
        True if valid IP address, False otherwise
    """
    if not ip_address:
        return False
    
    try:
        import ipaddress
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False


def validate_domain(domain: str, max_length: int = 253) -> bool:
    """
    Validate domain name format.
    
    Args:
        domain: Domain name to validate
        max_length: Maximum allowed length
        
    Returns:
        True if valid domain, False otherwise
    """
    if not domain or len(domain) > max_length:
        return False
    
    return _is_valid_domain(domain)


def _is_valid_domain(domain: str) -> bool:
    """Internal domain validation logic."""
    try:
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # Basic format check
        if not domain or domain.startswith('.') or domain.endswith('.'):
            return False
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9.-]+$', domain):
            return False
        
        # Check each label
        labels = domain.split('.')
        for label in labels:
            if not label or len(label) > 63:
                return False
            if label.startswith('-') or label.endswith('-'):
                return False
        
        # Must have at least one dot (unless localhost)
        if domain != 'localhost' and '.' not in domain:
            return False
        
        return True
        
    except Exception:
        return False


def sanitize_string(
    input_string: str,
    max_length: Optional[int] = None,
    allowed_chars: Optional[str] = None
) -> str:
    """
    Sanitize input string by removing/escaping dangerous characters.
    
    Args:
        input_string: String to sanitize
        max_length: Maximum allowed length (truncate if longer)
        allowed_chars: Regex pattern of allowed characters
        
    Returns:
        Sanitized string
    """
    if not input_string:
        return ""
    
    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', input_string)
    
    # Apply character filter if specified
    if allowed_chars:
        sanitized = re.sub(f'[^{allowed_chars}]', '', sanitized)
    
    # Truncate if too long
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def validate_event_data(event_data: dict, max_size: int = 10000) -> bool:
    """
    Validate event data structure and size.
    
    Args:
        event_data: Event data dictionary to validate
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(event_data, dict):
        return False
    
    try:
        import json
        serialized = json.dumps(event_data)
        
        # Check size
        if len(serialized.encode('utf-8')) > max_size:
            return False
        
        # Check for dangerous keys
        dangerous_keys = ['__proto__', 'constructor', 'prototype']
        for key in event_data.keys():
            if key.lower() in dangerous_keys:
                return False
        
        return True
        
    except Exception:
        return False


def validate_query_params(params: dict) -> dict:
    """
    Validate and sanitize query parameters.
    
    Args:
        params: Dictionary of query parameters
        
    Returns:
        Dictionary of validated parameters
    """
    validated = {}
    
    for key, value in params.items():
        # Sanitize key
        clean_key = sanitize_string(key, max_length=50, allowed_chars=r'a-zA-Z0-9_-')
        if not clean_key:
            continue
        
        # Sanitize value
        if isinstance(value, str):
            clean_value = sanitize_string(value, max_length=500)
            if clean_value:
                validated[clean_key] = clean_value
        elif isinstance(value, (int, float, bool)):
            validated[clean_key] = value
    
    return validated
