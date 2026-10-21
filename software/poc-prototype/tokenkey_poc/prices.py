"""Published provider prices used by the cost model (USD per million tokens).

Sources (accessed 2026-10-19):
 [P1] Anthropic pricing: https://platform.claude.com/docs/en/about-claude/pricing
 [P2] Anthropic prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
      (5-min cache write = 1.25x base input, 1-hour cache write = 2x base input, cache read = 0.1x base input for the models below;
       minimum cacheable prompt 1,024 tokens for Sonnet, 4,096 for Opus/Haiku 4.5 per
       https://platform.claude.com/cookbook/misc-prompt-caching)
 [P3] OpenAI prompt caching (GPT-5.6 and later: write 1.25x, read 0.1x, min 1,024 tokens):
      https://developers.openai.com/api/docs/guides/prompt-caching
"""
PRICES = {
    # model: base input, 5m cache write, cache read, output, min cacheable tokens
    "claude-sonnet-4-6": dict(input=3.00, cache_write=3.75, cache_write_1h=6.00, cache_read=0.30, output=15.00, min_cache=1024, src="[P1][P2]"),
    "claude-opus-4-7":   dict(input=5.00, cache_write=6.25, cache_write_1h=10.00, cache_read=0.50, output=25.00, min_cache=4096, src="[P1][P2]"),
    "claude-sonnet-5":   dict(input=2.00, cache_write=2.50, cache_write_1h=4.00, cache_read=0.20, output=10.00, min_cache=1024, src="[P1][P2]"),
}
DEFAULT_MODEL = "claude-sonnet-4-6"   # model used in the Claude Code cost-doc /usage example
