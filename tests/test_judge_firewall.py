from pelicanbench.judge_firewall import JudgeFirewallPolicy, evaluate_judge_input


def test_firewall_accepts_canonical_fixture_render(root):
    from pelicanbench.render import render_svg
    from pelicanbench.svg import inspect_svg

    svg = (root / "benchmark/fixtures/svg/pelican-bicycle-valid.svg").read_text()
    inspection = inspect_svg(svg)
    rendered = render_svg(svg, inspection=inspection)
    result = evaluate_judge_input(svg, inspection, rendered, policy=JudgeFirewallPolicy())
    assert result.eligible
    assert result.render_hash == rendered.render_hash
