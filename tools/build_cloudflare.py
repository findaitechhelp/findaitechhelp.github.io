"""Fail-closed Cloudflare Pages build: checks finish before output is deployable."""
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'site'))
from pages import public_site_origin

def main():
    try:
        if os.environ.get('CF_PAGES') and not os.environ.get('PUBLIC_SITE_ORIGIN'):
            raise ValueError('Cloudflare deployment requires explicit PUBLIC_SITE_ORIGIN.')
        public_site_origin(learning_review=True)
    except ValueError as error:
        print(str(error),file=sys.stderr)
        return 1
    commands=[
        [sys.executable,'tools/validate.py'],
        [sys.executable,'-m','unittest','discover','tests','-v'],
    ]
    # This final gate builds public review and inspects the exact resulting dist.
    commands.append([sys.executable,'tools/check_public_review.py'])
    for command in commands:
        try:
            subprocess.run(command,cwd=ROOT,check=True)
        except (subprocess.CalledProcessError,OSError) as error:
            print('Cloudflare build stopped: '+str(error),file=sys.stderr)
            return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
