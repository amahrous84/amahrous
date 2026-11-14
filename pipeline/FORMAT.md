# Daily Short format rules (from the 2026-11-14 ceiling study)

## Series from 2026-11-14: big real events (Ahmed's choice)
Ahmed chose on 2026-11-14 to change the idea: the daily Short is now a real event that sounds
impossible, shown with a number that proves it. The space "what if" comparisons stop (#12 was the
last). Topics and the facts to verify are in pipeline/events-queue.md. Why this idea: Krakatoa
("The Loudest Sound in History") is one of the two best Shorts (1,551 views) and 21% of its views
came from YouTube search, which keeps paying after day one; plain event titles get searched.
- Still drawn in code (maps, rings, scale bars, counters). No AI images or AI video.
- Each Short shows ONE event and ONE measurement growing on screen: a shockwave ring crossing a
  map, a plume rising past Everest and airliner height, a wave climbing past a skyscraper.
- Title = the plain thing people search ("The Wave Taller Than the Empire State Building"),
  no numbering in the title. On-screen corner tag: UNREAL BUT TRUE.
- Every number is checked against two sources and listed in the description. Deaths and injuries
  are stated plainly and never played for excitement.
- All the rules below still apply; they are what the ceiling study says matters most.

## Why these rules exist
Every Short gets one test batch of about 1,000 to 1,500 plays from the Shorts feed, then stops.
The batch size is almost the same whatever we post (12 Shorts checked, 106 to 1,573 views), and
no Short has cleared the test. In the test batch:
- 40-60% of viewers stay past the start (engaged views / views). Breakouts need about 70%+.
- Relative retention in the first third of the video is 0.26-0.56 (0.5 = the typical YouTube
  video of the same length). We are average or below exactly where the feed decides.
- Shares are 0 on almost every Short, comments 0-1, likes 1-5%.
So views cannot tell us which Short was better; the first two seconds decide everything.
WHAT IF #12 (Earth doubling) opened with 2.8 s of title text over a small, slow Earth: it broke
rules 1, 2 and 5 below and landed at the same ceiling (1,312 plays in 15 h).

## The rules (check every one before publishing)
1. **Action in frame 0.** No title card, no fade-in, no establishing shot. The counter is already
   running and something is already moving. A visible change within 0.5 s.
2. **Subject fills the frame.** The main object covers at least 40% of the frame height in the
   first frame. Bright and high contrast. Never a mostly black or empty first second.
3. **Show the target from the start.** The thing the viewer is waiting for (the Sun, the finish
   line, the last planet) is on screen in frame 0 with the gap visibly closing, plus 2-4 words
   that name it ("WAIT FOR THE SUN"). The question sits on top of the action as text.
4. **Guess prompt in the first 2 s.** One short on-screen line that makes the viewer commit to an
   answer ("GUESS THE SECOND"). The description and the last frame ask if they were right.
5. **A beat every second.** A new visible event at least every 1.0-1.5 s: a pop, a label, an
   object swallowed, a number milestone. No smooth slow zoom with nothing happening.
6. **9 to 13 seconds.** End on the payoff number. No outro card longer than 0.7 s.
7. **Seamless loop.** The last frame cuts straight back to the first, so replays count.
8. **Voice starts within 0.2 s.** First line is 7 words or fewer. 2-3 lines in total. No music.
9. **Same look every day.** Same font, colours, counter position and WHAT IF #N tag, so the feed
   learns one audience for the channel.
10. **Numbers on screen match the timer.** Any "X times bigger" figure is computed for the time
    shown on that frame (in #12 the end card said 216x at a 15.0 s timer; 216x was true at 14.5 s).

## Frame check (required)
Before publishing, export the frames at 0.0, 0.5, 1.0 and 2.0 s and confirm rules 1-5 by eye.
Do not publish a Short that fails rule 1, 2 or 3; fix it first.

## How to judge a Short (views are capped by the test batch)
Use a `{"deep": ["<video id>", ...]}` entry in publish/queue/ two days after upload. Log in
pipeline/performance.md, per Short:
- stayed = engaged views / views. Now 40-60%. Target 70%+.
- relative retention between 5% and 30% of the video. Now 0.26-0.56. Target 0.65+.
- average percentage viewed. Target above 100% (loops).
- shares and comments.
Change one thing per day (hook wording, first-frame layout, length) and note what changed, so the
numbers show which change moved "stayed". A Short that passes 3,000 views has cleared the test:
repeat its opening exactly.
