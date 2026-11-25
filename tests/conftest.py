import pytest

from tsvlab.sim import SimConfig, simulate

SHORT = SimConfig(duration=7_200.0, warmup=900.0, n_episodes=(2, 2), n_bursts=(1, 1))


@pytest.fixture(scope="session")
def short_cfg():
    return SHORT


@pytest.fixture(scope="session")
def sess_informed():
    return simulate(SHORT, 11)


@pytest.fixture(scope="session")
def sess_control():
    return simulate(SHORT.with_mode("control"), 11)
