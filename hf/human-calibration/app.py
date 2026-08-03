"""Reference-only PelicanBench human-calibration interface.

The Space demonstrates stage gating and the response schema. It deliberately has no
participant database, authentication, recruitment or production telemetry. A governed
study must connect it to an approved assignment service and data store.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gradio as gr

from pelicanbench.human_study import validate_calibration_response


def prompt_disclosure_permitted(*, blind_response_locked: bool) -> bool:
    return bool(blind_response_locked)


EXAMPLE_SVG = Path(__file__).with_name("example.svg")
EXAMPLE_PROMPT = "Generate an SVG of a pelican riding a bicycle"


def lock_blind_response(
    animal: str,
    mobile_object: str,
    relation: str,
    confidence: int,
) -> tuple[str, gr.update, gr.update]:
    response = {
        "animal_open_text": animal.strip(),
        "mobile_object_open_text": mobile_object.strip(),
        "relation_open_text": relation.strip(),
        "recognition_confidence": confidence,
    }
    validation = validate_calibration_response("blind-recognition", response)
    if not validation.valid:
        return (
            "Complete the blind fields before the prompt is revealed: "
            + ", ".join((*validation.missing_fields, *validation.invalid_fields)),
            gr.update(visible=False),
            gr.update(visible=False),
        )
    if not prompt_disclosure_permitted(blind_response_locked=True):
        raise RuntimeError("prompt disclosure gate failed")
    receipt = json.dumps(
        {
            "stage": "blind-recognition",
            "locked": True,
            "response": response,
        },
        indent=2,
    )
    return receipt, gr.update(value=EXAMPLE_PROMPT, visible=True), gr.update(visible=True)


def submit_criteria(
    animal_defects: str,
    object_defects: str,
    interaction_defects: str,
    animal_rating: int,
    object_rating: int,
    interaction_rating: int,
    confidence: int,
) -> str:
    response: dict[str, Any] = {
        "animal_defects": animal_defects.strip(),
        "object_defects": object_defects.strip(),
        "interaction_defects": interaction_defects.strip(),
        "animal_rating_1_to_5": animal_rating,
        "object_rating_1_to_5": object_rating,
        "interaction_rating_1_to_5": interaction_rating,
        "criterion_confidence": confidence,
    }
    validation = validate_calibration_response("prompt-aware-criteria", response)
    return json.dumps(
        {
            "stage": "prompt-aware-criteria",
            "valid": validation.valid,
            "missing_fields": validation.missing_fields,
            "invalid_fields": validation.invalid_fields,
            "response": response,
            "production_note": "Reference UI only; no response was persisted.",
        },
        indent=2,
    )


def submit_pairwise(winner: str) -> str:
    validation = validate_calibration_response("pairwise-preference", {"pairwise_winner": winner})
    return json.dumps(
        {
            "stage": "pairwise-preference",
            "valid": validation.valid,
            "winner": winner,
            "production_note": "Reference UI only; no response was persisted.",
        },
        indent=2,
    )


with gr.Blocks(title="PelicanBench Human Calibration") as demo:
    gr.Markdown(
        "# PelicanBench human-calibration reference\n"
        "The model identity is hidden. Describe the image before the generation prompt is revealed. "
        "This demonstration stores no participant data."
    )
    with gr.Tab("Artifact calibration"):
        gr.Image(value=str(EXAMPLE_SVG), label="Blinded rendered artifact", interactive=False)
        with gr.Group():
            animal = gr.Textbox(label="What animal is depicted?")
            mobile_object = gr.Textbox(label="What mobile object is depicted?")
            relation = gr.Textbox(label="What is the animal doing in relation to it?")
            recognition_confidence = gr.Slider(
                0, 100, value=50, step=1, label="Recognition confidence"
            )
            lock = gr.Button("Lock blind response and reveal prompt")
            blind_receipt = gr.Code(language="json", label="Blind-stage receipt")
        prompt = gr.Textbox(label="Generation prompt", visible=False, interactive=False)
        with gr.Group(visible=False) as criteria_group:
            gr.Markdown("Name visible defects before assigning ratings.")
            animal_defects = gr.Textbox(label="Animal defects")
            object_defects = gr.Textbox(label="Mobile-object defects")
            interaction_defects = gr.Textbox(label="Interaction/contact defects")
            animal_rating = gr.Slider(1, 5, value=3, step=1, label="Animal rating")
            object_rating = gr.Slider(1, 5, value=3, step=1, label="Object rating")
            interaction_rating = gr.Slider(1, 5, value=3, step=1, label="Interaction rating")
            criterion_confidence = gr.Slider(0, 100, value=50, step=1, label="Criterion confidence")
            criterion_submit = gr.Button("Validate criterion response")
            criterion_receipt = gr.Code(language="json", label="Criterion-stage receipt")
        lock.click(
            lock_blind_response,
            [animal, mobile_object, relation, recognition_confidence],
            [blind_receipt, prompt, criteria_group],
        )
        criterion_submit.click(
            submit_criteria,
            [
                animal_defects,
                object_defects,
                interaction_defects,
                animal_rating,
                object_rating,
                interaction_rating,
                criterion_confidence,
            ],
            criterion_receipt,
        )
    with gr.Tab("Pairwise preference"):
        gr.Markdown(
            "Production assignments present two different model artifacts for the same task, "
            "with left/right order randomised and model names hidden."
        )
        with gr.Row():
            gr.Image(value=str(EXAMPLE_SVG), label="A", interactive=False)
            gr.Image(value=str(EXAMPLE_SVG), label="B", interactive=False)
        winner = gr.Radio(["A", "B", "tie"], label="Which is better for the stated criterion?")
        pair_submit = gr.Button("Validate pairwise response")
        pair_receipt = gr.Code(language="json", label="Pairwise-stage receipt")
        pair_submit.click(submit_pairwise, winner, pair_receipt)


if __name__ == "__main__":
    demo.launch()
