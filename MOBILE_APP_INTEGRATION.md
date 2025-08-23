# Mobile App Integration with Java Backend

## Overview
This document describes how the Flutter mobile app integrates with both Supabase Authentication and the Java backend for user registration and authentication.

## Registration Flow

### 1. User Sign Up Process
1. **User enters email and password** in the Flutter app (`auth_screen.dart`)
2. **Sign up with Supabase** - User account is created in Supabase Authentication
3. **Password temporarily stored** - Password is saved in SharedPreferences for Java backend registration
4. **Email verification sent** - Supabase sends OTP to user's email
5. **User verifies email** - User enters OTP in verification screen
6. **Java backend registration** - After successful verification, user is automatically registered in Java backend
7. **Clean up** - Temporary password is removed from SharedPreferences
8. **Navigate to profile setup** - User proceeds to complete their profile

### 2. Sign In Process
- User signs in with Supabase credentials
- Java backend login is optional (only if accessing Java backend APIs)
- Token from Java backend can be stored for subsequent API calls

## Implementation Details

### Files Modified

#### 1. **JavaAuthService** (`lib/services/java_auth_service.dart`)
New service created to handle Java backend authentication:
- `registerUser()` - Registers user in Java backend
- `login()` - Logs into Java backend (optional)
- `getCaptcha()` - Returns bypass token for mobile apps
- `checkUserExists()` - Checks if user exists in Java backend

#### 2. **Email Verification Screen** (`lib/screens/email_verification_screen.dart`)
Modified to include Java backend registration after email verification:
```dart
// After successful Supabase verification
final javaAuthService = JavaAuthService();
final password = prefs.getString('temp_password_${widget.email}');
if (password != null) {
  await javaAuthService.registerUser(
    email: widget.email,
    password: password,
  );
}
```

#### 3. **Auth Screen** (`lib/screens/auth_screen.dart`)
Modified to temporarily store password:
```dart
// Store password for Java backend registration
final prefs = await SharedPreferences.getInstance();
await prefs.setString('temp_password_$email', password);
```

#### 4. **Java Backend Captcha Service** (`CaptchaServiceImpl.java`)
Modified to accept mobile app bypass token:
```java
if ("MOBILE_APP_BYPASS".equals(code)) {
    return true; // Mobile apps bypass captcha
}
```

## Configuration

### Update Base URL
In `lib/services/java_auth_service.dart`, update the base URL:
```dart
// For local development
static const String baseUrl = 'http://localhost:8002/xiaozhi';

// For production (replace with your server URL)
static const String baseUrl = 'https://your-server.com/xiaozhi';
```

### For iOS (local development)
If testing on iOS simulator with localhost:
```dart
static const String baseUrl = 'http://127.0.0.1:8002/xiaozhi';
```

### For Android (local development)
If testing on Android emulator:
```dart
static const String baseUrl = 'http://10.0.2.2:8002/xiaozhi';
```

### For physical devices (local development)
Use your machine's IP address:
```dart
static const String baseUrl = 'http://192.168.1.240:8002/xiaozhi';
```

## Security Considerations

### 1. Captcha Bypass
The current implementation uses a simple bypass token (`MOBILE_APP_BYPASS`) for mobile apps. In production, consider:
- Adding API key validation
- Implementing device fingerprinting
- Using OAuth2 or JWT tokens
- Rate limiting by device/IP

### 2. Password Storage
Passwords are temporarily stored in SharedPreferences. Consider:
- Using Flutter Secure Storage for sensitive data
- Encrypting the password before storage
- Clearing the password immediately after use

### 3. HTTPS
Always use HTTPS in production:
- Update all URLs to use `https://`
- Implement certificate pinning for additional security

## API Endpoints Used

### Registration
```bash
POST /xiaozhi/user/register
{
  "username": "user@example.com",
  "password": "password123",
  "captcha": "MOBILE_APP_BYPASS",
  "captchaId": "uuid-here"
}
```

### Login (Optional)
```bash
POST /xiaozhi/user/login
{
  "username": "user@example.com",
  "password": "password123",
  "captcha": "MOBILE_APP_BYPASS",
  "captchaId": "uuid-here"
}
```

## Testing

### 1. Run Flutter App
```bash
cd flutter-mobile-app
flutter pub get
flutter run
```

### 2. Test Registration Flow
1. Create new account with email/password
2. Check console logs for:
   - "✅ User registered in both Supabase and Java backend"
3. Verify user exists in both:
   - Supabase Dashboard
   - MySQL database (sys_user table)

### 3. Common Issues

#### Issue: Connection refused
**Solution**: Check that Java backend is running and accessible from your device

#### Issue: Captcha validation failed
**Solution**: Ensure CaptchaServiceImpl.java has the bypass code

#### Issue: User already exists
**Solution**: This is handled gracefully - the app will proceed even if user exists in Java backend

## Future Improvements

1. **Token Management**
   - Implement proper token storage and refresh
   - Use Java backend token for protected APIs

2. **Error Handling**
   - Add retry logic for network failures
   - Implement offline mode support

3. **Security Enhancements**
   - Add device-specific tokens
   - Implement biometric authentication
   - Add 2FA support

4. **Profile Sync**
   - Sync user profiles between Supabase and Java backend
   - Handle profile updates across both systems

## Dependencies Added

```yaml
# pubspec.yaml
dependencies:
  uuid: ^4.5.1  # For generating UUIDs
  shared_preferences: ^2.2.2  # Already existed
```

## Troubleshooting

### Check Java Backend Logs
```bash
tail -f main/manager-api/logs/xiaozhi-esp32-api.log
```

### Test API Directly
```bash
# Test registration endpoint
curl -X POST "http://localhost:8002/xiaozhi/user/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test@example.com",
    "password": "password123",
    "captcha": "MOBILE_APP_BYPASS",
    "captchaId": "test-uuid"
  }'
```

### Verify Database Entry
```sql
-- Check if user was created in MySQL
SELECT * FROM sys_user WHERE username = 'test@example.com';
```