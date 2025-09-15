# Changelog

## [2.2.1] - 2025-09-15

### 🎨 **UI/UX Enhancements**
- **Port Status Visual Differentiation**: Enhanced VLAN Manager port status display with improved color coding
  - **New `.status-disabled` CSS Class**: Added distinct blue (#3498db) styling for disabled ports
  - **Clear Visual Separation**: Disabled ports now visually distinguished from DOWN ports (gray #7f8c8d) and UP ports (green #27ae60)
  - **Consistent Design System**: Blue color matches existing application theme and button styling
  - **Improved User Experience**: Network administrators can now quickly identify disabled vs down ports in status tables
  - **Font Weight Enhancement**: Semi-bold (600) text for disabled ports provides additional visual emphasis

### 🔧 **Technical Improvements**
- **CSS Architecture**: Enhanced port status styling in `templates/vlan.html` following established design patterns
- **Port Status Detection**: Application correctly identifies and processes "disabled" status from switch outputs
- **Design Consistency**: Maintains coherent visual hierarchy across all port status indicators

### 📊 **Port Status Color Scheme**
- **UP Ports**: Green (#27ae60) with bold text - Active and operational
- **DOWN Ports**: Gray (#7f8c8d) with normal text - Inactive but administratively enabled
- **DISABLED Ports**: Blue (#3498db) with semi-bold text - Administratively disabled/shutdown
- **Enhanced Accessibility**: Clear color differentiation improves accessibility for network operations teams

## [2.2.0] - 2025-09-12

### ✨ **Workflow-Based VLAN Management**
- **Structured Workflows**: Introduced workflow-based VLAN management operations for consistent port management
  - 🟢 **Onboarding Workflow**: Enable Ports workflow for new user setup and port activation processes
  - 🔴 **Offboarding Workflow**: Shutdown Ports workflow for user departures and port deactivation processes
- **Enhanced User Interface**: Streamlined VLAN Manager form with workflow type selection
  - Compact workflow type dropdown with visual emoji indicators
  - Dynamic contextual help text that updates based on selected workflow type
  - Improved form layout with cleaner spacing and professional appearance
  - Removed parentheses from workflow options for cleaner, more concise interface

### 🎨 **Select2 Dropdown UI Enhancements**
- **Professional Styling**: Comprehensive Select2 dropdown styling improvements for consistent user experience
  - **Smart Color Management**: Intelligent differentiation between placeholder text (light gray) and selected values (dark text)
  - **Text Alignment**: Proper vertical centering and alignment for all dropdown text elements
  - **Search Optimization**: Workflow Type dropdown search disabled (only 2 options), Target Switch maintains search functionality
  - **Cross-Browser Consistency**: Enhanced CSS specificity and JavaScript fallbacks for uniform appearance
- **Enhanced User Experience**: Professional, consistent interface design across all Select2 elements
  - Real-time styling updates when selections change
  - Improved readability with proper contrast ratios
  - Consistent behavior across different browsers and devices
  - Event-driven styling ensures persistent visual consistency

### 🎯 **VLAN Manager Improvements**
- **Frontend Enhancements**:
  - Workflow type dropdown integration with backend parameter passing
  - Enhanced form validation with workflow-specific guidance
  - Improved visual design and user experience consistency
- **Backend Integration**:
  - Workflow type parameter passed through all VLAN management operations
  - Enhanced audit logging with workflow context for compliance tracking
  - Workflow-aware error handling and validation messages

### 📚 **Documentation Updates**
- **Updated README.md**: Comprehensive documentation of workflow type feature with examples
- **Version Updates**: Updated version badges and references across codebase to v2.2.0
- **Enhanced Changelog**: Detailed feature documentation with technical implementation details

### 🔧 **Technical Improvements**
- **Code Organization**: Enhanced frontend JavaScript for workflow type handling
- **Version Centralization**: Implemented single source of truth for version management
  - Centralized version definition in `app/__init__.py` with `__version__ = "2.2.0"`
  - Created `get_version.py` utility script for programmatic version access
  - Eliminated version duplication across multiple files for consistency
  - Enhanced version management for automated builds and deployments
- **Version Management**: Updated version references in main.py, run.py, and documentation
- **Form Optimization**: Improved form structure and styling for workflow selection

## [2.1.8] - 2025-01-09

### 🛠️ Performance & Logging Improvements
- **Debug Logging Cleanup**: Significantly reduced excessive debug logging in VLAN Manager for improved production performance
  - Removed granular column-by-column parsing debug statements from port status analysis
  - Eliminated verbose debug traces from VLAN parsing logic (General mode, access mode detection)
  - Cleaned up bulk port status processing debug output while preserving essential operational logs
  - Maintained all `logger.info()`, `logger.warning()`, and `logger.error()` statements for operational monitoring
  - Reduced log verbosity by ~70% while preserving critical troubleshooting information

### 🔧 Code Quality Enhancements
- **Enhanced SSH Command Execution**: Improved bulk port status retrieval with better pagination handling
  - Enhanced adaptive output collection for large switch outputs (stack 5+ scenarios)
  - Added terminal pagination disabling commands for more reliable bulk operations
  - Improved CLI prompt detection and automatic space key sending for paginated output
  - Better timeout handling for large `show interfaces status` commands on multi-stack switches

### 📊 Monitoring & Troubleshooting
- **Preserved Essential Logging**: Maintained critical operational logs for production monitoring
  - Port status inference decisions and link state detection results
  - VLAN assignment confirmations and General mode native VLAN detection
  - Bulk operation success/failure summaries and fallback scenarios
  - Switch connection status and command execution results
  - All error conditions and warning scenarios for network operations teams

### 🏆 Production Ready
- **Optimized for Large Deployments**: Improved performance for environments with multiple switch stacks
  - Reduced log file growth rate in high-volume VLAN management scenarios
  - Better handling of 8-stack Dell switch deployments with large port counts
  - Maintained full functionality while dramatically improving log readability

## [2.1.6] - 2025-08-27

### 🚀 Major Enhancements
- **Automatic Database Initialization**: Zero-configuration database setup with retry logic for containerized deployments
- **Enhanced Session Security**: Configurable session cookie settings for HTTP/HTTPS deployments (SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE)
- **Production Health Checks**: Enhanced health monitoring with database connectivity validation and schema verification
- **Fresh Server Deployment**: Comprehensive deployment strategies with automated scripts for multiple deployment scenarios
- **Docker Package Management**: Enhanced tagging strategy with develop-latest, version-specific tags, and proper semantic versioning

### 🔧 Technical Improvements
- **Database Connection Retry**: Robust database initialization with containerized deployment support and automatic schema creation
- **Docker Entrypoint**: Proper containerized startup sequence with database initialization via docker-entrypoint.sh
- **Enhanced CI Pipeline**: Improved Docker tagging with branch-specific and SHA-based tags for better traceability
- **Repository Cleanup**: Removed 15+ obsolete, duplicate, and sensitive files for cleaner, more professional codebase

### 🛡️ Security Enhancements
- **Environment-Based Configuration**: All session and security settings now configurable via environment variables
- **Container Security**: Enhanced with proper user permissions, resource limits, and security policies
- **Data Protection**: Removed sensitive files from repository and enhanced .gitignore patterns
- **Session Cookie Security**: Configurable security settings for different deployment environments

### 📚 Documentation Overhaul
- **Fresh Server Deployment Guide**: Complete guide with 6 deployment approaches (Docker Compose, Ansible, Kubernetes, Cloud platforms)
- **Docker Package Documentation**: Comprehensive Docker image management and tagging strategy guide
- **Git Branching Strategy**: Proper Git Flow implementation with semantic versioning guidelines
- **Repository Audit**: Complete cleanup of duplicate and outdated documentation

### 🔄 CI/CD Pipeline Changes
- **CD Pipeline**: Disabled automated deployment to allow flexible deployment tool choices
- **CI Pipeline**: Enhanced with improved Docker builds, health checks, and tag-based triggers
- **Package Registry**: Fresh builds with proper timestamps and version tags

### 🐛 Fixes
- **Session Login Loops**: Fixed HTTP/HTTPS cookie compatibility issues that caused login redirect loops
- **Docker Package Timestamps**: Resolved 'published 20 hours ago' issue with fresh builds
- **Health Check Validation**: Enhanced health checks now properly validate database connectivity and schema

### 🗑️ Removed
- **Obsolete Documentation**: Removed 8 duplicate/outdated documentation files
- **Legacy Scripts**: Removed 4 obsolete deployment scripts
- **Sensitive Files**: Removed files containing secrets and production configurations
- **Unused Docker Compose**: Removed 2 obsolete docker-compose variants

### ⚠️ Breaking Changes
- **Session Configuration**: Session cookie security is now environment-configurable (update .env files)
- **Database Initialization**: Now automatic (no manual schema setup required)
- **CD Pipeline**: Automated deployments disabled (manual deployment required)

### 🔄 Migration Guide
- Update .env files with new session security variables:
  ```env
  SESSION_COOKIE_SECURE=false  # Set to true for HTTPS
  SESSION_COOKIE_HTTPONLY=true
  SESSION_COOKIE_SAMESITE=Lax
  PERMANENT_SESSION_LIFETIME=5
  ```
- Use fresh server deployment tools for new installations
- Database schema initializes automatically on first startup

## [2.1.3] - 2025-01-12

### Added
- **Enhanced Management Interface**: Complete redesign of the admin interface with tabbed navigation
  - Separated tabs for Switches, Sites, and Floors management
  - Comprehensive CRUD operations for all entities with proper hierarchical relationships
  - Real-time data synchronization across tabs
  - Enhanced UI/UX with modern tab-based design patterns

- **Sites & Floors Administration**: Full lifecycle management for organizational hierarchy
  - Create, edit, and delete sites with automatic floor and switch cascade handling
  - Create, edit, and delete floors with proper site association
  - Intelligent validation preventing orphaned records and maintaining data integrity
  - Real-time counts and statistics display for sites, floors, and switches

- **API Enhancements**: Complete REST API coverage for all management operations
  - POST `/api/sites` - Create new sites with validation and audit logging
  - PUT `/api/sites/{id}` - Update existing sites with conflict detection
  - DELETE `/api/sites/{id}` - Delete sites with cascading cleanup of related records
  - POST `/api/floors` - Create new floors with site association validation
  - PUT `/api/floors/{id}` - Update existing floors with site relationship management
  - DELETE `/api/floors/{id}` - Delete floors with switch cascade handling
  - Enhanced authentication and authorization for all endpoints (NetAdmin/SuperAdmin only)

### Fixed
- **Switch Management API Route**: Corrected the switch creation API endpoint from incorrect `/api/sites` to proper `/api/switches` route
  - Fixes frontend switch creation functionality
  - Ensures proper request routing and backend processing
  - Maintains API consistency and expected behavior

- **Frontend Data Synchronization**: Enhanced cross-tab data refresh functionality
  - Switch creation/updates now refresh sites and floors data to update counts
  - Site and floor operations properly refresh dependent dropdowns and lists
  - Real-time UI updates without requiring page reloads
  - Consistent data state across all management tabs

### Security Enhancements
- **Role-Based API Protection**: All new API endpoints protected with proper permission checks
- **Input Validation**: Comprehensive validation for site and floor names with injection prevention
- **Audit Logging**: Complete audit trail for all site and floor management operations
- **Data Integrity**: Cascade delete protection and orphan record prevention

### Technical Improvements
- **JavaScript Code Organization**: Improved code structure and error handling
- **CSS Styling**: Enhanced visual design for tabbed interface and management forms
- **Database Operations**: Optimized queries and proper transaction handling
- **Error Handling**: Comprehensive error messages and user feedback

## [2.1.0] - 2025-07-30

### Added
- **Database Integration**: The application now uses a SQLite database to store switch, site, and floor information, replacing the `switches.json` file.
- **Switch Management UI**: A new web interface for administrators to perform CRUD (Create, Read, Update, Delete) operations on switches.
- **Database Migration Script**: A script to migrate data from the old `switches.json` file to the new database schema.
- **CPU and Protection Status UI**: A new UI to display the CPU and protection status of the system.
- **Static Assets**: a new `styles.css` file was added to improve the look and feel of the application.

### Changed
- `port_tracer_web.py`: Major changes to integrate with the new database, including new routes for the management UI and API endpoints.
- `requirements.txt`: Added new dependencies for database integration (`Flask-SQLAlchemy`, `Flask-Migrate`).
- `README.md`: Updated to reflect the new database-driven architecture and management UI.

## [2.1.2] - 2025-01-12

### 🛠️ CPU Safety Monitor Re-enabled
- **Enhanced CPU Load Monitoring**: Re-enabled CPU safety monitor with comprehensive load balancing and request throttling
- **Three-Zone CPU Management**: Green Zone (0-40%), Yellow Zone (40-60%), Red Zone (60%+) with intelligent request handling
- **Detailed Troubleshooting Documentation**: Added comprehensive comments explaining CPU protection zones and effects
- **Performance Logging**: Enhanced logging for CPU protection events and rejected requests for better monitoring

### 🎨 UI/UX Improvements
- **Fixed Trace Results Text Color**: Updated trace results header text from navy blue to white for better readability on dark backgrounds
- **Fixed Additional Information Text**: Changed "Additional Information:" text color to white for visibility
- **Enhanced Contrast**: Improved accessibility and readability across all trace result types
- **CSS Optimization**: Refined styling for optimal contrast ratios and user experience

### 🔧 Enhanced Troubleshooting Documentation
- **DellSwitchSSH Class Documentation**: Added comprehensive troubleshooting guide including:
  - Connection timeout solutions and network connectivity checks
  - Authentication failure troubleshooting (SWITCH_USERNAME/SWITCH_PASSWORD validation)
  - Dell switch SSH session limits (~10 concurrent sessions)
  - Command timeout handling and switch response delays
  - Lost connection recovery and automatic cleanup procedures
- **Switch Model Compatibility**: Detailed support documentation for N2000/N3000/N3200 series
- **Monitoring Integration**: Enhanced switch protection integration documentation

### 📚 Documentation Updates
- **Comprehensive README.md**: Updated with extensive troubleshooting sections including:
  - Step-by-step solutions for HTTP 503 Service Unavailable errors
  - Switch connection timeout resolution procedures
  - Database connection troubleshooting guides
  - Trace results visibility fixes
  - Windows Authentication troubleshooting
  - VLAN Manager loading issues and solutions
- **Log File Monitoring**: Enhanced documentation for application and audit log analysis
- **Performance Optimization**: Added system monitoring endpoints and metrics guidance

### Security Enhancements
- **Enhanced MAC Address Validation**: Implemented comprehensive MAC address format validation with strict regex patterns to prevent command injection attacks
- **Sanitized Error Messages**: Removed potentially harmful examples from MAC format error responses to prevent exposing malicious input patterns
- **Security-Focused Error Handling**: Updated `get_mac_format_error_message()` function to exclude incorrect examples and security notes
- **Frontend Security Updates**: Modified JavaScript error display to align with secure backend responses, removing display of potentially malicious examples

### Code Quality Improvements
- **Enhanced Documentation**: Updated function documentation for security-related components with detailed parameter descriptions
- **Improved Code Comments**: Added comprehensive comments explaining security measures and validation logic throughout codebase
- **Error Response Consistency**: Standardized error message format across frontend and backend components
- **Maintainability**: Enhanced code structure with better troubleshooting guidance for future maintenance

### Audit and Monitoring
- **Enhanced Audit Logging**: Improved logging for invalid MAC address attempts with security context
- **Input Validation Logging**: Added detailed logging for all input validation failures for security monitoring
- **CPU Protection Logging**: Added comprehensive logging for CPU-based request rejections
- **Performance Tracking**: Enhanced audit trail with timing and concurrency metrics

### Technical Details
- Modified `is_valid_mac()` function with enhanced regex pattern matching
- Updated frontend `showMacFormatError()` function to display only safe, helpful information
- Removed security-sensitive sections from error display templates
- Enhanced input sanitization across all user-facing input fields
- Re-enabled `check_cpu_before_request()` function with detailed load zone documentation
- Updated CSS styling for `.additional-info` and `.results h3` elements for better visibility

## [2.1.1] - 2025-08-15

### Added
- **VLAN Management v2**: Enhanced VLAN manager with improved UI and validation.
- **Dropdown Width Optimization**: Fixed dropdown width issues on Switch Management page with constrained 250px width.
- **VLAN Naming Conventions**: Updated placeholder examples to follow enterprise naming standards (e.g., "Zone_Client_Name", "Internal_Network").

### Fixed
- **UI/UX Improvements**: Select2 dropdowns on manage switches page now properly constrained to 250px width to prevent layout overflow.
- **CSS Specificity**: Added stronger CSS selectors with !important declarations to override global Select2 styles.
- **JavaScript Enhancement**: Added forced width application via jQuery .css() calls with timeout for runtime Select2 initialization.

### Technical Notes
- Scoped CSS changes to `.manage-page` class to prevent affecting other pages.
- Enhanced CSS targeting includes `body.manage-page` selectors for increased specificity.
- Applied width constraints to both Select2 containers and selection elements.

