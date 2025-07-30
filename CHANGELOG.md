# Changelog

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

