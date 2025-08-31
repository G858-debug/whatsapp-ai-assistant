# Claude Project Rules

These are the rules to follow when suggesting or editing code in this repository.

## Project Context
- **Project**: Refiloe - WhatsApp AI Assistant for South African personal trainers
- **Tech Stack**: Python Flask, Supabase, Railway, WhatsApp Business API
- **Target Users**: Personal trainers and their clients in South Africa
- **Primary Interface**: WhatsApp messages

## General Rules
- Never commit secrets (API keys, passwords, tokens). Always use environment variables.
- Keep your code changes small and focused.
- Write clear commit messages and pull request descriptions.
- Follow existing code patterns and structure.
- All code must be compatible with Railway deployment.

## South African Context 🇿🇦
- **Currency**: Always use Rand (R) not dollars ($)
- **Phone Format**: Use +27 format (e.g., +27821234567)
- **Time Zone**: Africa/Johannesburg (SAST)
- **Language**: South African English (colour not color, realise not realize)
- **Payment**: Support local payment methods (PayFast, not Stripe)

## WhatsApp Specific Rules 📱
- **Message Length**: Keep all responses under 1600 characters
- **Formatting**: Use WhatsApp-compatible formatting:
  - Bold: *text*
  - Italic: _text_
  - Strikethrough: ~text~
  - No HTML or Markdown
- **Emojis**: Use emojis appropriately for friendly tone
- **Natural Language**: Prefer understanding natural language over rigid commands
  - Good: "book me for Tuesday at 3pm"
  - Bad: "/book --date 2024-01-15 --time 15:00"
- **Session State**: Remember conversation context

## Database (Supabase) 🗄️
- Never change old migration files. Always create a **new migration file** for any database change.
- Migration file naming: `YYYYMMDDHHMMSS_descriptive_name.sql`
- Always include rollback comments in migrations:
  ```sql
  -- Migration: Add booking status
  ALTER TABLE bookings ADD COLUMN status VARCHAR(50);
  
  -- Rollback: 
  -- ALTER TABLE bookings DROP COLUMN status;

Include indexes for foreign keys and commonly queried fields
Follow Supabase security best practices:
- Use Row Level Security (RLS) policies
- Never expose service keys in client code
- Do not add policies that make data public unless explicitly requested
After making a migration, update any affected Python models/services

## Backend / API 🔧

Follow the existing folder structure:
/services     - Business logic
/routes       - API endpoints  
/utils        - Helper functions
/migrations   - Database migrations

- Always validate user input before saving to database
- Use the existing error handling pattern:
pythontry:
    # operation
except Exception as e:
    log_error(f"Context: {str(e)}")
    return friendly_error_message

## Error Handling & User Experience 🎯

- Always return user-friendly error messages via WhatsApp
- Never expose technical errors to end users
- Log technical errors for debugging
- Provide helpful suggestions when operations fail:
python# Good
"I couldn't find that booking. Try saying 'show my bookings' to see all your appointments 📅"

# Bad  
"Database query failed: no rows returned"

## Code Completeness Rules ✅
When encountering incomplete code:

- Complete ALL functions - no pass statements or ...
- Implement proper error handling in every function
- Add docstrings to all functions and classes
- Include type hints where helpful
- Never leave TODO comments - implement the functionality

## Testing 🧪

- If you add or change a feature, create corresponding tests
- Test file naming: test_[module_name].py
-  Include tests for:

 - Success cases
 - Failure cases
 - Edge cases (empty inputs, invalid data)

Ensure tests work with Railway deployment

## Dependencies 📦

- Before adding new packages, check if functionality exists in current packages
- Add new dependencies to requirements.txt with specific versions
- Ensure all packages are Railway-compatible (no OS-specific dependencies)
- Prefer lightweight packages for faster cold starts

## Performance Considerations ⚡

- Optimize for mobile users
- Minimize database queries (use joins over multiple queries)
- Cache frequently accessed data where appropriate

## Security Rules 🔒

- Sanitize all user inputs
- Use parameterized queries (never string concatenation for SQL)
- Validate phone numbers match expected format
- Implement rate limiting for all endpoints
- Never store payment card details - use tokenization
- Check user permissions before every operation

## Deployment (Railway) 🚂

- Ensure code works with Railway's ephemeral filesystem
- Use environment variables for all configuration
- Document any new environment variables needed:
python# When adding new env vars, include comment:
# Add to Railway: VARIABLE_NAME = "description of purpose"

- Don't use local file storage - use Supabase storage
- Ensure no hardcoded ports (use PORT env variable)

## AI Integration Rules 🤖
When implementing AI features:

- Use natural language understanding over commands
- Provide examples to users when they seem confused
- Gracefully handle when AI doesn't understand
- Keep AI responses conversational but professional
- Always maintain context about the user's business (fitness/training)

## Workflow Commands 🎮
When responding to GitHub comments:

- @claude - Analysis only, no changes
- @claude @apply - Make changes and commit to main
- @claude @pr @apply - Make changes in a new branch
- Always show reasoning before making changes
- List all files that will be modified
- Provide a summary of changes made

## Model Selection 🤖
When processing requests:
- **Sonnet 3.5** is used for: Simple fixes, single-file changes, documentation updates
- **Opus 4.1** is used for: Complex analysis, multi-file changes, system design
- Users can force a model with `@sonnet` or `@opus` flags
- Consider cost implications: Opus is 5x more expensive than Sonnet

## Priority Order 📊
When improving code, prioritize:

1. Critical bugs - Anything breaking core functionality
2. Incomplete functions - Complete all partial implementations
3. Security issues - Fix vulnerabilities
4. User experience - Improve WhatsApp interactions
5. Performance - Optimize slow operations
6. Technical debt - Refactor messy code
7. Features - Add new capabilities

## Do NOT 🚫

- Don't use print() for debugging - use proper logging
- Don't catch exceptions silently
- Don't use global variables
- Don't hardcode configuration values
- Don't create synchronous blocking operations
- Don't forget mobile users have limited data
- Don't use complex regex that users won't understand
- Don't create migrations that can't be rolled back

## Remember 💭
You're building for South African personal trainers who:

- May not be tech-savvy
- Use WhatsApp as primary interface
- Need simple, reliable functionality
- Want to focus on training, not admin

Every decision should make their lives easier!
