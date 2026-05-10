# Security Setup for Claude Code Agent

## ⚠️ IMPORTANT SECURITY NOTES

### NEVER DO THIS:
- ❌ Share API keys in chat messages, emails, or any unsecured communication
- ❌ Commit API keys to version control (Git, SVN, etc.)
- ❌ Hard-code API keys in source code
- ❌ Store API keys in plain text files
- ❌ Include API keys in configuration files that are shared

### ALWAYS DO THIS:
- ✅ Set API keys as environment variables
- ✅ Use secure credential management systems
- ✅ Rotate API keys regularly
- ✅ Use different keys for different environments
- ✅ Monitor API key usage and set up alerts

## Proper Setup Instructions

### 1. Set Environment Variable (Linux/Mac)
```bash
export ANTHROPIC_API_KEY='your-actual-api-key-here'
```

### 2. Set Environment Variable (Windows PowerShell)
```powershell
$env:ANTHROPIC_API_KEY='your-actual-api-key-here'
```

### 3. Add to Shell Profile (Persistent)
Add to your `~/.bashrc`, `~/.zshrc`, or `~/.profile`:
```bash
export ANTHROPIC_API_KEY='your-actual-api-key-here'
```

### 4. Using .env File (Development Only)
Create `.env` file (add to `.gitignore`):
```
ANTHROPIC_API_KEY=your-actual-api-key-here
```

Then load with:
```bash
source .env
```

## Testing the Agent

### Quick Test
```bash
cd /home/rohan/Public/morphic/backend/agents
python test_agent.py
```

### Manual Test
```bash
# Basic functionality test
python claude_code_agent.py /home/rohan/Public/morphic example_system_prompt.txt "Analyze this project"

# RCA test with sample logs
python claude_code_agent.py /home/rohan/Public/morphic sre_system_prompt.txt --rca sample_logs.txt
```

## If You've Shared an API Key

If you've accidentally shared an API key (like in the previous message):

1. **IMMEDIATELY REVOKE** the compromised key in your Anthropic dashboard
2. **GENERATE A NEW** API key
3. **UPDATE** all applications using the old key
4. **MONITOR** usage for any suspicious activity
5. **REVIEW** your security practices

## Recommended Security Tools

- **Credential Managers**: 1Password, LastPass, Bitwarden
- **Secret Management**: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
- **Environment Management**: direnv, python-dotenv
- **API Security**: Rate limiting, usage monitoring, anomaly detection

## Production Deployment

For production environments:
- Use IAM roles instead of API keys when possible
- Implement key rotation policies
- Set up usage alerts and quotas
- Use VPC endpoints and private networking
- Enable audit logging

Remember: Security is everyone's responsibility. Treat API keys like passwords!
