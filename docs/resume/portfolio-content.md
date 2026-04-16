# 이력서 포트폴리오 콘텐츠

> Notion 이력서 페이지에 삽입할 콘텐츠의 source of truth.
> 기술스택 (Type B) + 프로젝트 요약 (7줄 × 4 = 28줄) + 블로그 유도 링크.
>
> 작성일: 2026-04-16

---

## 기술 스택

### Language

**Python** — 능숙합니다
for/while 반복, list/dict comprehension, class·decorator 설계, 예외 처리, 정규표현식 패턴 매칭을 사용합니다. pytest로 단위·통합 테스트를 작성하고, typing으로 타입 힌트를 적용합니다.

**C#** — 익숙합니다
클래스·인터페이스 설계, LINQ 쿼리, async/await 비동기 처리, NuGet 패키지 관리를 수행합니다. .NET 기반 데스크톱 플러그인을 구현합니다.

### Data Processing

**pandas** — 능숙합니다
DataFrame 필터·그룹·조인, Parquet/CSV I/O로 데이터 정제를 수행합니다. ydata-profiling으로 품질 리포트를 생성합니다.

**SQL** — 능숙합니다
SELECT/JOIN/GROUP BY 집계, CTE, 윈도우 함수, FTS5 전문검색을 작성합니다.

### Semantic Web & Graph

**RDF / OWL / SPARQL** — 익숙합니다
트리플 패턴 매칭, OPTIONAL, FILTER, CONSTRUCT 그래프 변환으로 온톨로지를 질의합니다. rdflib로 OWL 클래스 계층을 설계합니다.

**SHACL** — 익숙합니다
shape 제약 정의, severity 정책 설계, pySHACL로 자동 검증 게이트를 운영합니다.

**Neo4j / Cypher** — 익숙합니다
MATCH-WHERE-RETURN 패턴, 다중 hop 경로 탐색, MERGE upsert, CSV import로 그래프를 구축·질의합니다.

### AI · ML · LLM

**PyTorch** — 익숙합니다
학습·평가 루프 구성, ResNet 등 사전학습 모델 fine-tuning, 데이터로더·증강 파이프라인을 구축합니다.

**LangGraph / LangChain** — 익숙합니다
ReAct 에이전트 구성, tool 정의, 상태 그래프 설계, LLM 어댑터 교체로 LLM-agnostic 에이전트를 만듭니다.

**OpenCV** — 익숙합니다
이미지 전처리, 컨투어 추출, 색상 변환, 마스크 연산으로 비전 파이프라인을 구성합니다.

### Backend

**FastAPI** — 익숙합니다
@app.get/@app.post 엔드포인트, Pydantic 모델 검증, 의존성 주입, Swagger 자동 문서를 구성합니다.

### Desktop & UI

**WPF / XAML** — 익숙합니다
MVVM 패턴, 데이터 바인딩, UserControl 설계로 데스크톱 대시보드를 구현합니다.

### Workflow & Infra

**Airflow** — 경험이 있습니다
DAG 정의, PythonOperator, Asset 의존성, dataset-aware scheduling을 설정합니다.

**Docker** — 경험이 있습니다
Dockerfile 작성, docker-compose, volume mount, 네트워크 구성을 합니다.

**Git** — 능숙합니다
branch 전략, rebase, conflict 해결, cherry-pick, reflog 복구를 수행합니다.

### Cloud & Platform

**Palantir Foundry** — 경험이 있습니다
Object/Link Type 업로드, dtype 호환 이슈 해결, Ontology Manager 구성을 수행합니다.

---

## 프로젝트 (7줄 × 4 = 28줄)

---

### 📊 보행자 안전 위험요소 프로파일링 (설문연구)

*2023.05 ~ 2023.11 · 1저자 · 80% 주도*

건설현장 인근 보행자 사고의 공식 통계 부재를 사진 300장 × 42인 설문 프로그램 자체 개발로 12,600건 응답 데이터셋 직접 구축

비모수 통계(Kruskal-Wallis) 분석으로 낙하물 4.21점 최상위 위험 정량 확인, 기존 연구가 간과한 '보행로 자체'를 최대 위험요소로 역발견하여 후속 VLM 연구의 기반 확보

1저자로 ICCEPM 2024 국제학회(삿포로) 발표, 전국대학생학술대회 최우수상 수상, 한국건설안전학회 논문 발표 달성

PySimpleGUI 기반 이미지 설문 프로그램 단독 설계·개발, 사진 300장 자동 랜덤 배치 및 5점 리커트 척도 응답 수집 자동화

Google 이미지 크롤링으로 건설현장 위험 사진 수집 후 연구자 교차 검수로 데이터 품질 확보

비모수 통계 분석(Kruskal-Wallis, Mann-Whitney U) 및 barrier wall 효과 분석으로 환경 요인별 위험 인식 정량화

`Python` `PySimpleGUI` `scipy` `pandas`

> 📝 **자세히 보기** → 기술 블로그 (예정)

---

### 👁 VLM-based Labeling Automation (컴퓨터비전)

*2024.02 ~ 2026.02 · 석사과정 1저자 · 80% 주도*

건설현장 보행자 위험요소의 수동 라벨링 비용(클래스당 수천 장)을 Florence-2 + SAM2 자동 파이프라인으로 클래스당 5장 수준까지 99% 절감

VLM의 도메인 특화 성능 한계(F1 52.56%)를 ResNet 기반 few-shot 필터링으로 F1 88.05%까지 35.49%p 향상, 4,959장 30분 내 처리

1저자 석사 논문 완성, Automation in Construction(SCIE) 투고 및 Applied Sciences(SCIE, 장애물 점유율 ρ=0.86) 게재 달성

Florence-2 open-vocabulary VLM으로 이미지 내 위험요소 탐지 후 SAM2 픽셀 단위 세그멘테이션으로 2단계 자동 라벨링 파이프라인 구현

autodistill 오픈소스 포크·확장으로 embedding_ontology 등 5개 모듈을 추가, 도메인 특화 라벨링 프레임워크 구축

ResNet 기반 few-shot 분류기로 VLM 출력 후처리, PyTorch 학습·평가 루프 및 OpenCV 이미지 전처리 파이프라인 구축

`Python` `PyTorch` `Florence-2` `SAM2` `OpenCV` `ResNet` `autodistill`

> 📝 **자세히 보기** → 기술 블로그 (예정)

---

### 🔧 DXTNavis

*2025.09 ~ 진행중 · 단독 개발 · 100% 단독*

플랜트 BIM 모델(SP3D)의 객체 데이터가 Navisworks 내부에 갇혀 분석 불가, C# 플러그인으로 12,009 객체 × 110,173 관계 자동 추출 구현

시공 시뮬레이션의 수동 설정 반복을 WPF 대시보드와 XLSX/RDF 자동 생성으로 원클릭 4D 시뮬레이션 환경 구축

추출 로직(InferClass)의 substring 매칭 버그를 regex negative lookahead로 수정, PR #3으로 오픈소스 기여 달성

Navisworks COM API를 C#/.NET으로 래핑, ModelItem 트리 순회 및 속성 추출 엔진 구현

WPF/XAML 기반 사용자 대시보드 설계, ClosedXML로 XLSX 자동 export(객체·관계·분류 시트)

RDF/SPARQL 기반 온톨로지 매핑 모듈 설계, Refinery 프로젝트 데이터 파이프라인과 연결

`C#` `.NET` `WPF` `XAML` `Navisworks API` `COM Interop` `ClosedXML` `RDF/SPARQL`

> 📝 **자세히 보기** → 기술 블로그 (예정)

---

### 🏭 Refinery Facility Ontology Analytics

*2025.07 ~ 진행중 · 단독 개발 · 100% 단독*

BIM 객체 분류 시 substring 매칭의 word boundary 부재로 Piping 997건(24.8%) 오분류, regex negative lookahead 적용 및 DXTnavis PR #3 기여로 근본 해결

정유시설 SP3D 12,009 객체의 비구조화 데이터를 Medallion 4계층 파이프라인과 OWL 온톨로지 설계로 477K triples · 261K edges 지식그래프 구축

시공 현장의 수동 SQL 질의 의존을 LangGraph 5-tool ReAct 에이전트와 FastAPI 12 endpoints 구현으로 자연어 설비 검색·KPI 조회 채널 실현

Bronze→Silver→Gold→Ontology Medallion 파이프라인에 Airflow 3.x DAG와 OpenLineage v2 ColumnLineage 적용으로 컬럼 단위 변경 추적 구현

SHACL 6 shapes 품질 게이트로 468 violations 자동 탐지, dev-standards R1~R11 자체 정립으로 팀 승계 가능한 작업 표준 구축

Foundry 10 datasets 업로드 및 6 Object Type 구성, PowerBI star schema와 Neo4j Docker 재현 가능 설정으로 다중 플랫폼 출력 완성

`Python` `pandas` `RDF/OWL` `SPARQL` `SHACL` `Neo4j` `LangGraph` `FastAPI` `Airflow` `Foundry`

> 📝 **자세히 보기** → [기술 블로그 · Refinery 시리즈](https://www.notion.so/3435a4e1f878804fb906eb605b53b975)

---

## 참조

- 기술스택 표현 참조: 이현섭 이력서 (hyunseob.github.io) — 문장 서술 + 숙련도 4단계 텍스트
- Notion 포트폴리오 DB: `fa6de2b4-3d69-47be-bc41-2ab8eaf4a8fa`
- 기술 블로그: <https://www.notion.so/3435a4e1f878804fb906eb605b53b975>
- dev-standards: <https://github.com/tygwan/dev-standards>
