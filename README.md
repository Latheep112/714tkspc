# School Management System

A comprehensive school management system built with Flask and SQLAlchemy.

## Features

- **Multi-role Dashboard**: Separate views for Admins, Staff, Teachers, Students, and Parents.
- **Student Management**: Profiles, transcripts, attendance, and fee management.
- **Course Management**: Course planning, sessions, enrollment, and materials.
- **Attendance Tracking**: Session-based attendance with CSV exports and status reporting.
- **Finance Module**: Invoice generation, fee payments, and budget tracking.
- **Parent Portal**: Linked access for parents to monitor their children's progress.
- **Resource Booking**: Management and booking of labs, classrooms, and equipment.
- **Teacher Management**: Workload tracking, performance monitoring, and leave management.
- **Admin Tools**: User management, audit logs, and system policy configuration.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd "python project"
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```bash
   python create_db.py
   python seed_data.py
   ```

## Usage

Run the application:
```bash
python run.py
```
The app will be available at `http://127.0.0.1:5000/`.

## Testing

Run tests using pytest:
```bash
pytest
```

## Project Structure

- `project/`: Main application package.
  - `models.py`: Database models.
  - `routes.py`: Route handlers and business logic.
  - `templates/`: Jinja2 templates.
  - `static/`: Static assets (CSS, JS, uploads).
- `tests/`: Unit and integration tests.
- `instance/`: Database and instance-specific files.
- `run.py`: Application entry point.
- `requirements.txt`: Project dependencies.
