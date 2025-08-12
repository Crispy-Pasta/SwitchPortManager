# Changelog

## [2.2.0] - 2025-01-12

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

## [2.1.2] - 2025-01-11

### Security Enhancements
- **Enhanced MAC Address Validation**: Implemented comprehensive MAC address format validation with strict regex patterns to prevent command injection attacks
- **Sanitized Error Messages**: Removed potentially harmful examples from MAC format error responses to prevent exposing malicious input patterns
- **Security-Focused Error Handling**: Updated `get_mac_format_error_message()` function to exclude incorrect examples and security notes
- **Frontend Security Updates**: Modified JavaScript error display to align with secure backend responses, removing display of potentially malicious examples

### Code Quality Improvements
- **Enhanced Documentation**: Updated function documentation for security-related components with detailed parameter descriptions
- **Improved Code Comments**: Added comprehensive comments explaining security measures and validation logic
- **Error Response Consistency**: Standardized error message format across frontend and backend components

### Audit and Monitoring
- **Enhanced Audit Logging**: Improved logging for invalid MAC address attempts with security context
- **Input Validation Logging**: Added detailed logging for all input validation failures for security monitoring

### Technical Details
- Modified `is_valid_mac()` function with enhanced regex pattern matching
- Updated frontend `showMacFormatError()` function to display only safe, helpful information
- Removed security-sensitive sections from error display templates
- Enhanced input sanitization across all user-facing input fields

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

