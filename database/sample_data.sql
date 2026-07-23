INSERT INTO fitness_goal(name, description)
VALUES
('Weight Loss','Lose body fat'),
('Muscle Gain','Increase muscle mass'),
('Endurance','Improve stamina');
----------------------------------------------------
-- USER PROFILE
----------------------------------------------------

INSERT INTO user_profile(core_user_id, age, height, weight, fitness_level)
VALUES
(101,22,170,68,'Beginner'),
(102,24,180,82,'Intermediate'),
(103,21,165,57,'Advanced'),
(104,26,175,74,'Intermediate'),
(105,23,168,63,'Beginner');

----------------------------------------------------
-- USER GOAL
----------------------------------------------------

INSERT INTO user_goal(user_id, goal_id)
VALUES
(1,1),
(2,2),
(3,3),
(4,2),
(5,1);

----------------------------------------------------
-- WORKOUT PREFERENCE
----------------------------------------------------

INSERT INTO workout_preference
(user_id, workout_type, available_days, equipment, preferred_time)
VALUES
(1,'Cardio','["Mon","Wed","Fri"]','["Treadmill"]','09:00'),
(2,'Strength','["Tue","Thu"]','["Barbell","Dumbbell"]','18:00'),
(3,'Running','["Sat","Sun"]','[]','07:30'),
(4,'CrossFit','["Mon","Thu"]','["Kettlebell"]','17:00'),
(5,'Yoga','["Wed","Fri"]','["Mat"]','08:30');

----------------------------------------------------
-- TRAINING GROUP
----------------------------------------------------

INSERT INTO training_group
(name,description,workout_type,difficulty_level,
goal_id,available_days,equipment,max_members,
start_time,end_time)

VALUES

('Morning Cardio',
'Cardio Lovers',
'Cardio',
'Beginner',
1,
'["Mon","Wed","Fri"]',
'["Treadmill"]',
20,
'08:00',
'09:30'),

('Muscle Builders',
'Strength Training',
'Strength',
'Intermediate',
2,
'["Tue","Thu"]',
'["Barbell","Bench"]',
15,
'18:00',
'19:30'),

('Weekend Runners',
'Outdoor Running',
'Running',
'Advanced',
3,
'["Sat","Sun"]',
'[]',
30,
'07:00',
'08:30');

----------------------------------------------------
-- GROUP MEMBERSHIP
----------------------------------------------------

INSERT INTO group_membership(user_id,group_id,status)

VALUES

(1,1,'Active'),
(2,2,'Active'),
(3,3,'Active'),
(4,2,'Pending'),
(5,1,'Active');

----------------------------------------------------
-- EXERCISE
----------------------------------------------------

INSERT INTO exercise
(name,type,difficulty,risk_level)

VALUES

('Running','Cardio','Easy','Low'),
('Bench Press','Strength','Medium','Medium'),
('Squat','Strength','Hard','High'),
('Plank','Core','Easy','Low'),
('Burpees','HIIT','Hard','High');

----------------------------------------------------
-- GROUP EXERCISE
----------------------------------------------------

INSERT INTO group_exercise
(group_id,exercise_id,intensity)

VALUES

(1,1,'Medium'),
(2,2,'High'),
(2,3,'High'),
(3,1,'High'),
(1,4,'Low');

----------------------------------------------------
-- INJURY HISTORY
----------------------------------------------------

INSERT INTO injury_history
(user_id,injury_type,body_part,severity,injury_date,notes)

VALUES

(2,'Sprain','Ankle','Medium','2024-05-10','Recovered'),

(3,'Shoulder Pain','Shoulder','Low','2025-02-15','Under Observation');

----------------------------------------------------
-- RISK ANALYSIS
----------------------------------------------------

INSERT INTO risk_analysis
(user_id,group_id,risk_level,score,recommendation)

VALUES

(1,1,'Low',20,'Continue current program'),

(2,2,'Medium',55,'Reduce intensity'),

(3,3,'High',85,'Medical evaluation required');