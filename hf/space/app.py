from __future__ import annotations

from pathlib import Path

import gradio as gr

try:
    from pelicanbench.explorer import evaluate
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from pelicanbench.explorer import evaluate


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
