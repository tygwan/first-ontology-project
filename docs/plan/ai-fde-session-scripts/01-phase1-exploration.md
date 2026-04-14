# Phase 1 세션 스크립트 — 데이터 탐색

**추천 설정**: Claude Sonnet 4.6 · Data Engineer skill · Dataset Reader + SQL Executor · PROJECT-JOURNAL.md + foundry-dataset-profiles + M4 finding

**목표**: AI FDE에 프로젝트 맥락을 주입하고, 11 데이터셋에 대한 **공유된 이해** 구축.
**예상 소요**: 30–60분 (대화 + 후속 질문)

---

## 📌 사용법

아래 프롬프트를 **순서대로** AI FDE에 복사-붙여넣기 하세요. 각 단계마다 AI FDE 응답을 보고 다음 프롬프트로 이동합니다. AI FDE가 추가 질문을 하면 답하고, 중요한 결론은 `docs/analysis/ai-fde-sessions/2026-04-15-phase1.md`에 기록하세요.

---

## Prompt 1 — 프로젝트 맥락 주입

```
I'm working on a BIM (Building Information Modeling) knowledge graph for a refining plant.

**Source data**: Navisworks NWD model of an SP3D plant, extracted via DXTnavis (C# tool).

**Project location**: /Datayoon-09825c/BIM-KG/

**11 datasets uploaded** (all share `object_id` as primary key):

Object Types (class-split BIM objects, 12,009 total):
- bim_piping       (3,062 objects) — flanges, valves, pipes, fittings
- bim_structural   (4,840 objects) — beams, columns, foundations, gratings
- bim_equipment    (770 objects)   — vessels, pumps, heat exchangers
- bim_electrical   (1,053 objects) — cable trays, conduits
- bim_hvac         (125 objects)   — ducts, ventilation
- bim_other        (2,159 objects) — unclassified / Navisworks containers

Link Types (relationships, 137,116 rows):
- bim_adjacent_to         (110,173) — spatial adjacency (AABB-based, Strong/Medium/All tiers)
- bim_has_parent          (12,008)  — hierarchy (parent-child)
- bim_belongs_to_pipeline (2,926)   — piping system membership
- bim_in_group            (12,009)  — connected component grouping

Media Set:
- bim_mesh (8,219 GLBs, 327 MB) — 3D geometry, path = `mesh/{object_id}.glb`

**Project status**: Phase 7 (Foundry integration). Ontology not yet configured — the 11 datasets are uploaded but not registered as Object Types in Ontology Manager.

**Prior findings** (avoid re-discovering; see M1–M4 in docs/findings/):
- M1: Piping misclassification — fixed upstream
- M2: Adjacency quality tiers — added strong/medium/all classification
- M3: Parent-box contamination — filtered via `is_parent_box` flag
- M4: FBX GUID mapping — 788 fbx_supplemented meshes mapped via Properties70
- 33 KPIs pre-computed (object/zone/pipeline/plant levels)
- 144 Louvain zones from adjacency graph

**My goal in this session**: Build shared understanding of this data before Ontology registration. I want you to:
1. Confirm your understanding of this domain
2. Point out anything ambiguous or missing
3. Suggest 3–5 questions you'd want to answer FIRST before modeling

Do you have any clarifying questions before we begin?
```

**AI FDE 응답 기대**: 도메인 이해 요약 + 2–4개 명확화 질문. 답변한 뒤 Prompt 2로.

---

## Prompt 2 — 단일 데이터셋 심층 분석

```
Let's start with the largest Object Type dataset: `bim_structural` (4,840 objects).

Please:
1. Read the dataset (first 100 rows sample is fine)
2. Group the ~219 columns by semantic role (identifiers, spatial, SP3D metadata, mesh, classification, etc.)
3. Identify the 10 most "information-dense" columns (high distinct count, low null rate, semantic importance)
4. Flag any columns whose presence/values seem inconsistent

Focus on structural-specific patterns — what differs from generic BIM objects?
```

**기대**: 컬럼 범주화 + dense columns 목록 + 이상 징후. 우리가 모르던 패턴 발견 가능.

---

## Prompt 3 — Cross-Dataset 관계 추론

```
Now let's look at all 6 Object Type datasets together.

I already have 4 explicit Link Types, but I suspect there are **implicit** relationships I haven't modeled.

Please analyze the following and propose 3–5 hidden relationships:

1. Do any `sp3d_system_path` values span multiple classes? (e.g., the same system path appears in both `bim_piping` and `bim_equipment`)
2. Are `group_id` values shared across classes? (we have `bim_in_group` but is it capturing all groupings?)
3. Are there hidden foreign keys I missed? (columns that look like IDs but I haven't linked)
4. Any composite keys worth exploring? (e.g., `sp3d_pipeline + sp3d_pipe_run`)

For each proposed relationship, tell me:
- The semantic meaning
- Which datasets it connects
- Whether it should become a new Link Type or a property
```

**기대**: AI FDE가 우리가 놓친 link 후보 2–3개 제안. 특히 `sp3d_system_path` 교집합은 흥미로움.

---

## Prompt 4 — 데이터 품질 검증

```
Without looking at my prior M1–M4 findings, run a fresh data quality audit on all 6 Object Type datasets.

For each, check:
- Null rate outliers (columns that are suspiciously null)
- Value distribution anomalies (suspicious concentrations)
- Referential integrity (object_id consistency, foreign key validity)
- Naming inconsistencies (typos, format drift in display_name)
- Volume/dimension outliers (e.g., bbox_volume_m3 = 0 or > 1000)

Return the top 5 findings. If any overlap with M1–M4, say so. If any are NEW, flag them clearly — they might become M5/M6 findings.
```

**기대**: 기존 M findings와 겹치는 것 제거 후 **새 M5/M6 후보** 발견. 특히 437개 missing GLB가 언급될 가능성 높음.

---

## Prompt 5 — 도메인 특화 질문

```
Treating me as the product owner of this BIM-KG, answer:

**Question A**: If a refinery operator says "I need to shut down pipeline P-10147 for maintenance — what equipment will be affected?", which datasets and columns would you query?

**Question B**: For a construction scheduler who needs to know installation order, what derived columns or Link Types are we missing?

**Question C**: For a safety auditor checking corrosion risk, which 3 properties are most important and how should they be combined?

Give me **concrete SPARQL/Cypher/SQL queries** for each question using my actual schema.
```

**기대**: AI FDE가 쿼리를 작성 → 우리의 33 KPIs나 precedence DAG를 아는지 검증 + 새 쿼리 패턴 발견.

---

## Prompt 6 — 탐색 마무리 / 요약 요청

```
Before we move to Phase 2 (Ontology modeling), please produce a final summary covering:

1. **Your current understanding** of this domain in 3 bullet points
2. **3 most important datasets** to prioritize in Ontology modeling (with reason)
3. **Top 3 property types** that need careful treatment (e.g., mesh_uri as Media Reference, sp3d_system_path as hierarchical identifier)
4. **1 critical risk** I should address before proceeding
5. **Specific decisions I need to make** before starting Phase 2 (your top 5 questions for me)

Format as markdown I can paste into my session log.
```

**기대**: 압축된 요약 + 다음 단계 action items. 이걸 `docs/analysis/ai-fde-sessions/2026-04-15-phase1.md`에 저장.

---

## 🎯 세션 종료 후 체크리스트

- [ ] AI FDE 응답 중 **새로운 발견**이 있었는가? → `docs/findings/` 에 M5 archive 시작
- [ ] **실수나 잘못된 가정**이 있었는가? → 기록해두고 Phase 2 prompt에서 교정
- [ ] Phase 2로 넘어갈 **준비된 질문 리스트**가 있는가?
- [ ] 세션 요약을 `docs/analysis/ai-fde-sessions/2026-04-15-phase1.md`로 저장했는가?

---

## 🔄 만약 AI FDE가 헤맨다면

### 증상 1: 일반적인 답변만 함 (BIM 도메인 모름)
→ SP3D / Navisworks에 대한 배경 문서를 추가로 upload. 예:
```
https://hexagon.com/products/sp3d (SP3D 공식 설명)
```

### 증상 2: 컬럼 의미를 잘못 추측
→ `docs/reference/DATA-SPECIFICATION.md` attach

### 증상 3: 우리 M1–M4를 모름
→ M4 finding README를 upload

### 증상 4: 너무 길고 모호한 답변
→ "Give me the top 3 in bullet points only" 추가
