# WhatsApp Flows Setup Guide

## Overview

This guide explains how to set up WhatsApp Flows for the trainer onboarding process in Refiloe. WhatsApp Flows provide a structured, form-like experience within WhatsApp for user registration.

## Current Status

✅ **Flow Message Format Fixed** - Updated to comply with WhatsApp Business API v17.0  
✅ **Fallback System Working** - Text-based registration works when Flows are unavailable  
⚠️ **Manual Setup Required** - Flow must be created in WhatsApp Business Manager  

## Why WhatsApp Flows Aren't Working

The main reasons why WhatsApp Flows aren't being sent:

### 1. **Flow Not Created in WhatsApp Business Manager**
- The Flow must be manually created and published in your WhatsApp Business Manager
- The Flow name must match exactly: `trainer_onboarding_flow`
- The Flow must be in "PUBLISHED" status to be sendable

### 2. **API Permissions**
- Your WhatsApp Business API account needs Flow message permissions
- Some accounts may not have access to Flows yet (it's a newer feature)

### 3. **Flow Message Format Issues** (FIXED)
- ✅ Added required fields: `recipient_type`, `messaging_product`
- ✅ Fixed action structure: `name` should be `"flow"`
- ✅ Added required parameters: `flow_message_version`, `flow_action`
- ✅ Corrected parameter names: `flow_id` → `flow_name`

## How to Enable WhatsApp Flows

### Step 1: Create Flow in WhatsApp Business Manager

1. **Log into WhatsApp Business Manager**
   - Go to [business.whatsapp.com](https://business.whatsapp.com)
   - Navigate to your business account

2. **Create New Flow**
   - Go to "Flows" section
   - Click "Create Flow"
   - Name it exactly: `trainer_onboarding_flow`
   - Category: "UTILITY"

3. **Design the Flow**
   - Use the Flow Builder to create the registration form
   - Or import the JSON from `whatsapp_flows/trainer_onboarding_flow.json`
   - Include all required fields: name, email, city, specialization, etc.

4. **Publish the Flow**
   - Test the Flow thoroughly
   - Click "Publish" when ready
   - Ensure status shows "PUBLISHED"

### Step 2: Verify API Permissions

1. **Check Your WhatsApp Business API Account**
   - Ensure you have Flow message permissions
   - Some accounts may need to request access to Flows

2. **Test Flow Availability**
   - The system will automatically detect if Flows are available
   - If not available, it falls back to text-based registration

### Step 3: Test the Integration

1. **Send Test Message**
   - Use a test phone number
   - Send message: "I'm a trainer"
   - Should receive Flow message if properly configured

2. **Check Logs**
   - Monitor Railway logs for Flow-related messages
   - Look for success/failure indicators

## Version Requirements

**Flow JSON Version:** `7.3` (required for WhatsApp Business Manager)  
**Message API Version:** `3.0` (for sending Flow messages)  
**Data API Version:** `3.0` (for Flow data handling)

## Current Flow Message Format

```json
{
  "recipient_type": "individual",
  "messaging_product": "whatsapp",
  "to": "phone_number",
  "type": "interactive",
  "interactive": {
    "type": "flow",
    "header": {
      "type": "text",
      "text": "🚀 Trainer Onboarding"
    },
    "body": {
      "text": "Welcome to Refiloe! Let's get you set up as a trainer. This will take about 2 minutes."
    },
    "footer": {
      "text": "Complete your profile setup"
    },
    "action": {
      "name": "flow",
      "parameters": {
        "flow_message_version": "3",
        "flow_token": "unique_token",
        "flow_name": "trainer_onboarding_flow",
        "flow_cta": "Start Setup",
        "flow_action": "navigate",
        "flow_action_payload": {
          "screen": "welcome",
          "data": {}
        }
      }
    }
  }
}
```

## Fallback System

If WhatsApp Flows are not available, the system automatically falls back to text-based registration:

1. **User says "I'm a trainer"**
2. **System tries to send Flow**
3. **If Flow fails → Falls back to text registration**
4. **User completes 7-step text-based registration**
5. **Same data collected, same end result**

## Troubleshooting

### Common Issues

1. **"Flow not available" message**
   - Flow not created in WhatsApp Business Manager
   - Flow not published
   - API permissions missing

2. **"Failed to send flow message"**
   - Check API token validity
   - Verify phone number format
   - Check API endpoint URL

3. **Flow message format errors**
   - Ensure all required fields are present
   - Verify parameter names match API spec
   - Check flow_message_version (should be "3")

### Debug Steps

1. **Check Railway Logs**
   ```bash
   railway logs --tail 50
   ```

2. **Look for Flow-related messages**
   - "Created flow message for..."
   - "Flow not available..."
   - "Failed to send onboarding flow..."

3. **Test with Different Phone Numbers**
   - Use verified test numbers
   - Check if issue is phone-specific

## Benefits of WhatsApp Flows

### For Users
- ✅ **Structured Experience** - Form-like interface
- ✅ **Better UX** - Guided step-by-step process
- ✅ **Validation** - Built-in field validation
- ✅ **Professional Look** - Polished appearance

### For Business
- ✅ **Higher Completion Rate** - Better user engagement
- ✅ **Consistent Data** - Structured data collection
- ✅ **Reduced Support** - Clear instructions
- ✅ **Analytics** - Better tracking of registration steps

## Alternative: Text-Based Registration

The current text-based registration works perfectly and provides the same functionality:

- ✅ **7-step guided process**
- ✅ **Same data collection**
- ✅ **Friendly conversational tone**
- ✅ **Works for all users**
- ✅ **No additional setup required**

## Next Steps

1. **Immediate**: Text-based registration is working perfectly
2. **Optional**: Set up WhatsApp Flows for enhanced UX
3. **Future**: Consider implementing Flow creation via API

The system is designed to work with or without Flows, ensuring all users can complete registration regardless of Flow availability.
