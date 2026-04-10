# Phase 0: Project Bootstrap

**일자**: 2026-04-10
**담당 Task**: #1
**커밋**: `ddac7b4`

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| TOML | `pyproject.toml` | Python 패키지 메타데이터, 의존성 선언, pytest/ruff 설정 |
| Python | `src/bimkg/__init__.py` | 패키지 루트, `__version__` 상수 |
| Python | `src/bimkg/config.py` | 프로젝트 경로 상수 + 2026-04-07 스냅샷의 expected counts |
| Python | `tests/conftest.py` | pytest fixture (`project_root`, `data_raw_dir`, `sqlite_ro`) |
| Python | `tests/test_config.py` | config 모듈 sanity 테스트 3건 |
| Make | `Makefile` | install/test/lint/format/clean 타겟 |

**핵심 설계 결정**:
- `src/bimkg/` layout 채택 (`pyproject.toml`에서 `[tool.setuptools.package-dir]`로 설정)
- 스냅샷 상수 (`EXPECTED_OBJECT_COUNT=12009` 등)를 config에 박아서 테스트에서 검증 포인트로 활용
- `SQLITE_BIMKG = bimkg.db`를 별도로 정의해 기존 `dxtnavis-semantic.db` 보존 (Phase 1 변경이 기존 데이터 오염 방지)

---

## 2. 문제

**문제 #1**: `python3 -m venv .venv` 실행 실패
```
The virtual environment was not created successfully because ensurepip is not available.
```

---

## 3. 분석

우분투(WSL2) 기본 Python 설치에 `python3-venv` 패키지가 없어 `ensurepip` 모듈이 부재. 시스템에 `sudo apt install python3-venv`를 요구하는 상황이지만, 이는 권한 상승 작업이라 회피가 바람직.

대안 확인 결과 사용자 시스템에 `uv`(Rust 기반 Python 패키지 매니저)가 이미 설치되어 있음 (`/home/taegwan-dev/.local/bin/uv`).

---

## 4. 해결방안

`uv`를 사용해 venv 생성 및 의존성 설치:
```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
```

장점:
- `python3-venv` 시스템 패키지 불필요 (번들 Python 사용)
- pip보다 10-100배 빠른 설치 속도
- `pyproject.toml` `[project.dependencies]`를 그대로 해석

---

## 5. 결과

✅ `.venv/` 정상 생성 (`Python 3.12.3`)
✅ `uv pip install -e ".[dev]"` 성공 — streamlit, fastapi, rdflib, pyshacl, networkx, anthropic, pandas, pydantic, pytest, ruff 등 모든 의존성 설치 완료
✅ `pytest tests/` 3/3 통과:
```
tests/test_config.py::test_project_root_contains_pyproject PASSED
tests/test_config.py::test_data_raw_path_is_2026_04_07     PASSED
tests/test_config.py::test_expected_counts_are_positive    PASSED
```
✅ 모든 config 경로가 실제 파일로 해석됨 (`DATA_RAW`, `RAW_ALL_PROPERTIES`, `SQLITE_DB`, `POWERBI_DIR` 전부 `exists() == True`)
✅ GitHub 푸시 완료: `ddac7b4 Phase 0: Project bootstrap`
