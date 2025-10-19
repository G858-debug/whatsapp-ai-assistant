# Social Media Scheduler

This module provides automated social media content generation, posting, and analytics collection for Refiloe's AI assistant.

## Features

- **Automated Content Generation**: AI-powered content creation using Claude API
- **Scheduled Posting**: Automatic posting to Facebook at optimal times
- **Image Generation**: AI-generated images using Replicate API
- **Analytics Collection**: Automated performance tracking
- **Railway Compatible**: Designed for single dyno deployment

## Quick Start

### 1. Environment Variables

Set the following environment variables:

```bash
# Required for content generation
ANTHROPIC_API_KEY=your_anthropic_api_key

# Required for image generation
REPLICATE_API_TOKEN=your_replicate_api_token

# Required for Facebook posting
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token
FACEBOOK_PAGE_ID=your_page_id

# Required for database operations
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### 2. Integration with Flask App

Add to your `app.py`:

```python
from social_media.scheduler import create_social_media_scheduler

# After creating your Flask app and Supabase client
social_scheduler = create_social_media_scheduler(app, supabase_client)

if social_scheduler:
    social_scheduler.start()
    print("Social media scheduler started")
```

### 3. Manual Usage

```python
from social_media.scheduler import SocialMediaScheduler

# Initialize scheduler
scheduler = SocialMediaScheduler(app, supabase_client)

# Start scheduling
scheduler.start()

# Check status
status = scheduler.get_scheduler_status()
print(f"Scheduler running: {status['running']}")

# Stop scheduler
scheduler.stop()
```

## Job Schedule

The scheduler runs three main jobs:

1. **Content Generation** (6:00 AM SAST daily)
   - Generates content for the next 7 days
   - Creates AI-generated images
   - Saves posts to database with scheduled times

2. **Content Posting** (Every 30 minutes)
   - Checks for posts scheduled to be published
   - Posts to Facebook with images
   - Updates post status in database

3. **Analytics Collection** (11:00 PM SAST daily)
   - Fetches performance data from Facebook
   - Saves analytics to database
   - Tracks engagement metrics

## Configuration

The scheduler uses `config.yaml` for configuration:

- **Posting Schedule**: Different posting frequencies by week
- **Content Themes**: AI personality and content types
- **Image Generation**: Visual style and branding
- **Facebook Settings**: Hashtags and engagement strategy

## Error Handling

- Comprehensive logging for all operations
- Graceful handling of API failures
- Automatic retry logic for transient errors
- Error notifications for critical failures

## Railway Deployment

The scheduler is optimized for Railway's single dyno deployment:

- Uses in-memory job storage
- Handles app restarts gracefully
- Checks for missed jobs on startup
- Prevents duplicate posts during restarts

## Monitoring

Check scheduler status:

```python
status = scheduler.get_scheduler_status()
print(f"Jobs: {len(status['jobs'])}")
print(f"Current week: {status['current_week']}")
print(f"Timezone: {status['timezone']}")
```

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Ensure all required API keys are set
   - Check Supabase credentials

2. **Facebook API Errors**
   - Verify page access token is valid
   - Check page permissions

3. **Content Generation Failures**
   - Verify Anthropic API key
   - Check API rate limits

4. **Image Generation Issues**
   - Verify Replicate API token
   - Check image generation quotas

### Logs

All operations are logged with the `refiloe` logger. Check logs for detailed error information.

## Development

### Testing

```python
# Test scheduler creation
from social_media.scheduler import create_social_media_scheduler

scheduler = create_social_media_scheduler(app, supabase_client)
assert scheduler is not None
```

### Manual Job Execution

```python
# Run jobs manually for testing
scheduler.job_generate_content()
scheduler.job_post_content()
scheduler.job_collect_analytics()
```

## Architecture

```
SocialMediaScheduler
├── ContentGenerator (Claude API)
├── ImageGenerator (Replicate API)
├── FacebookPoster (Facebook Graph API)
├── SocialMediaDatabase (Supabase)
└── APScheduler (Background Jobs)
```

## Dependencies

- `APScheduler`: Job scheduling
- `anthropic`: AI content generation
- `replicate`: AI image generation
- `supabase`: Database operations
- `pytz`: Timezone handling
- `requests`: HTTP requests