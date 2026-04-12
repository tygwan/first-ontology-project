# Foundry Upload — pandas 2.x String Dtype 호환 이슈

**발견 일자**: 2026-04-13
**영향**: palantir-sdk 0.12 + pandas 2.2+ 조합에서 parquet 업로드 실패

---

## 문제

palantir-sdk 의 `Dataset.write_pandas()` 가 pandas 2.x 의 새로운 string dtype 을 인식하지 못함.

### 에러 메시지

```
ValueError: Unsupported dtype: <class 'str'>
```

또는

```
IndexError: index 0 is out of bounds for axis 0 with size 0
```

### 원인

3 가지 dtype 호환 문제:

| 문제 | pandas 2.x 동작 | palantir-sdk 기대 | 에러 |
|------|----------------|------------------|------|
| **String inference** | `future.infer_string=True` (기본값) → string 컬럼이 `str` dtype | `object` dtype | `Unsupported dtype: str` |
| **All-null columns** | object 컬럼이 전부 NaN | `_get_field()` 에서 첫 값 접근 시도 | `IndexError: index 0 out of bounds` |
| **Nullable Int64** | pandas extension type `Int64` | numpy `int64` or `float64` | `Unsupported dtype: numpy.object_` |

### palantir-sdk 내부 코드 (schema.py)

```python
def _get_field(name, obj):
    dtype = _get_generic_type(obj)
    ...
    if pd.api.types.is_object_dtype(dtype):
        if isinstance(obj[obj.index[0]], date):  # ← IndexError on all-null
            ...
        if pd.api.types.is_string_dtype(dtype):  # ← only matches object, not str
            return Field(name, StringFieldType())
    raise ValueError(f"Unsupported dtype: {dtype}")  # ← str dtype reaches here
```

## 해결

```python
# 1. 모듈 시작에서 전역 설정
import pandas as pd
pd.set_option("future.infer_string", False)

# 2. DataFrame 변환 함수
def fix_dtypes_for_foundry(df):
    for col in df.columns:
        if str(df[col].dtype) == "Int64":
            df[col] = df[col].astype("float64")
        elif df[col].dtype == object:
            if df[col].isna().all():
                df[col] = ""
            else:
                df[col] = df[col].fillna("")
    return df
```

### 구현

`src/bimkg/ingest/exporters/foundry_upload.py` 에 정리됨.

## 영향받는 버전

- pandas ≥ 2.2 (future.infer_string 기본값 변경)
- palantir-sdk 0.12.0 (str dtype 미지원)
- 향후 palantir-sdk 업데이트로 해결될 수 있음

## 참고

- pandas 2.2 release notes: "StringDtype is now the default dtype for string data"
- palantir-sdk GitHub: https://github.com/palantir/palantir-python-sdk
