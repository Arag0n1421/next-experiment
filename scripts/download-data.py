"""Download the public source matrix and verify its exact SHA256."""
import hashlib
import time
from pathlib import Path
from urllib.request import urlopen

DEST = Path(__file__).resolve().parents[1] / 'data/countmatrix.xlsx'
URL = 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE268nnn/GSE268569/suppl/GSE268569_CountMatrix.xlsx'
EXPECTED = '64bb772834a1bacc0304826277546b9a2ec06972ead229ef5687b3fdc7cb6fe1'
if DEST.exists():
    if hashlib.sha256(DEST.read_bytes()).hexdigest() != EXPECTED:
        raise SystemExit('Existing matrix differs; preserve and inspect it before replacing.')
    print('Verified existing source matrix.')
else:
    # NCBI occasionally returns an empty HTTP 200 response. An HTTP status alone
    # is not successful delivery; every attempt must pass the content hash.
    error = ''
    for attempt in range(3):
        try:
            with urlopen(URL, timeout=30) as response:
                data = response.read(10_000_001)
            actual = hashlib.sha256(data).hexdigest()
            if actual == EXPECTED:
                break
            error = f'{len(data)} bytes; SHA256 {actual}'
        except OSError as exc:
            error = str(exc)
        if attempt < 2:
            time.sleep(attempt + 1)
    else:
        raise SystemExit(f'Source verification failed after three attempts ({error}); no matrix was installed.')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_bytes(data)
    print('Downloaded and hash-verified public source matrix.')
