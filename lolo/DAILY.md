# Lolo daily run book

Each daily run makes one long video and one Short for **Lolo's Learning Lagoon**,
reviews how the earlier ones did, and queues the new ones only after Ahmed approves.
Nothing here touches Unreal But True.

## 1. Daily review BEFORE making anything (Ahmed asked for this on 2026-10-25)
- Push `lolo/publish/queue/<date>-stats.json` containing `{"stats": true}`; the
  GitHub job writes live counts and 14-day analytics for the last 10 uploads into
  `lolo/publish/done/`. Analytics lag about 2 days, so lean on live counts for new videos.
- For each recent video note: views, engaged views, average view % and duration,
  likes, shares, subscribers gained. Made for Kids videos have no comments, so
  watch time and returning viewers are the main signals.
- Compare with other kids channels using YouTube search and video stats:
  - Big references: Finny The Shark / Super Simple Songs (the style Ahmed pointed
    to), Cocomelon, Bounce Patrol, Jack Hartmann. Look at their titles, thumbnails,
    length and pacing for the same letter or number.
  - Small and new AI kids channels (for example the many "Little Lumo", "Moko and
    Friends", "BumbleBop" copies) as a realistic benchmark for a new channel.
  - Check what kids-learning videos from the last 7 days are getting views.
- Diagnose: low average view % means the video drags or the opening is slow;
  low views with good watch % means the title or thumbnail is the problem;
  Shorts with low engaged views mean the first 2 seconds lose kids.
- Write `lolo/reviews/<date>.md`: a small table, the main problem, the concrete fix,
  and what a comparison channel does better. Apply the fix in today's video.
- Fixes within the current format (topic order, song, wording, length, images,
  title, thumbnail, description, tags) go ahead without asking. Anything that
  raises cost noticeably, adds a tool or service, or changes the format or old
  videos needs Ahmed's approval on a decision card first.

## 2. Make today's videos
- Follow the order in `lolo/queue.md` (letters A to Z, numbers 1 to 20, mixed with
  ABC and counting songs), adjusted by what the review shows works.
- Lolo always looks the same: images via fal.ai `fal-ai/flux-pro/kontext` with
  `/mnt/project-files/characters/lolo-axolotl.png` as reference. Voice: Jessica, ElevenLabs v3 via fal.ai.

## 3. Thumbnail for every video (Ahmed asked for this on 2026-10-25)
- 1280 x 720 JPG under 2 MB. Lolo big and happy on one side, the letter or number
  huge and bright on the other, 1 to 3 words of text max ("Letter A!", "Count to 5!").
- Bright, high-contrast colors; readable at phone size. Compare with the
  thumbnails of the top 3 videos for the same search before finalising.
- Shorts use a frame from the video; the long video gets the custom thumbnail.

## 4. Approval and scheduling
- Post the video, Short and thumbnail in the thread for Ahmed's OK.
- After approval, write `lolo/publish/queue/<date>-<slug>.json` with
  `publish_at` (default 7:00 AM US Eastern), `thumbnail` and `playlist`, and push
  to the `lolo` branch. The workflow uploads it private and YouTube publishes it on time.
