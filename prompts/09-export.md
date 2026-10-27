# Step 9 · Export the MP4

Don't ask it to "export the HTML to MP4": it loses the design. Say exactly this:

```
Export the video. Open each board in Chrome and record every single frame at
30 fps on a virtual clock (no screen recording, it drops frames). Then join the
frames into a video with FFmpeg, with my voice.
Split the render into parts and run 6 workers at once. Save each part as MKV,
not MP4, so a stopped render can still be opened.
Render the first 60 seconds first so I can check it.
At the end, check the number of frames matches the length of the video.
```
