CREATE TABLE user_profile (
    id SERIAL PRIMARY KEY,
    core_user_id INTEGER UNIQUE NOT NULL,
    age INTEGER NOT NULL,
    height FLOAT NOT NULL,
    weight FLOAT NOT NULL,
    fitness_level VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fitness_goal (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_goal (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    goal_id INTEGER NOT NULL,

    CONSTRAINT uq_user_goal UNIQUE(user_id, goal_id),

    FOREIGN KEY (user_id)
        REFERENCES user_profile(id)
        ON DELETE CASCADE,

    FOREIGN KEY (goal_id)
        REFERENCES fitness_goal(id)
        ON DELETE CASCADE
);

CREATE TABLE workout_preference (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,

    workout_type VARCHAR(100),
    available_days JSONB,
    equipment JSONB,
    preferred_time TIME,

    FOREIGN KEY (user_id)
        REFERENCES user_profile(id)
        ON DELETE CASCADE
);

CREATE TABLE training_group (
    id SERIAL PRIMARY KEY,

    name VARCHAR(100) NOT NULL,
    description TEXT,

    workout_type VARCHAR(100),
    difficulty_level VARCHAR(30),

    goal_id INTEGER NOT NULL,

    available_days JSONB,
    equipment JSONB,

    max_members INTEGER NOT NULL CHECK(max_members > 0),

    start_time TIME,
    end_time TIME,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (goal_id)
        REFERENCES fitness_goal(id)
        ON DELETE RESTRICT,

    CHECK(end_time > start_time)
);

CREATE TABLE group_membership (
    id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,

    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(20) DEFAULT 'Active',

    CONSTRAINT uq_group_member UNIQUE(user_id, group_id),

    FOREIGN KEY (user_id)
        REFERENCES user_profile(id)
        ON DELETE CASCADE,

    FOREIGN KEY (group_id)
        REFERENCES training_group(id)
        ON DELETE CASCADE
);

CREATE TABLE exercise (
    id SERIAL PRIMARY KEY,

    name VARCHAR(100) NOT NULL,
    type VARCHAR(50),
    difficulty VARCHAR(30),
    risk_level VARCHAR(30)
);

CREATE TABLE group_exercise (
    id SERIAL PRIMARY KEY,

    group_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,

    intensity VARCHAR(30),

    CONSTRAINT uq_group_exercise UNIQUE(group_id, exercise_id),

    FOREIGN KEY (group_id)
        REFERENCES training_group(id)
        ON DELETE CASCADE,

    FOREIGN KEY (exercise_id)
        REFERENCES exercise(id)
        ON DELETE CASCADE
);

CREATE TABLE injury_history (
    id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL,

    injury_type VARCHAR(100),
    body_part VARCHAR(100),
    severity VARCHAR(30),
    injury_date DATE,
    notes TEXT,

    FOREIGN KEY (user_id)
        REFERENCES user_profile(id)
        ON DELETE CASCADE
);

CREATE TABLE risk_analysis (
    id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,

    risk_level VARCHAR(30),
    score INTEGER,
    recommendation TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES user_profile(id)
        ON DELETE CASCADE,

    FOREIGN KEY (group_id)
        REFERENCES training_group(id)
        ON DELETE CASCADE
);