"""Active window's helper for Linux."""
import re
import subprocess


def get_active_window_title():
    """Return the tittle of the active window."""
    # Based on: https://askubuntu.com/questions/1199306/python-get-foreground-application-name-in-ubuntu-19-10
    root = subprocess.Popen(
        ["xprop", "-root", "_NET_ACTIVE_WINDOW"], stdout=subprocess.PIPE
    )
    stdout, stderr = root.communicate()
    m = re.search(b"^_NET_ACTIVE_WINDOW.* ([\w]+)$", stdout)
    if m != None:
        window_id = m.group(1)
        window = subprocess.Popen(
            ["xprop", "-id", window_id, "WM_NAME"], stdout=subprocess.PIPE
        )
        stdout, stderr = window.communicate()
    else:
        return None

    match = re.match(b"WM_NAME\(\w+\) = (?P<name>.+)$", stdout)
    if match != None:
        return match.group("name").strip(b'"').decode("utf-8")

    return None


if __name__ == "__main__":
    print(get_active_window_title())
