"""Screenshot to text, as a macmage cantrip: a region screenshot is transcribed
by OCR and copied to the clipboard, announced by a tone.

Bind `shot2text` to any macmage trigger in your `config.py`, e.g.
`mage(shot2text, keys='ctrl-opt-t')`. It transcribes with Gemini, needing the
`screen` grant (`Imp --grant screen`) and `GEMINI_API_KEY` in the agent's
environment: the README covers getting it there. `mk_shot2text` builds a cantrip
for any fastllm-supported model, or 'vision' for on-device Apple Vision
(`pip install shot2text[local]`; see the README for the accuracy tradeoff).
"""
__version__ = '0.0.2'

import asyncio, os, tempfile
from functools import partial
from pathlib import Path

from aidialog.msg_parts import mk_msg
from fastllm.acomplete import acomplete
from macmage import need, set_clip, tone

MODEL = 'models/gemini-3.7-flash'
MAX_TOKENS = 8192
PROMPT = 'Transcribe all text in this image exactly, preserving indentation and line breaks. Output only the text, no commentary, no code fences.'


async def _complete(
    png, # Image file to transcribe
    model=MODEL, # Any fastllm-supported model name
    effort='minimal', # Reasoning effort; None for models without configurable thinking
):
    "The transcription `Completion` for `png`"
    return await acomplete([mk_msg([PROMPT, png.read_bytes()])], model=model, max_tokens=MAX_TOKENS, reasoning_effort=effort)


async def llm_ocr(
    png, # Image file to transcribe
    model=MODEL, # Any fastllm-supported model name
    effort='minimal', # Reasoning effort; None for models without configurable thinking
):
    "Transcribe `png` with any fastllm-supported model"
    return (await _complete(png, model, effort)).message.text.strip()


def _vision(png):
    import Vision
    from fastcocoa import chk, nsurl, pythonify
    pythonify(Vision.VNRecognizeTextRequest, Vision.VNImageRequestHandler, mod=Vision)
    req = Vision.VNRecognizeTextRequest()
    req.recognitionLevel = Vision.VNRequestTextRecognitionLevelAccurate
    req.usesLanguageCorrection = True
    chk(Vision.VNImageRequestHandler(URL=nsurl(str(png)), options={}).performRequests_error_([req], None))
    return '\n'.join(r.topCandidates_(1)[0].string() for r in req.results)


async def vision_ocr(png):
    "Transcribe `png` on-device with Apple Vision"
    return await asyncio.to_thread(_vision, png)


def mk_shot2text(
    model=MODEL, # A fastllm model name, or 'vision' for on-device Apple Vision
    effort='minimal', # Reasoning effort; None for models without configurable thinking
):
    "A cantrip transcribing a region screenshot to the clipboard with `model`"
    ocr = vision_ocr if model == 'vision' else partial(llm_ocr, model=model, effort=effort)
    async def cantrip():
        need('screen')
        fd, p = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        png = Path(p)
        try:
            proc = await asyncio.create_subprocess_exec('screencapture', '-i', p)
            await proc.wait()
            if not png.stat().st_size: return  # Esc cancels the capture, leaving the file empty
            set_clip(await ocr(png))
            tone()
        finally: png.unlink()
    return cantrip


shot2text = mk_shot2text()
