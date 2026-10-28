# Daily Short: run book

Each daily run makes and publishes one Short for **Unreal But True**.
If `queue.md` already has a topic ticked with today's date, today's Short is done: post nothing new.

1. `bash pipeline/setup.sh` (skips downloads that already exist).
1b. Daily review BEFORE making anything (Ahmed asked for this on 2026-10-23):
   - For each of the last 7 Shorts read live views (`get_video_info`) and, from
     `get_my_channel_analytics` with dimensions=video: views, engagedViews,
     averageViewPercentage, averageViewDuration, likes, comments, shares,
     subscribersGained. If the PC is off, push `publish/queue/<date>-stats.json`
     containing `{"stats": true}`; the GitHub job writes the same numbers into
     `publish/done/`.
   - Diagnose each post: stayed % (engagedViews / views) under 60% means the opening
     loses people; watch % under 60% means the middle drags or it is too long; no
     comments means the closing question is weak; subs under 1% of views means no
     reason to subscribe. Compare with the best Shorts (Earth stopped, black hole).
   - Write `pipeline/reviews/<date>.md`: a small table, the main problem, and the
     concrete fix for today's video. Apply that fix in today's spec.
   - Fixes inside the current rules (topic, hook, wording, length, images, the
     opening clip, title, description, tags) go ahead without asking. Anything that
     costs more than about $0.30 a day, adds a tool or service, changes the series
     or format, or changes old videos (privacy, deletion, titles) needs Ahmed's
     approval first: ask on a decision card and keep to the current rules today.
   - Put the main finding and the fix in one line of the 7 pm reminder.
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
   - Topic lane (2026-10-23, Ahmed: "do whatever you advise"): space/cosmic disaster
     what-ifs only. No stickman, finance, psychology or Earth-only topics on this
     channel. No long videos for now (8 and 31 views); Shorts only.
3. Write `pipeline/specs/<slug>.json` (copy the shape of `specs/krakatoa.json`).
   - About 45 to 55 words of voiceover (about 20 seconds, never over 25), 4 or 5 segments.
     Live views 2026-10-23: 20-21 s Shorts beat 35-50 s ones.
     Shorts here stall near 1.5K because about half of viewers swipe away in the
     first seconds (engaged views are 40-50% of views, as of 2026-10-14). The
     21-second Short kept people best.
   - The first line is the hook and must land within 2 seconds: the strangest
     fact, said as a claim, no setup. Put the payoff number on screen at once.
   - The opening segment gets a `motion` line as well as `image` (Ahmed chose this
     2026-10-23: half of viewers swipe before the start). The maker animates that
     picture into a 5 s Kling clip on fal.ai (about $0.28, ~75 s to make). Describe big,
     clear movement (a planet breaking apart, a wave rising). Keep that segment under 5 s.
     Only the opening segment moves; the rest stay still pictures.
   - The first image must be bright, high-contrast and full of motion or
     colour (an explosion, glowing lava, a lit Earth). Never a mostly black frame.
   - Make it loop: the last line should lead straight back into the first, so a
     replay feels natural. Keep the sign-off short.
   - Numbered daily series (audit 2026-10-28: subscribe rate 0.24%, no reason to subscribe):
     opening `big` text is "WHAT IF #N" (N = count of what-if Shorts so far + 1), the line
     before the question is "Tomorrow: what if <next queued topic>?", the description starts
     with "A new what-if every day at 5:48 pm (Riyadh)." Use the yt-* skills in .claude/skills.
   - End with a direct question viewers can answer in one word (comments are ~0).
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
7. Make the thumbnail (every video gets one; Ahmed asked on 2026-10-20):
   `python3 pipeline/make_thumbnail.py "<bright picture prompt>" thumbnails/<slug>.jpg "BIG TEXT" "BADGE"`
   and look at it.
8. Publish through GitHub (works with Ahmed's PC off; tested 2026-10-23): write
   `publish/queue/<date>-<slug>.json` with video, thumbnail, title, description, tags,
   category_id "28", privacy_status "public"; commit it with the video and thumbnail
   and push. The Publish to YouTube job uploads, sets the thumbnail and moves the entry
   to `publish/done/` (with video_id) or `publish/failed/` (with the error). Wait a
   minute or two, pull, and read the result. Only if that fails, fall back to my-youtube
   `upload_video_from_url` + `set_thumbnail_from_url` (raw.githubusercontent links).
9. Tick the topic in `queue.md` with the date and the video link, and commit.
