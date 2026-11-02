"""Generate the README's accessible, theme-aware SVG diagrams using only stdlib.
Run from any directory: python3 scripts/render_architecture_diagrams.py
"""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'diagrams'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)

STYLE = '''
svg { color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --canvas:#f5f8f6; --surface:#ffffff; --ink:#153b36; --muted:#536f65;
  --line:#ceddd5; --wire:#789387; --teal:#126b5a; --teal-soft:#e2f0e9;
  --hero:#124b40; --hero-ink:#ffffff; --hero-muted:#d5ebe1;
  --blue:#3a65a2; --blue-soft:#e9f0fa; --amber:#936016; --amber-soft:#fbefcf;
  --purple:#6752a0; --purple-soft:#eeebf7;
}
@media (prefers-color-scheme:dark) {
  svg { --canvas:#0a1d19; --surface:#112c24; --ink:#e4f0e8; --muted:#b2cabc;
    --line:#345347; --wire:#8eaea0; --teal:#90d5b4; --teal-soft:#183e30;
    --hero:#174d3d; --hero-ink:#f0fff5; --hero-muted:#d0e7d6;
    --blue:#a8c8f3; --blue-soft:#1a3049; --amber:#f2ca80; --amber-soft:#3c3018;
    --purple:#cabaf1; --purple-soft:#2c2641;
  }
}
text { fill:var(--ink); }
.canvas { fill:var(--canvas); }
.surface { fill:var(--surface); stroke:var(--line); stroke-width:1.2; }
.soft { fill:var(--teal-soft); stroke:var(--line); stroke-width:1.2; }
.hero { fill:var(--hero); }
.purple-panel { fill:var(--purple-soft); stroke:var(--line); stroke-width:1.2; }
.muted { fill:var(--muted); }
.teal { fill:var(--teal); }
.blue { fill:var(--blue); }
.amber { fill:var(--amber); }
.purple { fill:var(--purple); }
.hero-text { fill:var(--hero-ink); }
.hero-muted { fill:var(--hero-muted); }
.wire { fill:none; stroke:var(--wire); stroke-width:1.7; stroke-linecap:round; stroke-linejoin:round; }
.rule { stroke:var(--line); stroke-width:1.2; }
.arrow-head { fill:var(--wire); }
'''


def element(parent, tag, **attrs):
    return ET.SubElement(parent, f'{{{NS}}}{tag}', {key.replace('_', '-'): str(value) for key, value in attrs.items()})


def text(svg, x, y, value, size=18, weight=400, cls=None, anchor=None):
    attrs = dict(x=x, y=y, font_size=size, font_weight=weight)
    if cls:
        attrs['class'] = cls
    if anchor:
        attrs['text_anchor'] = anchor
    node = element(svg, 'text', **attrs)
    node.text = value
    return node


def rect(svg, x, y, width, height, cls='surface', radius=14):
    return element(svg, 'rect', x=x, y=y, width=width, height=height, rx=radius, **{'class': cls})


def path(svg, d, arrow=False):
    attrs = {'d': d, 'class': 'wire'}
    if arrow:
        attrs['marker_end'] = 'url(#arrow)'
    return element(svg, 'path', **attrs)


def badge(svg, x, y, width, label, fill='var(--teal-soft)', cls='teal'):
    element(svg, 'rect', x=x, y=y, width=width, height=30, rx=15, fill=fill)
    text(svg, x + width / 2, y + 21, label, 16, 500, cls, 'middle')


def stage(svg, number, label, y):
    element(svg, 'circle', cx=57, cy=y-6, r=13, fill='var(--teal-soft)')
    text(svg, 57, y, number, 16, 500, 'teal', 'middle')
    text(svg, 82, y, label, 16, 500, 'muted')


def canvas(height, title, description):
    svg = ET.Element(f'{{{NS}}}svg', {
        'width': '1000', 'height': str(height), 'viewBox': f'0 0 1000 {height}',
        'role': 'img', 'aria-labelledby': 'diagram-title diagram-description',
    })
    element(svg, 'title', id='diagram-title').text = title
    element(svg, 'desc', id='diagram-description').text = description
    element(svg, 'style').text = STYLE
    defs = element(svg, 'defs')
    marker = element(defs, 'marker', id='arrow', markerWidth=8, markerHeight=8,
                     refX=7, refY=4, orient='auto', markerUnits='userSpaceOnUse')
    element(marker, 'path', d='M 1 1 L 7 4 L 1 7 Z', **{'class': 'arrow-head'})
    rect(svg, 0, 0, 1000, height, 'canvas', 24)
    return svg


def architecture():
    svg = canvas(1000, 'Agent architecture: four agents, one review workflow',
        'An officer console calls an authenticated gateway. Explicit illustrative scenarios go to the regime orchestrator, '
        'which coordinates supply and provenance, runway and eligibility, and spatial and human-impact specialists. '
        'Shared deterministic tools calculate scenarios and check budget, request, spatial and sensitivity constraints. '
        'The output is a draft report, not an award approval. Source records remain evidence-only; live cloud validation is pending.')
    text(svg, 44, 44, 'SYSTEM ARCHITECTURE', 16, 500, 'teal')
    text(svg, 44, 86, 'Four agents. One review workflow.', 34, 600)
    text(svg, 44, 116, 'Specialists assess the case; shared Python tools do the arithmetic.', 18, 400, 'muted')
    stage(svg, '1', 'REQUEST & COORDINATE', 158)
    for x, kicker, title, cls in [
        (44, 'OFFICER', 'Review console', 'surface'),
        (354, 'ACCESS LAYER', 'Authenticated API', 'surface'),
        (664, 'COORDINATOR', 'Regime orchestrator', 'hero'),
    ]:
        rect(svg, x, 178, 292, 90, cls)
        text(svg, x + 24, 207, kicker, 16, 500, 'hero-muted' if cls == 'hero' else 'muted')
        text(svg, x + 24, 240, title, 22, 500, 'hero-text' if cls == 'hero' else None)
    path(svg, 'M 336 223 H 354', True)
    path(svg, 'M 646 223 H 664', True)
    stage(svg, '2', 'THREE SPECIALIST AGENTS', 310)
    text(svg, 790, 309, 'Explicit scenario route', 16, 400, 'muted', 'end')
    path(svg, 'M 810 268 V 334 H 190')
    for center in (190, 500, 810):
        path(svg, f'M {center} 334 V 354', True)
    agents = [
        (44, 'SUPPLY', ('Supply &', 'provenance'), 'Dependencies · evidence labels'),
        (354, 'VIABILITY', ('Runway, sector', '& purity'), 'Cash runway · eligibility'),
        (664, 'COMMUNITY', ('Spatial &', 'human impact'), 'People exposure · cluster audit'),
    ]
    for x, kicker, lines, detail in agents:
        rect(svg, x, 354, 292, 116)
        element(svg, 'rect', x=x+1, y=365, width=4, height=90, rx=2, fill='var(--teal)')
        text(svg, x+24, 382, kicker, 16, 500, 'teal')
        text(svg, x+24, 410, lines[0], 22, 500)
        text(svg, x+24, 436, lines[1], 22, 500)
        text(svg, x+24, 458, detail, 16, 400, 'muted')
    for center in (190, 500, 810):
        path(svg, f'M {center} 470 V 496')
    path(svg, 'M 190 496 H 810')
    path(svg, 'M 500 496 V 548', True)
    stage(svg, '3', 'CALCULATE WITH SHARED TOOLS', 524)
    rect(svg, 44, 548, 912, 92, 'soft')
    text(svg, 76, 584, 'Deterministic Python engine', 23, 500)
    text(svg, 76, 614, 'Scores · A/B/C allocation · budget and request caps', 18, 400, 'muted')
    badge(svg, 776, 573, 148, 'Python tools')
    # The spatial specialist receives the selected funded set after allocation.
    path(svg, 'M 956 592 H 976 V 412 H 956', True)
    text(svg, 956, 520, 'Selected portfolio', 16, 400, 'muted', 'end')
    stage(svg, '4', 'AUDIT & EXPLAIN', 690)
    path(svg, 'M 500 640 V 704 H 267')
    path(svg, 'M 500 704 H 733')
    for center in (267, 733):
        path(svg, f'M {center} 704 V 714', True)
    for x, title, detail in [
        (44, 'Portfolio rules', 'Budget caps · full-or-zero cliffs'),
        (510, 'Scenario diagnostics', 'Overlap · spatial · sampled weights'),
    ]:
        rect(svg, x, 714, 446, 84)
        text(svg, x+24, 748, title, 21, 500)
        text(svg, x+24, 776, detail, 17, 400, 'muted')
    path(svg, 'M 267 798 V 820 H 733 V 798')
    path(svg, 'M 500 820 V 844', True)
    rect(svg, 44, 844, 912, 82, 'hero')
    text(svg, 76, 879, 'Draft review report', 23, 500, 'hero-text')
    text(svg, 76, 907, 'Proposed awards + supporting evidence gaps', 18, 400, 'hero-muted')
    badge(svg, 778, 870, 146, 'DRAFT ONLY', 'var(--amber-soft)', 'amber')
    text(svg, 44, 968, 'Source records stay EVIDENCE_ONLY. Live cloud execution awaits validation.', 17, 400, 'muted')
    return svg


def approach():
    svg = canvas(1060, 'Approach: evidence first, assumptions visible',
        'Three questions are kept separate. Registry and BEA inputs produce modeled exposure; historical SBA loan outcomes '
        'support industry charge-off priors, whose canonical export is pending; reviewed applicant financials establish cash '
        'runway but do not validate grant effectiveness. These source records produce evidence-only findings and no awards. '
        'A separate illustrative benchmark assumes finances and grant effects, compares regimes A, B and C under budget and '
        'indivisible-shock rules, and produces a draft report after overlap, spatial and sampled sensitivity checks.')
    text(svg, 44, 44, 'OUR APPROACH', 16, 500, 'teal')
    text(svg, 44, 86, 'Evidence first. Assumptions visible.', 34, 600)
    text(svg, 44, 116, 'Three questions guide the review — each needs its own evidence.', 18, 400, 'muted')
    lanes = [
        (44, '01 · EXPOSURE', ('Who is', 'exposed?'), 'teal', 'var(--teal-soft)', [
            ('Registry + BEA', ['IDs + input coefficients']),
            ('Model dependencies', ['Decay + buyer alternatives']),
            ('Trace exposure', ['Distinct reach + weights', '2-hop baseline; up to 8 hops']),
        ]),
        (354, '02 · INDUSTRY RISK', ('How risky is', 'this industry?'), 'blue', 'var(--blue-soft)', [
            ('SBA loan outcomes', ['Observed historical loans']),
            ('Horizon + holdout', ['Controls and validation']),
            ('Industry risk prior', ['Charge-off probability']),
        ]),
        (664, '03 · GRANT EFFECT', ('What could a', 'grant change?'), 'amber', 'var(--amber-soft)', [
            ('Applicant evidence', ['Cash, burn, debt, ownership']),
            ('Review a revision', ['Saved intake + officer review']),
            ('Cash runway reviewed', ['Grant effect remains unknown']),
        ]),
    ]
    for x, label, question, cls, fill, steps in lanes:
        rect(svg, x, 154, 292, 412)
        element(svg, 'rect', x=x+1, y=166, width=4, height=388, rx=2, fill=f'var(--{cls})')
        text(svg, x+24, 188, label, 16, 500, cls)
        text(svg, x+24, 222, question[0], 23, 500)
        text(svg, x+24, 249, question[1], 23, 500)
        for i, (title, lines) in enumerate(steps):
            y = (274, 366, 458)[i]
            element(svg, 'rect', x=x+20, y=y, width=252, height=72 if i < 2 else 88, rx=10, fill=fill)
            text(svg, x+36, y+28, title, 18, 500)
            for j, line in enumerate(lines):
                text(svg, x+36, y+52+j*22, line, 16, 400, 'muted')
            if i < 2:
                path(svg, f'M {x+146} {y+72} V {y+92}', True)
        if cls == 'blue':
            badge(svg, x+36, 514, 180, 'Export pending', 'var(--amber-soft)', 'amber')
    for center in (190, 500, 810):
        path(svg, f'M {center} 566 V 594')
    path(svg, 'M 190 594 H 810')
    path(svg, 'M 500 594 V 626', True)
    rect(svg, 44, 626, 912, 92, 'soft')
    text(svg, 76, 661, 'EVIDENCE_ONLY', 23, 500, 'teal')
    text(svg, 76, 690, 'Explain modeled exposure, reviewed intake and missing evidence.', 18, 400, 'muted')
    badge(svg, 778, 646, 146, 'NO AWARDS')
    element(svg, 'line', x1=44, y1=756, x2=956, y2=756, **{'class': 'rule'})
    rect(svg, 360, 740, 280, 32, 'canvas', 0)
    text(svg, 500, 762, 'SEPARATE BENCHMARK', 16, 500, 'purple', 'middle')
    rect(svg, 44, 786, 912, 242, 'purple-panel')
    text(svg, 68, 818, 'ILLUSTRATIVE SCENARIO · ASSUMPTIONS ONLY', 16, 500, 'purple')
    for x, title, lines in [
        (68, 'Assume inputs', ['Scenario finances', '+ grant-effect assumptions']),
        (365, 'Compare A / B / C', ['Full · bridge · hybrid', 'Budget caps; full-or-zero cliffs']),
        (662, 'Stress-test & explain', ['Overlap · spatial fit', '+ sampled weight sensitivity']),
    ]:
        rect(svg, x, 844, 270, 126)
        text(svg, x+20, 880, title, 20, 500)
        for j, line in enumerate(lines):
            text(svg, x+20, 911+j*24, line, 16, 400, 'muted')
    path(svg, 'M 338 907 H 365', True)
    path(svg, 'M 635 907 H 662', True)
    text(svg, 68, 1004, 'Draft report for officer review; document checks remain pending.', 17, 400, 'purple')
    return svg


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, drawing in [('agent-architecture.svg', architecture()), ('grant-review-approach.svg', approach())]:
        ET.indent(drawing, space='  ')
        destination = OUT / filename
        ET.ElementTree(drawing).write(destination, encoding='utf-8', xml_declaration=True)
        print(destination.relative_to(ROOT))


if __name__ == '__main__':
    main()
