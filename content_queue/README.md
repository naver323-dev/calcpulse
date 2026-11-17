# content_queue — 승인 원고 대기열 (CalcPulse)

피클 + 제미나이 + 그록봇이 **미리 만들어 승인까지 끝낸 가이드**를 여기에 넣어 둡니다.
매일 10:15 KST 파이프라인은 **여기서 먼저 꺼내 쓰고**, 오늘 낼 게 없을 때만 무료 공개
소스 수집 + 무료 LLM 파이프라인(`scripts/generate_guide.py`)으로 폴백합니다. 큐가 찬 날은
수집·생성이 0회라 Gemini/Grok 한도를 다음 배치에 씁니다.

## 파일 하나 = 가이드 하나

- 파일명: `<id>.json` (예: `cp-2026-11-20-01.json`)
- 하루 1편 상한(`pipeline_state.json`)은 큐에서 꺼낸 가이드에도 적용됩니다.
- 발행되면 파일은 그 커밋에서 삭제됩니다(발행 기록은 `scripts/pipeline_state.json`의 `model: queue:<id>`).
- 검수를 통과하지 못한 원고는 `content_queue/rejected/`로 옮겨지고 `rejected.reasons`에 사유가 붙습니다.
  뒤에 있는 원고는 막지 않습니다.
- 큐에서 꺼낸 원고도 `npm test`(빌드·계산기·DOM·금칙어·샘플)를 통과해야 커밋됩니다.

## 스키마

```json
{
  "schema": "content-queue/1",
  "id": "cp-2026-11-20-01",
  "created_at": "2026-11-18T23:40:00+09:00",
  "batch": "20261118-3way-a",
  "publish_after": "2026-11-20",
  "expires_at": null,
  "review": {
    "gemini": "approved 2026-11-18",
    "grok": "approved 2026-11-18 (compressed fact checkpoints)",
    "pickle": "validate_draft pass, no forbidden terms"
  },
  "payload": {
    "topic": {
      "family": "AI cost",
      "source": "Hacker News",
      "source_title": "Show HN: how we cut our LLM bill",
      "source_url": "https://news.ycombinator.com/item?id=0000000",
      "points": 42
    },
    "draft": {
      "slug": "llm-api-cost-calculator-small-teams",
      "title": "What a Small Team Actually Pays for LLM APIs",
      "h1": "...",
      "description": "One complete sentence, 60-160 characters.",
      "summary": "60-220 characters.",
      "lede": "...",
      "sections": [{ "heading": "...", "paragraphs": ["..."] }],
      "checklist": ["..."],
      "faq": [{ "q": "...", "a": "..." }],
      "keywords": ["...", "...", "..."],
      "minutes": 7,
      "topic": "AI cost"
    }
  }
}
```

- `topic.family`는 `AI cost` / `SaaS & tooling` / `Small-business finance` 중 하나여야 하고,
  `draft.topic`과 같아야 합니다(같은 계산기가 페이지에 붙습니다).
- `topic`은 페이지 하단에 인용되는 출처입니다. `source_url`은 실제로 열리는 `https://` 주소여야 합니다.
- 본문에 링크·금칙어·중복 슬러그가 있으면 `validate_draft`가 거부합니다(생성 원고와 같은 규칙).
- `publish_after` 이전에는 내보내지 않습니다. `expires_at`이 있으면 그날이 지난 뒤 거부됩니다.

## 넣기 전에 스스로 검사

```bash
python3 scripts/generate_guide.py --queue-validate   # 스키마 + 편집 규칙 + 중복 슬러그, 게시 없음
python3 scripts/generate_guide.py --queue-list       # 오늘 낼 수 있는 것 / 대기 중인 것
python3 scripts/generate_guide.py --no-queue         # (운영용) 큐를 건너뛰고 라이브 파이프라인만
```

`--queue-validate`가 0으로 끝나야 커밋하세요.
