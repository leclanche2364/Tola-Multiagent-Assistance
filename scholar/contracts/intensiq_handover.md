# IntenSIQ Handover Contract

## Existing IntenSIQ Capabilities (inspected, not invented)

The existing IntenSIQ codebase provides these routes:

### Read routes
- course/topic/content
- goals
- progress
- practice
- tests
- cases
- study materials
- recordings
- reasoning

### Three NEW integration additions

Scholar requires exactly three narrow integration additions to IntenSIQ:

### Read routes
- course/topic/content
- goals
- progress
- practice
- tests
- cases
- study materials
- recordings
- reasoning

### Scholar integration additions (3 new routes)

#### 1. Learner State Read Model

GET /api/v1/integration/learner-state?course_id=...

Response fields:
- schema_version
- state_version
- as_of
- course
- course_goals
- proficiency_context[]
- topics[]
  - progress
  - next_action
  - practice_units
  - recent_assessments
  - recent_study_activity
- reasoning_evidence[]
- competency_evidence[]
- revision_items[]
- cursor

Principle: learner-state = what is true now. Exposes evidence, not formal clinical sign-off unless that sign-off is authoritative.

#### 2. Versioned Learning Plan

GET /api/v1/integration/courses/:courseId/learning-plan
PUT /api/v1/integration/courses/:courseId/learning-plan

Minimum fields:
- plan_id
- goal_id
- course_id
- version
- expected_previous_version
- status
- objective
- target_date
- proficiency_refs[]
- ordered_learning_items[]
- weekly_minutes
- minimum_session_minutes
- review_policy
- mastery_targets
- rationale
- created_by = "scholar"
- updated_at

The plan defines what to study and how much. It must not contain calendar times.

#### 3. Durable Learning Events (pollable outbox)

GET /api/v1/integration/events?cursor=...

Minimum event types:
- study_session.recorded
- practice_unit.completed
- assessment.submitted
- reasoning_session.completed
- recording.transcription_completed
- course_goals.updated
- learning_plan.updated
- topic.progress_changed
- proficiency_context.updated

Minimum event fields:
- event_id
- event_type
- schema_version
- occurred_at
- course_id
- topic_id
- aggregate_id
- payload

Principle: events = what changed. Events are immutable and replayable. Cursor advances only after safe processing.