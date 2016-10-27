from urllib.request import urlopen

from core import echo_console

from .paths import ADPURGE_DATA_PATH


CONNECTION_TIMEOUT = 2
TLDS_SOURCE_URL_TXT_PATH = ADPURGE_DATA_PATH / "tlds-source.url.txt"
TLDS_TXT_PATH = ADPURGE_DATA_PATH / "tlds.txt"


class TLDListUnavailableError(Exception):
    pass


with open(TLDS_SOURCE_URL_TXT_PATH) as f:
    TLDS_SOURCE_URL = f.read()


def download_tlds_list():
    try:
        with urlopen(TLDS_SOURCE_URL, timeout=CONNECTION_TIMEOUT) as request:
            tlds = request.read().decode('utf-8').split("\n")
    except OSError:
        return None

    # Remove empty strings and comments
    tlds = filter(lambda tld: tld and not tld.startswith("#"), tlds)

    # Make all domains lower-case
    tlds = map(lambda tld: tld.lower(), tlds)

    tlds = list(tlds)
    return tlds


def save_local_tlds_list(tlds):
    with open(TLDS_TXT_PATH, 'w') as f:
        f.write("\n".join(tlds))


def load_local_tlds_list():
    try:
        with open(TLDS_TXT_PATH) as f:
            return f.read().split('\n')
    except OSError:
        return None


echo_console("[AdPurge] Attempting to get TLD "
             "list from {url}...".format(url=TLDS_SOURCE_URL))

tlds = download_tlds_list()
if tlds is None:
    echo_console("[AdPurge] Couldn't get TLD list from the given url, "
                 "obtaining local copy...")

    tlds = load_local_tlds_list()
    if tlds is None:
        raise TLDListUnavailableError(
            "Top Level Domain list couldn't be obtained")
else:
    echo_console("[AdPurge] {number} domains were obtained from "
                 "the given url".format(number=len(tlds)))

    save_local_tlds_list(tlds)
