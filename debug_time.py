from utils.validators import Validators

# Test the time validation
validator = Validators()

test_times = ["9am", "9 am", "9:00", "09:00", "9 AM"]

for time_str in test_times:
    result = validator.validate_time(time_str)
    print(f"Time: {time_str}")
    print(f"Result: {result}")
    
    # Also test the wrapper
    is_valid, error = validator.validate_time_format(time_str)
    print(f"Format result: is_valid={is_valid}, error={error}")
    print("---")
