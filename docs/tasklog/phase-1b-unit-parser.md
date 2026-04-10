# Phase 1b: Unit Parser

**일자**: 2026-04-10
**담당 Task**: #3
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| Python | `src/bimkg/ingest/__init__.py` | ingest 서브패키지 초기화 |
| Python | `src/bimkg/ingest/unit_parser.py` | SP3D 문자열 물리량 → SI 단위 파서 (순수 함수, 외부 의존성 없음) |
| Python | `tests/test_ingest/__init__.py` | 테스트 서브패키지 초기화 |
| Python | `tests/test_ingest/test_unit_parser.py` | 44개 단위 테스트 (합성 + 실제 샘플) |

**파서 함수 5종**:
- `parse_length(s) -> float | None` → 미터 (ft, in, mm 혼합 지원)
- `parse_weight(s) -> float | None` → kg (lbm)
- `parse_pressure(s) -> float | None` → kPa (psi)
- `parse_temperature(s) -> float | None` → 섭씨 (F)
- `parse_npd(s) -> tuple[float, float] | None` → (end1_m, end2_m)

**지원 포맷 (실제 데이터 기반)**:
- 길이: `"21 ft  4.00 in"`, `"2 1/2 in"`, `"29.53 in"`, `"0 ft  9.00 in"`, `"24 ft   .43 in"`, `"200mm"`
- 무게: `"178.55 lbm"`, `"0 lbm"`
- 압력: `"0.00 psi"`
- 온도: `"492.80 F"`
- NPD: `"4in x 4in"`, `"0.75in x 0.75in"`, `"4in x 0"`, `"200mm x 200mm"`

**설계 원칙**:
- 순수 함수 (DB 의존 없음) → 빠른 단위 테스트 가능
- 실패 시 `None` 반환, 예외 발생 없음 (대량 처리 시 한 건 실패가 전체를 중단시키지 않도록)
- 공통 숫자 패턴 `_NUM = r"-?(?:\d+(?:\.\d+)?|\.\d+)"` 로 모든 정규식 통일
- 정규식 case-insensitive

---

## 2. 문제

초기 구현 후 실제 SQLite 전체 데이터셋에 대해 커버리지 검증 시 두 건의 파싱 실패 발견:

**문제 #1**: Length 필드에서 1,690건 중 8건(0.5%) 실패
```
'24 ft   .43 in' — 앞자리 정수가 없는 소수 ".43"
```

**문제 #2**: NPD 필드에서 2,926건 중 50건(1.7%) 실패
```
'200mm x 200mm' — 인치가 아닌 밀리미터 단위
```

---

## 3. 분석

**문제 #1**: 초기 정규식 `\d+(?:\.\d+)?` 는 `.43` 형태(정수부 없는 소수)를 매칭하지 못함. 플랜트 모델에서 1피트 미만의 소수 인치를 표현할 때 SP3D가 앞자리 0을 생략하고 `.43`처럼 출력하는 케이스가 존재.

**문제 #2**: 초기 NPD 파서는 인치 단위만 지원. 그러나 실제 데이터에 밀리미터 단위 배관(예: 200mm 파이프)이 혼재. SP3D 프로젝트 단위 체계가 프로젝트별로 다르기 때문에 발생한 정상 데이터.

---

## 4. 해결방안

**해결 #1**: 공용 숫자 패턴 상수 도입
```python
_NUM = r"-?(?:\d+(?:\.\d+)?|\.\d+)"
```
- `\d+(?:\.\d+)?` : `"4"`, `"4.00"`
- `\.\d+` : `".43"`
- 모든 길이·무게·압력·온도·NPD 정규식에 f-string으로 일괄 적용

**해결 #2**: NPD 파서에 mm 단위 정규식 6종 추가
- `_NPD_PAIR_MM_RE` : `"200mm x 200mm"`
- `_NPD_REDUCER_MM_RE` : `"200mm x 0"`
- `_NPD_SINGLE_MM_RE` : `"200mm"`
- `parse_length`에도 `_LENGTH_MM_RE` 추가 (일관성)

**해결 #3**: 엣지 케이스 회귀 테스트 3건 추가
- `test_leading_dot_inches`
- `test_millimeters`
- `test_mm_pair`

---

## 5. 결과

✅ 단위 테스트: **44/44 통과** (0.07초)
```
tests/test_ingest/test_unit_parser.py::TestParseLength       12 passed
tests/test_ingest/test_unit_parser.py::TestParseWeight        7 passed
tests/test_ingest/test_unit_parser.py::TestParsePressure      5 passed
tests/test_ingest/test_unit_parser.py::TestParseTemperature   6 passed
tests/test_ingest/test_unit_parser.py::TestParseNpd           7 passed
tests/test_ingest/test_unit_parser.py::test_real_*_samples    5 passed
```

✅ 실제 데이터 커버리지: **11개 필드 모두 100%**
```
[OK] Dry Weight              5135/5135 (100.0%)
[OK] Wet Weight               116/ 116 (100.0%)
[OK] Length                  1690/1690 (100.0%)
[OK] Width                   1772/1772 (100.0%)
[OK] Depth                   1564/1564 (100.0%)
[OK] Height                    45/  45 (100.0%)
[OK] Diameter                  36/  36 (100.0%)
[OK] Bend Radius               42/  42 (100.0%)
[OK] Design Max Pressure     2356/2356 (100.0%)
[OK] Design Max Temperature  2356/2356 (100.0%)
[OK] NPD                     2926/2926 (100.0%)
```

**영향**: Phase 1c에서 `bim_objects` 테이블의 SI 단위 컬럼 (`dry_weight_kg`, `length_m`, `design_pressure_kpa`, `design_temperature_c`)을 채울 때 11개 필드에서 데이터 손실 0건 보장.
