# Foundry Next-Steps Roadmap

**작성일**: 2026-04-15
**현재 상태**: Phase 7 (Foundry integration) 진행 중 — Object/Link/Media 업로드 완료
**목표**: 10 Dataset + 1 Media Set을 조합해 **작동하는 BIM Knowledge Graph 플랫폼**으로 전개

---

## 1. Current Asset Inventory

### Foundry 에 올라간 것 (2026-04-15 기준)

| 자산 | 수량 | 경로 |
|---|---|---|
| Object Type Datasets | 6 (12,009 objects) | `/Datayoon-09825c/BIM-KG/bim_{class}` |
| Link Type Datasets | 4 (137,116 rows) | `/Datayoon-09825c/BIM-KG/bim_{link}` |
| Media Set | 1 (8,219 GLBs, 327 MB) | `/Datayoon-09825c/BIM-KG/bim_mesh` |

### 로컬 에 있는 것 (업로드 가능)

| 자산 | 수량 | 우선도 |
|---|---|---|
| Gold layer (bim_objects_enriched) | 12,009 × 219 cols | 낮음 (분할본으로 대체) |
| Symmetric adjacency | 220,346 edges | 낮음 (bim_adjacent_to로 대체) |
| OWL/TTL (477K triples) | 5 files | 중간 (SPARQL 재구현용) |
| Neo4j CSV export | 12 files | 낮음 (중복) |
| 33 KPIs 계산 결과 | 4 levels | **높음** (Ontology Property로 통합 가치) |
| Connected groups 메타 | 3,355 rows | 중간 |
| 144 Louvain zones | 할당 + 메타 | **높음** (analytics 관점 중심 뷰) |

---

## 2. 로드맵 5갈래

각 방향은 독립적으로 진행 가능하지만, **A (Ontology 구성)는 B–E 의 전제**.

```
               ┌─────────────────────────────────────┐
               │  A. Ontology 구성 (Object + Link)    │  ← 1–2시간, UI 중심
               │     └─ mesh_uri → Media Reference    │
               └──────────────┬──────────────────────┘
                              │
         ┌────────────┬───────┼────────┬──────────┐
         ▼            ▼       ▼        ▼          ▼
   ┌──────────┐  ┌──────┐  ┌────────┐  ┌─────┐  ┌────────┐
   │ B. OSDK  │  │ C.    │  │ D.     │  │ E.   │  │ F.      │
   │ + React  │  │ Work- │  │ AIP    │  │ Quiv-│  │ AIP     │
   │ 3D view  │  │ shop  │  │ Agent  │  │ er   │  │ Logic   │
   │          │  │ app   │  │ (Phase5│  │ dash │  │ func-   │
   │          │  │       │  │ + 통합 │  │ board│  │ tions   │
   └──────────┘  └──────┘  └────────┘  └─────┘  └────────┘
```

---

## 3. 방향 A — Ontology 구성 (Phase 7a)

### 목표
Foundry Ontology Manager 에서 **6 Object Type + 4 Link Type** 을 등록하고
`mesh_uri` 를 Media Reference property 로 연결.

### 산출물
- 6 Object Type 정의 (`BimPiping`, `BimStructural`, ...)
- 4 Link Type 정의 (`bim_adjacent_to`, `bim_has_parent`, `bim_belongs_to_pipeline`, `bim_in_group`)
- `mesh_uri` property 가 3D preview 지원
- Primary key = `object_id`

### 단계
1. Foundry UI → Ontology Manager 로 이동
2. "Create Object Type" → `bim_piping` dataset 선택
3. Primary key: `object_id`
4. Display column: `display_name`
5. **`mesh_uri` property 의 data type 을 "Media Reference" 로 변경**
   - Source: `bim_mesh` Media Set
   - Path template: `${mesh_uri_column_value}` (이미 `mesh/{object_id}.glb` 형식)
6. 나머지 5 Object Type 반복
7. Link Type 4개 등록 (source/target Object Type 지정)
8. 각 Link 의 basis column 설정 (`source_object_id` / `target_object_id`)

### 소요 시간
**1–2 시간** (UI 클릭 작업 위주)

### 검증
- Ontology Object 페이지에서 1 객체 클릭 → 3D preview 렌더링 확인
- Relationship 탭에서 인접 객체 자동 로드 확인

---

## 4. 방향 B — OSDK + React 3D Viewer (Phase 7b)

### 목표
OSDK TypeScript 패키지를 발급받아 Next.js 앱에서 **클릭-가능한 플랜트 3D viewer** 구축.

### 핵심 기능
- 12,009 객체를 bbox 기반 placeholder 로 렌더링 (초기 로드 최적화)
- 카메라가 가까워지면 해당 영역의 GLB 를 Media Set API 로 lazy load
- 객체 클릭 → Ontology 쿼리로 인접 객체 + KPI 표시
- 사이드패널: Object properties (219 cols) 중 핵심 15개만 표시
- 파이프라인 필터 (`P-10147`, `P-015` 등)

### 기술 스택
```
Next.js 14 (App Router)
├── @osdk/client (Foundry 자동 생성)
├── @react-three/fiber
├── @react-three/drei (OrbitControls, Html overlay)
├── react-query (데이터 캐싱)
└── Tailwind + shadcn/ui
```

### 단계
1. Foundry CLI 로 OSDK 패키지 발급 (`foundry typescript sdk generate`)
2. Next.js 프로젝트 scaffolding
3. Ontology 객체 목록 페이지 (virtualized list)
4. `<ThreeViewer>` 컴포넌트 — GLB loader + Ontology-query hook
5. Media Set REST API 인증 래퍼 (token 관리)
6. Adjacency highlight 인터랙션
7. Deploy (Vercel 또는 Foundry hosted app)

### 소요 시간
**2–3 일** (MVP)

### 포트폴리오 가치
- **가장 임팩트 큰** 결과물 (영상 시연 가능)
- 기술적 깊이: OSDK + Ontology + Three.js + Media Set 통합
- "현업 BIM viewer 수준" 으로 보일 수 있음

---

## 5. 방향 C — Workshop App (Phase 7c)

### 목표
Foundry Workshop 으로 **non-developer 탐색 도구** 제작 (코드 없이).

### UI 구성
- 좌측: Object class 필터 + pipeline dropdown
- 중앙: 3D Viewer widget (Ontology Media Reference 자동)
- 우측: 선택 객체의 properties + linked objects
- 하단: KPI dashboard (zone-level heatmap)

### 단계
1. Foundry UI → Workshop → Create module
2. Object Set filter widget 배치
3. 3D Viewer widget + Object selector 바인딩
4. Side-panel template 작성
5. Publish (팀 공유)

### 소요 시간
**반나절** (UI 빌드)

### 포트폴리오 가치
- **비개발자도 쓰는 완성품** 보여주기 용이
- 스크린 녹화 쉬움

---

## 6. 방향 D — AIP Agent Integration (Phase 7d)

### 목표
기존 Phase 5 의 Gemini LangGraph agent 를 **Foundry AIP Agent Studio** 로 re-deploy.
5 retrieval tools (SQL/FTS/SPARQL/Cypher/KPI) 를 Ontology 쿼리로 대체.

### 아키텍처
```
User query (자연어)
    ↓
AIP Agent (GPT-4 or Claude via Foundry)
    ↓
Ontology tool (자동 생성) — Object Type 조회
    ↓
Function tool (custom) — KPI 계산, Cypher 쿼리
    ↓
3D Media reference — 시각적 응답
```

### 단계
1. AIP Agent Studio 에서 agent 생성
2. Ontology Object Types 을 tool 로 attach
3. Phase 5 의 5 tools 를 Foundry Function 으로 재구현 (or 일부만)
4. System prompt 작성 (BIM 도메인 지식 + few-shot examples)
5. AIP Threads 로 테스트

### 소요 시간
**1–2 일**

### 포트폴리오 가치
- "로컬 agent 를 enterprise platform 에 이식" 스토리
- Foundry 고유 기능(AIP) 활용 사례

---

## 7. 방향 E — Quiver Analytics Dashboard (Phase 7e)

### 목표
**33 KPIs + 144 Louvain zones** 를 Quiver 대화형 차트로 전개.
M4 finding (pipeline fragmentation) 같은 구조 분석을 live dashboard 로.

### 예시 대시보드
- **Adjacency tier 분포**: Strong/Medium/All 의 edge 개수 시각화
- **Pipeline criticality heatmap**: 144 zones × 6 classes
- **Critical path timeline**: 17–88 steps 의 구성 순서
- **fbx_supplemented 영향도**: 40 pipelines의 before/after fragmentation

### 단계
1. Foundry Quiver 에서 새 analysis 생성
2. Object Set 으로 KPI 데이터셋 import
3. 각 차트 (histogram, sankey, treemap) 배치
4. 필터 컨트롤 연결
5. Share link 발급

### 소요 시간
**반나절–1일**

---

## 8. 방향 F — AIP Logic 서버리스 함수 (Phase 7f)

### 목표
33 KPIs 중 실시간 재계산이 필요한 것들을 **Foundry Function** 으로 re-implement.
로컬 Python 코드 → Foundry TypeScript Function 이식.

### 대상 KPI
- `equipment_criticality_score` (object-level, 실시간 필터 반응)
- `pipeline_isolation_sections` (사용자가 valve 제거 시뮬레이션 시)
- `zone_shutdown_impact` (zone 선택 시)

### 단계
1. Foundry UI → Functions → TypeScript project
2. Ontology client import
3. KPI 로직 TypeScript 포팅
4. Deploy → Workshop / Quiver 에서 호출

### 소요 시간
**1–2 일**

---

## 9. 권장 실행 순서

### Week 1 — Foundation
| Day | 방향 | 결과물 |
|---|---|---|
| 1 | **A — Ontology 구성** | 6 Object Type + 4 Link Type 등록, 3D preview 활성 |
| 2–3 | **B — React 3D Viewer MVP** | 작동하는 플랜트 viewer |

### Week 2 — Demo-ready
| Day | 방향 | 결과물 |
|---|---|---|
| 1 | **C — Workshop 대시보드** | 비개발자용 탐색 UI |
| 2–3 | **D — AIP Agent** | 자연어 쿼리 인터페이스 |

### Week 3 — Analytics polish
| Day | 방향 | 결과물 |
|---|---|---|
| 1 | **E — Quiver dashboard** | M4 finding + KPI 시각화 |
| 2 | **F — AIP Logic** | 서버리스 KPI 함수 |
| 3 | **문서화 + demo video** | 포트폴리오 완성 |

---

## 10. 각 방향의 성공 기준

| 방향 | 성공 기준 |
|---|---|
| A | Ontology Object 페이지에서 3D preview 가 렌더링되고, 인접 객체가 자동 로드됨 |
| B | 12,009 객체가 원활히 렌더링되고, 클릭 시 250ms 내 response |
| C | 필터 + 3D + KPI 가 한 화면에서 작동 |
| D | 자연어 쿼리 5개가 정확히 Ontology 로 매핑됨 |
| E | 3개 이상의 차트로 M4 finding 을 시각화 |
| F | 1개 이상의 KPI 가 Function 으로 호출 가능 |

---

## 11. 블로커 / 위험 요소

| 위험 | 영향 | 완화책 |
|---|---|---|
| Developer Tier 의 AIP 제한 | D, F 불가능할 수 있음 | Tier 확인 후 D, F skip 가능 |
| OSDK 생성 권한 부족 | B 불가 | Workshop(C) 우선 진행 |
| Media Set API rate limit | B 의 실시간 로딩 느림 | Bbox placeholder + lazy load 전략 |
| Ontology 등록 시 link 충돌 | A 지연 | 테스트 브랜치에서 선행 검증 |
| `mesh_uri` 값이 `mesh/xxx.glb` 형식 vs Media Set 내부 path 불일치 | 3D preview 실패 | Media item path template 조정 |

---

## 12. 관련 문서

- M4 Finding: `docs/findings/2026-04-15-M4-fbx-guid-mapping/`
- Foundry Setup: `docs/reference/foundry-setup-guide.md`
- FBX Mapping Analysis: `docs/reference/fbx-mapping-numerical-analysis.md`
- Phase 6 API: `src/bimkg/api/` (로컬 FastAPI → Foundry Function 이식 대상)
- Phase 5 LLM: `src/bimkg/llm/` (AIP Agent 마이그레이션 대상)

---

## 13. 즉시 다음 액션

1. **이 로드맵 리뷰 & 승인**
2. **방향 A 착수** — Ontology Manager 에서 첫 Object Type 등록 + 3D preview 검증
3. AI FDE (AIP Assist) 로 "내 Ontology 에서 할 수 있는 것" 탐색 → 새 발견 시 이 로드맵 업데이트
