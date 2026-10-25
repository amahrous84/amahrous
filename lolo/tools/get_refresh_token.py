#!/usr/bin/env python3
"""One-time sign-in for the Lolo's Learning Lagoon channel.

Run this on your own computer, sign in with the Lolo Gmail (not your
Unreal But True account), and pick the Lolo channel if Google asks. It prints
a refresh token: paste that into the GitHub secret LOLO_YT_REFRESH_TOKEN.

    pip install google-auth-oauthlib
    python lolo/tools/get_refresh_token.py path/to/client_secret.json

Use the same client_secret.json (OAuth client of type "Desktop app") that the
Unreal But True tools already use. If its Google Cloud consent screen is in
"Testing", add the Lolo Gmail as a test user first, and switch it to
"In production": in Testing, Google expires refresh tokens after 7 days.
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/yt-analytics.readonly',
]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    creds = flow.run_local_server(port=0, prompt='consent', access_type='offline')
    print('\nSigned in. Copy everything on the next line into the GitHub secret '
          'LOLO_YT_REFRESH_TOKEN:\n')
    print(creds.refresh_token)


if __name__ == '__main__':
    main()
