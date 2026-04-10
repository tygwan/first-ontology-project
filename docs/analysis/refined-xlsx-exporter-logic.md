# RefinedXlsxExporter — Logic Reference

> **출처**: https://github.com/tygwan/DXTnavis/blob/main/Services/RefinedXlsxExporter.cs
> **분석 시점**: 2026-04-11
> **대상 커밋**: main branch (HEAD 당시)
> **원본 파일**: `Services/RefinedXlsxExporter.cs` (786 lines, C#/.NET)
>
> 이 문서는 `first-ontology-project` 가 XLSX 를 source-of-truth 로 사용하기 위해 필요한 **C# 로직의 Python 재구현 참조** 이다.
> C# 원본을 매번 다시 읽지 않도록, 분류 규칙과 메타데이터를 한 곳에 박제한다.

---

## 1. Exporter 의 역할

Navisworks 활성 문서에서 모델을 순회하여 **12,009 객체 × 동적 컬럼** 피벗 엑셀 파일을 생성한다.
출력 파일: `Refining_ObjectID_<yyyyMMdd_HHmmss>.xlsx`

5개의 시트:

| Sheet | 이름 | 행 수 | 생성 조건 |
|-------|-----|------:|----------|
| 1 | `Refining_ObjectID_Pivot` | 12,009 | 항상 |
| 2 | `Pipeline_Summary` | 147 (헤더 포함) | Pipeline 속성 존재 시 |
| 3 | `Class_Distribution` | 7 (Total 포함) | 항상 |
| 4 | `Equipment_Summary` | 110 | Equipment Name 속성 존재 시 |
| 5 | `PipeRun_Detail` | 334 | PipeRun 속성 존재 시 |

**메인 시트**(`Refining_ObjectID_Pivot`)만 Phase 1a 의 primary source 로 사용한다. 나머지 4개는 파생 summary 이므로 우리가 SQL / Python 으로 재계산 가능하다.

---

## 2. 메타 컬럼 (항상 첫 5개, 고정 순서)

```csharp
private static readonly string[] MetaColumns = new[]
{
    "Class",            // 추론된 분류 결과
    "ObjectId(GUID)",   // 원본 InstanceGuid
    "DisplayName",      // Navisworks display name
    "System Path",      // 계층 경로
    "Level"             // 계층 깊이 (정수, 문자열로 저장)
};
```

이후 모든 속성 컬럼은 `"Category|PropertyName"` 형식의 키로 알파벳 정렬되어 나열된다.
예: `"SmartPlant 3D|Dry Weight"`, `"항목|내부 유형"`, `"재질|광택"`.

---

## 3. 데이터 추출 흐름 (Export 메서드)

```
1. Navisworks ActiveDocument 획득
2. NavisworksDataExtractor.TraverseAndExtractProperties 로 모델 트리 전체 순회
   → List<HierarchicalPropertyRecord>
3. BuildObjectDataMap: ObjectId 별로 속성 딕셔너리로 피벗
4. BuildDynamicColumns: 모든 속성 키를 수집해 동적 컬럼 리스트 구성
5. BuildPivotRows: 각 객체에 대해 Class 추론 + PivotRow 생성
6. WritePivotSheet + Summary sheets
7. SaveAs(outputPath)
```

### 3.1 `HierarchicalPropertyRecord` (입력)

- `Guid ObjectId` — Navisworks InstanceGuid
- `Guid ParentId` — 부모 객체 GUID
- `int Level` — 0..N 깊이
- `string DisplayName`
- `string SysPath`
- `string Category` — Navisworks 카테고리 이름 (예: "SmartPlant 3D", "항목")
- `string PropertyName`
- `string PropertyValue`

### 3.2 `BuildObjectDataMap` 의 핵심 동작

```csharp
objectDataMap[record.ObjectId]["__ObjectId"]    = record.ObjectId.ToString();
objectDataMap[record.ObjectId]["__ParentId"]    = record.ParentId.ToString();
objectDataMap[record.ObjectId]["__Level"]       = record.Level.ToString();
objectDataMap[record.ObjectId]["__DisplayName"] = record.DisplayName ?? string.Empty;
objectDataMap[record.ObjectId]["__SysPath"]     = record.SysPath ?? string.Empty;

// 속성 키는 "Category|PropertyName" 형식
string propertyKey = $"{record.Category}|{record.PropertyName}";
objectDataMap[record.ObjectId][propertyKey] = record.PropertyValue ?? string.Empty;
```

**핵심 제약**: `__` 접두사 키는 `BuildDynamicColumns` 에서 제외된다 (line 213).
→ **ParentId 는 XLSX 출력에 포함되지 않는다.**

### 3.3 `CleanDisplayString`

```csharp
// "DisplayString:abc" → "abc"
if (value.StartsWith("DisplayString:", StringComparison.OrdinalIgnoreCase))
    return value.Substring("DisplayString:".Length).Trim();
```

모든 속성 값에 적용된다.

---

## 4. `InferClass` — 분류 핵심 로직

### 4.1 3-Tier 우선순위 시스템

```
Tier 1 (최우선): 명시적 Class 속성
  └─ 어떤 속성 키의 PropertyName 이 "ClassDisplayName" 또는 "Class" 이면 그 값 사용

Tier 2 (중간): 속성 키 존재 여부 기반 추론
  ├─ 어떤 키가 "pipeline" / "piperun" / "piping" 포함 → "Piping"
  └─ 어떤 키가 "equipment" / "eqp type" 포함 → "Equipment"
  ※ Piping 이 Equipment 보다 먼저 평가되어 우선

Tier 3 (최저): 키워드 substring 매칭
  대상 문자열 = (sysPath + " " + displayName + " " + 모든 속성 키) 를 소문자로 변환
  평가 순서 (위에서부터, 첫 매칭 시 return):
    1. Piping          (pipe/valve/flange/elbow/tee/reducer/nozzle/coupling)
    2. Equipment       (equipment/vessel/pump/tank/compressor/exchanger/heater/reactor)
    3. Structure       (struct/steel/beam/column/brace/foundation/slab/plate/grating/handrail/ladder/stair)
    4. Electrical      (electrical/cable/conduit/tray)
    5. HVAC            (hvac/duct/ventilat)
    6. Instrumentation (instrument)
    7. 기본값: Other
```

### 4.2 키워드 전체 목록 (Tier 3)

| Class | Keywords |
|-------|----------|
| Piping | `pipe`, `valve`, `flange`, `elbow`, `tee`, `reducer`, `nozzle`, `coupling` |
| Equipment | `equipment`, `vessel`, `pump`, `tank`, `compressor`, `exchanger`, `heater`, `reactor` |
| Structure | `struct`, `steel`, `beam`, `column`, `brace`, `foundation`, `slab`, `plate`, `grating`, `handrail`, `ladder`, `stair` |
| Electrical | `electrical`, `cable`, `conduit`, `tray` |
| HVAC | `hvac`, `duct`, `ventilat` |
| Instrumentation | `instrument` |

### 4.3 매칭 방식의 특성

- **Substring 기반, word-boundary 없음**:
  - `"plate"` → `"BasePlate"`, `"Plate_BlockExposed"`, `"NamePlate"` 모두 매칭
  - `"cable"` → `"Cableway"`, `"CableTray"`, `"cableSupport"` 모두 매칭
- **대상 문자열에 모든 속성 키가 포함됨**: 속성 값이 아닌 속성 **키 이름**까지 검색 대상이다.
  → `SmartPlant 3D|Pipeline` 이라는 키를 가지면 "pipeline" 이 combined 에 존재하게 되어 Tier 3 에서도 `Piping` 으로 히트. (하지만 실제로는 Tier 2 에서 먼저 결정됨)
- **Tier 2 의 Piping > Equipment 우선순위**: 한 객체가 Pipeline 속성과 Eqp Type 속성을 동시에 가질 경우 `Piping` 이 선택된다.

### 4.4 "Support" 클래스가 사라진 이유

코드 어디에도 `"support"` 키워드가 없다. 백엔드 SQLite 에서 `object_class='Support'` 였던 715 개 객체는 XLSX 에서 다음과 같이 재분류된다:

| 시나리오 | 재분류 결과 |
|---------|------------|
| 이름에 `PipeSupport` 등 `pipe` 포함 | Piping |
| 이름에 `SteelSupport` 등 `steel` 포함 | Structure |
| SysPath 에 `\Structure\` 포함 | Structure (Tier 3 에서 `struct` 매칭) |
| 그 외 (Support 만 있고 다른 키워드 없음) | Other |

**실측 결과** (cross-tab):
- SQLite Support 715 건 → XLSX Structure 550, Piping 165
- 즉 Support 는 "지지 대상" 의 클래스에 흡수됨

### 4.5 "Other" 697 건의 실체

XLSX 에서 끝까지 `Other` 로 남은 697 건:
- 310 건: 컨테이너 (MeshQuality=skipped_container, AdjacencyCount=0)
- 305 건: box placeholder (계층 노드 L1~L7, MeshQuality=box_placeholder)
- 82 건: 실제 mesh 보유 (Geometry=41, Insulation Volume=41)

이들은 **Tier 3 의 7개 키워드 세트 어디에도 매칭되지 않는** 객체들이다.

---

## 5. 출력 컬럼 결정 로직 (`BuildDynamicColumns`)

```csharp
var columns = new List<string>(MetaColumns);  // 5개 메타

var propertyKeys = new SortedSet<string>(StringComparer.OrdinalIgnoreCase);
foreach (var objData in objectDataMap.Values)
{
    foreach (var key in objData.Keys)
    {
        if (key.StartsWith("__")) continue;   // __ 접두사 메타 키 제외
        propertyKeys.Add(key);
    }
}

columns.AddRange(propertyKeys);

if (columns.Count > 16384)  // XLSX 한도
    columns = columns.Take(16384).ToList();
```

**결과**: 2026-04-07 스냅샷에서 메타 5 + 속성 130 = 총 **135 컬럼**.

---

## 6. `FindKey` — 속성 키 검색 유틸리티

요약 시트(Pipeline_Summary, Equipment_Summary, PipeRun_Detail) 작성 시 사용된다.

```csharp
// 1) 정확 매칭 (대소문자 무시)
var exact = columns.FirstOrDefault(k => k.Equals(hint, StringComparison.OrdinalIgnoreCase));

// 2) "Category|PropertyName" 의 PropertyName 부분 매칭
var partial = columns.FirstOrDefault(k =>
{
    int barIdx = k.IndexOf('|');
    return barIdx >= 0 && k.Substring(barIdx + 1).Equals(hint, StringComparison.OrdinalIgnoreCase);
});
```

예: `FindKey(columns, "Pipeline")` → `SmartPlant 3D|Pipeline` 의 `Pipeline` 부분 매칭으로 선택.

**함의**: 요약 시트는 "첫 번째로 매칭되는 Pipeline 컬럼" 만 사용한다. 만약 여러 카테고리가 `Pipeline` 이라는 이름의 속성을 가지면 **하나만 쓰이고 나머지는 무시됨**. 이것이 147 vs 157 pipeline 차이의 원인일 가능성.

---

## 7. XLSX 출력의 알려진 제한

### 7.1 손실 컬럼

| 컬럼 | 이유 | 영향 |
|------|------|------|
| `ParentId` | `__` 접두사 메타 키는 출력에 제외됨 | **계층 구조 재구성 불가** — AllProperties CSV 에서 조인 필요 |
| `__SysPath` 의 초기 빈 값 | 수집 도중 비어있지 않은 값으로 갱신되지만, 객체의 초기 위치에 따라 다를 수 있음 | 소수 케이스 |

### 7.2 중복 속성 키 (multi-category collision)

Navisworks 에서 같은 PropertyName 을 여러 Category 가 가질 수 있다.
예: `SmartPlant 3D|Pipeline` 과 `Item|Pipeline`.

둘 다 컬럼으로 출력되지만, **summary 시트의 `FindKey` 로직은 하나만 선택**한다.
그래서 Pipeline_Summary 가 147개인 반면, 메인 Pivot 에는 157개 distinct pipeline 값이 존재할 수 있다.

### 7.3 정렬 불안정성

- Excel 행 순서는 `Dictionary<Guid, ...>` 의 enumeration 순서에 의존한다.
- .NET `Dictionary` 는 삽입 순서를 대체로 유지하지만 보장되지 않는다.
- **행 순서에 의존하지 말 것**. Primary key 로 항상 `ObjectId(GUID)` 를 사용해야 한다.

### 7.4 타입 strictness

모든 값이 **문자열**로 저장된다 (`ws.Cell(r, c).Value = string`).
→ Foundry 로 넘길 때 **명시적 타입 캐스팅**이 필수이다.
→ `Level` 컬럼도 문자열 (`"7"`, `"8"`) 이므로 INTEGER 로 캐스팅해야 한다.

### 7.5 일부 시트 non-생성

Pipeline/Equipment/PipeRun 속성이 없으면 해당 시트는 **아예 생성되지 않는다**.
2026-04-07 스냅샷에서는 5개 모두 생성되어 있음을 확인.

---

## 8. Python 재구현 체크리스트

`src/bimkg/ingest/xlsx_classifier.py` 에서 다음을 구현해야 한다:

- [ ] `clean_display_string(value: str) -> str` — `DisplayString:` 접두사 제거
- [ ] 상수 7개: `PIPING_KEYWORDS`, `EQUIPMENT_KEYWORDS`, `STRUCTURE_KEYWORDS`, `ELECTRICAL_KEYWORDS`, `HVAC_KEYWORDS`, `INSTRUMENTATION_KEYWORDS` (C# 코드와 1:1)
- [ ] `infer_class(properties: dict[str,str], sys_path: str, display_name: str) -> str`
  - Tier 1: `Class` 또는 `ClassDisplayName` 이름을 가진 속성 검색
  - Tier 2: 속성 키에 `pipeline`/`piperun`/`piping` 또는 `equipment`/`eqp type` 포함 여부
  - Tier 3: combined 문자열에서 키워드 7세트 순차 검색
  - 기본값: `"Other"`
- [ ] Oracle 테스트: `test_xlsx_classifier.py`
  - AllProperties CSV 에서 136 컬럼 로드
  - 행별로 `infer_class()` 호출
  - XLSX `Class` 컬럼과 12,009 건 비교
  - 기대: 100% 일치
  - 실패 시 불일치 건 리포트

---

## 9. 우리가 override 할 가능성이 있는 지점

XLSX 분류를 일반적으로 신뢰하되, 다음 케이스는 **플래그로 별도 표시**해야 한다:

| 케이스 | 처리 |
|--------|------|
| Insulation Volume 145건 (Piping 83 / Other 41 / HVAC 20 / Equipment 1) | `is_analysis_volume=True` — 원래 클래스 유지하되 그래프 참여 제외 |
| MeshQuality=`skipped_container` 객체들 | `is_container=True` — 원래 클래스 유지 |
| MeshQuality=`box_placeholder` 객체들 (계층 노드) | `is_bbox_placeholder=True` |
| Generic "Geometry" 이름 41건 (Other) | 별도 플래그 없이 Uncategorized 로 남김 |

이 플래그들은 `refined_class` 를 **덮지 않고** 보조 상태 컬럼으로 존재한다. 사용자가 원하면 언제든 원본 XLSX 분류로 roll-back 가능.

---

## 10. 참고 링크

- C# 원본: https://github.com/tygwan/DXTnavis/blob/main/Services/RefinedXlsxExporter.cs
- Phase 1a 설계 문서: `docs/analysis/phase-1a-data-realignment-design.md`
- Phase 1b 단위 파서: `src/bimkg/ingest/unit_parser.py`
