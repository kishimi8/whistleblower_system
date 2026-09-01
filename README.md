#  Whistleblowing  portal

A secure, anonymous whistleblowing platform built with Django that allows users to report misconduct while maintaining complete anonymity and providing secure communication channels.

## ✨ Features

- **Anonymous Reporting**: Submit reports without revealing identity
- **Secure Case Tracking**: Track report progress with unique Case ID and Access Code
- **Encrypted Communication**: Secure messaging between whistleblowers and investigators
- **File Upload Support**: Attach evidence files (up to 10MB)
- **Audit Trail**: Complete logging of all actions for transparency
- **Responsive Design**: Mobile-friendly interface built with Tailwind CSS
- **Multiple Categories**: Support for various types of misconduct reporting

## 🛠️ Tech Stack

- **Backend**: Django 5.2, Python 3.12
- **Frontend**: HTML5, Tailwind CSS 4.1
- **Database**: SQLite (development), PostgreSQL ready
- **File Storage**: Local filesystem with media handling
- **Containerization**: Docker support included

## 📋 Prerequisites

- Python 3.12+
- Node.js 18+
- npm or yarn
- Docker (optional)

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd WhistleBlower
```

2. **Set up Python environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install django python-dotenv django-compressor
```

3. **Install frontend dependencies**
```bash
npm install
```

4. **Environment setup**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Database setup**
```bash
python manage.py migrate
python manage.py createsuperuser  # Optional: for admin access
```

6. **Build CSS**
```bash
npx tailwindcss -i ./static/src/input.css -o ./static/src/output.css --watch
```

7. **Run development server**
```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

### Docker Deployment

1. **Build and run with Docker**
```bash
docker build -t whistleblower .
docker run -p 8059:8059 whistleblower
```

## 📁 Project Structure

```
WhistleBlower/
├── reports/                 # Main Django app
│   ├── models.py           # Report, Communication, AuditLog models
│   ├── views.py            # Application views
│   ├── forms.py            # Django forms
│   └── urls.py             # URL routing
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   └── reports/            # Report-specific templates
├── static/                 # Static files
│   └── src/                # CSS source files
├── media/                  # User uploaded files
├── WhistleBlower/          # Django project settings
└── Dockerfile              # Container configuration
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Security Settings

The application includes production-ready security settings:
- CSRF protection enabled
- Secure file upload handling
- XSS protection
- Content type validation

## 📊 Database Models

### Report Model
- **case_id**: Unique identifier (WB + year + random number)
- **access_code**: 8-character secure access code
- **title, description, category**: Report details
- **incident_date**: When the incident occurred
- **evidence_file**: Optional file attachment
- **status**: New, Under Review, Investigating, Closed

### Communication Model
- Secure messaging between whistleblowers and investigators
- Tracks sender type (whistleblower vs investigator)
- Maintains conversation history

### AuditLog Model
- Complete audit trail of all actions
- Tracks user actions and system events
- Ensures transparency and accountability

## 🎯 Usage

### For Whistleblowers

1. **Submit Report**: Fill out the anonymous report form
2. **Save Credentials**: Note down your Case ID and Access Code
3. **Track Progress**: Use credentials to check report status
4. **Communicate**: Send secure messages to investigators

### For Investigators (Admin)

1. **Access Admin Panel**: `/admin/` with superuser credentials
2. **Review Reports**: View and manage submitted reports
3. **Update Status**: Change report status as investigation progresses
4. **Communicate**: Send messages to whistleblowers
5. **Close Cases**: Add resolution summary when complete

## 🔒 Security Features

- **Anonymous Submissions**: No personal information required
- **Secure Access**: Case ID + Access Code authentication
- **File Validation**: Secure file upload with size limits
- **CSRF Protection**: Prevents cross-site request forgery
- **Audit Logging**: Complete action tracking
- **Data Encryption**: Secure data transmission

🔑 Save These Details to Track Your Case
Case ID:
WB2025665010
Access Code:
VNJ0COWC
⚠️ Important: Write down or screenshot these details!

You'll need both to track your case and communicate with investigators.
