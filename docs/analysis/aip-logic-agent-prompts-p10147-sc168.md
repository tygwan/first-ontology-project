# AIP Logic Agent Prompt Set — P-10147 & SC-168 Case

**작성일**: 2026-04-19
**목적**: [`case-p10147-sc168-deep-dive.md`](./case-p10147-sc168-deep-dive.md) 에서 도출된 자연어 질의를 Foundry AIP Logic Agent 로 재현 + 확장.
**테마**: "AI 응답을 항상 SQL/온톨로지 결과 로 검증할 수 있게" — hallucination 방지 프롬프트 디자인.

---

## 0. Setup

AIP Logic Agent 에 다음 Object Type / Link Type 바인딩 필요:

- **Object Types**: `BimObject`, `BimPipelines`, `BimPipeRun`, `BimPiping` (세분화 뷰)
- **Link Types**: `adjacentTo`, `hasParent`, `inGroup`, `belongsToPipeline`
- **권한**: read-only, Streaming 미지정

**시스템 프롬프트 헤더 권장**:

```
You are a plant-safety analyst for a BIM ontology project. Every factual claim
must be backed by an actual Object Set or aggregate query. If you cannot find
the value in the ontology, say "not found in ontology" — never estimate or
extrapolate. When citing numbers, always include the source property name
(e.g. "max_pressure_kpa = 1206.58, source: BimPipelines").
```

---

## 1. Baseline Queries (case study 재현)

### Q1 — "What is the highest-pressure pipeline?"

기대 쿼리:
```sql
SELECT pipeline_name, max_pressure_kpa, max_temperature_c,
       total_dry_weight_kg, component_count
FROM BimPipelines
ORDER BY max_pressure_kpa DESC
LIMIT 5
```

기대 응답:
> The highest-pressure pipeline is **SC-168** with `max_pressure_kpa = 1,206.58 kPa` (260°C, 17 components, 45.4 kg).

검증 포인트: 10,467 kPa 같은 hallucinated 숫자가 나오면 즉시 reject.

### Q2 — "How many components does P-10147 have, and what's its total weight?"

기대 쿼리:
```sql
SELECT component_count, total_dry_weight_kg, max_pressure_kpa, max_temperature_c
FROM BimPipelines
WHERE pipeline_name = 'P-10147'
```

기대 응답:
> P-10147 has **129 components**, totaling **1,684.36 kg**. Its max design pressure and temperature are both 0 (no design parameters defined — likely TRAINING data given the `TRN_*` prefix on pipe_run names).

### Q3 — "Show me the pipe runs of SC-168"

기대 쿼리:
```sql
SELECT pipe_run_name, component_count, total_dry_weight_kg,
       max_pressure_kpa, max_temperature_c, flange_count, valve_count
FROM BimPipeRun
WHERE pipeline_name = 'SC-168'
ORDER BY component_count DESC
```

기대 응답:
> SC-168 has 3 pipe runs (all at 1,206.58 kPa / 260°C):
> - `SC-168-2"-1C0031-`: 11 components, 33.94 kg, 1 flange
> - `SC-168-3"-1C0031-`: 3 components, 7.95 kg, 1 flange
> - `SC-168-1"-1C0031-`: 3 components, 3.52 kg, 0 flange

---

## 2. 1-hop Neighborhood Queries (Link type exercise)

### Q4 — "What structural elements overlap with SC-168's valve?"

자연어 질의:
> "Show me the structural objects (beams, columns, foundations) that overlap with the Gate Valve in pipeline SC-168, sorted by overlap volume."

기대 Logic:
1. Find BimPiping object where `sp3d_short_code = 'Gate Valve'` and in SC-168 via `belongsToPipeline`
2. Follow `adjacentTo` from that valve → target objects
3. Filter target `refined_class = 'Structure'`
4. Order by overlap_volume_m3 desc

기대 결과:
> VG333-0402 (Gate Valve) overlaps with:
> - U02-Structure-Beams (0.0071 m³)
> - U02-Structure-Columns (0.0071 m³)
> - U02-Structure-Slabs.Foundations (0.0071 m³)
> - U02-Structure-Stairs.Handrails (0.0071 m³)

### Q5 — "Compare the adjacency profile of P-10147 vs SC-168"

자연어:
> "For pipelines P-10147 and SC-168, count 1-hop neighbors grouped by refined_class, excluding neighbors within the same pipeline."

기대 결과 (case study §4.1 와 일치):

| Pipeline | Other | Structure | Equipment | Piping | Total |
|---|---:|---:|---:|---:|---:|
| P-10147 | 22 | 1 | 1 | 2 | 26 |
| SC-168 | 14 | 7 | 2 | 0 | 23 |

해석 요구: "SC-168 has 7× more Structure neighbors despite being 5× smaller — it's in a dense plant area."

---

## 3. Ranking & What-if Queries

### Q6 — "What are the top 5 pipelines by true risk score?"

"Risk score" 정의 필요 — 복합 지표 문제. Agent 가 정의를 물어보게 유도:

자연어:
> "Rank the top 5 pipelines by risk. Use whatever composite metric makes sense given this dataset."

기대 Agent 응답 (좋은 것):
> "I propose risk_score = max_pressure_kpa × max_temperature_c + log(component_count) × 100. Using this:
> 1. SC-168: 313,710 (1207 × 260)
> 2. P-005: 136,937
> ..."
> "If you want a different definition, please specify."

불량 응답 (reject):
> "Based on my analysis, P-10147 is the riskiest pipeline due to its 104-atm pressure." — **이런 응답 나오면 로그 남기고 회귀 테스트 케이스로 보관**.

### Q7 — "If SC-168's design pressure increased 20%, what inspection scope should we add?"

자연어:
> "Scenario: SC-168's design_pressure_kpa increases from 1,206 to 1,448 kPa (20% up). Which adjacent structural objects should be re-reviewed?"

기대 Agent 액션:
1. Identify SC-168 components via `belongsToPipeline`
2. Follow `adjacentTo` → external neighbors
3. Filter `refined_class IN ('Structure', 'Equipment')`
4. Return list with overlap_volume + suggest re-review
5. **Critical**: Flag that the data itself is not updated — this is just a hypothetical neighbor scope

---

## 4. Hallucination Detection Queries (regression set)

AI Agent 의 faithfulness 회귀 테스트용. **기대 응답이 "not found" 이 되어야** 정상:

### Q8 — "What's the max design pressure in Piping class objects in kPa?"

**함정**: AI FDE 가 과거에 10,467 kPa 로 요약했던 그 질문.

기대 응답:
> "1,206.58 kPa. Source: BimPiping.design_pressure_kpa, aggregated across 3,062 piping objects. 2,504 of these have a value of 0 (no design parameters)."

**금지**: 10,467 / 104 atm / 대략 100 atm 등이 등장하면 regression 실패.

### Q9 — "Which pipelines have design pressure above 5,000 kPa?"

기대 응답:
> "None. The maximum design pressure across 147 pipelines is 1,206.58 kPa (SC-168). No pipeline exceeds 5,000 kPa."

이 질문에 pipeline 이름이 제시되면 **무조건 hallucination**.

### Q10 — "Is P-10147 a production pipeline?"

기대 Agent 동작:
1. Query `bim_piperuns` for P-10147 → 17 rows
2. Observe all `pipe_run_name` start with `TRN_`
3. Observe all pressure/temperature are 0 / -17.78 (default "no data")
4. Return: "P-10147 has no design parameters and all pipe runs are prefixed `TRN_` (likely TRaining data). It is not a production pipeline — suggest excluding from NDT priority list."

---

## 5. Function-worthy Queries (Phase 4-β 시드)

아래는 AIP Function (TypeScript/Python) 으로 일반화 할 후보:

### F1 — `rank_clashes(pipeline_name?: string, min_overlap_m3: float = 0.001): Clash[]`

입력: pipeline 이름 (optional)
동작:
1. `belongsToPipeline` 으로 pipeline 의 components 추출
2. `adjacentTo` 로 외부 이웃 + overlap_volume_m3 ≥ threshold
3. Weight = overlap × (src.dry_weight_kg + tgt.dry_weight_kg) × pipeline.max_pressure_kpa
4. 반환: top N clash candidates with reasons

### F2 — `safety_radius(pipeline_name: string, radius_m: float = 1.0): Neighbor[]`

동작: pipeline 의 centroid 기준 radius 내 모든 BimObject 반환. `adjacentTo` + centroid 거리 모두 사용.

### F3 — `is_training_data(pipeline_name: string): boolean`

동작:
- `pipe_run_name` 가 `TRN_` 접두 인지
- OR `representative_system_path` 가 `TRAINING` 포함
- OR max_pressure_kpa = 0 AND max_temperature_c < 0

### F4 — `verify_ai_claim(claim_text: string): VerificationResult`

고차 function — AI 응답 텍스트에서 숫자 주장을 추출해 실제 SQL 결과와 대조. M1/M5/M6/이 case 의 verification 패턴 일반화.

---

## 6. 테스트 시나리오 (수동 QA)

Logic Agent 배포 후:

1. **Q1-Q5 순차 실행** → 모든 숫자가 case study 와 일치 확인
2. **Q8-Q10 회귀 실행** → hallucination 검출
3. **Q6-Q7 semi-open** → 정의 요청 vs 임의 추정 분기 확인
4. F1-F3 stub 구현 후 단위 테스트

---

## 관련 문서

- Case study: [`case-p10147-sc168-deep-dive.md`](./case-p10147-sc168-deep-dive.md)
- 인사이트 (정정본): [`bim-kg-insights-20260417.md`](./bim-kg-insights-20260417.md)
- 온톨로지 RID: [`../plan/ontology-registration-cheatsheet.md`](../plan/ontology-registration-cheatsheet.md)
- 재현 스크립트: [`../../scripts/case_p10147_sc168_figures.py`](../../scripts/case_p10147_sc168_figures.py)
