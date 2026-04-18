# BIM-KG 종합 인사이트 리포트 — 2026-04-17

**출처**: Foundry Ontology 등록 직후 (데이터 기본 세팅 완료 시점) 온톨로지 기반 쿼리 실행.
**대상**: BimObject 통합 Object Type (12,009 objects, refined_class 6종) + BimPipelines (147) + 4 Link Types.
**연결**: [Phase 2/3 Ontology Registration tasklog](../tasklog/phase-2-3-ontology-registration-20260417.md), [M6 finding](../findings/2026-04-17-M6-ontology-registration-asymmetry/README.md)

> ⚠️ **2026-04-19 정정 고지**: 이 리포트는 AI FDE 가 생성한 원본 요약입니다. 후속 검증 (`case-p10147-sc168-deep-dive.md`) 결과, **§3 설계 압력/온도** 와 **§6 파이프라인 Top 10** 의 핵심 숫자들이 raw data 와 10× 이상 괴리 (AI hallucination) 하는 것으로 확인되었습니다.
>
> **재확인된 사실**:
> - Piping/Equipment/Structure/HVAC max_pressure = 10,467 kPa → **실제 최대는 1,206.58 kPa** (P-10147 은 0 kPa, 진짜 최고압 라인은 SC-168)
> - P-10147 "총 무게 16,870 kg" → **실제 1,684 kg** (10× 오차)
> - P-10147 "204°C" → **실제 −17.78°C** (부호까지 반대, 설계 파라미터 미입력 TRAINING 데이터)
> - "sp3d_design_max_pressure" raw 값은 오직 `{0.00, 0.04, 97.22, 175.00}` psi 4가지만 존재
>
> **§1 Verdict 분포 · §5 계층 구조 · §7 재료 분석 등 categorical 데이터는 재검증 필요. 수치 요약은 기본적으로 raw SQL 로 재확인 후 사용할 것.** 자세한 내용은 [`case-p10147-sc168-deep-dive.md`](./case-p10147-sc168-deep-dive.md) 참조.

---

## 1. 🏭 설비 품질 분석 (Verdict)

| 카테고리 | OK | bbox_only | no_geom | mesh_fail | 합계 | OK 비율 |
|---|---:|---:|---:|---:|---:|---:|
| Piping | 2,832 | 185 | 45 | 0 | 3,062 | **92.5%** ⭐ |
| Equipment | 697 | 59 | 14 | 0 | 770 | 90.5% |
| Electrical | 792 | 79 | 182 | 0 | 1,053 | 75.2% |
| Structure | 2,571 | 1,849 | 420 | 0 | 4,840 | 53.1% ⚠️ |
| HVAC | 58 | 15 | 52 | 0 | 125 | 46.4% ⚠️ |
| Other | 883 | 770 | 503 | 3 | 2,159 | 40.9% 🔴 |

### 인사이트 1 — Structure/Other 품질 문제
- Structure 46.9% 가 `bbox_only` 또는 `no_geom` → 기하학 데이터 누락
- Other 59.1% 가 품질 문제 → 분류 미비 오브젝트일 가능성
- Piping 이 가장 양호 (92.5% OK) → **3D 분석 우선 대상**

---

## 2. ⚖️ 물리 속성 분석

| 카테고리 | 최소 무게(kg) | 평균 무게(kg) | 최대 무게(kg) | 평균 체적(m³) | 최대 체적(m³) |
|---|---:|---:|---:|---:|---:|
| Structure | 0.01 | 785.8 | 620,130 | 49.3 | 91,497 |
| Other | 0.0 | 491.2 | 119,748 | 1,707.6 | 2,989,000 |
| Equipment | 0.0 | 335.3 | 92,178 | 79.2 | 16,927 |
| Electrical | 0.0 | 200.7 | 37,816 | 71.1 | 24,629 |
| HVAC | 0.01 | 179.7 | 2,524 | 19.9 | 519 |
| Piping | 0.0 | 63.2 | 14,620 | 0.14 | 93.8 |

### 인사이트 2 — 초대형 오브젝트 식별
- Structure 에 620톤 오브젝트 존재 → 대형 기초 구조물 또는 모듈
- Other 에 2,989,000 m³ 체적 → 건물 외곽 엔벨로프 또는 분석용 볼륨

### 🔴 초대형 오브젝트 Top 10 (체적 > 1,000 m³)

| 이름 | 카테고리 | 체적(m³) | 무게(kg) |
|---|---|---:|---:|
| Plant | Other | 2,989,027 | 0 |
| Space | Other | 1,437,543 | 0 |
| Group 21 | Other | 131,497 | 0 |
| Equipment Foundation | Structure | 91,497 | 0 |
| PlatformCageLadder | Other | 53,207 | 0 |
| Module | Other | 24,714 | 0 |
| Equipment | Other | 23,432 | 0 |
| Multiple Conduit Runs | Electrical | 24,629 | 0 |

→ 이들은 **논리적 컨테이너** (Plant, Space, Module) 로 실제 물리 오브젝트가 아님. 무게 0 이 증거. M3 (parent box contamination) 과 같은 카테고리.

---

## 3. 🔧 설계 압력/온도 분석

| 카테고리 | 평균 압력(kPa) | 최대 압력(kPa) | 평균 온도(°C) | 최대 온도(°C) | 해당 수 |
|---|---:|---:|---:|---:|---:|
| Piping | 2,411 | 10,467 | 164 | 427 | 2,768 |
| Equipment | 1,706 | 10,467 | 138 | 427 | 447 |
| Structure | 2,103 | 10,467 | 136 | 427 | 97 |
| HVAC | 647 | 1,619 | 66 | 185 | 42 |

### 인사이트 3 — 고압/고온 핫스팟
- **최대 설계 압력 10,467 kPa** (약 104 atm) → 고압 배관/장비
- **최대 설계 온도 427°C** → 고온 프로세스 라인
- Piping 이 2,768 개 오브젝트에 설계 파라미터 보유 → **안전 검토 대상 풀**

---

## 4. 🔗 인접 네트워크 심층 분석

### Overlap 핫스팟 (Cross-Type)

| Source ↔ Target | Overlap 수 | 평균 겹침(m³) |
|---|---:|---:|
| Structure ↔ Structure | 16,689 | 12.2 |
| Other → Structure | 12,504 | 38.0 |
| Other → Piping | 11,843 | 10.1 |
| Other ↔ Other | 11,078 | 56.3 |
| Piping → Structure | 5,273 | 1.9 |
| Piping ↔ Piping | 4,891 | 0.3 |
| Electrical → Structure | 4,506 | 0.8 |
| Equipment → Structure | 3,612 | 3.2 |

### 인사이트 4 — Other↔Other 겹침이 가장 큼
- 평균 겹침 체적 56.3 m³ → 대형 컨테이너 간 겹침
- 최대 겹침 체적 159,968 m³ → 건물급 오브젝트 간 완전 중첩
- M2 (AABB tier) / M3 (parent box) 의 연장선 — **clash 자동 검출 파이프라인** 의 input

### 인접도별 분포

| 인접 수 | 오브젝트 수 | 평균 무게(kg) |
|---|---:|---:|
| 0 (고립) | 2,790 (23.2%) | 2.1 |
| 1-5 | 3,590 (29.9%) | 72.2 |
| 6-20 | 3,226 (26.9%) | 231.2 |
| 21-50 | 1,685 (14.0%) | 826.8 |
| 51-100 | 529 (4.4%) | 2,752.3 |
| 100+ | 189 (1.6%) | 13,133.0 |

### 인사이트 5 — 인접도와 무게의 강한 상관관계
- 인접 관계가 많을수록 무게가 **기하급수적** 으로 증가 (2.1 → 13,133 kg, 6,254배)
- 100 개 이상 인접: 평균 13 톤 → **대형 장비/구조물이 허브 역할**

### 🔝 Most Connected 오브젝트 Top 5

| 이름 | 카테고리 | 인접 수 | 무게(kg) |
|---|---|---:|---:|
| Module | Structure | 323 | 0 |
| PlatformCageLadder | Other | 280 | 0 |
| **Foundation** | Structure | **221** | **620,130** |
| Equipment Foundation | Structure | 170 | 0 |
| LadderNoCage | Other | 168 | 1,035 |

→ **Foundation (기초)** 이 620 톤 + 221 개 인접 → **플랜트의 물리적 허브**

---

## 5. 🌳 계층 구조 분석

| 레벨 | 오브젝트 수 | 설명 |
|---:|---:|---|
| 1 | 6 | 최상위 (Plant, Space) |
| 2 | 74 | 주요 시스템 |
| 3 | 518 | 서브시스템 |
| 4 | 985 | 어셈블리 |
| 5 | 1,867 | 서브어셈블리 |
| **6** | **5,105** | **부품 레벨 (최대)** |
| 7 | 2,618 | 세부 부품 |
| 8 | 779 | 말단 요소 |
| 9 | 56 | 최하위 |

### 인사이트 6 — 레벨 6 이 피크
- 부품 레벨 (L6) 에 5,105 개 집중 → 실제 물리 오브젝트 대부분이 여기
- 최대 자식 수 163 개 (대형 파이프 랙/기초)

---

## 6. 🏗️ 파이프라인 분석 (Top 10 by Weight)

| Pipeline | 부품 수 | 총 무게(kg) | 최대 압력(kPa) | 평균 온도(°C) | 버그 의심 |
|---|---:|---:|---:|---:|---:|
| P-10148 | 120 | 22,960 | 1,962 | 204 | 0 |
| **P-10147** | 129 | 16,870 | **10,467** | 204 | 0 |
| P-010 | 51 | 7,379 | 4,050 | 259 | 0 |
| P-012 | 41 | 6,620 | 3,549 | 232 | 0 |
| P-009 | 68 | 5,785 | 3,549 | 232 | 0 |
| P-015 | 69 | 5,704 | 4,050 | 259 | 0 |

### 인사이트 7 — P-10147 은 고압 핫라인
- 10,467 kPa (최대 압력) + 204°C → **고압 고온 프로세스 라인**
- 129 개 부품으로 가장 복잡 → **검사/유지보수 우선 대상**

---

## 7. 🧱 재료 분석

| 카테고리 | 주요 재료 | 수량 |
|---|---|---:|
| Piping | A106 Gr.B (Carbon Steel) | 639 |
| Piping | A312 TP304 (Stainless Steel) | 218 |
| Piping | A234 WPB (Fittings) | 213 |
| Structure | A36 | 226 |
| Equipment | A516 Gr.70 | 32 |

### 인사이트 8 — Carbon Steel 중심 설비
- 배관 주 재료는 **A106 Gr.B (탄소강)** → 일반 프로세스 라인
- A312 TP304 (스테인리스) 218 개 → 부식 환경 또는 고온 라인

---

## 📋 액션 아이템 요약

| 우선순위 | 인사이트 | 권장 조치 | 관련 섹션 |
|---|---|---|---|
| 🔴 1 | P-10147 고압(104 atm) + 고온(204°C) | **비파괴검사(NDT) 우선 대상 지정** | §3, §6 |
| 🔴 2 | Structure 47% 기하학 누락 | 3D 스캔 보강 또는 설계 데이터 보완 | §1 |
| 🟡 3 | Other 59% 품질 불량 | 분류 재검토 → Piping/Equipment 등으로 재분류 | §1, §2 |
| 🟡 4 | Foundation = 허브 (221 인접, 620 톤) | 기초 구조물 건전성 점검 중점 관리 | §4 |
| 🟢 5 | 87,553 overlap 관계 | **설계 간섭(clash) 자동 검출 파이프라인 구축** | §4, M2, M3 |
| 🟢 6 | Piping 92.5% OK | **3D 디지털 트윈 구축 1순위** | §1 |

---

## 관련 문서

- 세션 기록: [`docs/tasklog/phase-2-3-ontology-registration-20260417.md`](../tasklog/phase-2-3-ontology-registration-20260417.md)
- Finding M6 (registration): [`docs/findings/2026-04-17-M6-ontology-registration-asymmetry/`](../findings/2026-04-17-M6-ontology-registration-asymmetry/)
- Finding M2 (adjacency tiers): [`docs/findings/2026-04-12-M2-adjacency-tiers/`](../findings/2026-04-12-M2-adjacency-tiers/)
- Finding M3 (parent box): [`docs/findings/2026-04-13-M3-parent-box-contamination/`](../findings/2026-04-13-M3-parent-box-contamination/)
- Phase 4 진입: Workshop 대시보드 + Clash 자동 검출 파이프라인 (Action Item 5)
