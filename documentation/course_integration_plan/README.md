# Course Integration Feature - Complete Plan

**Status:** ✅ Planning Complete | ⏳ Implementation Pending
**Last Updated:** 2025-12-23
**Scope:** Full-stack feature (backend + frontend)
**Total Timeline:** ~10-12 days
**Files Affected:** ~25-30

---

## 🎯 What This Plan Covers

This comprehensive plan enables students to organize study sessions into courses. Instead of having scattered sessions, users can create courses (like "Biology 101") and add related sessions within them.

### Key Value
- **Organization:** Group related study sessions by subject/topic
- **Navigation:** Breadcrumb context (Biology > Photosynthesis)
- **Progress:** Track completion across sessions in a course
- **UX:** Clear hierarchy and user education

### Design Principle
**Non-breaking:** Course integration is 100% backward compatible. Existing standalone sessions work unchanged.

---

## ✅ Planning Status

**ALL DECISIONS MADE** - Plan is finalized and ready for implementation
- ✅ 9 critical decisions resolved (see [CRITICAL_DECISIONS_NEEDED.md](CRITICAL_DECISIONS_NEEDED.md))
- ✅ Simplified for LLMOps focus (no authentication, simple approaches)
- ✅ All 16 ambiguities addressed (see [AMBIGUITIES_AND_CLARIFICATIONS.md](AMBIGUITIES_AND_CLARIFICATIONS.md))
- ✅ 4 backend phases documented with acceptance criteria
- ✅ 2 frontend phases documented with user journeys

---

## 📚 Documentation Structure

### Decision & Planning Documents
| Document | Purpose | Status |
|----------|---------|--------|
| **[CRITICAL_DECISIONS_NEEDED.md](CRITICAL_DECISIONS_NEEDED.md)** | All 9 decisions with resolutions | ✅ RESOLVED |
| **[AMBIGUITIES_AND_CLARIFICATIONS.md](AMBIGUITIES_AND_CLARIFICATIONS.md)** | Original ambiguities (now resolved) | ✅ RESOLVED |

### Core Planning Documents
| Document | Purpose | Audience |
|----------|---------|----------|
| **[overview.md](overview.md)** | Architecture & design decisions | Architects, Reviewers |
| **[change_log.md](change_log.md)** | Progress tracking & timeline | Project Managers |
| **[frontend_integration_overview.md](frontend_integration_overview.md)** | User flows, UX/UI, onboarding | Designers, Frontend Devs |

### Backend Implementation
| Document | Purpose | Audience |
|----------|---------|----------|
| **[phase1_database_layer.md](phase1_database_layer.md)** | ORM models, CRUD | Backend Devs |
| **[phase2_service_layer.md](phase2_service_layer.md)** | Business logic, services | Backend Devs |
| **[phase3_api_layer.md](phase3_api_layer.md)** | REST endpoints, routers | Backend Devs |
| **[phase4_integration.md](phase4_integration.md)** | Backward compatibility | Backend Devs |

### Frontend Implementation
| Document | Purpose | Audience |
|----------|---------|----------|
| **[frontend_phase1_components.md](frontend_phase1_components.md)** | Components, services, hooks | Frontend Devs |
| **[frontend_phase2_integration.md](frontend_phase2_integration.md)** | Page/session integration | Frontend Devs |

---

## 🏗️ Architecture Overview

### Data Model
```
┌────────────────────────────────────────────────┐
│ Courses (NEW)                                  │
├────────────────────────────────────────────────┤
│ id: UUID PK                                    │
│ name: String (255 chars)                       │
│ description: Text (nullable)                   │
│ metadata: JSON                                 │
│ created_at, updated_at: DateTime               │
└────────────────────────────────────────────────┘
                      │
                      │ One-to-Many FK
                      │ (ON DELETE SET NULL)
                      ▼
┌────────────────────────────────────────────────┐
│ Sessions (MODIFIED)                            │
├────────────────────────────────────────────────┤
│ id: UUID PK (existing)                         │
│ course_id: UUID FK (NEW, nullable)             │
│ ... existing fields ...                        │
└────────────────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    Documents    Chat History   Images
    (FK)         (session_id)    (FK)
```

### Backend Layers
```
REST API Layer (api/)
  ├─ courses_router.py (NEW)
  ├─ sessions_router.py (MODIFIED)
  └─ deps.py (add CourseService injection)

Service Layer (application/services/)
  ├─ course_service.py (NEW)
  └─ session_service.py (MODIFIED)

Domain Layer (core/)
  └─ (No changes - uses services)

Boundary Layer (boundary/db/)
  ├─ models/course_model.py (NEW)
  ├─ models/session_model.py (MODIFIED)
  └─ CRUD/course_crud.py (NEW)
```

### Frontend Architecture
```
Pages (pages/)
  ├─ CoursesPage.tsx (NEW)
  ├─ CourseDetailPage.tsx (NEW)
  ├─ SessionPage.tsx (MODIFIED - breadcrumb)
  └─ Index.tsx (MODIFIED - course section)

Components (components/courses/ NEW)
  ├─ CourseCard.tsx
  ├─ CreateCourseModal.tsx
  ├─ CourseBreadcrumb.tsx
  └─ CourseProgressBar.tsx

Services (services/)
  ├─ courses.service.ts (NEW)
  └─ sessions.service.ts (MODIFIED)

Hooks (hooks/)
  ├─ useCourses.ts (NEW)
  ├─ useCourseDetail.ts (NEW)
  └─ useSession.ts (MODIFIED)
```

---

## 🔄 Complete Data Flow: User Creates Course & Session

### Flow Diagram
```
FRONTEND: User clicks "Create Course"
  │
  ├─→ CreateCourseModal opens
  │   └─→ Form: name, description
  │
  ├─→ User submits
  │
  ├─→ useCourses.createCourse()
  │   │
  │   └─→ coursesService.createCourse()
  │       │
  │       └─→ HTTP POST /api/v1/courses
  │           │
  │           ▼
  │
BACKEND: POST /api/v1/courses
  │
  ├─→ courses_router.create_course()
  │   │
  │   ├─→ Validate request (Pydantic)
  │   │
  │   ├─→ CourseService.create_course()
  │   │   │
  │   │   └─→ course_crud.create()
  │   │       └─→ INSERT INTO courses...
  │   │
  │   └─→ Return CourseResponse (201)
  │
  └─→ FRONTEND: Response received
      │
      ├─→ useCourses state updated
      │
      ├─→ Navigate to /courses/{courseId}
      │
      └─→ CourseDetailPage loads
          │
          └─→ Show "No sessions yet"
              "Create First Session" button
```

### Flow: Create Session in Course
```
FRONTEND: CourseDetailPage → "Create Session" button
  │
  ├─→ CreateSessionDialog opens (with courseId prop)
  │   └─→ Form: session name, description
  │       └─→ Show: "Creating in: Biology 101"
  │
  ├─→ User submits
  │
  ├─→ useCourseDetail.createSessionInCourse()
  │   │
  │   └─→ coursesService.createCourseSession()
  │       │
  │       └─→ HTTP POST /api/v1/courses/{courseId}/sessions
  │           │
  │           ▼
  │
BACKEND: POST /api/v1/courses/{courseId}/sessions
  │
  ├─→ courses_router.create_session_in_course()
  │   │
  │   ├─→ Validate courseId exists
  │   │
  │   ├─→ SessionService.create_session(
  │   │       metadata,
  │   │       course_id={courseId}
  │   │   )
  │   │   │
  │   │   └─→ session_crud.create() with course_id FK
  │   │       └─→ INSERT INTO sessions
  │   │           (id, course_id, ...)
  │   │
  │   └─→ Return SessionResponse (201)
  │       └─→ Includes: course_id=xyz
  │
  └─→ FRONTEND: Response received
      │
      ├─→ useCourseDetail state updated
      │
      ├─→ Session added to course's sessions array
      │
      ├─→ Navigate /session/{sessionId}
      │
      └─→ SessionPage loads
          │
          └─→ CourseBreadcrumb shows:
              Home > Biology > Photosynthesis
```

### Flow: Query Sessions by Course
```
FRONTEND: CourseDetailPage mounts
  │
  ├─→ useCourseDetail(courseId) hook
  │   │
  │   └─→ Parallel API calls:
  │       ├─→ coursesService.getCourse(courseId)
  │       │   └─→ GET /api/v1/courses/{courseId}
  │       │
  │       └─→ coursesService.getCourseSessions(courseId)
  │           └─→ GET /api/v1/courses/{courseId}/sessions
  │
  │           ▼
  │
BACKEND: GET /api/v1/courses/{courseId}
  │
  ├─→ courses_router.get_course()
  │   └─→ course_crud.get_by_id(courseId)
  │       └─→ SELECT * FROM courses WHERE id=courseId
  │
  └─→ Return CourseResponse

BACKEND: GET /api/v1/courses/{courseId}/sessions
  │
  ├─→ courses_router.get_course_sessions()
  │   └─→ course_crud.get_by_course_id(courseId)
  │       └─→ session_crud.get_by_course_id()
  │           └─→ SELECT * FROM sessions
  │               WHERE course_id=courseId
  │               ORDER BY created_at DESC
  │
  └─→ Return [SessionResponse, ...]

FRONTEND: Both responses received
  │
  ├─→ useCourseDetail state updated
  │
  ├─→ CourseDetailPage renders:
  │   ├─→ Course header with name/description
  │   ├─→ Progress bar (e.g., 3/5 sessions)
  │   └─→ SessionCard grid with sessions
  │
  └─→ User can click session to continue studying
```

---

## 🎯 User Journeys

### Journey 1: First-Time User (Onboarding)
```
Land on home (/)
  ↓
See hero + "Your Sessions" section
  ↓
Empty state: "Ready to start learning?"
  ↓
See two CTAs:
  [Create a Course]  [Create a Standalone Session]
  ↓
Click "Create a Course"
  ↓
Dialog: "Courses let you group related sessions"
  (Brief explanation + example)
  ↓
Form: Course name (required) + description (optional)
  ↓
Submit → Create "Biology 101"
  ↓
Redirect to /courses/{courseId}
  ↓
Empty course: "No sessions yet"
  ↓
Click "Create First Session"
  ↓
Session created with course_id
  ↓
Redirect to /session/{sessionId}
  ↓
Breadcrumb: Home > Biology 101 > Photosynthesis
  ↓
Upload document + chat
```

### Journey 2: Experienced User (Course + Multi-Session)
```
Click "Courses" in nav → /courses
  ↓
See grid: Biology (3/5), Chemistry (1/3), Physics (2/4)
  ↓
Click "Biology"
  ↓
→ /courses/{biologyId}
  ↓
See sessions:
  [Photosynthesis ✓] [Evolution ✓] [Genetics ⏳]
  ↓
Click "Evolution"
  ↓
→ /session/{sessionId}
  ↓
Breadcrumb allows navigation:
  Biology 101 > Evolution ✓

  Next: Gene Expression >
  ↓
Can click "Gene Expression" to jump to next session
```

### Journey 3: Backward Compatible (Standalone Sessions)
```
User who doesn't want courses
  ↓
Click "Create a Standalone Session" (on home)
  ↓
Session created with course_id=NULL
  ↓
Session appears in:
  - Index.tsx "Standalone Sessions" section
  - /session/{sessionId} (no breadcrumb/course)
  ↓
Search, upload, chat as before
  ↓
No impact from course feature
```

---

## ✅ Phased Delivery Timeline

### Backend: 2 weeks
- **Week 1:**
  - Day 1: Database models + CRUD
  - Day 2: Services + business logic
  - Day 3: API endpoints
  - Day 4: Integration + backward compat
  - Day 5: Tests

### Frontend: 2 weeks
- **Week 2:**
  - Day 6: Core components (CoursesPage, CourseCard, etc.)
  - Day 7: Services + hooks
  - Day 8: CourseDetailPage + session integration
  - Day 9: Breadcrumbs + progress tracking
  - Day 10: Polish + testing

### Deployment Ready: End of Week 2

---

## 🔐 Backward Compatibility Guarantee

**Nothing Breaks:**
```
✅ Existing sessions work unchanged
✅ course_id is optional (default NULL)
✅ All existing endpoints accept same parameters
✅ New endpoints are additions, not modifications
✅ No data migration required
✅ No schema breaking changes
```

**Verification:**
- Create session without course_id → works
- Query sessions → includes course_id field (null)
- Upload documents → works on any session (course or standalone)
- Chat → works on any session (course or standalone)
- Visual knowledge → works on any session (course or standalone)

---

## 🧪 Testing Strategy

### Backend
- **Unit:** CRUD, service logic (mock DB)
- **Integration:** Real DB, relationship constraints
- **API:** Full request/response cycles
- **Backward Compat:** Old code paths still work

### Frontend
- **Component:** CourseCard, CreateCourseModal (React Testing Library)
- **Hook:** useCourses, useCourseDetail (mock API)
- **Integration:** Full user flows (e2e tests)
- **Responsive:** Mobile, tablet, desktop

---

## 📋 Pre-Implementation Checklist

**Planning Phase:** ✅ COMPLETE

Before starting implementation:
- [x] All 7 documentation files reviewed and finalized
- [x] Backend architecture confirmed (ORM, service pattern)
- [x] Frontend patterns defined (hooks, components, pages)
- [x] API structure confirmed (7 endpoints)
- [x] All 9 critical decisions MADE (see CRITICAL_DECISIONS_NEEDED.md)
- [x] Plan simplified for LLMOps (no auth, simple approaches)
- [x] All 16 ambiguities RESOLVED

**Implementation Phase - Ready When You Are:**
- [ ] Setup local environment (Python 3.11+, Node 18+)
- [ ] Database credentials ready
- [ ] Create feature branch: `feature/course-integration`
- [ ] Begin Backend Phase 1 (Database Layer)

---

## 🚀 Ready for Implementation

**Plan Status: ✅ COMPLETE AND SIMPLIFIED**

All decisions have been made with a focus on LLMOps simplicity (no authentication, straightforward approaches).

### For Backend Developers

**Start Here:** [Backend Phase 1: Database Layer](phase1_database_layer.md)

Follow phases in order:
1. **Phase 1:** Create CourseModel + CourseCRUD (~2-3 hours)
2. **Phase 2:** Build CourseService with business logic (~1.5-2 hours)
3. **Phase 3:** Create REST endpoints with dependency injection (~2-3 hours)
4. **Phase 4:** Integrate with existing system, verify backward compatibility (~2 hours)

**Key Guidelines:**
- All code should be async
- Include type hints and docstrings
- Use structured logging
- Follow patterns from SessionService/SessionCRUD
- No authentication needed (shared courses for all users)

### For Frontend Developers

**Start Here:** [Frontend Integration Overview](frontend_integration_overview.md) then [Phase 1: Components & Services](frontend_phase1_components.md)

Follow phases in order:
1. **Phase 1:** Create CourseCard, CreateCourseModal, CoursesPage (~3-4 hours)
2. **Phase 2:** Build CourseDetailPage, breadcrumbs, session integration (~3-4 hours)

**Key Guidelines:**
- Use React hooks + SWR for data fetching
- No Redux or Context API needed (simple approach)
- Follow existing SessionCard patterns
- Use TailwindCSS and Framer Motion for UI

### For Project Managers

1. All planning is complete - no more ambiguities
2. Track progress using **[change_log.md](change_log.md)**
3. Check acceptance criteria for each phase
4. Estimated timeline: ~10-12 days (4-5 backend + 4-5 frontend)
5. Risk: Very low (100% backward compatible, no breaking changes)

---

## 📞 Common Questions

**Q: Will existing sessions break?**
A: No. course_id is optional. All existing code works unchanged.

**Q: Do I have to use courses?**
A: No. Users can still create standalone sessions without courses.

**Q: How do I move a session between courses?**
A: Phase 5 future enhancement. Current plan: create new session in target course.

**Q: Can sessions belong to multiple courses?**
A: No. One course → many sessions. Sessions don't share courses.

**Q: What happens if I delete a course?**
A: Sessions survive (course_id becomes NULL). Data is preserved.

---

## 🎓 Key Learning Points

### Architecture Pattern: Separate Entity
- CourseModel is independent
- Sessions reference courses (FK)
- Loose coupling: course deletion doesn't cascade

### Clean Code: SOLID Principles
- **SRP:** Each layer has single responsibility
- **OCP:** Open to extension (new course endpoints), closed to modification
- **DIP:** Depend on interfaces (service abstractions)

### Type Safety: End-to-End
- Pydantic schemas validate requests
- SQLAlchemy ORM for type-safe DB ops
- TypeScript frontend with strict types

### Async Throughout
- FastAPI async handlers
- SQLAlchemy async ORM
- React hooks with async operations

---

## 📄 Summary Statistics

| Metric | Value |
|--------|-------|
| Total Files | ~25-30 |
| Backend Files | ~12-15 |
| Frontend Files | ~12-15 |
| New API Endpoints | 7 |
| New Database Tables | 1 (courses) |
| Modified Tables | 1 (sessions - add course_id) |
| Total Timeline | 10-12 days |
| Breaking Changes | 0 (100% backward compatible) |
| Test Coverage Target | 85%+ |

---

## 🔗 Quick Links

**Backend**
- [Database Layer](phase1_database_layer.md)
- [Service Layer](phase2_service_layer.md)
- [API Layer](phase3_api_layer.md)
- [Integration](phase4_integration.md)

**Frontend**
- [UX/UI Overview](frontend_integration_overview.md)
- [Components & Services](frontend_phase1_components.md)
- [Session Integration](frontend_phase2_integration.md)

**Tracking**
- [Change Log](change_log.md)

---

**Last Updated:** 2025-12-23
**Status:** ✅ Planning COMPLETE | ✅ All Decisions MADE | ✅ Plan SIMPLIFIED | 🚀 Ready for Implementation

## 📌 Key Achievements

✅ **9 Critical Decisions Made** - All ambiguities resolved with LLMOps-first approach
✅ **Simplified Implementation** - No authentication, simple approaches throughout
✅ **100% Backward Compatible** - Existing sessions and code paths unchanged
✅ **Phase-Based Roadmap** - Clear 4-phase backend + 2-phase frontend plan
✅ **Acceptance Criteria** - Each phase has defined success metrics
✅ **Pattern References** - All implementations reference existing code patterns
✅ **Low Risk** - No breaking changes, straightforward architecture

## 🎯 Next Step

**You're ready to start implementation whenever you choose.**

1. Backend team: Start with [Phase 1: Database Layer](phase1_database_layer.md)
2. Frontend team: Start with [Frontend Overview](frontend_integration_overview.md)
3. Both teams coordinate using [change_log.md](change_log.md)

No more planning needed - time to build! 🚀

