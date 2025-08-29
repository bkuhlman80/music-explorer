import re, math
from datetime import datetime
def parse_date(x):
    if not x or str(x).strip()=="":
        return None
    for fmt in ("%Y-%m-%d","%Y-%m","%Y"):
        try:
            dt = datetime.strptime(x, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def to_ms(x):
    if x in (None,"",float("nan")): return None
    try:
        v = int(x)
        return v if v>=0 else None
    except Exception:
        return None

UUID_RX = re.compile(r"^[0-9a-fA-F-]{36}$")
def is_uuid(x): return bool(x) and bool(UUID_RX.match(str(x)))

def norm_country(x):
    return str(x).upper() if x else None
