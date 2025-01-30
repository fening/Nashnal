# NST Timesheet Management System

A comprehensive web-based timesheet management system built with Django that allows employees to submit, track, and manage their work hours and mileage, with a built-in approval workflow system.

## Features

- **User Authentication & Authorization**
  - Role-based access control (Admin, Supervisor, Employee)
  - Secure login with reCAPTCHA integration
  - Password reset functionality

- **Timesheet Management**
  - Create and edit daily time entries
  - Track arrival/departure times
  - Record job details and labor codes
  - Automatic lunch break deduction
  - File attachments support
  - Mileage tracking and calculations

- **Approval Workflow**
  - Multi-level approval process
  - Comments and feedback system
  - Approval history tracking
  - Email notifications

- **Reporting**
  - Detailed time entry views
  - Summary reports
  - Printable timesheet formats
  - Team timesheet overview for supervisors

- **Additional Features**
  - Dark mode support
  - Responsive design
  - Rate management
  - Job details management

## Technology Stack

- Backend: Django
- Database: PostgreSQL
- Frontend: HTML, Tailwind CSS, JavaScript
- Authentication: Django Authentication System
- Security: reCAPTCHA

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/nst_timesheet.git
cd nst_timesheet
```

2. Create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
Create a `.env` file in the project root and add:
```
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=your_database_url
RECAPTCHA_PUBLIC_KEY=your_recaptcha_public_key
RECAPTCHA_PRIVATE_KEY=your_recaptcha_private_key
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

## Project Structure

```
nst_timesheet/
├── accounts/          # User authentication and management
├── timesheets/        # Core timesheet functionality
├── static/           # Static files (CSS, JS, images)
├── templates/        # HTML templates
├── media/           # User-uploaded files
└── nst_timesheet/   # Project settings
```

## Usage

1. Log in with your credentials
2. Create a new time entry for your work day
3. Add job details and travel information
4. Submit for approval
5. Supervisors can review and approve/reject submissions
6. Generate reports as needed

## Development

- Follow PEP 8 style guide
- Write tests for new features
- Document code changes
- Use feature branches and pull requests

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is proprietary and confidential. Unauthorized copying or distribution is prohibited.

## Support

For support, please contact your system administrator or create an issue in the project repository.

## Acknowledgments

- Django Framework
- Tailwind CSS
- All contributors and maintainers
