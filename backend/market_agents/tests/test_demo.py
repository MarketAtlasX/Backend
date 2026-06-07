from market_agents.main import run_demo


def test_demo_runs():
    result = run_demo()
    assert "snapshot" in result
    assert "impact" in result
    assert "recommendation" in result
