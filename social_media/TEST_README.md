# Social Media System Test Suite

This directory contains comprehensive tests for the social media automation system.

## Quick Start

### Option 1: Using the Test Runner (Recommended)
```bash
python run_social_media_tests.py
```

### Option 2: Direct Test Execution
```bash
python social_media/test_system.py
```

## Required Environment Variables

### Required for Basic Testing
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Your Supabase anonymous key
- `ANTHROPIC_API_KEY` - Your Anthropic Claude API key
- `REPLICATE_API_TOKEN` - Your Replicate API token

### Optional for Full Testing
- `FACEBOOK_PAGE_ACCESS_TOKEN` - Facebook page access token
- `FACEBOOK_PAGE_ID` - Facebook page ID

## Test Functions

### 1. `test_config()`
- Tests config.yaml loading
- Validates required configuration sections
- Checks AI influencer settings

### 2. `test_database()`
- Tests Supabase database connection
- Verifies table accessibility
- Validates database service initialization

### 3. `test_content_generation()`
- Generates 3 test posts using different themes
- Validates post structure and content
- Tests AI content generation pipeline

### 4. `test_image_generation()`
- Generates 1 test image using Replicate API
- Tests image upload to Supabase Storage
- Validates image metadata storage

### 5. `test_facebook_api()`
- Tests Facebook API connection
- Validates page access token
- Retrieves page information (no posting)

### 6. `test_full_workflow()`
- Complete end-to-end test
- Generates post → generates image → saves to database
- Simulates publication (no actual Facebook posting)
- Verifies data integrity

## Test Output

The test suite provides clear, color-coded output:

```
🧪 Testing Social Media System
================================

✅ Config loaded successfully
✅ Database connection OK
✅ Generated 3 test posts
✅ Generated test image
✅ Facebook API token valid
✅ Full workflow completed

================================
All tests passed! 🎉
```

## Test Data Cleanup

The test suite automatically cleans up test data after running:
- Deletes test posts from database
- Removes test images from storage
- Ensures no test data remains in production

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Set all required environment variables
   - Use the test runner to check your setup

2. **Database Connection Issues**
   - Verify Supabase credentials
   - Check network connectivity
   - Ensure database tables exist

3. **API Key Issues**
   - Verify Anthropic API key is valid
   - Check Replicate API token
   - Ensure sufficient API credits

4. **Facebook API Issues**
   - Verify page access token is valid
   - Check page permissions
   - Ensure token hasn't expired

### Debug Mode

For detailed logging, set the log level:
```bash
export LOG_LEVEL=DEBUG
python social_media/test_system.py
```

## Integration with CI/CD

The test suite is designed to work with continuous integration:

```yaml
# Example GitHub Actions step
- name: Test Social Media System
  run: python social_media/test_system.py
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    REPLICATE_API_TOKEN: ${{ secrets.REPLICATE_API_TOKEN }}
```

## Safety Features

- **No Real Posting**: Tests never post to actual Facebook
- **Test Data Isolation**: Uses test trainer IDs and data
- **Automatic Cleanup**: Removes all test data after completion
- **Error Handling**: Graceful failure with detailed error messages
- **Environment Validation**: Checks all required variables before running

## Development

To add new tests:

1. Add test function to `SocialMediaSystemTester` class
2. Follow naming convention: `test_<component_name>()`
3. Return dictionary with `success`, `details`, and `error` keys
4. Add test to `run_all_tests()` function
5. Update this README

## Support

For issues or questions about the test suite, check the main project documentation or contact the development team.