# Daily Short: run book

Each daily run makes and publishes one Short for **Unreal But True**.
If `queue.md` already has a topic ticked with today's date, today's Short is done: post nothing new.

1. `bash pipeline/setup.sh` (skips downloads that already exist).
2. Pick the topic from data, not just the queue order:
   - Read the channel stats with my-youtube `get_my_channel_analytics` and
     `get_channel_videos` (analytics lag about 2 days, so also read live view
     counts with `get_video_info` for Shorts from the last 3 days). Note views, subs gained and
     subscribe rate per Short in `performance.md`.
   - See which themes win (space, Earth, history, the body, myth-busting) and
     which flop, and lean the next topics toward the winners.
   - Check what is trending in the niche on YouTube search (Shorts from the last
     7 days on candidate topics: median and top views). Skip topics flooded with
     recent copies.
   - Reorder or replace entries in `queue.md` to match, then take the top one.
     Write one line in `performance.md` on why it was picked.
   - Target: a 7-day average of 1,000+ views per Short and a subscribe rate of
     1% or more. Until both hold, keep changing topics and hooks; once they
     hold, keep the formula and keep checking weekly.
3. Write `pipeline/specs/<slug>.json` (copy the shape of `specs/krakatoa.json`).
   - About 50 to 65 words of voiceover (20 to 25 seconds), 4 or 5 segments.
     Shorts here stall near 1.5K because about half of viewers swipe away in the
     first seconds (engaged views are 40-50% of views, as of 2026-10-14). The
     21-second Short kept people best.
   - The first line is the hook and must land within 2 seconds: the strangest
     fact, said as a claim, no setup. Put the payoff number on screen at once.
   - The first image must be bright, high-contrast and full of motion or
     colour (an explosion, glowing lava, a lit Earth). Never a mostly black frame.
   - Make it loop: the last line should lead straight back into the first, so a
     replay feels natural. Keep the sign-off short.
   - One line that invites a reply or a share (a question, "send this to
     someone who..."), because shares are currently zero.
   - Plain title, no emoji, no hashtags in the title. `#shorts` goes in the description.
   - Check every number against a reliable source before using it.
   - Put numbers the voice must read in words in `say`.
   - Give every segment an `image` prompt: one concrete, realistic scene, no text in
     the picture. The Short maker makes it with fal.ai FLUX schnell (about $0.004 each,
     needs FAL_KEY) and adds a slow zoom. Use a drawn `scene` (map, globe, counter)
     instead only where a diagram explains better than a photo.
   - Last line ends with "Unreal, but true." (add "Subscribe." only if it still loops).
4. Voice it with ElevenLabs (Ahmed asked for this on 2026-10-15, replacing Kokoro).
   Since 2026-10-16 the ElevenLabs connector refuses most lines ("Free Tier access has
   been disabled"), so use ElevenLabs through fal.ai instead: POST
   `https://fal.run/fal-ai/elevenlabs/tts/eleven-v3` with header `Authorization: Key $FAL_KEY`
   and body `{"text": <say or text>, "voice": "TX3LPaxmHKxFdv7VOQHJ"}`; download
   `audio.url` (swap host v3b.fal.media for v3.fal.media) to `pipeline/audio/<slug>/NN.mp3`.
   The connector steps below are the old route, only if fal.ai fails:
   - For each segment, call the ElevenLabs connector `creative_generate_speech` with
     the segment's `say` (or `text`), model `eleven_v4`, voice "Liam - Energetic, Social Media
     Creator" (voice_id `TX3LPaxmHKxFdv7VOQHJ`, Ahmed picked it 2026-10-15), `generations_count` 1. Never
     re-call to retry a slow one; poll `creative_get_flow_run_status` instead.
   - Download each `content_url` (storage.googleapis.com, reachable from the cloud)
     to `pipeline/audio/<slug>/NN.mp3` and set that path as the segment's `audio`.
   - About 350 credits per Short. If the connector is missing or fails, render with
     Kokoro (leave `audio` out) and say so in the 7 pm reminder.
5. Render: `python3 pipeline/make_short.py pipeline/specs/<slug>.json shorts/videos/<date>-<slug>.mp4`
6. Look at frames from the video before publishing (ffmpeg `-ss` grabs).
7. Commit the spec and video, push, then upload with my-youtube
   `upload_video_from_url` using
   `https://raw.githubusercontent.com/amahrous84/amahrous/<branch>/shorts/videos/<date>-<slug>.mp4`,
   category 28, privacy public.
8. Tick the topic in `queue.md` with the date and the video link, and commit.
