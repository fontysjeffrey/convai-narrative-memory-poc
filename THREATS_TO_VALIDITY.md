# Threat model for the **Anchor → Flux** memory system

**Construct creep.** Are you measuring “memory drift,” or just the language the model believes people use when they say “yesterday / last year”? If prompts cue stereotypes about recall (hedging, vagueness), your effects can be prompt theater, not memory.

**Anchor leakage.** If the retelling can see the anchor verbatim (or its near paraphrase via retrieval), your “drift” collapses into style tweaks. If it sees prior retellings, you get a telephone game that measures compounding paraphrases, not decay.

**Instrumentation bias.** Your open LIWC‑ish features and affect‑arc are proxies. They’re great for *relative* differences, but they’re blind to meaning and fragile on short text. PVD is text‑values, not human values; sparse hits make Schwartz angles jittery and under‑voice some values, so “value drift” can be a counting artifact.

**Style ≠ content.** LSM and function words mostly track style. Rising “distance from anchor” could be the model shifting persona, not forgetting facts. If you don’t pair style drift with a factual accuracy score, you’ll over‑read noise as memory.

**Temporal stance proxies.** Past‑tense endings and time adverbs are crude; in Dutch they break differently, and translation washes signals. You can claim “more past focus,” while the model merely swapped discourse markers.

**Generation confounds.** Temperature, nucleus cutoffs, length penalties, stop words, and system prompt tweaks can swing your metrics more than the “elapsed time” factor. Lock seeds, models, and decoding, or you’ll chase ghosts.

**Stimulus bias.** If anchors are model‑written or topic‑skewed, base rates leak in. A security‑flavored anchor will naturally tilt PVD to Conservation even without any decay; mixing topics without blocking for theme makes “time” look powerful.

**Rehearsal effects.** If Flux retells from the last retelling rather than the anchor, you’re measuring *rehearsal drift*, not time decay. That’s a different construct and needs its own claim.

**Stats fragility.** You’re testing lots of features; something will look “significant” by accident. Retellings from the same anchor are not independent; simple tests inflate certainty. Without a pre-registered analysis and mixed‑effects models, conclusions wobble.

**External validity.** Today’s GPT‑ish stack in English is not “LLMs” or “narrative memory” in general. Drift patterns won’t automatically hold for Dutch, for speech‑to‑text inputs, or for the next model update.

**Ethical mirage.** Value profiles and “memory talk” can look like personality. They aren’t. If stories reference real people, privacy and misattribution risks appear, especially when Flux invents “remembering.”

How to stay on the rails without bloating the project: keep Flux blind to the anchor text and feed it only a compact, fixed representation; pair style/value drift with a hard **content accuracy** score per fact; bootstrap your Schwartz angles and require minimum token counts; stratify anchors by topic and analyze within‑topic; treat retellings as repeated measures in a mixed model; lock decoding and version everything; and do a tiny human rating on factual accuracy and coherence as a check. 