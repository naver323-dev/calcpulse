# CalcPulse — P1 실전 가이드·계산기 허브

무료 스택(Astro 정적 빌드 + Cloudflare Pages)으로 돌리는 **트래픽 엔진**입니다.
2차 3자 토론 문서의 P1(1순위 가동) 중 **1개월 1~2주차 뼈대**에 해당합니다.

- 브랜드: **CalcPulse**
- 도메인(임시): `https://calcpulse.pages.dev` (`SITE_URL` 환경변수로 교체)
- **광고 없음. 결제 없음. 쿠키 없음.** 계산기는 전부 브라우저 안에서만 연산합니다.

## 수익화 방침 (2026-11-17 사용자 확정)

| 항목 | 결정 |
| --- | --- |
| AdSense | **사용하지 않음.** 스크립트·광고 슬롯·`ads.txt`·승인 절차 전부 제외 |
| 제휴 링크 | 사용. 승인된 프로그램만, 링크 옆에 `rel="sponsored nofollow"` + 고지 |
| P2 볼트(Gumroad) | 내부 업셀 CTA로 유입. 결제는 Gumroad 도메인에서만 일어남 |
| P3 CSV(Gumroad) | 같은 Gumroad 계정의 두 번째 상품군 — P1은 유입만 담당 |
| 정산 축 | **Gumroad 단일** (한국 개인 계좌 KRW 정산). Lemon Squeezy는 신규 가입이 닫혀 제외 |

수익 동선은 두 곳에만 존재합니다.

1. 가이드 본문/하단의 **오퍼 슬롯** — `src/components/OfferSlot.astro`, 설정은 `src/data/monetization.ts`
2. 가이드 사이의 **내부 왕복 링크** — 서로 다른 계산기로 이어지는 문맥 링크

`monetization.ts`에서 `url`이 비어 있는 오퍼는 **렌더링되지 않습니다.** 제휴 승인 전 링크가
그럴듯하게 박혀 나가는 일을 막기 위한 장치이고, 그래서 지금 배포해도 죽은 링크가 없습니다.

---

## 1. 지금 들어 있는 것

| 구성 | 상태 |
| --- | --- |
| Astro 7 + Tailwind 4 정적 사이트 | `npm run build` 오류 0 |
| 공통 레이아웃(SEO·canonical·OG·JSON-LD·favicon) | 완료. 외부 스크립트 0개 |
| 실전 가이드 + 내장 계산기 3종 | 완료 (아래 표) |
| `/llms.txt`, `/sitemap.xml`, `/robots.txt` | 엔드포인트로 자동 생성 (도메인 하드코딩 없음) |
| 금칙어·구조·광고태그 배포 가드 | `scripts/forbidden_terms.py` |
| 계산기 산술 단위 테스트 15개 | `scripts/test_calculations.ts` |
| 계산기 DOM 배선 테스트 4개 | `scripts/test_dom.mjs` |
| 파이프라인 오프라인 테스트 18개 | `scripts/test_pipeline.py` (npm test에 포함) |
| 배포 | Cloudflare Pages **Git 연동** — `main` 푸시가 곧 배포 (워크플로 불필요) |
| 일일 생성 워크플로 | `.github/workflows/daily-guide.yml` (KST 10:15 + 수동 실행) |
| 오퍼 슬롯(제휴·P2 유입) | `src/data/monetization.ts` + `OfferSlot.astro` |
| P2 볼트 페이지 `/vault/` | 무료 샘플 3종(프롬프트 2 + 파이썬 1) 전문 공개 + $14/$5 안내 + Gumroad 링크(환경변수) |
| P3 데이터셋 페이지 `/datasets/` | 이번 주 실측 6개 시리즈 표 + 샘플 CSV 다운로드 + 컬럼 사전 + $9 팩 안내 + Dataset JSON-LD |

### 발행된 가이드

| 경로 | 계산기 | 입력 → 출력 |
| --- | --- | --- |
| `/guides/ai-api-cost-calculator/` | LLM API 원가 계산기 | 일 요청 수, 입·출력 토큰, 100만 토큰당 단가, 캐시 적중률, 재시도율 → 월 청구액·요청당 원가·1,000건당 원가·항목별 분해 |
| `/guides/payment-fee-calculator/` | 결제 수수료 계산기 | 월 결제 건수, 평균 결제액, % 수수료, 건당 고정 수수료, 환불 비율, 월 플랫폼 요금 → 월 수수료, 순매출, 실효 수수료율, 건당 수수료 |
| `/guides/saas-break-even-calculator/` | SaaS 손익분기/ROI 계산기 | 좌석 수, 좌석당 월 요금, 초기 도입비, 좌석당 월 절감시간, 시급, 실제 주간 사용률 → 회수 개월, 월 순편익, 12개월 ROI, 손익분기 좌석수 |

계산 로직은 `src/lib/calculations.ts` 한 곳에 있고, 페이지는 그 결과만 표시합니다.
산술을 바꾸면 테스트가 먼저 깨지도록 설계했습니다.

### 오퍼 슬롯에 지금 연결된 것

| 오퍼 | 상태 | 링크 |
| --- | --- | --- |
| `vault` (P2 볼트) | 활성 | `/vault/` 내부 유입 — 무료 샘플이 있는 페이지에서 Gumroad로 이동 |
| `csv` (P3 오픈데이터) | 활성 | `/datasets/` 내부 유입 — 무료 샘플 표·CSV에서 $9 팩으로 이동 |
| `stackverdict` (자체 사이트) | 활성 | `https://stackverdict-two.vercel.app` — **배포 전 실제 공개 URL 확인 필요** |
| `make` (제휴) | 활성, **URL 미설정 → 화면에 나오지 않음** | 프로그램 승인 후 `url` 입력 |

### /vault/ 페이지와 Gumroad 링크

볼트 상품 페이지는 `src/pages/vault.astro`입니다. 무료 샘플 3종은 상품 빌드의 파일을
그대로 복사해 `src/data/vault-samples/`에 두고 `?raw`로 읽습니다(내용을 손으로 옮겨 적지
않으므로 판매용 파일과 화면 문구가 어긋날 수 없습니다).

- `npm run sync:samples` — 상품 빌드(`../p2-ai-vault`)에서 샘플 3종을 복사
- `npm run test:samples` — 사본이 상품 빌드와 같은지 SHA-256 비교(`npm test`에 포함).
  상품 빌드가 없는 체크아웃에서는 skip하고 통과합니다.

결제 링크는 **Cloudflare Pages → Settings → Environment variables**의
`PUBLIC_GUMROAD_VAULT_URL`(빌드 시점 값)로만 들어갑니다.

| 환경변수 | 화면 |
| --- | --- |
| 미설정 | "On sale shortly" 안내 + 무료 샘플. 죽은 `href=""`가 나가지 않음 |
| `https://…gumroad.com/l/…` | 상단·가격 섹션 버튼이 Gumroad로 연결되고 Product JSON-LD가 켜짐 |

> **2026-11-17 설정 완료.** Cloudflare Pages `calcpulse` 프로젝트의 Production 환경변수에
> `PUBLIC_GUMROAD_VAULT_URL`·`PUBLIC_GUMROAD_DATASET_URL`을 등록하고 재배포했습니다.
> 프로덕션에서 두 링크가 실제로 살아 있는 것을 확인했습니다(아래 라이브 URL).

가드(`scripts/forbidden_terms.py`)는 `href=""`·`href="#"`를 배포 실패로 처리하므로,
링크 유무 두 상태를 모두 명시적으로 렌더링합니다.

### /datasets/ 페이지와 무료 샘플

`src/pages/datasets.astro`는 P3 파이프라인(`../p3-opendata-diff`)이 실제로 수집한 값으로
채워집니다. 손으로 옮겨 적지 않습니다.

- `src/data/dataset-sample.json` — 파이프라인이 `python3 -m pipeline.export_site_sample`로
  생성한 6개 시리즈 스냅샷(라벨·최신값·전주값·증감률·z-score·이상치 플래그).
- `public/datasets/calcpulse-open-data-sample-<week>.csv` — 같은 6행의 실제 CSV(20컬럼 전부).
- 주 1회 팩을 만들 때 이 두 파일을 갱신하고 커밋하면 페이지가 그 주 숫자로 바뀝니다.
- 결제 링크는 `PUBLIC_GUMROAD_DATASET_URL`(빌드 시점)로만 들어가고, 미설정이면
  "Gumroad listing opens with the first shipped pack" 안내와 샘플만 렌더링합니다.

### 라이브 URL (2026-11-17 게시)

| 대상 | URL | 가격 |
| --- | --- | --- |
| Gumroad 스토어프론트 | `https://calcpulse.gumroad.com` | — |
| P2 볼트 (2티어: Complete bundle / Starter) | `https://calcpulse.gumroad.com/l/ai-workflow-vault` | $14 / $5 |
| P3 주간 오픈데이터 팩 (2026-W47) | `https://calcpulse.gumroad.com/l/calcpulse-opendata-weekly` | $9 |
| 사이트 P2 페이지 | `https://calcpulse.pages.dev/vault/` | — |
| 사이트 P3 페이지 | `https://calcpulse.pages.dev/datasets/` | — |

판매자 표기는 **CalcPulse** / **CalcPulse Editorial Team**만 사용하며, 공개 프로필·상품 페이지에
개인 실명이나 닉네임은 넣지 않습니다.

---

## 2. 로컬 실행·검증

```bash
export PATH=/workspace/.local/node/bin:$PATH   # 이 환경의 node 24 위치
npm install
npm run build          # 정적 빌드 → dist/
npm run test:calc      # 계산 산술 테스트 10개
npm run test:dom       # 빌드 산출물의 계산기 배선 테스트 3개
npm run guard          # 금칙어 + 필수 페이지 + 광고태그/카드필드 검사
npm test               # 위 4개를 순서대로 한 번에
```

2026-11-17 기준 실제 실행 결과:

```
11 page(s) built in 3.4s
15 checks passed
4 DOM checks passed
checked 11 pages in dist
PASS: no forbidden topics, all required pages present
18 pipeline checks passed
```

`npm run guard`는 다음을 막습니다: 금칙 주제(국방·군수·방산·조달 등) 단어, 필수 페이지 누락,
canonical 누락, 광고 네트워크 태그(`googlesyndication` 계열), 카드 입력 필드, 미설정 플레이스홀더.

---

## 3. 배포에 필요한 입력 (사람 확인 필요)

**외부 계정은 하나도 만들지 않았습니다.** 아래는 배포를 위해 필요한 것입니다.

| # | 필요한 것 | 왜 필요한가 | 비용 |
| --- | --- | --- | --- |
| 1 | Cloudflare 계정 + Pages 프로젝트 | 정적 호스팅(빌드 500회/월, 파일 2만 개, 파일당 25MiB, 대역폭 무제한) | 0원 |
| 2 | GitHub 저장소 | Pages 자동 배포 + Actions 무료 | 0원 |
| 3 | Gumroad 개인 계정 | P2·P3 결제·정산 단일 축. P1은 링크만 걸므로 P1 단독 배포에는 불필요 | 0원 |
| 4 | (선택) 도메인 | **광고를 하지 않으므로 필수가 아님.** `*.pages.dev`로도 제휴·유입 동선은 그대로 작동 | 0원 (사용 안 함) |

> 도메인은 AdSense를 쓸 때만 필요했습니다. 광고를 빼기로 했으므로 **0원 원칙이 그대로 유지**됩니다.
> 대신 후속 판단 하나가 남습니다: `*.pages.dev`는 검색엔진·AI 인용에는 문제가 없지만,
> 사이트 신뢰 신호(브랜드 도메인)와 제휴 프로그램 심사에서 다소 불리할 수 있습니다.

### 배포 절차

1. `git init` → GitHub에 저장소 생성 후 push
2. Cloudflare 대시보드 → Workers & Pages → Pages → Git 연결 → 빌드 명령 `npm run build`, 출력 `dist`
3. 환경변수 `SITE_URL` 설정(없으면 `https://calcpulse.pages.dev` 사용). 커스텀 도메인을 붙이면
   그 주소로 바꿔 재배포 — canonical·sitemap·llms.txt가 이 값을 씁니다
4. Search Console·네이버 서치어드바이저에 `sitemap.xml` 제출
5. `src/data/monetization.ts`의 빈 `url`을 채워 오퍼 슬롯 활성화 (제휴 승인 후)

---

## 4. 일일 자동 수집·생성·배포 파이프라인 (2주차)

매일 KST 10:15에 GitHub Actions(`.github/workflows/daily-guide.yml`)가 1회 실행되어
가이드 1편을 만들고, 모든 검증을 통과한 경우에만 `main`에 커밋·푸시합니다. 푸시가 곧
Cloudflare Pages 배포입니다.

| 단계 | 파일 | 하는 일 |
| --- | --- | --- |
| 수집 | `scripts/collect_topic.py` | Hacker News(Algolia)·GitHub·Google Trends에서 주제 1건 선정. 요일 로테이션으로 세 주제(AI 원가 / SaaS·툴 / 생활금융)를 돌아가며 쓰고, 이미 발행한 슬러그·제목·키워드·출처 URL과 겹치면 버립니다 |
| 생성 | `scripts/generate_guide.py` | 3단 무료 폴백 체인(`scripts/llm_fallback.py`)으로 JSON 초안 작성: Gemini(`gemini-3.8-flash` → `gemini-3.5-flash-lite`) → Groq(`openai/gpt-oss-120b` → `openai/gpt-oss-20b`) → OpenRouter(`nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-26b-a4b-it:free`). 검증 실패 시 1회 수정 요청 |
| 검증 | 같은 파일 | 슬러그·길이·문단·FAQ 구조, 링크 금지, Astro를 깨는 문자 금지, 그리고 `scripts/forbidden_terms.py`의 금칙어 목록을 **그대로 import**해 사전 차단 |
| 렌더 | `src/pages/guides/<slug>.astro` + `src/data/guides.ts` | 실제 사이트 구조 그대로 생성. 주제에 맞는 계산기 컴포넌트를 본문에 넣고, StackVerdict 링크와 다른 계산기 가이드 내부 링크를 붙입니다 |
| 게이트 | `npm test` | 빌드 + 산술 + DOM + 금칙어 가드 + 파이프라인 테스트. 실패하면 생성 파일을 되돌리고 커밋하지 않습니다 |
| 발행 | `git commit` → `push` | `--publish`일 때만. 커밋 메시지는 가이드 제목 |

무료 한도 보호: 한 티어가 429/쿼터로 막히면 다음 티어가 이어서 씁니다. **모든** 티어가
쿼터로 막혔을 때만 **그날 건너뛰기(exit 0)**로 끝나고, 키가 틀렸거나 서비스가 죽은 경우는
종료코드 3으로 드러납니다. 1회 실행 최대 1편, 하루 1편 상한은 `scripts/pipeline_state.json`이 기억합니다.

### 3단 무료 폴백 체인 (`scripts/llm_fallback.py`)

| 순서 | 티어 | 필요한 값 | 무료 조건(2026-11-17 확인) |
| --- | --- | --- | --- |
| 1 | Gemini (Google AI Studio) | `GEMINI_API_KEY` | Flash 계열 무료 등급 |
| 2 | Groq (`https://api.groq.com/openai/v1`) | `GROQ_API_KEY` | gpt-oss-120b/20b: 30 RPM, 1,000 RPD, 8K TPM, 200K TPD. **카드 불필요** |
| 3 | OpenRouter (`https://openrouter.ai/api/v1`, `:free` 모델) | `OPENROUTER_API_KEY` | :free 모델은 입력·출력 단가 $0. **카드 불필요**(크레딧 0으로도 동작). 2026-11-17 실호출 확인: `nvidia/nemotron-3-ultra-550b-a55b:free`, `google/gemma-4-26b-a4b-it:free` |

- 세 키 중 **하나만 있어도** 생성됩니다. 없는 티어는 조용히 건너뜁니다.
- 429/쿼터 → 다음 모델 → 다음 티어. 401/403(키 오류) → 그 티어만 포기하고 다음 티어.
  404/410(모델·엔드포인트 종료) → 다음 모델. 5xx/타임아웃 → 1회 재시도 후 다음 티어.
- 답이 JSON이 아니면 그 모델은 버리고 다음으로 넘어갑니다. 초안 검증기는 그대로 최종 관문입니다.
- 발행 기록의 `model` 값이 `groq:openai/gpt-oss-120b`처럼 **어느 티어가 쓴 글인지** 남깁니다.
- Groq은 Cloudflare 뒤에 있어 Python 기본 User-Agent(`Python-urllib/3.x`)를 403(1010)로 막습니다.
  모듈이 자체 User-Agent를 보냅니다.
- gpt-oss 계열은 추론 토큰을 답변 예산에서 씁니다. `GROQ_REASONING_EFFORT`(기본 `medium`)로
  조절하고, 출력 상한은 TPM 8K 보호를 위해 4,096 토큰으로 낮춰 둡니다.

```bash
python3 scripts/llm_fallback.py --check   # 지금 어느 티어가 살아 있는지 (발행 없음)
```

3번 티어는 OpenRouter의 `:free` 모델입니다. 입력·출력 단가가 0으로 고정돼 있고 크레딧을
충전하지 않아도 호출되므로(잔액 $0, 카드 없음) 과금 위험이 없습니다. 무료 풀은 붐빌 때
upstream 429를 돌려주는데, 그때는 다음 모델(`gemma-4-26b-a4b-it:free`)로 넘어갑니다.

- GitHub Models는 2026-07-30자로 서비스가 종료되어 기본 순서에서 뺐습니다. `GITHUB_MODELS_*`
  변수를 쓰는 OpenAI 호환 슬롯은 코드에 남아 있어 `LLM_PROVIDERS`로 되살릴 수 있습니다.
- Cerebras는 키를 만들어도 콘솔이 "API access isn't active yet"이라 카드 등록을 요구합니다.
  그래서 기본 순서에 넣지 않았고, 카드를 넣기로 하면 `CEREBRAS_API_KEY`만 추가하면 됩니다.
- `LLM_PROVIDERS`(예: `gemini,groq`)로 순서를 줄이거나 바꿀 수 있습니다.

로컬 명령:

```bash
python3 scripts/collect_topic.py                 # 오늘의 주제만 확인
python3 scripts/generate_guide.py --collect-only # 수집까지
python3 scripts/generate_guide.py --dry-run      # API 없이 픽스처로 렌더+게이트 후 되돌리기
python3 scripts/generate_guide.py --publish      # 실제 발행(커밋·푸시)
python3 scripts/generate_guide.py --self-test    # 검증기 자체 테스트
```

계산기는 세 개입니다: LLM API 원가, SaaS 손익분기/ROI, 결제 수수료. 각 주제가 정확히
하나의 계산기와 짝을 이뤄, 생성되는 가이드는 항상 "계산기가 붙은 페이지"가 됩니다.

## 5. 이번 단계에서 확인한 외부 사실

검증 결과는 `NOTES-verification-2026-11-17.md`에 출처 링크와 등급(공식/3자/커뮤니티)과 함께 정리했습니다.

- **Lemon Squeezy는 2026-11-16부로 신규 가입을 닫았습니다.** 2027-03-31 서비스 종료.
  P2 결제 축에서 제외하고 Gumroad 단일 축으로 갑니다.
- LS가 권하는 대체 경로(Stripe Managed Payments)는 **한국 사업자 미지원**입니다.
- **Gumroad는 한국 개인 가입·KRW 은행 정산이 가능**합니다(직접판매 10% + $0.50, Discover 30%).
  최소 정산액은 공식 문서 안에서 `KRW 40,000`과 `$100`이 충돌해 미확정입니다.
- **AdSense는 `pages.dev` 서브도메인을 승인하지 않습니다.** 광고를 빼기로 한 결정과 별개로,
  나중에 광고를 검토한다면 도메인이 선행 조건입니다.
- Cloudflare 약관 §2.7에 카드 입력·결제 금지 조항은 없습니다. "카드 입력창 금지"는 약관이 아니라
  PCI DSS 범위를 만들지 않기 위한 실무 원칙입니다.
