# Medallion Data Flow — 다이어그램 검토 및 수정

> Figma 다이어그램 검토 결과. 기존 구조의 정확한 부분과 수정/추가가 필요한 부분을 정리합니다.
> 이 문서는 dev-standards 에 architecture/workflow 규칙 (R11 후보) 을 적용하기 전 시연 자료입니다.

---

## 현재 다이어그램 (Figma)

```
Bronze Layer          Silver Layer              Gold Layer              Output
─────────────       ──────────────           ──────────────         ──────────────
*.xlsx ──────────→ Classification fix ──┐
  6 class labels     neg. lookahead     │
                                        │    Confidence layer
adjacency.csv ──→ Type normalization ──┼──→ HIGH/LOW/LIKELY_BUG ──┐
  110,173 edges      str→float/int      │                          │   OWL/RDF
                                        ├──→ Enriched Parquet ─────┼──→ 477K triples
AllProperties ──→ Column rename ────────┤      218 cols            │
  136 cols raw      snake_case+prefix   │                          │   PowerBI
                                        │    Derived flags ────────┼──→ 10 CSV
                   Unit conversion ─────┘    is_container          │
                     imperial→SI             is_parent_box         │   Foundry
                                                                   ├──→ 10 Parquet
                                             SQLite DB ────────────┤
                                             FTS5 full-text        │   Neo4j
                                                                   └──→ 261K edges
```

## 발견된 문제

### 1. Unit conversion 연결 끊김 ❌

**현재**: Unit conversion 이 어떤 Bronze 소스와도 연결되지 않음
**실제**: AllProperties.csv 의 SP3D 문자열 컬럼 (`sp3d_dry_weight "284.23 lbm"` 등) → unit_parser.py → SI float

**수정**: `AllProperties.csv → Unit conversion` 화살표 추가

### 2. Bronze 소스 누락

**현재**: 3개 (xlsx, adjacency, AllProperties)
**실제**: 7개 파일이 Gold 생성에 참여

| Bronze 파일 | Silver 변환 | 기여 |
|------------|-----------|------|
| *.xlsx | Classification fix, Column rename | class, display_name, 속성 |
| AllProperties.csv | Column rename, **Unit conversion** | parent_id, SP3D 원본 문자열 |
| adjacency.csv | Type normalization | 110,173 공간 관계 |
| **geometry.csv** | (직접 조인) | centroid, bbox, mesh 메타 |
| **validation.csv** | (직접 조인) | mesh_quality, verdict → is_container |
| **connected_groups.csv** | (직접 조인) | group_id, group_size → in_giant_group |
| manifest.json | (참조만) | 스냅샷 메타데이터 |

### 3. Gold cols 수 오류

**현재**: 218 cols
**실제**: **219 cols** (M3 이후 `is_parent_box` 추가)

### 4. Analytics 레이어 누락

Gold → Output 사이에 분석 단계가 있지만 다이어그램에 없음:
- SHACL 검증 (6 shapes → 468 violations)
- Louvain zones (144)
- Precedence DAG (18K edges, 44 steps)
- 33 KPIs

### 5. Output 누락

- LLM Agent (Gemini 2.5 Flash, 5 tools)
- FastAPI (12 REST endpoints)

---

## 수정된 구조

```
Bronze Layer              Silver Layer                   Gold Layer
═══════════             ═══════════════               ═══════════════
                        
*.xlsx ─────────────→ Classification fix ────────┐
  6 class labels         neg. lookahead          │
                                                  │
AllProperties.csv ──┬→ Column rename ────────────┤
  136 cols raw      │    snake_case + prefix      │
                    │                             │
                    └→ Unit conversion ───────────┤    Enriched Parquet
                         imperial → SI            ├──→ 219 cols
                                                  │    (object_id PK)
adjacency.csv ─────→ Type normalization ─────────┤
  110,173 edges          str → float/int          │
                                                  │
geometry.csv ───────→ (직접 조인) ────────────────┤    + Confidence layer
  centroid, bbox                                  │      HIGH / LIKELY_BUG
                                                  │
validation.csv ─────→ (직접 조인) ────────────────┤    + Derived flags
  mesh_quality                                    │      is_container
                                                  │      is_analysis_volume
connected_groups ───→ (직접 조인) ────────────────┘      is_parent_box (M3)
  3,355 groups                                          graph_participant

                                                          │
                              ┌────────────────────────────┘
                              ▼
                    Analytics Layer
                    ═══════════════
                    
                    SHACL Validation ──→ 468 violations (6 shapes)
                    
                    Louvain Zones ─────→ 144 zones (res=3.0)
                    
                    Precedence DAG ────→ 18,214 edges
                    └── adjacency_tier     44 steps critical chain
                        (Strong+Medium)
                    
                    33 KPIs ───────────→ 4 levels
                    └── criticality        (object/zone/pipeline/plant)
                        accessibility
                        corrosion
                        isolation
                              │
                              ▼
                    Output Layer
                    ════════════
                    
                    ┌── OWL/RDF ────────── 477K triples (3 TTL files)
                    │
                    ├── PowerBI ────────── 10 CSV star schema
                    │
                    ├── Foundry ────────── 10 Parquet datasets
                    │                      6 Object Types configured
                    │
                    ├── Neo4j ─────────── 261K edges (6 relationship types)
                    │
                    ├── SQLite + FTS5 ─── 12,009 objects + full-text search
                    │
                    ├── FastAPI ────────── 12 REST endpoints
                    │
                    └── LLM Agent ──────── Gemini 2.5 Flash
                                           5 tools (SQL/FTS5/SPARQL/Cypher/KPI)
```

## dev-standards R11 후보: Architecture Documentation

이 검토에서 드러난 교훈:

1. **다이어그램과 코드의 불일치**는 시간이 지나면 반드시 발생 → 정기 검토 필요
2. **레이어 정의가 명확해야** 함 — Bronze/Silver/Gold 까지는 있지만 Analytics 레이어가 빠져있었음
3. **입출력 연결 누락**은 유지보수 시 혼란 (Unit conversion 사례)
4. **수치 (218 vs 219)** 가 변할 때 다이어그램도 같이 갱신해야 함

R11 후보 규칙:
- 프로젝트에 architecture 다이어그램이 있으면, **코드 변경 시 다이어그램 갱신 체크** 포함
- 다이어그램은 **소스 (Figma/draw.io)** 와 **렌더링 (PNG)** 을 모두 보관
- 매 Phase 완료 시 다이어그램 검토를 task log 체크리스트에 포함

---

*Last updated: 2026-04-14*
