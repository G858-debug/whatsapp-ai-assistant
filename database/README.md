# Database Migrations

This directory contains SQL migration files for the WhatsApp AI Assistant database.

## Applying Migrations

These migrations should be applied to your Supabase database. You can apply them in one of two ways:

### Option 1: Supabase Dashboard (Recommended)
1. Log in to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy the contents of the migration file
4. Paste into the SQL Editor
5. Click "Run" to execute

### Option 2: Supabase CLI
```bash
supabase db push
```

## Migration Files

- `001_create_invitation_reminder_logs.sql` - Creates the `invitation_reminder_logs` table for tracking invitation reminders (24h, 72h, 7d)

## Notes

- Migrations are numbered sequentially (001, 002, etc.)
- Always review migrations before applying to production
- Ensure migrations are idempotent (can be run multiple times safely)
