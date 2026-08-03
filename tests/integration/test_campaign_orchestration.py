import json

from pelicanbench.campaign import CampaignManifest


def test_campaign_fixture_has_one_budgeted_ready_cell(root):
    value = json.loads((root / "benchmark/fixtures/campaign/manifest.json").read_text())
    manifest = CampaignManifest.from_mapping(value)
    assert manifest.budget_gate == "pass"
    assert [cell.state for cell in manifest.cells] == ["ready"]
