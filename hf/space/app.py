from __future__ import annotations

import json
from pathlib import Path

import gradio as gr

try:
    from pelicanbench.scoring import score_svg
    from pelicanbench.taskgen import heritage_task
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from pelicanbench.scoring import score_svg
    from pelicanbench.taskgen import heritage_task


def evaluate(svg: str) -> tuple[str, str]:
    card = score_svg(heritage_task(), svg, submission_id="interactive")
    summary = f"Aggregate: {card.aggregate:.3f} | Critical success: {card.valid}"
    return summary, json.dumps(card.model_dump(mode="json"), indent=2)


with gr.Blocks(title="PelicanBench Explorer") as demo:
    gr.Markdown(
        "# PelicanBench Explorer\nPaste an SVG to inspect the transparent V1 structural scorecard."
    )
    source = gr.Code(language="html", label="SVG source")
    run = gr.Button("Evaluate")
    summary = gr.Textbox(label="Summary")
    details = gr.Code(language="json", label="Scorecard")
    run.click(evaluate, source, [summary, details])

if __name__ == "__main__":
    demo.launch()
