# Phase 3 세션 스크립트 — 고도화

**추천 설정**: Claude Sonnet (iteration 속도) · Analytics + Code Generator skills · Code Sandbox + Ontology Query + Function Executor tools · Phase 2 설계 + M4 finding

**목표**: Ontology 구성 이후 **Functions / AIP Agent / Workshop 앱** 설계. 코드 생성 + 자동화 중심.
**전제**: Phase 2 완료, Ontology가 UI에서 등록됨 (`docs/plan/ontology-design-final.md` 기준)

---

## Prompt 1 — 상태 확인 & Phase 3 scope 설정

```
Ontology registration is complete. The state:

[PASTE the registered Object Types / Link Types / Interfaces from Phase 2 output]

Now Phase 3 focuses on:
- Functions (serverless compute)
- AIP Agent (domain-specific AI assistant)
- Workshop app (interactive UI)
- Quiver analytics (dashboards)

What's the right order given my team of 1 (me) and ~3 days of work?

Prioritize by:
- Portfolio demonstration value (I'm using this for job applications)
- Technical depth showcase
- Time to first demo
- Reusability

Propose a Phase 3 day-by-day plan.
```

**기대**: 구체적인 3일 실행 계획. Portfolio 관점에서 우선순위 조정.

---

## Prompt 2 — Function 설계 (what-if 시뮬레이션)

```
Design a Foundry Function called `calculatePipelineIsolation`.

Purpose: Given a pipeline_id and an optional valve_to_exclude, return the set of objects that would be isolated.

Input:
- pipeline_id: string (e.g., "P-10147")
- valve_to_exclude: object_id[] (optional)

Output:
- isolated_objects: BimPiping[]
- isolation_section_count: int
- affected_equipment: BimEquipment[]

Implementation language: TypeScript (Foundry standard)

Constraints:
- Must use the Ontology SDK (not raw SQL)
- Must complete in <5 seconds for typical input
- Should be idempotent (pure function, no side effects)

Please write:
1. Full TypeScript implementation
2. Input/output JSON schema
3. 3 test cases (realistic pipeline IDs)
4. How to register this in Foundry UI

Reference: We already have 33 KPIs in Python at src/bimkg/analytics/kpi.py — port logic but adapt to Ontology SDK.
```

**기대**: 실행 가능한 TypeScript 코드 + 등록 가이드. 실제 코드 리뷰 후 UI에서 붙여넣기.

---

## Prompt 3 — AIP Agent 설계 (상세)

```
Design an AIP Agent called "BIM Inspector" for plant maintenance staff.

Target users: Refining plant operators, maintenance planners, safety auditors.

User scenarios (must support):

1. "Show me all valves on pipeline P-10147" → Object Set + 3D viewer
2. "What happens if I remove valve V-234?" → isolation impact + visual
3. "Which zones have highest corrosion risk this quarter?" → heatmap
4. "Find equipment near the main compressor that needs inspection" → spatial query
5. "Generate a maintenance shutdown plan for Unit 12" → Gantt-like output

For the Agent, design:

1. **System prompt** (full text, Korean + English mixed acceptable)
2. **Tool list**:
   - Ontology queries (which Object Types to expose)
   - Functions (which to attach — from Prompt 2 and others)
   - Media Set access (for 3D previews)
3. **Response format guidelines** (when to show table, when to show 3D, when to show chart)
4. **Few-shot examples** (3 turns of conversation)
5. **Fallback behavior** (when query is ambiguous)
6. **Permission boundaries** (what agent should NEVER do)

Output as YAML I can paste into AIP Agent Studio configuration.
```

**기대**: 완성된 agent 스펙. UI에 그대로 입력 가능.

---

## Prompt 4 — Workshop 앱 설계

```
Design a Workshop module called "BIM Explorer".

Target audience: Non-technical plant engineers (no SQL knowledge).

Layout (3-pane):
- LEFT: Filter panel (class, pipeline, zone, status)
- CENTER: 3D Viewer (Ontology Media Reference auto-renders)
- RIGHT: Object details + linked objects + KPIs

Required widgets:
1. Object Set Filter (by Object Type, property range)
2. 3D Viewer (linked to filtered Object Set)
3. Object Detail Card (properties, 5 most relevant KPIs)
4. Related Objects List (via bim_adjacent_to, grouped by class)
5. KPI Cards (for selected object or zone)
6. Action Buttons (TagForInspection, etc. — from Phase 2 Actions)

For each widget, specify:
- Data source (Ontology Object Set / Query / Function)
- Binding to other widgets (user clicks object → detail updates)
- Loading state / empty state / error state
- Styling hints (color coding for class, alert highlight for high risk)

Output format: Markdown with a mockup-style description I can follow in Workshop UI.
```

**기대**: UI 구성도. Workshop에서 그대로 조립 가능.

---

## Prompt 5 — Quiver 대시보드 설계

```
Design a Quiver analysis called "Plant Knowledge Graph Insights".

This is for executives / stakeholders to see value from the BIM-KG.

Required charts (5–8 total):

1. **Coverage donut**: mesh_quality distribution (full_mesh / box_placeholder / fbx_supplemented / skipped_container)
2. **Class distribution**: 6 Object Types count
3. **Adjacency network density**: histogram of degree per object
4. **Pipeline complexity ranking**: top 10 pipelines by object count or span
5. **Zone heatmap**: 144 zones × mean corrosion_risk
6. **Critical path gantt**: construction order from precedence DAG
7. **M4 validation**: FBX mapping 788/788 coverage
8. **KPI scorecard**: plant-level 8 KPIs (total weight, critical chain, etc.)

For each chart:
- Chart type (donut / bar / histogram / heatmap / scatter / gantt)
- X/Y axes or grouping
- Data source (Ontology Aggregate / Function call)
- Filters that should apply
- Color scheme (use project palette: #3182F6 primary blue, #00C471 green, etc.)

Output as Quiver-compatible JSON or markdown spec.
```

**기대**: 8개 차트 스펙 + 색상/팔레트. Quiver UI에서 구축 가능.

---

## Prompt 6 — 포트폴리오 스토리 구성

```
I'm using this project for job applications (data engineer / ontology engineer roles).

Help me structure a **3-minute demo script** for the final deliverable.

Available artifacts:
- Foundry project with 11 datasets + Ontology + Media Set
- "BIM Inspector" AIP Agent
- "BIM Explorer" Workshop module
- Quiver dashboard
- (Optional) OSDK React app

Structure the demo:
- Opening hook (30 sec): "I processed 12,009 BIM objects from a refining plant..."
- Problem framing (30 sec)
- Live demo sequence (90 sec): 3 concrete user journeys
- Technical depth reveal (30 sec): M4 finding, custom FBX parser, Foundry integration

For each segment:
- What to show on screen
- What to say
- What technical details to emphasize
- What NOT to mention (too technical for 3 min)

Include alternative scripts for:
- 30-second elevator pitch (hallway conversation)
- 10-minute deep dive (technical interview)
```

**기대**: 3가지 길이의 demo script. 포트폴리오에 붙이거나 면접 준비에 활용.

---

## Prompt 7 — 최종 체크리스트

```
Produce a single "Phase 3 closeout checklist" I can work through:

- [ ] Functions: N deployed, M tested
- [ ] Agent: configured and validated with 5 test queries
- [ ] Workshop: published and shared with link
- [ ] Quiver: 8 charts built and filterable
- [ ] Demo script: rehearsed and timed
- [ ] Documentation: all Phase 3 outputs archived

For each item, include:
- Success criteria (how I know it's done)
- Common failure modes (what typically goes wrong)
- Estimated time to complete

Also propose 2–3 "nice-to-haves" I could add if I have extra time, and 2–3 things I could defer indefinitely without hurting the portfolio.
```

**기대**: 실행 추적 체크리스트 + 시간 관리 가이드.

---

## 🎯 세션 종료 후 체크리스트

- [ ] Function 코드 작성되고 UI에 등록됨
- [ ] AIP Agent 설정 완료, 5개 테스트 쿼리 통과
- [ ] Workshop 앱 publish됨
- [ ] Quiver 대시보드 live 링크 확보
- [ ] 3-분 demo script 연습 완료
- [ ] 모든 산출물을 `docs/analysis/ai-fde-sessions/` 에 아카이브

---

## 🔄 AI FDE 가 헤맬 때 대응

### 증상 1: "Foundry Function SDK API를 모름"
→ TypeScript example을 직접 제공:
```typescript
import { OntologyObject } from '@foundry/functions-api';
// ...
```

### 증상 2: Agent system prompt가 너무 장황
→ "Keep under 500 words. Prioritize behavior over background."

### 증상 3: Quiver 차트 스펙이 추상적
→ "Give me exact JSON config, not a description."

### 증상 4: 코드 품질이 낮음
→ "Treat this as production code. Include error handling, type hints, JSDoc."
