# Phase 1 Verification Findings

> 이 문서는 Phase 1 (0~1d) 결과의 수동 검증 중 발견한 이슈를 기록합니다.
> 각 항목은 **Phase 2 시작 전에 해결할 것인지 연기할 것인지** 명확히 표시합니다.
>
> 가이드: [`phase-1-verification-guide.md`](phase-1-verification-guide.md)

---

## Status Key

- ✅ **Resolved** — 수정 완료, 참조 커밋 기재
- 🔄 **In progress** — 조사 또는 수정 중
- 📋 **Deferred to Phase 2** — Phase 2 에서 온톨로지와 함께 처리
- 🔭 **Accept as-is** — 원천 데이터 한계로 받아들임
- ❓ **Needs decision** — 사용자 판단 필요

---

## 자동으로 이미 감지된 알려진 이슈

### A1. `sp3d_pipeline = "Pipelines"` 라벨 153 건  📋 Phase 2

**발견**: Top 10 pipeline 리스트에 `"Pipelines"` 가 153 건으로 1위로 등장.

**분석**:
- XLSX 와 AllProperties CSV 모두에 `"Pipelines"` 문자열이 sp3d_pipeline 속성값으로 기록됨
- SP3D 에서 `Pipeline` 필드가 특정 객체에 대해 라벨 이름 "Pipelines" 로 잘못 채워진 것으로 추정
- 해당 153 객체의 상세 분석 필요

**영향**:
- `dim_pipeline.csv` 에 가짜 파이프라인 1건 포함 (147 중)
- Foundry `belongs_to_pipeline.parquet` 에도 153 건이 이 값으로 연결됨

**권장 처리**:
- Phase 2 에서 `Pipeline` Object Type 정의 시 이 값을 제외하거나 `is_valid=False` 플래그
- 또는 Phase 1e 패치로 clean.py 에서 필터링

---

### A2. Equipment `sp3d_eqp_type_0` 커버리지 18%  🔭 Accept

**발견**: Equipment 클래스 851 개 중 153 개만 `Eqp Type 0` 속성 보유.

**분석**:
- SP3D 프로젝트에서 Equipment taxonomy 가 일부 객체에만 할당됨
- 153 개는 "Process Equipment", "Electrical Equipment" 등 4단계 taxonomy 보유
- 698 개는 Equipment 로 분류되었지만 세부 taxonomy 없음

**영향**: Phase 2 Equipment subclass 설계 시 698 개를 "Equipment > Unclassified" 로 모델링해야 함.

**권장 처리**: 원천 데이터 한계로 받아들임. Phase 2 에서 optional 로 처리.

---

### A3. Pipeline 147 (XLSX) vs 157 (legacy SQLite) 불일치  📋 Phase 2

**발견**: 같은 데이터셋인데 파이프라인 개수가 다름.

**분석**:
- XLSX RefinedXlsxExporter 의 `FindKey` 함수가 "Pipeline" 이름을 가진 첫 번째 속성만 선택
- `SmartPlant 3D|Pipeline` 과 `Item|Pipeline` 같은 중복 이름이 있으면 1개만 사용됨
- 누락된 10 건은 `U12-*-MZ-*-1S3984` 시리즈

**권장 처리**: Phase 2 에서 온톨로지 구축 시 AllProperties.csv 에서 보완 조인.

---

## 사용자 검증 중 발견한 이슈

### (검증 진행 후 여기에 기록)

---

## 해결된 이슈

(없음 — Phase 1 완료 시점)

---

## 기록 포맷 템플릿

새 이슈 발견 시 아래 형식으로 추가하세요:

```markdown
### [식별자] 한 줄 요약  [상태 이모지] [상태 키워드]

**발견**: 어디서 어떻게 발견했는지 (Power BI 화면, 파이썬 쿼리, 그래프 이상 등)

**재현**:
```python
# 또는 sql 쿼리
...
```

**분석**: 왜 이런 일이 일어났을 것인지

**영향**: 어느 Phase / 어느 출력물에 영향

**권장 처리**: 제안하는 해결 방향 + 우선순위

**관련 파일**: 관련 소스 파일과 라인
```
