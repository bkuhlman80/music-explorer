# app/report/build.py
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from pathlib import Path

FIGS = [
    Path("docs/figures/rg_per_year.png"),
    Path("docs/figures/collab_network.png"),
    Path("docs/figures/genre_evolution.png"),
]
DOC = Path("docs/report.pdf")
DOC.parent.mkdir(parents=True, exist_ok=True)


def main():
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(DOC))
    flow = [Paragraph("Music Explorer – Results", styles["Title"]), Spacer(1, 12)]
    for p in FIGS:
        if p.exists():
            flow += [Image(str(p), width=520, height=320), Spacer(1, 12)]
    doc.build(flow)
    print(f"[INFO] wrote {DOC.resolve()}")


if __name__ == "__main__":
    main()
