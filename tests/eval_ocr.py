"""Run every OCR engine over the images in tests/img and write a comparison table.

    python tests/eval_ocr.py                  # all engines, writes tests/results.md
    python tests/eval_ocr.py --engines vision # skip the network engine
    python tests/eval_ocr.py --regen          # re-render the built-in fixtures first

Any image dropped into tests/img is picked up; a sibling `<name>.txt` holding the
image's true text adds a similarity score for each engine.
Not a test suite: run it when judging an engine or a prompt change.
Needs the `[local]` extra (`pip install shot2text[local]`) for the vision engine,
and the `GEMINI_API_KEY` from macmage's `.env` for the gemini engine."""
import asyncio, difflib, time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fastcore.script import call_parse

IMGDIR = Path(__file__).parent/'img'

CODE = '''def load_cfg(path):
    "Read a cfg file, merging over DEFAULTS"
    config = dict(DEFAULTS)
    for line in open(path).read().splitlines():
        k, v = line.split('=', 1)
        config[k.strip()] = v.strip()
    return config'''

PROSE = '''macOS grants permissions per program, and drops them when a binary is
rebuilt or a venv moves. With Python that means scripts break for no
reason, and Settings fills with entries called python3.13.

Imp is a tiny signed app that holds the grants: anything you run
through it has them.'''

FIXTURES = dict(code=(CODE, 13, 'black'), prose=(PROSE, 13, 'black'), code_small=(CODE, 9, '#777777'))


def render(text, path, size, fg):
    font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', size)
    lines = text.splitlines()
    w = max(font.getlength(l) for l in lines)
    img = Image.new('RGB', (int(w)+40, len(lines)*(size+4)+40), 'white')
    ImageDraw.Draw(img).multiline_text((20, 20), text, font=font, fill=fg, spacing=4)
    img.save(path)
    return path


def regen_fixtures():
    "Render the built-in fixtures and their ground-truth sidecars into IMGDIR"
    for name, (text, size, fg) in FIXTURES.items():
        render(text, IMGDIR/f'{name}.png', size, fg)
        (IMGDIR/f'{name}.txt').write_text(text)


def vision_ocr(png):
    import shot2text
    return shot2text._vision(png), 0.0


def gemini_ocr(png):
    import shot2text
    r = asyncio.run(shot2text._complete(png))
    return r.message.text.strip(), r.cost


ENGINES = dict(vision=vision_ocr, gemini=gemini_ocr)


@call_parse
def main(
    engines: str='vision,gemini', # Comma-separated engines to run
    regen: bool=False, # Re-render the built-in fixtures before running
    diffs: bool=False, # Print a unified diff for each imperfect transcription
):
    "OCR every image in tests/img with each engine, save transcripts to tests/results, and write the accuracy table to tests/results.md"
    from dotenv import load_dotenv
    from macmage import config_dir
    load_dotenv(config_dir/'.env', override=False)
    IMGDIR.mkdir(exist_ok=True)
    if regen or not any(IMGDIR.glob('*.png')): regen_fixtures()
    engs = engines.split(',')
    resdir = Path(__file__).parent/'results'
    resdir.mkdir(exist_ok=True)
    rows, times, costs = [], {e: [] for e in engs}, {e: [] for e in engs}
    for png in sorted(IMGDIR.glob('*.png')):
        tf = png.with_suffix('.txt')
        truth = tf.read_text() if tf.exists() else None
        row = [png.stem]
        for eng in engs:
            t0 = time.time()
            got, cost = ENGINES[eng](png)
            times[eng].append(time.time()-t0)
            costs[eng].append(cost)
            (resdir/f'{png.stem}.{eng}.txt').write_text(got)
            score = f'{difflib.SequenceMatcher(None, truth, got).ratio():.3f}' if truth else '-'
            row.append(score)
            print(f'{png.stem:12} {eng:15} {score:6} {times[eng][-1]:4.1f}s ${cost:.4f}')
            if diffs and truth and got != truth:
                print('\n'.join(difflib.unified_diff(truth.splitlines(), got.splitlines(), 'truth', eng, lineterm='')))
        rows.append(row)
    md = ['| image | ' + ' | '.join(engs) + ' |', '|' + '---|'*(len(engs)+1)]
    md += ['| ' + ' | '.join(r) + ' |' for r in rows]
    md += ['', '| engine | time/call | cost/call |', '|---|---|---|']
    for eng in engs:
        t, c = times[eng], costs[eng]
        cost = 'free' if max(c) == 0 else f'${min(c):.3f}–${max(c):.3f}'
        md.append(f'| {eng} | {min(t):.1f}–{max(t):.1f}s | {cost} |')
    out = Path(__file__).parent/'results.md'
    out.write_text('\n'.join(md) + '\n')
    print(f'wrote {out}')
