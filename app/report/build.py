from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from pathlib import Path

FIG = Path("docs/figures/rg_per_year.png")
FIG = Path("docs/figures/collab_network.png")
FIG = Path("docs/figures/genre_evolution.png")
DOC = Path("docs/report.pdf")
DOC.parent.mkdir(parents=True, exist_ok=True)

S = getSampleStyleSheet()
els = [
    Paragraph("Music Explorer — Summary", S["Title"]),
    Paragraph("Data: MusicBrainz (CC BY-NC-SA 4.0).", S["Normal"]),
    Spacer(1, 12),
]
if FIG.exists():
    els.append(Image(str(FIG), width=480, height=280))
else:
    els.append(Paragraph("Figure missing: docs/figures/rg_per_year.png", S["Italic"]))

SimpleDocTemplate(str(DOC)).build(els)
print(f"Wrote {DOC}")
