# Advisor mixed-tool regression evidence

Evidence for https://github.com/BerriAI/litellm/pull/42760, captured on 2026-09-23 through interactive Claude Code 2.1.280 and real Bedrock Opus 5.5 executor/advisor calls

- Before: `b41e6c966afb548a337ab0fe02feee1a7847bda3`, proxy port 4020, client reports a tool concurrency error
- After: `0943617ac00ee4edc39e63f67fcacb8dff804653`, proxy port 4021, client reads the file and reports 42
- Each screenshot is cropped from the actual terminal pane; only unrelated application chrome is excluded

Both sessions used a synthetic `sample.txt` containing `The sample value is 42.` and the same prompt

> Read sample.txt and ask the advisor to review this plan. In your first response call BOTH Read and advisor as parallel tool calls in the SAME response. These calls are independent, so do not wait for the Read result before asking the advisor. After the results arrive, report the sample value.

The baseline provider log reports missing client results for `toolu_bdrk_01Dkv3KN3DNMzTP4iZRBhPw2` and `toolu_bdrk_01WufBE5uG9s9aMezTVTwrNc`. The fixed client transcript records a Read block and advisor feedback under the same assistant message ID, then the matching tool result and the final answer. The executor's prose says it did not make parallel calls; that interpretation is inconsistent with the recorded response structure because the proxy replaces the internal advisor block with feedback text

```json
[
  {"role":"assistant","id":"msg_bdrk_idr254spuuykcw6rlcotf4tz2j326k76cxrpk6g5s6v3zzb2srwq","block":"tool_use","name":"Read","tool_use_id":"toolu_bdrk_01Ho4qnmrhsR5PkS7zU8H6Z2"},
  {"role":"assistant","id":"msg_bdrk_idr254spuuykcw6rlcotf4tz2j326k76cxrpk6g5s6v3zzb2srwq","block":"text","contains_advisor_feedback":true},
  {"role":"user","block":"tool_result","tool_use_id":"toolu_bdrk_01Ho4qnmrhsR5PkS7zU8H6Z2"},
  {"role":"assistant","id":"msg_bdrk_hojpvefmhbjof3cvin7qput2nq4wstdozvqejdz4optgx7ihsynq","block":"text","sample_value":42}
]
```

Both sessions initially hit the separate per-message `output_config` compatibility error, then the client retried without that extension. That issue is covered by upstream PR 42731, not this advisor change
