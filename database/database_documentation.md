# Database Documentation

## PolyLife - Microservice 9

---

# 1. UserProfile

**Purpose**

Stores users' physical profile information received from the Core Authentication service.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| core_user_id | INTEGER | User ID received from Core (Unique) |
| age | INTEGER | User age |
| height | FLOAT | Height (cm) |
| weight | FLOAT | Weight (kg) |
| fitness_level | VARCHAR(20) | User fitness level |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |

---

# 2. FitnessGoal

**Purpose**

Stores predefined fitness goals.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| name | VARCHAR(100) | Goal name |
| description | TEXT | Goal description |
| created_at | TIMESTAMP | Creation time |

---

# 3. UserGoal

**Purpose**

Maps users to their fitness goals.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| user_id | INTEGER | Foreign Key → UserProfile(id) |
| goal_id | INTEGER | Foreign Key → FitnessGoal(id) |

**Constraint**

- UNIQUE(user_id, goal_id)

---

# 4. WorkoutPreference

**Purpose**

Stores each user's workout preferences. Each user has exactly one preference record (One-to-One relationship with UserProfile).

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| user_id | INTEGER | Unique Foreign Key → UserProfile(id) |
| workout_type | VARCHAR(100) | Preferred workout type |
| available_days | JSONB | Available workout days (e.g. `["Mon","Wed","Fri"]`) |
| equipment | JSONB | Available equipment (e.g. `["Dumbbell","Resistance Band"]`) |
| preferred_start_time | TIME | Preferred workout start time |
| preferred_end_time | TIME | Preferred workout end time |

**Constraints**

- user_id is UNIQUE (One-to-One relationship)
- user_id references UserProfile(id)
- available_days is stored as JSONB
- equipment is stored as JSONB
- preferred_end_time should be later than preferred_start_time

---

# 5. TrainingGroup

**Purpose**

Stores training groups available for users.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| name | VARCHAR(100) | Group name |
| description | TEXT | Group description |
| workout_type | VARCHAR(100) | Workout category |
| difficulty_level | VARCHAR(30) | Difficulty level |
| goal_id | INTEGER | Foreign Key → FitnessGoal(id) |
| available_days | JSONB | Training days |
| equipment | JSONB | Required equipment |
| max_members | INTEGER | Maximum number of members |
| start_time | TIME | Group start time |
| end_time | TIME | Group end time |
| created_at | TIMESTAMP | Creation time |

**Constraints**

- CHECK(max_members > 0)
- CHECK(end_time > start_time)

---

# 6. GroupMembership

**Purpose**

Stores user memberships in training groups.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| user_id | INTEGER | Foreign Key → UserProfile(id) |
| group_id | INTEGER | Foreign Key → TrainingGroup(id) |
| joined_at | TIMESTAMP | Join date |
| status | VARCHAR(20) | Membership status |

**Default**

- Active

**Constraint**

- UNIQUE(user_id, group_id)

---

# 7. Exercise

**Purpose**

Stores exercises used in training groups.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| name | VARCHAR(100) | Exercise name |
| type | VARCHAR(50) | Exercise category |
| difficulty | VARCHAR(30) | Difficulty level |
| risk_level | VARCHAR(30) | Injury risk level |

---

# 8. GroupExercise

**Purpose**

Maps exercises to training groups.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| group_id | INTEGER | Foreign Key → TrainingGroup(id) |
| exercise_id | INTEGER | Foreign Key → Exercise(id) |
| intensity | VARCHAR(30) | Exercise intensity |

**Constraint**

- UNIQUE(group_id, exercise_id)

---

# 9. InjuryHistory

**Purpose**

Stores users' previous injury history.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| user_id | INTEGER | Foreign Key → UserProfile(id) |
| injury_type | VARCHAR(100) | Type of injury |
| body_part | VARCHAR(100) | Injured body part |
| severity | VARCHAR(30) | Injury severity |
| injury_date | DATE | Date of injury |
| notes | TEXT | Additional notes |

---

# 10. RiskAnalysis

**Purpose**

Stores injury risk analysis results for users.

| Field | Type | Description |
|------|------|-------------|
| id | SERIAL | Primary Key |
| user_id | INTEGER | Foreign Key → UserProfile(id) |
| group_id | INTEGER | Foreign Key → TrainingGroup(id) |
| risk_level | VARCHAR(30) | Calculated risk level |
| score | INTEGER | Risk score |
| recommendation | TEXT | Suggested recommendation |
| created_at | TIMESTAMP | Analysis date |

---

# Relationships

- UserProfile (1) ←→ (1) WorkoutPreference
- UserProfile (1) ←→ (N) UserGoal
- FitnessGoal (1) ←→ (N) UserGoal
- FitnessGoal (1) ←→ (N) TrainingGroup
- UserProfile (1) ←→ (N) GroupMembership
- TrainingGroup (1) ←→ (N) GroupMembership
- TrainingGroup (1) ←→ (N) GroupExercise
- Exercise (1) ←→ (N) GroupExercise
- UserProfile (1) ←→ (N) InjuryHistory
- UserProfile (1) ←→ (N) RiskAnalysis
- TrainingGroup (1) ←→ (N) RiskAnalysis

---

# Constraints Summary

- Primary Key defined for all tables.
- Foreign Keys enforce referential integrity.
- WorkoutPreference.user_id is UNIQUE (One-to-One).
- UserGoal(user_id, goal_id) is UNIQUE.
- GroupMembership(user_id, group_id) is UNIQUE.
- GroupExercise(group_id, exercise_id) is UNIQUE.
- TrainingGroup.max_members must be greater than zero.
- TrainingGroup.end_time must be later than start_time.
- Default membership status is Active.