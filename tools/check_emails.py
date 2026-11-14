"""Keep fixture emails synthetic; permit approved identities only in Git metadata."""
import re
import subprocess
import sys
from pathlib import Path

AUTHOR = "Collin Craig <5287878+CollinCraig@users.noreply.github.com>"
COAUTHOR = "Claude Opus 5.5 <noreply@anthropic.com>"
EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def fixture_emails_allowed(text):
    return all(email.rsplit('@', 1)[1] == 'example.invalid' for email in EMAIL.findall(text))


def metadata_allowed(author, committer, message):
    if any(identity != AUTHOR and not fixture_emails_allowed(identity) for identity in (author, committer)):
        return False
    allowed_trailers = {'Signed-off-by: ' + AUTHOR, 'Co-Authored-By: ' + COAUTHOR}
    trailers = subprocess.check_output(['git', 'interpret-trailers', '--parse'], input=message, text=True).splitlines()
    for line in message.splitlines():
        if line in allowed_trailers and line in trailers:
            continue
        if not fixture_emails_allowed(line):
            return False
    return True


def main(base, head):
    if not all(re.fullmatch(r'[0-9a-fA-F]{40}', value) for value in (base, head)):
        raise ValueError('Full commit SHAs required')
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--', 'tests', 'examples', 'contract/examples']).split(b'\0')
    for raw_path in filter(None, paths):
        path = Path(raw_path.decode())
        if not fixture_emails_allowed(path.read_text()):
            print(f'Non-synthetic fixture email in {path}', file=sys.stderr)
            return 1
    commits = subprocess.check_output(['git', 'rev-list', base + '..' + head], text=True).splitlines()
    for commit in commits:
        fields = subprocess.check_output(['git', 'show', '-s', '--format=%an <%ae>%x00%cn <%ce>%x00%B', commit], text=True).split('\0', 2)
        if not metadata_allowed(*fields):
            print(f'Unapproved metadata email in {commit}', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:]))
