#!/usr/bin/env python3
"""
API Utilities and Response Standards
====================================

Standardized API responses, input validation, and error handling
for consistent REST API behavior.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from flask import jsonify, request, current_app
import re
import ipaddress
from datetime import datetime
import functools


class APIStatus(Enum):
    """Standard API status codes."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


@dataclass
class APIResponse:
    """Standardized API response format."""
    status: str
    message: str
    data: Optional[Union[Dict, List]] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + 'Z'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        
        # Remove None values for cleaner JSON
        return {k: v for k, v in result.items() if v is not None}
    
    def to_flask_response(self, status_code: int = 200):
        """Convert to Flask JSON response."""
        return jsonify(self.to_dict()), status_code


class ValidationError(Exception):
    """Custom validation error."""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class InputValidator:
    """Input validation utilities."""
    
    # Common regex patterns
    MAC_ADDRESS_PATTERNS = [
        r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',  # XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX
        r'^([0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}$'        # XXXX.YYYY.ZZZZ
    ]
    
    SWITCH_NAME_PATTERN = r'^[A-Za-z0-9\-_\.]+$'
    PORT_NAME_PATTERN = r'^(Gi|Te|Tw|Po)\d+(/\d+)*$'
    VLAN_ID_PATTERN = r'^[1-9]\d{0,3}$'  # 1-9999
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]):
        """Validate that required fields are present and non-empty."""
        missing_fields = []
        empty_fields = []
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif not data[field] or str(data[field]).strip() == '':
                empty_fields.append(field)
        
        errors = []
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        if empty_fields:
            errors.append(f"Empty required fields: {', '.join(empty_fields)}")
        
        if errors:
            raise ValidationError('; '.join(errors))
    
    @staticmethod
    def validate_mac_address(mac: str) -> str:
        """Validate and normalize MAC address format."""
        if not mac or not isinstance(mac, str):
            raise ValidationError("MAC address is required and must be a string", "mac")
        
        mac = mac.strip().upper()
        
        # Check against known patterns
        for pattern in InputValidator.MAC_ADDRESS_PATTERNS:
            if re.match(pattern, mac):
                return mac
        
        raise ValidationError("Invalid MAC address format. Expected formats: XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX, or XXXX.YYYY.ZZZZ", "mac")
    
    @staticmethod
    def validate_ip_address(ip: str) -> str:
        """Validate IP address format."""
        if not ip or not isinstance(ip, str):
            raise ValidationError("IP address is required and must be a string", "ip")
        
        try:
            # This validates both IPv4 and IPv6
            ipaddress.ip_address(ip.strip())
            return ip.strip()
        except ValueError:
            raise ValidationError("Invalid IP address format", "ip")
    
    @staticmethod
    def validate_switch_name(name: str) -> str:
        """Validate switch name format."""
        if not name or not isinstance(name, str):
            raise ValidationError("Switch name is required and must be a string", "name")
        
        name = name.strip()
        
        if not re.match(InputValidator.SWITCH_NAME_PATTERN, name):
            raise ValidationError("Switch name can only contain letters, numbers, hyphens, underscores, and dots", "name")
        
        if len(name) < 3 or len(name) > 100:
            raise ValidationError("Switch name must be between 3 and 100 characters", "name")
        
        return name
    
    @staticmethod
    def validate_port_name(port: str) -> str:
        """Validate Dell switch port name format."""
        if not port or not isinstance(port, str):
            raise ValidationError("Port name is required and must be a string", "port")
        
        port = port.strip()
        
        if not re.match(InputValidator.PORT_NAME_PATTERN, port):
            raise ValidationError("Invalid port name format. Expected formats: Gi1/0/1, Te1/0/1, Tw1/0/1, Po1", "port")
        
        return port
    
    @staticmethod
    def validate_vlan_id(vlan_id: Union[str, int]) -> int:
        """Validate VLAN ID."""
        if vlan_id is None:
            raise ValidationError("VLAN ID is required", "vlan_id")
        
        # Convert to string for regex validation
        vlan_str = str(vlan_id).strip()
        
        if not re.match(InputValidator.VLAN_ID_PATTERN, vlan_str):
            raise ValidationError("VLAN ID must be between 1 and 9999", "vlan_id")
        
        vlan_int = int(vlan_str)
        
        # Additional range validation
        if vlan_int < 1 or vlan_int > 4094:  # Standard VLAN range
            raise ValidationError("VLAN ID must be between 1 and 4094", "vlan_id")
        
        return vlan_int
    
    @staticmethod
    def validate_vlan_name(name: str) -> str:
        """Validate VLAN name format."""
        if not name or not isinstance(name, str):
            raise ValidationError("VLAN name is required and must be a string", "name")
        
        name = name.strip()
        
        if len(name) < 3 or len(name) > 64:
            raise ValidationError("VLAN name must be between 3 and 64 characters", "name")
        
        # Check for valid characters (allow letters, numbers, underscores, hyphens)
        if not re.match(r'^[A-Za-z0-9_\-]+$', name):
            raise ValidationError("VLAN name can only contain letters, numbers, underscores, and hyphens", "name")
        
        return name


class PaginationHelper:
    """Pagination utility for API responses."""
    
    @staticmethod
    def get_pagination_params() -> Tuple[int, int]:
        """Extract pagination parameters from request."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Validate parameters
        page = max(1, page)  # Minimum page 1
        per_page = min(100, max(1, per_page))  # Between 1 and 100 items per page
        
        return page, per_page
    
    @staticmethod
    def paginate_results(items: List[Any], page: int, per_page: int) -> Dict[str, Any]:
        """Paginate a list of items."""
        total = len(items)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        paginated_items = items[start_idx:end_idx]
        
        return {
            'items': paginated_items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_next': end_idx < total,
                'has_prev': page > 1
            }
        }


def api_response(status: APIStatus = APIStatus.SUCCESS,
                message: str = "",
                data: Optional[Union[Dict, List]] = None,
                errors: Optional[List[str]] = None,
                warnings: Optional[List[str]] = None,
                metadata: Optional[Dict[str, Any]] = None,
                status_code: int = 200) -> Tuple[Dict, int]:
    """Create standardized API response."""
    
    response = APIResponse(
        status=status.value,
        message=message,
        data=data,
        errors=errors,
        warnings=warnings,
        metadata=metadata
    )
    
    return response.to_flask_response(status_code)


def validate_json_request(required_fields: List[str] = None,
                         optional_fields: List[str] = None):
    """Decorator for JSON request validation."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return api_response(
                    status=APIStatus.ERROR,
                    message="Content-Type must be application/json",
                    errors=["Invalid content type"],
                    status_code=400
                )
            
            try:
                data = request.get_json()
                if data is None:
                    return api_response(
                        status=APIStatus.ERROR,
                        message="Invalid JSON payload",
                        errors=["Request body must contain valid JSON"],
                        status_code=400
                    )
                
                # Validate required fields
                if required_fields:
                    InputValidator.validate_required_fields(data, required_fields)
                
                # Add validated data to kwargs
                kwargs['validated_data'] = data
                
                return func(*args, **kwargs)
                
            except ValidationError as e:
                return api_response(
                    status=APIStatus.ERROR,
                    message="Validation failed",
                    errors=[e.message],
                    status_code=400
                )
            except Exception as e:
                current_app.logger.error(f"Request validation error: {str(e)}", exc_info=True)
                return api_response(
                    status=APIStatus.ERROR,
                    message="Request validation failed",
                    errors=["Internal validation error"],
                    status_code=500
                )
        
        return wrapper
    return decorator


def handle_api_errors(func):
    """Decorator for consistent API error handling."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        
        except ValidationError as e:
            return api_response(
                status=APIStatus.ERROR,
                message="Validation failed",
                errors=[e.message],
                status_code=400
            )
        
        except PermissionError as e:
            return api_response(
                status=APIStatus.ERROR,
                message="Insufficient permissions",
                errors=[str(e)],
                status_code=403
            )
        
        except FileNotFoundError as e:
            return api_response(
                status=APIStatus.ERROR,
                message="Resource not found",
                errors=[str(e)],
                status_code=404
            )
        
        except Exception as e:
            current_app.logger.error(f"Unhandled API error in {func.__name__}: {str(e)}", exc_info=True)
            return api_response(
                status=APIStatus.ERROR,
                message="Internal server error",
                errors=["An unexpected error occurred"],
                status_code=500
            )
    
    return wrapper


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            key: Unique identifier (e.g., IP address, user ID)
            limit: Number of requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = datetime.utcnow().timestamp()
        
        # Clean old entries
        if key in self.requests:
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if now - timestamp <= window
            ]
        else:
            self.requests[key] = []
        
        current_count = len(self.requests[key])
        
        if current_count < limit:
            self.requests[key].append(now)
            return True, {
                'limit': limit,
                'remaining': limit - current_count - 1,
                'reset_time': int(now + window)
            }
        else:
            return False, {
                'limit': limit,
                'remaining': 0,
                'reset_time': int(self.requests[key][0] + window)
            }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(limit: int = 100, window: int = 3600, key_func=None):
    """
    Rate limiting decorator.
    
    Args:
        limit: Number of requests allowed
        window: Time window in seconds
        key_func: Function to generate rate limit key (default: IP address)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate key for rate limiting
            if key_func:
                key = key_func()
            else:
                key = request.remote_addr or 'unknown'
            
            allowed, rate_info = rate_limiter.is_allowed(key, limit, window)
            
            if not allowed:
                return api_response(
                    status=APIStatus.ERROR,
                    message="Rate limit exceeded",
                    errors=["Too many requests"],
                    metadata=rate_info,
                    status_code=429
                )
            
            response = func(*args, **kwargs)
            
            # Add rate limit headers if it's a Flask response
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(rate_info['reset_time'])
            
            return response
        
        return wrapper
    return decorator
