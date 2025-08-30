# Claude Project Rules

These are the rules to follow when suggesting or editing code in this repository.  

## General
- Never commit secrets (API keys, passwords, tokens). Always use environment variables.
- Keep your code changes small and focused.
- Write clear commit messages and pull request descriptions.

## Database (Supabase)
- Never change old migration files. Always create a **new migration file** for any database change.
- Clearly explain what the migration does in the pull request.
- After making a migration, also update the generated Supabase **types** so the app code stays in sync.
- Follow Supabase security best practices. Do not add policies that make data public unless explicitly requested.

## Backend / API
- Follow the existing folder and file structure.
- Always validate user input before saving it to the database.
- Do not log sensitive information (like tokens or passwords).

## Frontend
- Keep components simple and reusable.
- Do not put side effects directly in rendering functions.
- Follow the styling patterns already used in the project.

## Testing
- If you add or change a feature, also add or update tests if possible.
- Confirm that the app still builds and tests pass before suggesting a merge.

## Deployment (Railway)
- Ensure that any environment variables required for new features are documented.
- Do not hardcode database URLs, API keys, or secrets in the codebase.
