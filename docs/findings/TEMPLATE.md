# YYYY-MM-DD — \<ID\> — \<Title\>

**Severity**: 🔴/🟠/🟡 CRITICAL/MAJOR/MINOR
**Status**: 🔄 Open | 🛠 Fixing | ✅ Resolved | 📋 Deferred | 🔭 Accepted
**Discovered by**: session / audit script / user / test
**Affects**: which Phase(s), which output files

---

## 1. Finding

한 문단으로 무엇을 발견했는지, 어떤 데이터 품질 이슈인지.

- 핵심 숫자 1~2개
- 어느 테이블/파일에서 발생했는지
- 영향 범위의 첫인상

## 2. Evidence

### 2.1 Reproducible audit

```bash
.venv/bin/python docs/findings/YYYY-MM-DD-ID-slug/audit.py
```

### 2.2 Data artifacts

`data/` 하위의 CSV 증거 파일 설명:

- `data/...csv` — (n rows × m cols): 의미 설명
- `data/...csv` — 집계/샘플 목적

### 2.3 Visualizations

`figures/` 하위의 차트 요약:

- ![title](figures/01_xxx.png) — 무엇을 보여주는지
- ![title](figures/02_xxx.png)

## 3. Analysis

### 3.1 Root cause

무엇이 이 이슈를 일으켰는지. 코드/데이터/설계 레벨에서.

### 3.2 Impact

어느 downstream phase가 영향받는지, 얼마나 많은 행/객체/edge에 영향있는지.

### 3.3 Related known issues

기존 findings 또는 문서의 어떤 기록과 연결되는지.

## 4. Resolution

### 4.1 Options considered

| 옵션 | 접근 | 장점 | 단점 | 시간 |
|------|------|------|------|------|
| 1 | ... | ... | ... | ... |

### 4.2 Selected approach

어떤 옵션을 선택했는지, 왜 그렇게 결정했는지.

### 4.3 Action items

- [ ] 구체 작업 1 — 담당/일정
- [ ] 구체 작업 2

### 4.4 Resolution commit

해결 후 이 섹션에 커밋 해시와 테스트 결과 기재.

## 5. References

- Source files: `src/bimkg/...`
- Tests: `tests/...`
- Related docs: `docs/analysis/...`
- External: DXTnavis issue/PR link if applicable
