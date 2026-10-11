# Daily Short: run book

Each daily run makes and publishes one Short for **Unreal But True**.

1. `bash pipeline/setup.sh` (skips downloads that already exist).
2. Pick the topic from data, not just the queue order:
   - Read the channel stats with my-youtube `get_my_channel_analytics` and
     `get_channel_videos` (they lag about 2 days). Note views, subs gained and
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
   - About 80 to 95 words of voiceover, 6 segments, a hook in the first line.
   - Plain title, no emoji, no hashtags in the title. `#shorts` goes in the description.
   - Check every number against a reliable source before using it.
   - Put numbers the voice must read in words in `say`.
   - Last line ends with "Unreal, but true. Subscribe."
4. Render: `python3 pipeline/make_short.py pipeline/specs/<slug>.json shorts/videos/<date>-<slug>.mp4`
5. Look at frames from the video before publishing (ffmpeg `-ss` grabs).
6. Commit the spec and video, push, then upload with my-youtube
   `upload_video_from_url` using
   `https://raw.githubusercontent.com/amahrous84/amahrous/<branch>/shorts/videos/<date>-<slug>.mp4`,
   category 28, privacy public.
7. Tick the topic in `queue.md` with the date and the video link, and commit.
