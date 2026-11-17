# 외부 사실 검증 노트 — 2026-11-17

> **적용 결정(2026-11-17, 사용자):** "무과금(0원) 고수: AdSense 빼고 제휴·Gumroad 유입용으로만 돌릴게요."
> - AdSense: **사용하지 않음** (아래 6장의 AdSense 사실은 기록으로만 남김. 현재 사이트에는 광고 태그·슬롯·`ads.txt`가 없고, 가드가 재유입을 막음)
> - Lemon Squeezy: **제외** (신규 가입 불가)
> - 정산 축: **Gumroad 단일** (아래 3장)
> - 수익 동선: 제휴 링크 + P2·P3 Gumroad 유입 CTA (`src/data/monetization.ts`)

2차 토론 문서 9장이 "실행 전 확인 필요"로 남긴 항목을 공식 문서 기준으로 확인한 기록입니다.
**출처 등급**을 구분했습니다: `공식`(사업자 자체 문서), `3자`(독립 가이드·집계 사이트), `커뮤니티`(포럼 답변).

---

## 1. Lemon Squeezy — **신규 가입 불가 (전제 붕괴) → 결정: 제외**

| 항목 | 확인 결과 | 등급 |
| --- | --- | --- |
| 신규 가입 | **2026-11-16부로 신규 사용자·스토어 가입 중단** | 공식 |
| 서비스 종료 | 2027-03-31 결제 처리(구독 갱신 포함) 전면 중단. 연장 없음 | 공식 |
| 권장 대체 경로 | Stripe **Managed Payments**(MoR) | 공식 |
| 수수료(기존 계정) | 5% + 건당 $0.50 | 공식 |
| 정산 | 월 2회(1일·15일 생성, 14일·28일 지급), 13일 홀드, 최소 $50, PayPal은 USD 고정 | 공식 |
| 한국 정산 | 은행 정산 지원국 119개에 "Republic of Korea (ROK)" 포함 | 공식 |

- 출처: <https://www.lemonsqueezy.com/> (FAQ "Can I still sign up…" → No),
  <https://docs.lemonsqueezy.com/migration> (주요 일자 표),
  <https://docs.lemonsqueezy.com/help/getting-started/supported-countries>,
  <https://docs.lemonsqueezy.com/help/getting-started/getting-paid>
- **함의:** 2차 문서 P2의 "Lemon Squeezy(한국 개인 가입 가능) 또는 Gumroad" 전제는 성립하지 않습니다.
  한국 개인 조건을 검증할 대상 자체가 사라졌습니다(가입 자체가 닫힘).

## 2. Stripe Managed Payments — **한국 미지원**

- 지원 사업 소재지: CA, US + EU/EEA 다수 + AU, HK, JP, SG. **KR 없음.**
- 따라서 LS가 권하는 마이그레이션 경로를 한국 사업자·개인은 쓸 수 없습니다.
- 출처: <https://docs.stripe.com/payments/managed-payments/eligibility> (Supported business locations)
- 부가: Managed Payments는 PayPal 미지원, 스토어프런트·디지털 파일 배포·라이선스 키 미제공(직접 구현 필요).
  출처: <https://docs.lemonsqueezy.com/migration>

## 3. Gumroad — **한국 개인 가입·KRW 은행 정산 가능 (P2 대체 경로)**

| 항목 | 확인 결과 | 등급 |
| --- | --- | --- |
| 개인 가입 | 가능. **사업자등록 서류가 없으면 'Individual'** 선택(개인사업자 포함) | 공식 |
| 정산 방식(한국) | **한국 은행계좌로 KRW 지급** (PayPal 아님) | 공식 |
| 최소 정산액 | 표에는 `Korea — KRW (min 40,000)`, 본문에는 "최소 $100" 병기 → **두 서술이 불일치** | 공식(문서 내 불일치) |
| 정산 요일 | 한국 은행계좌는 **수요일** | 공식 |
| 수수료 | 직접 판매 **10% + $0.50**, Discover 경유 30%(처리비 포함), 월 $0 | 공식 |
| 카드 처리비 | 2.9% + $0.30이 10% 위에 별도 부과 — **3자 집계 기준. Gumroad 자체 페이지에서 이번 세션에 확인 못 함** | 3자 |
| 세금 | 2025-01-01부터 Gumroad가 MoR. 판매세·VAT 자동 처리, 세금 설정 불필요 | 공식 |
| 1099 | 미국 계정만 발급. 한국 계정은 대상 아님 | 공식 |
| W-8BEN | **Gumroad 공식 도움말에는 W-8BEN 요구 언급 없음.** 3자 가이드는 "요청될 수 있다"고만 서술 | 공식(부재 확인) / 3자 |
| KYC | Stripe가 생년월일·법적 성명·주소·국가 ID번호·신분증 사진·(경우에 따라) 거주 증빙 요구 | 공식 |
| 실효 수수료 | $9 상품 기준 약 $1.96(≈22%) → 실수령 $7.04. $29 상품은 약 84% 수령 | 3자 |

- 출처: <https://gumroad.com/help/article/13-getting-paid>,
  <https://gumroad.com/help/article/260-your-payout-settings-page>,
  <https://gumroad.com/help/article/15-1099s>, <https://gumroad.com/pricing>
- **함의:** P2 볼트의 결제 축은 Gumroad 단일 경로로 확정하는 것이 안전합니다.
  가격 설계 시 **고정비 $0.80(10% 중 $0.50 + 카드 $0.30)이 붙는 구조**라 $5~9 저가 상품은
  실수령이 70%대로 떨어집니다. 문서의 $14 평생 번들 가정은 유지 가능하지만,
  $5/월 구독은 실수령 기준으로 재계산이 필요합니다.

## 4. 대체 판매 채널 후보 — Paddle (백업)

- 한국은 Paddle **판매 지원국** 목록에 포함(KR, KRW, tax inclusive).
- 정산: 월 1회, 최소 $100, 은행 송금 또는 Payoneer, 일부 국가 $15 SWIFT 수수료.
- 제약: **소프트웨어·SaaS 계열 중심** 상품 심사. 승인 절차 별도.
- 출처: <https://developer.paddle.com/concepts/sell/supported-countries-locales>,
  <https://www.paddle.com/help/manage/get-paid/when-and-how-do-i-get-paid>
- 등급: 공식(판매 지원국·정산) / 3자(한국 사업자 온보딩 가능 여부)
- **함의:** Gumroad 계정이 거절될 경우의 2순위. 단, 개인(사업자 없음) 승인 가능성은 미확인.

## 5. Cloudflare Pages 무료 플랜 — 약관상 문제 없음 (단, 전제 수정)

| 항목 | 확인 결과 | 등급 |
| --- | --- | --- |
| 무료 한도 | 빌드 500회/월(동시 1), 파일 2만 개/사이트, 파일당 25MiB, 프로젝트 100개/계정, 커스텀 도메인 100개/프로젝트 | 공식 |
| 대역폭·요청 | 문서상 무료 플랜에 별도 상한 없음(정적 자산 기준) | 공식 |
| 약관 제한 | Self-Serve Subscription Agreement §2.7 Acceptable Use: (a) Cloudflare와의 오인 가능 제휴, (b) 침해·불법 콘텐츠, (c) 악성코드, (d) 피싱·스팸·기술적 남용, (e) 불법 활동. **카드 입력·결제 처리 금지 조항은 없음** | 공식 |
| CDN 조항 | 무료 CDN으로 **동영상·대용량 파일을 과도하게 서빙**하면 제한 가능(사전 통지 노력). 정적 HTML/JS 사이트는 해당 없음 | 공식 |
| SLA | 무료 서비스는 보증·배상 없음(§2.6) | 공식 |
| 무료 서비스 종료 | Cloudflare가 재량으로 중단 가능(§2.6) | 공식 |

- 출처: <https://developers.cloudflare.com/pages/platform/limits/>,
  <https://www.cloudflare.com/terms/> (§2.6, §2.7),
  <https://www.cloudflare.com/service-specific-terms-application-services/> (CDN 조항)
- **전제 수정:** 2차 문서의 "직접 카드 입력창 금지"는 **Cloudflare 약관 조항이 아닙니다.**
  약관에 그런 조항이 없고, 실제 근거는 **PCI DSS 범위 회피**입니다. Cloudflare는 자사 네트워크에
  대해 PCI DSS Level 1이지만 그 인증이 고객 사이트로 자동 확장되지 않습니다.
  출처: <https://developers.cloudflare.com/ssl/reference/compliance-and-vulnerabilities/>
- 결론: **정적 사이트 + 외부 체크아웃(Gumroad 등) 링크 이동 방식은 약관 위반 요소가 없습니다.**
  결제 페이지를 직접 만들지 않는 것은 약관 때문이 아니라 PCI 범위를 만들지 않기 위한 선택입니다.

## 6. AdSense — **`*.pages.dev`로는 승인 불가 (도메인 필수) → 결정: 사용하지 않음**

- AdSense는 **루트 도메인 소유** 또는 **퍼블릭 서펙스 리스트(PSL)에 등재된 플랫폼의 서브도메인**만
  사이트로 등록합니다. `pages.dev`는 PSL에 없어 `xxx.pages.dev`는 "남의 도메인 하위"로 취급됩니다.
- Google AdSense 커뮤니티(2026-02)에서도 `*.pages.dev` 사이트들이 연속 반려되었다는 보고와
  "서브도메인은 메인 도메인 소유자만 허용"이라는 전문가 답변이 확인됩니다.
- 출처: <https://support.google.com/adsense/answer/12169212> (사이트 소유·검증 절차),
  <https://support.google.com/adsense/thread/408524764/…> (커뮤니티, 등급: 커뮤니티),
  <https://realfin.dev/blog/adsense-new-static-site-setup/> (3자, 실제 신청 경험)
- 부가: EEA/UK/스위스 방문자에게 개인화 광고를 노출하려면 **Google 인증 CMP** 필요(2026년 기준 TCF v2.3).
  출처: <https://approvalens.com/guides/adsense-requirements-2026> (3자)
- **함의:** P1의 AdSense 경로는 **도메인 구매(연 $10~12)** 없이는 열리지 않습니다.
  도메인을 사지 않으면 P1 수익은 제휴 링크 + P2·P3 내부 업셀로 한정됩니다.

---

## 7. 이번 단계에서 확정하지 못한 것

1. **Gumroad의 카드 처리비 2.9% + $0.30 부과 여부** — 자체 요금 페이지에는 10% + $0.50만 표기.
   실제 계정의 Settings → Payments 화면에서 확인 필요(계정 생성 후).
2. **Gumroad 한국 최소 정산액** — 공식 문서 내 `KRW 40,000`과 `$100` 서술이 충돌.
3. **Paddle 개인(사업자 없음) 승인 가능성** — 공식 문서는 "소프트웨어 사업자"만 서술.
4. **Gemini 무료 등급 실제 일일 한도** — API 키 발급 후 AI Studio 한도 화면에서 확인(문서 값은 변동).
5. **AdSense 승인 확률** — 도메인 확보 후 신청해야 확인 가능. 1차 반려 시 3~4주 추가 소요.
6. **한국 세무 처리** — Gumroad MoR은 판매세만 처리하며, 국내 소득 신고 의무는 별도로 남습니다
   (개인 종합소득세 신고 대상 여부는 세무 전문가 확인 필요). 이 노트는 세무 조언이 아닙니다.
