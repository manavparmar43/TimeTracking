import sys

from chrome import get_chrome_history_data
from firefox import get_firefox_history_data

if sys.platform in ["darwin"]:
    from safari import get_safari_history_data

    get_safari_history_data()

get_chrome_history_data()
get_firefox_history_data()

print("¯\_(ツ)_/¯")
