# shot2text

Hotkey OCR for macOS: copy text from anywhere on your screen. Press the hotkey, drag out a region, and everything written in it lands on your clipboard ready to paste, transcribed by Gemini. 

You'll hear a confirmation tone when the text is ready to paste in your clipboard. 

Very useful to quickly screenshot text or code during calls, getting quotes from PDFs or in general quick text extraction from images.

Implemented as a [macmage](https://github.com/AnswerDotAI/macmage) cantrip and requires [Imp](https://github.com/AnswerDotAI/imp).

## Install

Install into the same environment as macmage, the one the agent runs from:

```
pip install shot2text
```

The interactive capture needs the screen recording permission, held by [Imp](https://github.com/AnswerDotAI/imp):

```
imp --grant screen
```

## Configure

The agent runs under launchd, so exports in your shell profile and thus your env variables never reach it. 

Shot2text uses gemini for the transcription. Add your `GEMINI_API_KEY` to `~/.config/macmage/.env`:

```
GEMINI_API_KEY=...
```

macmage loads `.env` automatically before your config. Bind the cantrip to a trigger of your choice in `~/.config/macmage/config.py`:

```
from macmage import mage
from shot2text import shot2text

mage(shot2text, keys='ctrl-opt-t')
```

Once the file is saved and the permissions granted ctrl-opt-t (ctrl-alt on PC keyboards) captures. After you change `.env`, run `macmage --install`; a `config.py` save alone does not pick up new environment variables.

## Other models

`shot2text` transcribes with Gemini. `mk_shot2text` builds the same cantrip for any [fastllm](https://github.com/AnswerDotAI/fastllm)-supported model, or `'vision'` for on-device Apple Vision. 

Apple Vision is free, fast and on-device, but noticeably worse on code (see the comparison below). Vision needs `pip install shot2text[local]` and no API key:

```
from shot2text import mk_shot2text

mage(mk_shot2text('vision'), keys='ctrl-opt-l')
mage(mk_shot2text('claude-haiku-4-5', effort=None), keys='ctrl-opt-t')
```

## Comparison

Similarity to ground truth per test image, then per-engine time and cost ranges. Regenerate with `python tests/eval_ocr.py`.

You can see the input images, ground truth and transcripts of each model  in [tests](tests):

| image | vision | gemini |
|---|---|---|
| code | 0.796 | 1.000 |
| code_small | 0.771 | 1.000 |
| prose | 0.979 | 1.000 |
| terminal_ui | 0.925 | 0.980 |

| engine | time/call | cost/call |
|---|---|---|
| vision | 0.1–1.1s | free |
| gemini | 2.2–5.5s | $0.001–$0.002 |

## Contributing

If you find a model that works better for you, please add it to the comparison table! 