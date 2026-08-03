from pelicanbench.reassessment import plan_replicate_wave


def test_wave_counts_are_additive():
    assert (
        plan_replicate_wave(models=7, tasks=64, current_replicates=3, target_replicates=5)[
            "cell_count"
        ]
        == 896
    )
