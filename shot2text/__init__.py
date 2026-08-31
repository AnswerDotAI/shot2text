"""Screenshot to text, as a macmage cantrip: a region screenshot is transcribed
by Gemini and copied to the clipboard, announced by a tone.

Bind `shot2text` to any macmage trigger in your `config.py`, e.g.
`mage(shot2text, keys='ctrl-opt-t')`. Needs the `screen` grant (`Imp --grant screen`)
and `GEMINI_API_KEY` in the agent's environment: the README covers getting it there.
"""
__version__ = '0.0.1'

import asyncio, os, tempfile
from pathlib import Path

from aidialog.msg_parts import mk_msg
from fastllm.acomplete import acomplete
from macmage import need, set_clip, tone

MODEL = 'models/gemini-3.7-flash'
MAX_TOKENS = 2048
PROMPT = 'Transcribe all text in this image exactly, preserving indentation and line breaks. Output only the text, no commentary, no code fences.'


async def shot2text():
    need('screen')
    fd, p = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    png = Path(p)
    try:
        proc = await asyncio.create_subprocess_exec('screencapture', '-i', p)
        await proc.wait()
        if not png.stat().st_size: return  # Esc cancels the capture, leaving the file empty
        r = await acomplete([mk_msg([PROMPT, png.read_bytes()])], model=MODEL, max_tokens=MAX_TOKENS)
        set_clip(r.message.text.strip())
        tone()
    finally: png.unlink()
