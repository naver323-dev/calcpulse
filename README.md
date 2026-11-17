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
| 실전 가이드 + 내장 계산기 2종 | 완료 (아래 표) |
| `/llms.txt`, `/sitemap.xml`, `/robots.txt` | 엔드포인트로 자동 생성 (도메인 하드코딩 없음) |
| 금칙어·구조·광고태그 배포 가드 | `scripts/forbidden_terms.py` |
| 계산기 산술 단위 테스트 10개 | `scripts/test_calculations.ts` |
| 계산기 DOM 배선 테스트 3개 | `scripts/test_dom.mjs` |
| Cloudflare Pages 배포 워크플로 | `.github/workflows/deploy.yml` (시크릿 입력 전까지 비활성) |
| 오퍼 슬롯(제휴·P2 유입) | `src/data/monetization.ts` + `OfferSlot.astro` |

### 발행된 가이드

| 경로 | 계산기 | 입력 → 출력 |
| --- | --- | --- |
| `/guides/ai-api-cost-calculator/` | LLM API 원가 계산기 | 일 요청 수, 입·출력 토큰, 100만 토큰당 단가, 캐시 적중률, 재시도율 → 월 청구액·요청당 원가·1,000건당 원가·항목별 분해 |
| `/guides/saas-break-even-calculator/` | SaaS 손익분기/ROI 계산기 | 좌석 수, 좌석당 월 요금, 초기 도입비, 좌석당 월 절감시간, 시급, 실제 주간 사용률 → 회수 개월, 월 순편익, 12개월 ROI, 손익분기 좌석수 |

계산 로직은 `src/lib/calculations.ts` 한 곳에 있고, 페이지는 그 결과만 표시합니다.
산술을 바꾸면 테스트가 먼저 깨지도록 설계했습니다.

### 오퍼 슬롯에 지금 연결된 것

| 오퍼 | 상태 | 링크 |
| --- | --- | --- |
| `vault` (P2 볼트) | 활성, **URL 미설정 → 화면에 나오지 않음** | Gumroad 상품 생성 후 `url` 입력 |
| `stackverdict` (자체 사이트) | 활성 | `https://stackverdict-two.vercel.app` — **배포 전 실제 공개 URL 확인 필요** |
| `make` (제휴) | 활성, **URL 미설정 → 화면에 나오지 않음** | 프로그램 승인 후 `url` 입력 |

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
7 page(s) built in 2.24s
10 checks passed
3 DOM checks passed
checked 7 pages in dist
PASS: no forbidden topics, all required pages present
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
| 생성 | `scripts/generate_guide.py` | `gemini-3.8-flash` → 실패 시 `gemini-3.5-flash-lite`(무료 등급, Search 그라운딩 미사용). JSON 초안 → 검증 실패 시 1회 수정 요청 |
| 검증 | 같은 파일 | 슬러그·길이·문단·FAQ 구조, 링크 금지, Astro를 깨는 문자 금지, 그리고 `scripts/forbidden_terms.py`의 금칙어 목록을 **그대로 import**해 사전 차단 |
| 렌더 | `src/pages/guides/<slug>.astro` + `src/data/guides.ts` | 실제 사이트 구조 그대로 생성. 주제에 맞는 계산기 컴포넌트를 본문에 넣고, StackVerdict 링크와 다른 계산기 가이드 내부 링크를 붙입니다 |
| 게이트 | `npm test` | 빌드 + 산술 + DOM + 금칙어 가드 + 파이프라인 테스트. 실패하면 생성 파일을 되돌리고 커밋하지 않습니다 |
| 발행 | `git commit` → `push` | `--publish`일 때만. 커밋 메시지는 가이드 제목 |

무료 한도 보호: 429/쿼터 응답은 실패가 아니라 **그날 건너뛰기(exit 0)**로 끝납니다.
1회 실행 최대 1편, 하루 1편 상한은 `scripts/pipeline_state.json`이 기억합니다.

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
