# DellPortTracer Performance Optimization Guide

## Current Performance Analysis

### Strengths ✅
- **Concurrent Processing**: Uses `ThreadPoolExecutor` for parallel switch connections
- **Connection Pooling**: PostgreSQL connection pooling with `pool_pre_ping=True`
- **CPU Safety Monitoring**: Real-time CPU monitoring with protection zones
- **Switch Connection Limits**: Proper connection throttling per switch
- **Caching**: Role-based filtering results are cached

### Areas for Improvement 🚀

## 1. Database Optimization

### Connection Pool Tuning
```python
# Current settings
'SQLALCHEMY_ENGINE_OPTIONS': {
    'pool_recycle': 300,  # 5 minutes
    'pool_pre_ping': True
}

# Recommended settings
'SQLALCHEMY_ENGINE_OPTIONS': {
    'pool_size': 20,         # Base connections
    'max_overflow': 30,      # Additional connections
    'pool_recycle': 3600,    # 1 hour (longer for stability)
    'pool_pre_ping': True,   # Keep for connection validation
    'pool_timeout': 30,      # Connection timeout
    'echo': False           # Disable SQL logging in production
}
```

### Query Optimization
```python
# Add database indexes for frequent queries
class Switch(db.Model):
    # Add composite indexes
    __table_args__ = (
        Index('idx_switch_site_floor', 'floor_id', 'enabled'),
        Index('idx_switch_ip', 'ip_address'),
        Index('idx_switch_name', 'name'),
    )

# Use eager loading for relationships
switches = db.session.query(Switch, Floor, Site).join(
    Floor, Switch.floor_id == Floor.id
).join(
    Site, Floor.site_id == Site.id
).options(
    joinedload(Switch.floor),
    joinedload(Floor.site)
).filter(Switch.enabled == True).all()
```

## 2. Caching Strategy

### Redis Implementation
```python
import redis
from functools import wraps
import pickle
import hashlib

class CacheManager:
    def __init__(self, redis_url='redis://localhost:6379/0'):
        self.redis_client = redis.from_url(redis_url)
        self.default_ttl = 300  # 5 minutes
    
    def cache_key(self, prefix, *args):
        """Generate cache key from arguments."""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def cached_result(self, ttl=None, prefix="cache"):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self.cache_key(prefix, func.__name__, *args, **kwargs)
                
                # Try to get from cache
                try:
                    cached = self.redis_client.get(cache_key)
                    if cached:
                        return pickle.loads(cached)
                except Exception:
                    pass  # Cache miss or error
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                try:
                    self.redis_client.setex(
                        cache_key, 
                        ttl or self.default_ttl, 
                        pickle.dumps(result)
                    )
                except Exception:
                    pass  # Cache write error (non-critical)
                
                return result
            return wrapper
        return decorator

# Usage examples
cache_manager = CacheManager()

@cache_manager.cached_result(ttl=600, prefix="switches")
def get_site_switches(site_id, floor_id):
    """Cache switch lookup results."""
    return get_site_floor_switches(site_id, floor_id)

@cache_manager.cached_result(ttl=1800, prefix="switch_config") 
def get_switch_configuration(switch_ip):
    """Cache switch configuration."""
    # Expensive SSH operation - cache for 30 minutes
    pass
```

## 3. Asynchronous Processing

### Celery Background Tasks
```python
from celery import Celery
from app.utils.logging_utils import PerformanceLogger

celery_app = Celery('dell_port_tracer')
performance_logger = PerformanceLogger()

@celery_app.task(bind=True)
def trace_mac_async(self, switches, mac_address, username):
    """Asynchronous MAC tracing with progress tracking."""
    total_switches = len(switches)
    
    for i, switch_info in enumerate(switches):
        try:
            result = trace_single_switch(switch_info, mac_address, username)
            
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': total_switches,
                    'switch': switch_info['name'],
                    'status': result.get('status', 'unknown')
                }
            )
            
        except Exception as e:
            logger.error(f"Switch {switch_info['name']} failed: {e}")
    
    return {'status': 'completed', 'total_processed': total_switches}

# Usage in web routes
@app.route('/trace-async', methods=['POST'])
def trace_mac_async_endpoint():
    """Asynchronous MAC tracing endpoint."""
    data = request.json
    switches = get_site_floor_switches(data['site'], data['floor'])
    
    # Start background task
    task = trace_mac_async.delay(switches, data['mac'], session['username'])
    
    return api_response(
        status=APIStatus.SUCCESS,
        message="MAC tracing started",
        data={'task_id': task.id}
    )

@app.route('/trace-status/<task_id>')
def trace_status(task_id):
    """Check async task status."""
    task = trace_mac_async.AsyncResult(task_id)
    
    if task.state == 'PROGRESS':
        response = {
            'status': 'running',
            'progress': task.info
        }
    elif task.state == 'SUCCESS':
        response = {
            'status': 'completed',
            'result': task.result
        }
    else:
        response = {
            'status': 'error',
            'message': str(task.info)
        }
    
    return api_response(data=response)
```

## 4. SSH Connection Optimization

### Connection Pooling for SSH
```python
import paramiko
from queue import Queue, Empty
import threading
from contextlib import contextmanager

class SSHConnectionPool:
    """SSH connection pool for switch connections."""
    
    def __init__(self, max_connections=10):
        self.pools = {}  # switch_ip -> Queue of connections
        self.locks = {}  # switch_ip -> Lock
        self.max_connections = max_connections
    
    def _get_pool(self, switch_ip):
        """Get connection pool for switch."""
        if switch_ip not in self.pools:
            self.pools[switch_ip] = Queue(maxsize=self.max_connections)
            self.locks[switch_ip] = threading.Lock()
        return self.pools[switch_ip], self.locks[switch_ip]
    
    @contextmanager
    def get_connection(self, switch_ip, username, password):
        """Get SSH connection from pool."""
        pool, lock = self._get_pool(switch_ip)
        connection = None
        
        try:
            # Try to get existing connection
            connection = pool.get_nowait()
            if not self._is_connection_alive(connection):
                connection.close()
                connection = None
        except Empty:
            pass
        
        # Create new connection if needed
        if not connection:
            connection = self._create_connection(switch_ip, username, password)
        
        try:
            yield connection
        finally:
            # Return connection to pool
            if connection and self._is_connection_alive(connection):
                try:
                    pool.put_nowait(connection)
                except:
                    connection.close()
            elif connection:
                connection.close()
    
    def _create_connection(self, switch_ip, username, password):
        """Create new SSH connection."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=switch_ip,
            username=username,
            password=password,
            timeout=15
        )
        return client
    
    def _is_connection_alive(self, connection):
        """Check if SSH connection is still alive."""
        try:
            transport = connection.get_transport()
            return transport and transport.is_active()
        except:
            return False

# Global connection pool
ssh_pool = SSHConnectionPool(max_connections=5)

# Updated switch communication
def trace_single_switch_optimized(switch_info, mac_address, username):
    """Optimized switch tracing with connection pooling."""
    switch_ip = switch_info['ip']
    
    with ssh_pool.get_connection(switch_ip, SWITCH_USERNAME, SWITCH_PASSWORD) as ssh:
        # Use pooled connection for commands
        stdin, stdout, stderr = ssh.exec_command(f"show mac address-table address {mac_address}")
        output = stdout.read().decode('utf-8')
        return parse_mac_table_output(output, mac_address)
```

## 5. Frontend Optimization

### API Response Compression
```python
from flask import Flask
import gzip

def gzip_response(response):
    """Compress API responses."""
    if (response.status_code < 200 or 
        response.status_code >= 300 or 
        len(response.data) < 1024):  # Don't compress small responses
        return response
    
    response.data = gzip.compress(response.data)
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(response.data)
    
    return response

# Apply to API routes
@app.after_request
def compress_response(response):
    if request.endpoint and request.endpoint.startswith('api'):
        return gzip_response(response)
    return response
```

### Client-Side Caching
```javascript
// Enhanced client-side caching
class APICache {
    constructor(maxSize = 100, ttl = 300000) { // 5 minutes TTL
        this.cache = new Map();
        this.maxSize = maxSize;
        this.ttl = ttl;
    }
    
    set(key, value) {
        // Remove oldest entries if at capacity
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        this.cache.set(key, {
            value,
            timestamp: Date.now()
        });
    }
    
    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;
        
        // Check if expired
        if (Date.now() - item.timestamp > this.ttl) {
            this.cache.delete(key);
            return null;
        }
        
        return item.value;
    }
}

const apiCache = new APICache();

// Enhanced fetch with caching
async function cachedFetch(url, options = {}) {
    const cacheKey = `${url}:${JSON.stringify(options)}`;
    
    // Try cache first for GET requests
    if (!options.method || options.method === 'GET') {
        const cached = apiCache.get(cacheKey);
        if (cached) {
            return Promise.resolve(cached);
        }
    }
    
    const response = await fetch(url, options);
    const data = await response.json();
    
    // Cache successful GET responses
    if (response.ok && (!options.method || options.method === 'GET')) {
        apiCache.set(cacheKey, data);
    }
    
    return data;
}
```

## 6. Memory Optimization

### Object Pool Pattern
```python
from queue import Queue
import threading

class ObjectPool:
    """Generic object pool for expensive objects."""
    
    def __init__(self, factory_func, max_size=10):
        self.factory_func = factory_func
        self.pool = Queue(maxsize=max_size)
        self.lock = threading.Lock()
    
    @contextmanager
    def get_object(self):
        """Get object from pool or create new one."""
        obj = None
        try:
            obj = self.pool.get_nowait()
        except Empty:
            obj = self.factory_func()
        
        try:
            yield obj
        finally:
            # Return to pool
            try:
                self.pool.put_nowait(obj)
            except:
                pass  # Pool is full, object will be garbage collected

# Usage for SSH connections
def create_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return client

ssh_client_pool = ObjectPool(create_ssh_client, max_size=20)
```

## 7. Monitoring and Metrics

### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_ssh_connections', 'Active SSH connections')
MAC_TRACE_DURATION = Histogram('mac_trace_duration_seconds', 'MAC trace operation duration')

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown'
    ).inc()
    
    REQUEST_DURATION.observe(time.time() - request.start_time)
    return response

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(), 200, {'Content-Type': 'text/plain'}
```

## Implementation Priority

1. **High Priority (Immediate Impact)**
   - Redis caching for switch configurations
   - SSH connection pooling
   - Database query optimization

2. **Medium Priority (Scalability)**
   - Async processing with Celery
   - API response compression
   - Enhanced monitoring

3. **Low Priority (Long-term)**
   - Object pooling
   - Client-side caching enhancements
   - Advanced metrics collection

## Expected Performance Gains

- **MAC Tracing**: 40-60% reduction in response time
- **Database Queries**: 70% reduction in query time
- **Memory Usage**: 30% reduction in memory footprint  
- **Concurrent Users**: Support 3-5x more concurrent users
- **Cache Hit Rate**: 80%+ for frequently accessed data

## Configuration Recommendations

```env
# Production optimizations
FLASK_ENV=production
REDIS_URL=redis://redis-server:6379/0
CELERY_BROKER_URL=redis://redis-server:6379/1

# Database optimization
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=30
POSTGRES_POOL_RECYCLE=3600

# Caching
CACHE_DEFAULT_TIMEOUT=300
CACHE_SWITCH_CONFIG_TIMEOUT=1800

# SSH optimization
SSH_POOL_SIZE=10
SSH_CONNECTION_TIMEOUT=15
```
