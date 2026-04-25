# Fine-Tuning Conceptual Primer

For a first-time fine-tuner. No code. The mental model and the decisions you'll face.

## 1. What fine-tuning actually does

LFM2-VL was pre-trained on ~10–12 trillion tokens. It already "knows" what an impoundment, a pond, a wall, an erosion gully look like in a generic visual sense, and it can produce coherent text. **Fine-tuning does not add knowledge. It adjusts how the model expresses what it already knows.**

For SatDiff, we are not teaching the model new objects. We are teaching it three things:

1. **Vocabulary and framing** — speak in *claim conditions*, not free-form description. Use phrases like "Claim 2 elevated severity due to pond-to-wall proximity at <50m" rather than "I see a body of water near a structure."
2. **Format discipline** — output strict JSON conforming to our schema, every time, even on edge cases.
3. **Judgment under uncertainty** — when an image is ambiguous, prefer "elevated, flag for review" over "urgent" or "nominal." Calibration toward our contract's risk thresholds.

If you keep this lens, you'll make better decisions about data, about evaluation, and about when to stop training.

## 2. Why LoRA (low-rank adaptation), conceptually

Full fine-tuning means adjusting all the model's weights — for a 1.6B parameter model, that's billions of numbers. Compute-prohibitive on a laptop, and risky: the model can lose its general capability ("catastrophic forgetting") if we push too hard.

LoRA freezes the original model and adds a small *adapter* — typically <1% the size of the base. The base model keeps everything it knows; the adapter learns the small adjustment we want. Cheap, fast, easy to share, and gracefully reversible (we can use base alone or base+adapter).

Why LoRA is right for SatDiff:
- We only have ~30–100 examples to train on.
- We want format and framing changes, not deep capability changes.
- We need to ship trained weights publicly. LoRA adapters are small (megabytes, not gigabytes).

You'll see the term **QLoRA** too — that's LoRA on top of a quantized (lower-precision) base. Saves more memory at small accuracy cost. Use it if VRAM is tight; skip if not needed.

## 3. The four decisions that determine outcome

Before running anything, four questions need answers. The order matters.

### Decision A — What's our metric?

This is the hardest and most important decision. The rubric requires "measurable improvement over the base model." Without a metric defined *before* training, we can't honestly claim improvement.

For SatDiff, candidate metrics:

- **JSON schema validity rate.** Of N test passes, what fraction produce JSON that parses and conforms to the contract schema? Trivially measurable, immediately observable improvement story if base hallucinates structure.
- **Claim-level severity accuracy.** Given a hand-labelled "ground-truth" severity per claim per pass, what fraction does the model match? Requires labelled test set.
- **Hallucination rate.** Of outputs, what fraction reference features not actually present in the image? Manual to score.
- **Latency / token efficiency.** Fine-tuned model often produces shorter, cleaner outputs.

**Recommended baseline metric:** JSON schema validity + claim-severity accuracy on a small held-out set. Both numbers, both computed on base and fine-tuned, both reported.

The reason this is the hard decision: if you pick a metric you can't compute reliably, the whole exercise is theatre. Pick a metric where the measurement is mechanical and reproducible by a judge running our eval script.

### Decision B — What's our training data?

We curate a small corpus of (image, image, contract-prompt) → (target JSON output) examples. Probably 30–80 of these.

The image pairs are baseline-vs-current Sentinel-2 patches. The target JSON is a hand-written, contract-conformant assessment for that pair.

**Quality matters more than quantity.** If 50% of your labels are inconsistent — calling the same anomaly different severities, using different phrasings — the model learns inconsistency. **Hand-write 30 careful examples** rather than auto-generating 200 noisy ones.

Source images:
- Jagersfontein 2014–2017 baseline vs 2018–2022 progressive (positive class with ground truth from Torres-Cruz)
- A few peer TSFs (Mount Polley pre-2014, Samarco pre-2015) for diversity
- Unrelated stable EO scenes (other Sentinel-2 patches with no anomaly) so the model doesn't always flag everything as elevated

**Hold out a test set up front.** Pick ~10–15 examples from the corpus, set them aside, do not look at them again until evaluation. This is the most common first-time-fine-tuner mistake: using the test set during development. Once contaminated, your "improvement" number is meaningless.

### Decision C — Hyperparameters

For LoRA on a 1.6B-parameter VLM with ~50 training examples, defensible starting points (we'll tune from here):

- **Rank (r):** 8 or 16. Bigger rank = more adapter capacity but more risk of overfitting on small data.
- **Alpha:** typically 2× rank.
- **Learning rate:** ~1e-4 to 5e-5. LoRA tolerates higher LRs than full fine-tuning.
- **Epochs:** 1–3. With 50 examples, 3 epochs = 150 gradient updates. More than that risks overfitting.
- **Batch size:** as big as VRAM allows. With one image-pair per example, 2–4 is typical.
- **Target modules:** the attention projections (`q_proj`, `v_proj`, sometimes `k_proj` and `o_proj`). The vision encoder usually stays frozen.

These aren't gospel — we'll likely revise after seeing the loss curve.

### Decision D — What's "good enough to ship"?

Define this in advance. Examples:

- **JSON validity rate** rises from base 70% → fine-tuned 95%
- **Claim-severity accuracy** rises from base 40% → fine-tuned 65%
- No catastrophic regression on general visual reasoning (sanity check: model can still describe a non-tailings image coherently)

If you hit your "good enough" thresholds, ship. Don't keep training in pursuit of marginal gains — you'll just overfit. If you don't hit them, see §6 (graceful degradation).

## 4. The training loop, conceptually

What actually happens when training runs:

1. The model sees an image-pair + contract prompt.
2. It generates a JSON output.
3. The trainer compares its output to our hand-written target output, computes loss (how wrong it is, token by token).
4. The optimizer adjusts the LoRA adapter weights to reduce that loss.
5. Repeat for the next example. After all examples = one epoch.

What you watch:

- **Training loss** — should decrease epoch over epoch. A flat curve = nothing learning. A noisy curve = LR too high.
- **Validation loss** (computed on a small held-aside-from-training-but-not-the-final-test set) — should also decrease but rise *after* training loss continues falling. That divergence is the overfitting signal: the model is memorising training, not learning to generalise.
- **Sample outputs every N steps** — eyeball them. Training metrics can lie; reading actual outputs catches it when the model is getting better numerically but worse qualitatively (e.g., generating valid JSON but hallucinating features).

## 5. What can go wrong and how to recognise it

| Symptom | Likely cause | Response |
|---------|-------------|----------|
| Loss not decreasing | Learning rate too low; data formatted wrong | Raise LR; check that image pairs and target JSON pair correctly in the dataset |
| Loss decreasing then exploding | LR too high; bad batch | Lower LR; inspect the batch right before the explosion |
| Training loss falls; val loss rises | Overfitting | Stop earlier; reduce rank; add more data; lower LR |
| Outputs become repetitive / collapse | Mode collapse (over-training on small data) | Stop earlier; reduce epochs |
| JSON breaks where base was fine | Format catastrophic forgetting | Ensure target outputs are well-formed; reduce LR; consider a few "format-only" examples |
| Model loses general visual reasoning | Adapter touched too much of the network | Reduce target modules; use lower rank |
| Improvement is statistically insignificant | Test set too small; metric too noisy | Bigger test set; better metric; report honestly anyway |

## 6. Graceful degradation — what if it doesn't beat the base?

This is fine. The rubric rewards "measurable improvement," but it also rewards "documented methodology." A clean fine-tuning experiment that produced a *negative* or *null* result, written up honestly with the eval methodology and an explanation of why we think the base was already strong, is better than:

- A "win" claimed without honest evaluation
- Skipping fine-tuning entirely

If we end up reporting a null result, the writeup says: "We fine-tuned LFM2-VL-1.6B on a curated set of N tailings-dam image pairs using LoRA. On our held-out test set of M examples, JSON validity rate was X% (base) vs Y% (fine-tuned), claim accuracy was P% vs Q%. The improvement was [small / not statistically significant]. We hypothesise this is because [the contract framing is already learnable via prompting / our test set was too small to detect the effect / etc.]. Training code, data card, and adapter weights are public anyway because reproducibility matters."

That's a respectable submission section. It would lose a bit on the "rewarded" axis but stay honest, which the rubric explicitly values ("clearly articulating the problem and solution").

## 7. The deliverables, concretely

To check off every requirement in the rubric:

| Deliverable | Where it lives |
|------------|----------------|
| Documented methodology | `training/README.md` in the submission repo. Sections: data curation, label format, hyperparameters, hardware, training time, eval methodology. |
| Measurable improvement | `training/eval.py` — runs base and fine-tuned on the held-out test set, prints both numbers and the delta. |
| Public weights | HuggingFace repo: `<your-handle>/satdiff-lfm2-vl-1.6b-lora-tailings`. Include a model card with intended use + limits. |
| Public training code | `training/train.py` (or a notebook), checked into the submission repo with all required configs. Reproducible from a fresh checkout if a runner has the same data. |
| Public training data | `training/dataset.json` (or .jsonl) in the repo, with image refs and target outputs. *If images are public Sentinel-2 we can ship the references; if any image is non-redistributable we ship the script that pulls them from STAC.* |

## 8. The questions you'll face during execution and what to answer

In rough order of when they appear:

- **"How do I know my eval metric works?"** — Run it on the base model with a tiny stub corpus before doing any training. If you can't get a stable number on base, the metric isn't ready.
- **"How do I label an image pair?"** — Re-read Torres-Cruz & O'Donovan and write 5 example labels in the same vocabulary first. Show them to me. We iterate together until the label style is consistent. Then you label the rest.
- **"Loss is wobbly, is something wrong?"** — Probably not. With small batch and small data, loss curves are noisy. What matters is the trend across epochs.
- **"It's been training for an hour, should I stop?"** — Check val loss. If it's still falling, keep going. If it's been rising for 100+ steps, stop and use the earlier checkpoint.
- **"My JSON output broke after fine-tuning — disaster?"** — Probably a recoverable hyperparameter issue (rank too high, LR too high, bad batch). Reduce one variable, retry. Don't change three things at once.
- **"Should I include the failed training runs in the writeup?"** — Yes, briefly. Negative results with diagnoses are credibility-builders.
- **"Can we ship without fine-tuning if Spike 3 fails?"** — Yes. We document the attempt, ship base-only, and lose those points but don't lose the submission.

## 9. The 80/20 of getting fine-tuning right

If you only remember three things:

1. **Design the eval before you train.** A held-out test set, a metric you can compute mechanically, baseline numbers from the base model. Without these, "improvement" is a vibe.
2. **Quality of labels >> quantity.** Thirty hand-written, internally-consistent examples beat three hundred noisy ones.
3. **Stop early.** With small data and LoRA, overfitting happens fast. Trust the validation curve, not the training curve.

The first time is mostly about not making rookie mistakes. We won't break records on Day 6. We'll produce a clean, honest, reproducible artefact that scores well precisely because it's clean and honest.
