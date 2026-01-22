# Authentication Setup Guide

## Overview
The Survey Tracking System now includes comprehensive authentication with the following features:
- User login/logout with secure password hashing
- Role-based access control (user, admin, superadmin)
- JWT token-based API authentication
- Protected API endpoints
- Streamlit frontend authentication

## Admin User Configuration

### Default Superadmin Account
- **Username**: `admin`
- **Password**: `Amazing@2001`
- **Email**: `lmabena@nsa.org.na`
- **Role**: `superadmin` (full system access)

## Setup Instructions

### 1. Install Dependencies

#### Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Frontend Dependencies
```bash
cd frontend  
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the environment template and configure authentication settings:

```bash
cd backend
cp env.template .env
```

Edit `.env` with your settings:
```env
# Database (required)
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/survey_tracking

# Authentication (required for production)
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# KoboToolbox Integration
KOBO_BASE_URL=https://kf.kobotoolbox.org
KOBO_TOKEN=your_kobo_api_token_here
KOBO_ASSET_ID=your_form_asset_uid_here
```

**Important**: Generate secure keys for production:
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### 3. Initialize Database and Admin User

Run the admin setup script:
```bash
cd backend
python setup_admin.py
```

This will:
- Create all database tables
- Create the superadmin user with provided credentials
- Display confirmation of the setup

### 4. Start the Services

#### Start Backend API
```bash
cd backend
python kobo_app.py
```
Backend runs on: http://localhost:5000

#### Start Frontend Dashboard
```bash
cd frontend
streamlit run kobo_dashboard.py
```
Frontend runs on: http://localhost:8501

### 5. Access the Dashboard

1. Navigate to http://localhost:8501
2. Log in with:
   - **Username**: `admin`
   - **Password**: `Amazing@2001`
3. Access the protected dashboard features

## Authentication Features

### Role-Based Access Control

- **superadmin**: Full system access, user management
- **admin**: Dashboard access, data viewing
- **user**: Basic access (future expansion)

### Protected Endpoints

All API endpoints are now protected:
- `/api/kobo/submissions` - Admin only
- `/api/kobo/summary` - Admin only  
- `/api/kobo/refresh` - Admin only
- `/api/auth/*` - Authentication endpoints

### User Management (Superadmin Only)

The superadmin can:
- Create new users
- Update user roles and permissions
- Deactivate/reactivate users
- Change passwords
- Delete users

Access user management via API:
- `POST /api/auth/users` - Create user
- `GET /api/auth/users` - List users
- `PUT /api/auth/users/{id}` - Update user
- `DELETE /api/auth/users/{id}` - Delete user

## Security Considerations

1. **Change Default Credentials**: Update the admin password after initial setup
2. **Use HTTPS**: Enable SSL/TLS in production
3. **Secure Environment**: Keep `.env` file secure and never commit to version control
4. **Regular Updates**: Keep dependencies updated for security patches
5. **Access Logs**: Monitor authentication attempts and access patterns

## Troubleshooting

### Login Issues
- Verify backend is running on port 5000
- Check database connection
- Confirm admin user exists: `python setup_admin.py`

### API Authentication Errors  
- Verify JWT tokens are being sent correctly
- Check SECRET_KEY and JWT_SECRET_KEY are set
- Ensure user has appropriate role permissions

### Database Issues
- Verify DATABASE_URL is correct
- Ensure PostgreSQL is running
- Run setup script to create tables: `python setup_admin.py`

## API Usage Examples

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Amazing@2001"}'
```

### Access Protected Endpoint
```bash
curl -X GET http://localhost:5000/api/kobo/summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Create New User (Superadmin)
```bash
curl -X POST http://localhost:5000/api/auth/users \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username":"newuser",
    "email":"user@example.com", 
    "password":"SecurePass123",
    "role":"admin"
  }'
```

The authentication system is now fully configured and ready for use!