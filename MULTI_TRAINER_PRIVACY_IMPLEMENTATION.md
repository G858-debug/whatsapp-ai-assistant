# Multi-Trainer Profile Privacy Implementation

## Overview

This implementation ensures proper privacy boundaries when a client trains with multiple trainers simultaneously. Each trainer sees the client's shared profile but has completely isolated trainer-specific data.

## Privacy Architecture

### 1. Shared Client Profile (Visible to All Trainers)

The `clients` table contains data that **ALL trainers** can see:

- **Personal Info**: `name`, `email`, `whatsapp`, `age`, `gender`
- **Training Info**: `experience_level`, `fitness_goals`, `health_conditions`
- **Availability**: `availability`, `preferred_training_times`, `dietary_preferences`
- **Status**: `status`, `created_at`

**Why shared?** This information helps all trainers provide better service and is necessary for training planning.

### 2. Trainer-Specific Data (Privacy Isolated)

The `trainer_client_list` table contains data that **ONLY the specific trainer** can see:

- **Custom Pricing**: `custom_price_per_session` - Each trainer sets their own price
- **Private Notes**: `private_notes` - Personal observations about the client
- **Session Count**: `sessions_count` - Number of sessions with this specific trainer
- **Relationship Metadata**: `connection_status`, `created_at`, `approved_at`, `updated_at`

**Why isolated?** This prevents pricing competition and protects trainer's private observations.

## Database Schema Changes

### New Columns Added to `trainer_client_list`

```sql
ALTER TABLE trainer_client_list ADD COLUMN custom_price_per_session DECIMAL(10, 2);
ALTER TABLE trainer_client_list ADD COLUMN private_notes TEXT;
ALTER TABLE trainer_client_list ADD COLUMN sessions_count INTEGER DEFAULT 0;
ALTER TABLE trainer_client_list ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
```

### Row Level Security (RLS) Policies

**Policy 1: Trainers See Only Their Own Relationships**
```sql
CREATE POLICY "trainers_see_own_relationships" ON trainer_client_list
FOR SELECT USING (auth.uid()::text = trainer_id);
```

**Policy 2: Clients See Their Own Relationships**
```sql
CREATE POLICY "clients_see_own_relationships" ON trainer_client_list
FOR SELECT USING (auth.uid()::text = client_id);
```

**Policy 3: Trainers Update Only Their Own Data**
```sql
CREATE POLICY "trainers_update_own_relationships" ON trainer_client_list
FOR UPDATE USING (auth.uid()::text = trainer_id);
```

## Implementation Details

### Services

#### 1. ProfilePrivacyService (`services/relationships/profile_privacy_service.py`)

**Core Methods:**

```python
# Shared profile access (all trainers)
get_shared_client_profile(client_id, trainer_id) -> Dict

# Trainer-specific data (isolated)
get_trainer_specific_data(trainer_id, client_id) -> Dict
set_trainer_custom_pricing(trainer_id, client_id, price) -> Tuple[bool, str]
get_trainer_pricing_for_client(trainer_id, client_id) -> float
set_private_notes(trainer_id, client_id, notes) -> Tuple[bool, str]
get_private_notes(trainer_id, client_id) -> str

# Session history (filtered by trainer)
get_trainer_client_sessions(trainer_id, client_id, limit) -> List[Dict]

# Client multi-trainer view
get_client_multi_trainer_view(client_id) -> Dict
```

#### 2. RelationshipService Integration

The main `RelationshipService` now includes all ProfilePrivacyService methods:

```python
from services.relationships import RelationshipService

rel_service = RelationshipService(supabase_client)

# Get shared profile
profile = rel_service.get_shared_client_profile(client_id, trainer_id)

# Get trainer-specific pricing
price = rel_service.get_trainer_pricing_for_client(trainer_id, client_id)

# Set private notes
success, msg = rel_service.set_private_notes(trainer_id, client_id, "Client prefers morning sessions")
```

#### 3. DashboardService Updates

The `DashboardService` now uses privacy-aware data retrieval:

**For Trainers:**
```python
# Trainer sees:
# - Shared client profile (goals, health, etc.)
# - Their own custom pricing
# - Their own private notes
# - Their own session count

dashboard_service.get_relationships(trainer_id, role='trainer', status='active')
```

**For Clients:**
```python
# Client sees:
# - All their trainers
# - Each trainer's pricing (for them)
# - Session count with each trainer
# - Last session date with each trainer
# - NO private notes from trainers

dashboard_service.get_relationships(client_id, role='client', status='active')
```

## Privacy Guarantees

### ✅ What Trainers CAN See

1. **Shared Client Profile:**
   - Name, email, phone
   - Fitness goals and experience level
   - Health conditions and injuries
   - Availability and preferences

2. **Their Own Data:**
   - Custom pricing they set
   - Private notes they wrote
   - Session history with this client
   - Session count with this client

### ❌ What Trainers CANNOT See

1. **Other Trainer's Data:**
   - Custom pricing set by other trainers
   - Private notes written by other trainers
   - Session history with other trainers
   - Session count with other trainers

### ✅ What Clients CAN See

1. **All Their Trainers:**
   - List of all trainers they work with
   - Each trainer's profile information
   - Custom pricing each trainer charges them
   - Session count with each trainer
   - Last session date with each trainer

2. **Their Own Profile:**
   - All shared profile data
   - All relationships and status

### ❌ What Clients CANNOT See

1. **Trainer's Private Notes:**
   - Cannot see notes trainers write about them
   - This protects trainer's observations and planning

## Usage Examples

### Example 1: Trainer Views Client Profile

```python
from services.relationships import RelationshipService

rel_service = RelationshipService(supabase_client)

# Trainer views shared profile
profile = rel_service.get_shared_client_profile('CLIENT001', 'TRAINER001')
print(f"Client: {profile['name']}")
print(f"Goals: {profile['fitness_goals']}")
print(f"Health: {profile['health_conditions']}")

# Trainer gets their own specific data
specific = rel_service.get_trainer_specific_data('TRAINER001', 'CLIENT001')
print(f"My pricing: R{specific['custom_price_per_session']}")
print(f"My notes: {specific['private_notes']}")
print(f"Sessions: {specific['sessions_count']}")
```

### Example 2: Trainer Sets Custom Pricing

```python
# Trainer 1 sets their pricing
success, msg = rel_service.set_trainer_custom_pricing(
    'TRAINER001',
    'CLIENT001',
    500.00  # R500 per session
)
print(msg)  # "Custom pricing set to R500"

# Trainer 2 sets different pricing for same client
success, msg = rel_service.set_trainer_custom_pricing(
    'TRAINER002',
    'CLIENT001',
    450.00  # R450 per session
)
print(msg)  # "Custom pricing set to R450"

# Neither trainer can see the other's pricing
price1 = rel_service.get_trainer_pricing_for_client('TRAINER001', 'CLIENT001')
# Returns 500.00 (only their own)

price2 = rel_service.get_trainer_pricing_for_client('TRAINER002', 'CLIENT001')
# Returns 450.00 (only their own)
```

### Example 3: Trainer Adds Private Notes

```python
# Trainer 1 adds notes
rel_service.set_private_notes(
    'TRAINER001',
    'CLIENT001',
    "Client has knee injury. Focus on low-impact exercises."
)

# Trainer 2 adds different notes
rel_service.set_private_notes(
    'TRAINER002',
    'CLIENT001',
    "Client needs encouragement on diet adherence."
)

# Each trainer only sees their own notes
notes1 = rel_service.get_private_notes('TRAINER001', 'CLIENT001')
# Returns: "Client has knee injury..."

notes2 = rel_service.get_private_notes('TRAINER002', 'CLIENT001')
# Returns: "Client needs encouragement..."
```

### Example 4: Client Views All Trainers

```python
# Client views their multi-trainer dashboard
view = rel_service.get_client_multi_trainer_view('CLIENT001')

print(f"Total trainers: {view['total_trainers']}")

for trainer in view['trainers']:
    print(f"\nTrainer: {trainer['trainer_name']}")
    print(f"Pricing: R{trainer['custom_pricing']}")
    print(f"Sessions: {trainer['session_count']}")
    print(f"Last session: {trainer['last_session']}")
    # Note: private_notes are NOT included for clients
```

### Example 5: Session History (Filtered by Trainer)

```python
# Trainer 1 views their sessions with client
sessions1 = rel_service.get_trainer_client_sessions('TRAINER001', 'CLIENT001')
print(f"Trainer 1 sessions: {len(sessions1)}")
# Returns only sessions between Trainer 1 and Client

# Trainer 2 views their sessions with same client
sessions2 = rel_service.get_trainer_client_sessions('TRAINER002', 'CLIENT001')
print(f"Trainer 2 sessions: {len(sessions2)}")
# Returns only sessions between Trainer 2 and Client

# Lists are completely separate and different
```

## Testing

### Running Privacy Tests

```bash
# Run all privacy tests
python -m pytest tests/test_profile_privacy.py -v

# Run specific test
python -m pytest tests/test_profile_privacy.py::TestProfilePrivacy::test_pricing_privacy_boundary -v
```

### Test Coverage

The test suite covers:

1. ✅ Shared profile access (authorized vs unauthorized)
2. ✅ Trainer-specific data isolation
3. ✅ Pricing privacy boundaries
4. ✅ Private notes isolation
5. ✅ Session history filtering
6. ✅ Client multi-trainer view
7. ✅ Unauthorized access blocking
8. ✅ End-to-end multi-trainer scenario

## Migration Guide

### Step 1: Run Database Migration

```bash
# Apply the SQL migration
psql -d your_database -f database/migrations/add_privacy_columns_to_trainer_client_list.sql
```

### Step 2: Update Existing Code

**Before:**
```python
# Old way (no privacy)
client = db.table('clients').select('*').eq('client_id', client_id).execute()
pricing = client.data[0].get('custom_price_per_session')
```

**After:**
```python
# New way (privacy-aware)
profile = rel_service.get_shared_client_profile(client_id, trainer_id)
pricing = rel_service.get_trainer_pricing_for_client(trainer_id, client_id)
```

### Step 3: Migrate Existing Pricing Data (Optional)

If you have existing `custom_price_per_session` data in the `clients` table:

```sql
-- Migrate to trainer_client_list
UPDATE trainer_client_list tcl
SET custom_price_per_session = c.custom_price_per_session
FROM clients c
WHERE tcl.client_id = c.client_id
  AND c.custom_price_per_session IS NOT NULL
  AND tcl.custom_price_per_session IS NULL;
```

## Security Considerations

### 1. Row Level Security (RLS)

- **ALWAYS ENABLED** on `trainer_client_list`
- Policies enforce trainer-client boundaries at database level
- Even if application code has bugs, database prevents unauthorized access

### 2. Service Role Access

- Service role has full access (for admin operations)
- Regular users (trainers/clients) are restricted by RLS policies

### 3. Authorization Checks

All methods verify relationship exists before allowing access:

```python
def _verify_trainer_client_relationship(self, trainer_id: str, client_id: str) -> bool:
    """Verify active relationship exists"""
    result = self.db.table('trainer_client_list').select('id').eq(
        'trainer_id', trainer_id
    ).eq('client_id', client_id).eq(
        'connection_status', 'active'
    ).execute()
    return bool(result.data)
```

### 4. Logging

All privacy-sensitive operations are logged:
- ✅ Successful access logged with INFO
- ❌ Unauthorized access attempts logged with WARNING
- 🐛 Errors logged with ERROR

## Future Enhancements

### Planned Features

1. **Audit Trail**: Track all pricing and note changes
2. **Data Export**: Allow trainers to export their client data
3. **Bulk Operations**: Update pricing for multiple clients
4. **Analytics**: Trainer-specific reports on client progress

### API Endpoints (Future)

```
GET    /api/trainers/{trainer_id}/clients/{client_id}/profile
GET    /api/trainers/{trainer_id}/clients/{client_id}/pricing
PUT    /api/trainers/{trainer_id}/clients/{client_id}/pricing
GET    /api/trainers/{trainer_id}/clients/{client_id}/notes
PUT    /api/trainers/{trainer_id}/clients/{client_id}/notes
GET    /api/trainers/{trainer_id}/clients/{client_id}/sessions
GET    /api/clients/{client_id}/trainers
```

## Support

For questions or issues:

1. Check test suite: `tests/test_profile_privacy.py`
2. Review implementation: `services/relationships/profile_privacy_service.py`
3. Check database migration: `database/migrations/add_privacy_columns_to_trainer_client_list.sql`

## Summary

This implementation provides **robust privacy boundaries** for multi-trainer scenarios:

- ✅ Shared profile data (all trainers see)
- ✅ Isolated trainer-specific data (only owner sees)
- ✅ Database-level security (RLS policies)
- ✅ Application-level checks (authorization)
- ✅ Comprehensive test coverage
- ✅ Easy-to-use API

**Critical Privacy Guarantee**: One trainer can NEVER see another trainer's pricing or private notes for the same client.
