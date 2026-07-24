# Team 6 API Contracts

Version: 1.0  
Status: Final

## Base URL

```text
http://localhost:9106/api
```

اطلاعات کاربر توسط Gateway از طریق Headerهای زیر ارسال میشود:

```text
X-User-Id
X-User-Username
```

Backend تیم 6 جدول User جداگانه ندارد و JWT را پردازش نمیکند.

---

## Standard Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {}
}
```

## Standard Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Readable error message",
    "details": {}
  }
}
```

---

## Final Endpoints

### Health

```http
GET /api/health
```

### Fitness Profile

```http
GET    /api/profile
POST   /api/profile
PATCH  /api/profile
DELETE /api/profile
```

### Training Groups

```http
GET /api/groups
GET /api/groups/{group_id}
GET /api/groups/{group_id}/members
```

### Group Recommendation

```http
POST /api/groups/recommend
```

### Injury Risk Analysis

```http
POST /api/risk-analysis
```

### Alternative Groups

```http
GET /api/groups/{group_id}/alternatives
```

### Memberships

```http
GET    /api/memberships
POST   /api/memberships
GET    /api/memberships/{membership_id}
DELETE /api/memberships/{membership_id}
```

---

## Initial Error Codes

```text
AUTH_HEADERS_MISSING
VALIDATION_ERROR
PROFILE_NOT_FOUND
PROFILE_ALREADY_EXISTS
PROFILE_INCOMPLETE
GOAL_NOT_FOUND
GROUP_NOT_FOUND
GROUP_FULL
HIGH_RISK_GROUP
NO_SAFE_ALTERNATIVE_FOUND
ALREADY_MEMBER
MEMBERSHIP_NOT_FOUND
INTERNAL_SERVER_ERROR

```
---

# Group Recommendation

## Endpoint

```http
POST /api/groups/recommend
```

این API بر اساس هدف ورزشی، سطح آمادگی، نوع تمرین، زمان مورد نظر، تجهیزات و محدودیت های جسمانی کاربر، گروه های مناسب را پیشنهاد میکند.

## Headers

```text
X-User-Id: 15
X-User-Username: murteza
Content-Type: application/json
```

## Request

```json
{
  "goal_id": 1,
  "fitness_level": "beginner",
  "workout_type": "running",
  "available_days": [
    "saturday",
    "monday"
  ],
  "preferred_start_time": "16:00",
  "preferred_end_time": "18:00",
  "equipment": [
    "exercise_mat"
  ],
  "physical_limitations": [
    {
      "body_part": "knee",
      "severity": "mild"
    }
  ]
}
```

## فیلدهای اجباری

```text
goal_id
fitness_level
workout_type
available_days
preferred_start_time
preferred_end_time
```

## فیلدهای اختیاری

```text
equipment
physical_limitations
```

در صورت نداشتن تجهیزات یا محدودیت جسمانی:

```json
{
  "equipment": [],
  "physical_limitations": []
}
```

## Response موفق

HTTP Status:

```text
200 OK
```

```json
{
  "success": true,
  "message": "Recommended groups retrieved successfully",
  "data": {
    "groups": [
      {
        "id": 7,
        "name": "Beginner Running Group",
        "description": "Running exercises suitable for beginners",
        "goal": {
          "id": 1,
          "name": "Weight Loss"
        },
        "workout_type": "running",
        "difficulty_level": "easy",
        "available_days": [
          "saturday",
          "monday"
        ],
        "start_time": "16:00",
        "end_time": "18:00",
        "equipment": [
          "exercise_mat"
        ],
        "member_count": 8,
        "max_members": 15,
        "match_score": 90,
        "risk": {
          "score": 20,
          "level": "low",
          "recommendation": "This group is suitable for the user."
        }
      }
    ]
  }
}
```

## نحوه محاسبه Match Score

```text
Goal: 30%
Fitness level: 25%
Available time: 20%
Workout type: 15%
Equipment: 10%
```

## پیدا نشدن گروه مناسب

پیدا نشدن گروه مناسب خطای Backend محسوب نمیشود.

HTTP Status:

```text
200 OK
```

```json
{
  "success": true,
  "message": "No matching training groups were found",
  "data": {
    "groups": []
  }
}
```

## خطای اطلاعات ناقص یا نامعتبر

HTTP Status:

```text
400 Bad Request
```

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Some required fields are missing or invalid.",
    "details": {
      "goal_id": [
        "This field is required."
      ]
    }
  }
}
```

## پیدا نشدن هدف ورزشی

HTTP Status:

```text
404 Not Found
```

```json
{
  "success": false,
  "error": {
    "code": "GOAL_NOT_FOUND",
    "message": "Fitness goal was not found.",
    "details": {}
  }
}
```

## نبودن Header های کاربر

HTTP Status:

```text
401 Unauthorized
```

```json
{
  "success": false,
  "error": {
    "code": "AUTH_HEADERS_MISSING",
    "message": "User authentication headers are missing.",
    "details": {}
  }
}
```
---

# Group Details

## Endpoint

```http
GET /api/groups/{group_id}
```

مثال:

```http
GET /api/groups/7
```

این API اطلاعات کامل یک گروه تمرینی را برمیگرداند. اطلاعات ریسک بر اساس پروفایل و سابقه آسیب کاربر فعلی محاسبه میشود.

## Headers

```text
X-User-Id: 15
X-User-Username: murteza
```

## Response موفق

HTTP Status:

```text
200 OK
```

```json
{
  "success": true,
  "message": "Group details retrieved successfully",
  "data": {
    "group": {
      "id": 7,
      "name": "Beginner Running Group",
      "description": "Running exercises suitable for beginners",
      "goal": {
        "id": 1,
        "name": "Weight Loss"
      },
      "workout_type": "running",
      "difficulty_level": "easy",
      "available_days": [
        "saturday",
        "monday"
      ],
      "start_time": "16:00",
      "end_time": "18:00",
      "equipment": [
        "exercise_mat"
      ],
      "member_count": 8,
      "max_members": 15,
      "is_full": false,
      "exercises": [
        {
          "id": 4,
          "name": "Light Running",
          "type": "running",
          "difficulty": "easy",
          "intensity": "medium",
          "risk_level": "low"
        }
      ],
      "risk": {
        "score": 20,
        "level": "low",
        "recommendation": "This group is suitable for the user."
      }
    }
  }
}
```

## پیدا نشدن گروه

HTTP Status:

```text
404 Not Found
```

```json
{
  "success": false,
  "error": {
    "code": "GROUP_NOT_FOUND",
    "message": "Training group was not found.",
    "details": {}
  }
}
```

## نبودن Header های کاربر

HTTP Status:

```text
401 Unauthorized
```

```json
{
  "success": false,
  "error": {
    "code": "AUTH_HEADERS_MISSING",
    "message": "User authentication headers are missing.",
    "details": {}
  }
}
```
---

# Injury Risk Analysis

## Endpoint

```http
POST /api/risk-analysis
```

این API میزان خطر یک گروه تمرینی را برای کاربر فعلی بررسی میکند. Backend اطلاعات زیر را خودش از دیتابیس دریافت میکند:

```text
UserProfile
InjuryHistory
TrainingGroup
GroupExercise
Exercise
```

## Headers

```text
X-User-Id: 15
X-User-Username: murteza
Content-Type: application/json
```

## Request

```json
{
  "group_id": 7
}
```

## پاسخ ریسک پایین

HTTP Status:

```text
200 OK
```

```json
{
  "success": true,
  "message": "Injury risk analysis completed successfully",
  "data": {
    "analysis": {
      "group_id": 7,
      "score": 20,
      "level": "low",
      "is_safe": true,
      "reasons": [],
      "recommendation": "This group is suitable for the user."
    }
  }
}
```

## پاسخ ریسک متوسط

```json
{
  "success": true,
  "message": "Injury risk analysis completed successfully",
  "data": {
    "analysis": {
      "group_id": 7,
      "score": 55,
      "level": "medium",
      "is_safe": true,
      "reasons": [
        {
          "body_part": "knee",
          "exercise": "Running",
          "message": "This exercise may place pressure on the user's knee."
        }
      ],
      "recommendation": "The user should exercise with reduced intensity."
    }
  }
}
```

## پاسخ ریسک بالا

خود عملیات تحلیل موفق است، بنابراین HTTP Status همچنان `200` است؛ اما `is_safe` برابر `false` میشود:

```json
{
  "success": true,
  "message": "High injury risk detected",
  "data": {
    "analysis": {
      "group_id": 7,
      "score": 85,
      "level": "high",
      "is_safe": false,
      "reasons": [
        {
          "body_part": "knee",
          "exercise": "High Intensity Running",
          "message": "The exercise conflicts with a severe knee injury."
        }
      ],
      "recommendation": "Joining this group is not recommended."
    }
  }
}
```

## پروفایل پیدا نشد

HTTP Status:

```text
404 Not Found
```

```json
{
  "success": false,
  "error": {
    "code": "PROFILE_NOT_FOUND",
    "message": "Fitness profile was not found.",
    "details": {}
  }
}
```

## گروه پیدا نشد

HTTP Status:

```text
404 Not Found
```

```json
{
  "success": false,
  "error": {
    "code": "GROUP_NOT_FOUND",
    "message": "Training group was not found.",
    "details": {}
  }
}
```

## Request نامعتبر

HTTP Status:

```text
400 Bad Request
```

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request data is invalid.",
    "details": {
      "group_id": [
        "This field is required."
      ]
    }
  }
}
```
---

# Final Frontend Options

## fitness_level

```text
beginner
intermediate
advanced
```

## goal

```text
Weight Loss
Muscle Gain
Endurance
Flexibility
General Fitness
```

Frontend بهتر است شناسه هدف را از Backend دریافت کرده و در Request مقدار `goal_id` را ارسال کند.

## workout_type

```text
gym
running
swimming
cycling
yoga
hiit
crossfit
home_workout
```

## difficulty_level

```text
easy
medium
hard
```

## risk_level

```text
low
medium
high
```

## severity

```text
mild
moderate
severe
```

## membership_status

```text
pending
active
left
rejected
```