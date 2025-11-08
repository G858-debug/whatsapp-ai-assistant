#!/usr/bin/env python3
"""
Script to fetch and analyze the current WhatsApp Flow JSON from Meta Business Manager.
"""

import os
import sys
import json
import requests
from typing import Dict, Any


def fetch_flow_from_meta(flow_id: str, access_token: str) -> Dict[str, Any]:
    """
    Fetch flow data from Meta's Graph API.

    Args:
        flow_id: The WhatsApp Flow ID
        access_token: Meta access token

    Returns:
        Flow data as dictionary
    """
    url = f"https://graph.facebook.com/v17.0/{flow_id}"

    params = {
        "access_token": access_token,
        "fields": "id,name,status,categories,validation_errors,json_version,data_api_version,endpoint_uri,preview"
    }

    print(f"Fetching flow {flow_id} from Meta...")
    print(f"URL: {url}")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching flow: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        sys.exit(1)


def analyze_registration_complete_payload(flow_data: Dict[str, Any]) -> None:
    """
    Analyze the registration_complete screen's payload structure.

    Args:
        flow_data: The flow data from Meta
    """
    print("\n" + "=" * 80)
    print("ANALYZING REGISTRATION_COMPLETE SCREEN PAYLOAD")
    print("=" * 80)

    try:
        # Parse the preview.preview_url or the actual flow JSON
        flow_json = None

        # First, check if there's a 'preview' field with the flow structure
        if 'preview' in flow_data and 'preview' in flow_data['preview']:
            preview_data = flow_data['preview']['preview']
            if isinstance(preview_data, str):
                flow_json = json.loads(preview_data)
            else:
                flow_json = preview_data

        # If no preview, the flow data itself might contain the screens
        if not flow_json and 'screens' in flow_data:
            flow_json = flow_data

        if not flow_json:
            print("⚠️  Could not find flow JSON structure in the response")
            print("Available keys in response:", list(flow_data.keys()))
            return

        # Find registration_complete screen
        screens = flow_json.get('screens', [])
        registration_screen = None

        for screen in screens:
            if screen.get('id') == 'registration_complete':
                registration_screen = screen
                break

        if not registration_screen:
            print("❌ No 'registration_complete' screen found!")
            print(f"Available screens: {[s.get('id') for s in screens]}")
            return

        print("✅ Found 'registration_complete' screen")
        print()

        # Check for payload
        if 'on-complete' in registration_screen:
            on_complete = registration_screen['on-complete']
            print(f"on-complete type: {on_complete.get('type', 'N/A')}")

            if 'payload' in on_complete:
                payload = on_complete['payload']
                print("\n✅ PAYLOAD IS DEFINED")
                print()
                print("Fields in payload:")
                print("-" * 40)

                for key, value in payload.items():
                    print(f"  • {key}: {value}")

                print()
                print("Complete payload structure:")
                print("-" * 40)
                print(json.dumps(payload, indent=2))

                # Check for form field references
                print()
                print("Form field references:")
                print("-" * 40)
                form_refs = [v for v in payload.values() if isinstance(v, str) and '${form.' in v]
                if form_refs:
                    for ref in form_refs:
                        print(f"  ✓ {ref}")
                else:
                    print("  ⚠️  No form field references found (should be like ${form.field_name})")
            else:
                print("\n❌ NO PAYLOAD DEFINED in on-complete")
        else:
            print("❌ No 'on-complete' action found in registration_complete screen")
            print(f"Available keys in screen: {list(registration_screen.keys())}")

        print()
        print("Full registration_complete screen structure:")
        print("-" * 80)
        print(json.dumps(registration_screen, indent=2))

    except Exception as e:
        print(f"❌ Error analyzing payload: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function."""
    print("WhatsApp Flow JSON Checker")
    print("=" * 80)

    # Get environment variables
    access_token = os.getenv('ACCESS_TOKEN')
    flow_id = "775047838492907"

    if not access_token:
        print("❌ ERROR: ACCESS_TOKEN environment variable not set")
        print("Please set it with: export ACCESS_TOKEN='your_token'")
        sys.exit(1)

    print(f"Flow ID: {flow_id}")
    print(f"Access Token: {'*' * 20}{access_token[-10:]}")
    print()

    # Fetch flow data
    flow_data = fetch_flow_from_meta(flow_id, access_token)

    # Save to file
    output_file = "current_flow_from_meta.json"
    print(f"\n✅ Flow fetched successfully!")
    print(f"Saving to {output_file}...")

    with open(output_file, 'w') as f:
        json.dump(flow_data, indent=2, fp=f)

    print(f"✅ Saved to {output_file}")

    # Print basic info
    print()
    print("Flow Information:")
    print("-" * 40)
    print(f"Name: {flow_data.get('name', 'N/A')}")
    print(f"Status: {flow_data.get('status', 'N/A')}")
    print(f"Categories: {flow_data.get('categories', 'N/A')}")
    print(f"JSON Version: {flow_data.get('json_version', 'N/A')}")

    if 'validation_errors' in flow_data and flow_data['validation_errors']:
        print(f"⚠️  Validation Errors: {flow_data['validation_errors']}")

    # Analyze the registration_complete payload
    analyze_registration_complete_payload(flow_data)

    print()
    print("=" * 80)
    print("Analysis complete!")
    print(f"Full response saved to: {output_file}")


if __name__ == "__main__":
    main()
