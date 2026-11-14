"""Check each PR commit for a sign-off that matches its author."""
import re
import subprocess
import sys


def main(base, head):
    if not all(re.fullmatch(r'[0-9a-fA-F]{40}', value) for value in (base, head)):
        raise ValueError('Full commit SHAs required')
    commits = subprocess.check_output(['git', 'rev-list', base + '..' + head], text=True).splitlines()
    for commit in commits:
        author = subprocess.check_output(['git', 'show', '-s', '--format=%an <%ae>', commit], text=True).strip()
        message = subprocess.check_output(['git', 'show', '-s', '--format=%B', commit], text=True)
        trailers = subprocess.check_output(['git', 'interpret-trailers', '--parse'], input=message, text=True)
        if f'Signed-off-by: {author}' not in trailers.splitlines():
            print(f'Missing author sign-off: {commit}', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:]))
