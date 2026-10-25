# Lolo's Learning Lagoon

Everything for the kids channel lives in this folder and on the `lolo` branch,
kept apart from Unreal But True: its own queue, workflow and YouTube sign-in.

## How daily publishing works
1. A daily routine makes the next video (letters and numbers in order) and
   posts it for Ahmed's approval.
2. Once approved, it writes `lolo/publish/queue/<date>-<slug>.json` with a
   `publish_at` time (default 7:00 AM US Eastern) and pushes to `lolo`.
3. `.github/workflows/lolo-publish.yml` uploads it private, marked made for
   kids, and YouTube makes it public at `publish_at` by itself.
4. The entry moves to `lolo/publish/done/` with the video link.

## One-time setup
| Secret | Where it comes from |
|---|---|
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET` | Already in the repo for Unreal But True (same Google Cloud project). |
| `LOLO_YT_REFRESH_TOKEN` | Run `python lolo/tools/get_refresh_token.py client_secret.json`, sign in with the Lolo Gmail. |

Test the sign-in by pushing `lolo/publish/queue/signin-test.json` containing
`{"check": true}`; the result in `lolo/publish/done/` should name the Lolo channel.
The publisher refuses to upload if the signed-in channel is not Lolo's.
