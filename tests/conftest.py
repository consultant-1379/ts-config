import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--track",
        action='store',
        default='all',
        type=str,
        required=False,
        help="Resource files that need to run, like: nfvi,openshift. "
             "Default is all, means run all the resource files."
    )
    parser.addoption(
        "--detail",
        action='store_true',
        default=False,
        required=False,
        help="Open it to get all logs"
    )


@pytest.fixture(scope='session')
def get_cmdopts(request):
    return {
        'track': request.config.getoption("--track"),
        'detail': request.config.getoption("--detail")
    }