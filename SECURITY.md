# Security Policy

## Reporting Security Issues

If you discover a security vulnerability in this project, please report it by emailing the maintainers directly. **Do not create a public GitHub issue.**

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Security Best Practices

### Environment Variables

- **Never commit `.env` files** to version control
- Use `.env.example` as a template with placeholder values
- Store sensitive credentials in environment variables or secure secret management systems

### Database Security

- Use strong, unique passwords for database connections
- Configure `DATABASE_URL` in `.env` file, never hardcode credentials
- Use SSL/TLS for database connections in production
- Restrict database access to necessary IP addresses only

### API Keys

- Rotate API keys regularly
- Use separate API keys for development, staging, and production
- Store API keys in environment variables, never in code
- Monitor API key usage for unusual activity

### Production Deployment

- Use HTTPS for all API endpoints
- Enable rate limiting on API endpoints
- Implement proper authentication and authorization
- Keep dependencies up to date
- Use a firewall to restrict access to database and internal services
- Enable audit logging for sensitive operations

### AWS Deployment

- Use IAM roles instead of access keys when possible
- Follow principle of least privilege for IAM permissions
- Enable CloudWatch logging for monitoring
- Use AWS Secrets Manager for sensitive credentials
- Enable VPC security groups to restrict network access

## Known Security Considerations

### Demo Credentials

This project includes demo login credentials for testing purposes. **These should be changed or removed in production deployments.**

### Database Migrations

Migration scripts require database credentials. Always use environment variables and never commit credentials to version control.

### LLM API Keys

The application requires API keys for LLM providers (OpenAI, Groq, xAI). Protect these keys as they may incur costs if compromised.

## Dependencies

- Regularly update dependencies to patch security vulnerabilities
- Run `pip install --upgrade -r requirements.txt` to update packages
- Monitor security advisories for Python packages used in this project
