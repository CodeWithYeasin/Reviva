---
title: Reviva
emoji: "✨"
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
license: mit
short_description: AI photo enhancer - upscale and restore faces. Nothing stored.
---

# Reviva

Open-source AI photo & video enhancer. No database, no sign-in: your upload is
processed in memory and discarded the moment the result is sent back.

- `/` - the React UI
- `/gradio` - minimal Gradio UI (and a free auto-generated API)
- `/api/enhance/photo` - `POST` multipart: `file`, `restore_faces`
- `/health` - liveness probe

Models: [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) for upscaling,
[GFPGAN](https://github.com/TencentARC/GFPGAN) for face restoration.

This Space runs on free CPU hardware, so a photo takes roughly 20-60 seconds
and the very first request also downloads the model weights. For GPU speed,
run it yourself: **https://github.com/CodeWithYeasin/Reviva**
