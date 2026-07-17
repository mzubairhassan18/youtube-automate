"""
YouTube Automate - Streamlit Web GUI
Stepper-based interface with Auto/Manual modes.
"""

import os
import sys
import json
import time
import streamlit as st
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.usage_tracker import UsageTracker
from src.script_generator import ScriptGenerator
from src.image_generator import ImageGenerator
from src.voiceover_generator import VoiceoverGenerator
from src.video_assembler import VideoAssembler
from src.shorts_creator import ShortsCreator
from src.youtube_uploader import YouTubeUploader

for d in ["output/images", "output/audio", "output/full_videos", "output/shorts", "output/scripts"]:
    Path(d).mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Bedtime Stories Automator", page_icon=":crescent_moon:", layout="wide")

STEPS = ["Configure", "Script", "Images", "Voiceover", "Video", "YouTube", "Done"]

def init_session():
    defaults = {
        "mode": "Auto",
        "current_step": 0,
        "script": None,
        "image_paths": [],
        "audio_paths": [],
        "video_path": None,
        "short_paths": [],
        "running": False,
        "completed_steps": [],
        "topic_from_queue": None,
        "youtube_result": None,
        "upload_privacy": "private",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


def reset_all():
    for k in ["script", "image_paths", "audio_paths", "video_path", "short_paths",
               "current_step", "completed_steps", "running", "topic_from_queue",
               "youtube_result"]:
        if k == "current_step":
            st.session_state[k] = 0
        elif k == "completed_steps":
            st.session_state[k] = []
        elif k in ("running", "topic_from_queue"):
            st.session_state[k] = False if k == "running" else None
        else:
            st.session_state[k] = [] if isinstance(st.session_state.get(k), list) else None


def render_stepper():
    step_html = '<div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap;">'
    for i, name in enumerate(STEPS):
        if i in st.session_state.get("completed_steps", []):
            bg, fg, icon = "#1b5e20", "#fff", "✓"
        elif i == st.session_state["current_step"]:
            bg, fg, icon = "#1565c0", "#fff", "●"
        else:
            bg, fg, icon = "#e0e0e0", "#666", str(i + 1)
        step_html += f'<div style="background:{bg};color:{fg};padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600;">{icon} {name}</div>'
    step_html += '</div>'
    st.markdown(step_html, unsafe_allow_html=True)


def sidebar():
    with st.sidebar:
        st.header("Quick Stats")
        usage = UsageTracker()
        status = usage.get_status()
        st.metric("Videos Today", status.get("videos_created", 0))
        st.metric("Shorts Today", status.get("shorts_created", 0))
        st.divider()
        can_create, reason = usage.can_create_video()
        if can_create:
            st.success("Ready to create!")
        else:
            st.error(reason)
        st.divider()
        st.caption("Groq + Edge TTS + Pollinations + FFmpeg")


def run_auto_pipeline(topic, age_group, duration, create_shorts, custom_prompt=None):
    """Run all steps automatically with progress tracking."""
    st.session_state.pop("topic_from_queue", None)
    st.session_state.pop("queue_duration", None)
    st.session_state.pop("queue_age_group", None)

    progress_bar = st.progress(0)
    status_text = st.empty()
    log_area = st.empty()

    def log(msg):
        status_text.info(msg)

    # Step 1: Script
    log("Generating script...")
    progress_bar.progress(3, text="Step 1/6: Generating script...")

    sg = ScriptGenerator()
    num_segments = max(10, duration * 2)
    script = sg.generate_script(
        topic, age_group, duration, "calm", num_segments=num_segments
    )
    if not script:
        st.error("Script generation failed. Check Groq quota.")
        st.session_state["running"] = False
        return
    st.session_state["script"] = script
    st.session_state["completed_steps"].append(1)
    progress_bar.progress(15, text="Step 1/6: Script generated!")
    log(f"Script ready: {len(script.get('segments', []))} segments")

    # Step 2: Images
    log("Generating images...")
    progress_bar.progress(18, text="Step 2/6: Generating images...")

    ig = ImageGenerator()
    prefix = "story_%d" % int(time.time())
    paths = ig.generate_images(script["segments"], output_prefix=prefix)
    st.session_state["image_paths"] = paths
    st.session_state["completed_steps"].append(2)
    progress_bar.progress(50, text="Step 2/6: Images generated!")
    log(f"Generated {len(paths)} images")

    # Step 3: Voiceover
    log("Generating voiceover...")
    progress_bar.progress(52, text="Step 3/6: Generating voiceover...")

    vg = VoiceoverGenerator()
    audio_paths = vg.generate_voiceover(script["segments"], output_prefix=prefix)
    st.session_state["audio_paths"] = audio_paths
    st.session_state["completed_steps"].append(3)
    progress_bar.progress(70, text="Step 3/6: Voiceover generated!")
    log(f"Generated {len(audio_paths)} audio segments")

    # Step 4: Video Assembly
    log("Assembling video...")
    progress_bar.progress(72, text="Step 4/6: Assembling video...")

    va = VideoAssembler()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in script.get("title", "video")[:30])
    output_file = "%s_%s.mp4" % (safe_title, timestamp)

    video_path = va.assemble_video(
        image_paths=paths,
        audio_paths=audio_paths,
        output_filename=output_file,
    )

    short_paths = []
    if create_shorts and video_path:
        log("Creating shorts...")
        sc = ShortsCreator()
        short_paths = sc.create_shorts(video_path, script, output_prefix="short_%s" % timestamp)

    if not video_path:
        st.error("Video assembly failed")
        st.session_state["running"] = False
        return

    st.session_state["video_path"] = video_path
    st.session_state["short_paths"] = short_paths
    usage = UsageTracker()
    usage.record_video_created(len(short_paths))
    st.session_state["completed_steps"].append(4)
    progress_bar.progress(85, text="Step 4/6: Video assembled!")

    # Step 5: YouTube Upload (conditional)
    auto_upload = st.session_state.get("auto_upload_yt", False)

    if auto_upload:
        log("Uploading to YouTube...")
        progress_bar.progress(87, text="Step 5/6: Uploading to YouTube...")

        uploader = YouTubeUploader()
        metadata = uploader.build_metadata_from_script(
            script, privacy=st.session_state.get("upload_privacy", "private")
        )

        yt_result = uploader.upload_video(
            video_path=video_path,
            title=metadata["title"],
            description=metadata["description"],
            tags=metadata["tags"],
            privacy_status=metadata["privacy_status"],
            made_for_kids=metadata["made_for_kids"],
        )

        if yt_result:
            st.session_state["youtube_result"] = yt_result
            st.session_state["completed_steps"].append(5)
            progress_bar.progress(98, text="Step 5/6: Uploaded to YouTube!")
            log(f"Uploaded: {yt_result['url']}")
        else:
            log("YouTube upload skipped (auth or quota issue)")
    else:
        st.session_state["completed_steps"].append(5)
        progress_bar.progress(95, text="Step 5/6: YouTube upload skipped (manual mode)")

    # Step 6: Done
    st.session_state["completed_steps"].append(6)
    progress_bar.progress(100, text="Complete!")
    st.session_state["current_step"] = 6
    st.session_state["running"] = False
    log("All done!")
    time.sleep(0.5)
    st.rerun()


def render_step_configure():
    st.subheader("Configuration")

    topic = st.text_input(
        "Story Topic",
        value=st.session_state.get("topic_from_queue", "") or "",
        placeholder="e.g., The Brave Little Sparrow",
        key="topic_input",
    )

    age_options = ["toddler", "preschool", "school_age", "preteen", "all_ages"]
    queue_age = st.session_state.get("queue_age_group", "all_ages")
    age_idx = age_options.index(queue_age) if queue_age in age_options else 4

    queue_dur = st.session_state.get("queue_duration", 5)

    col1, col2, col3 = st.columns(3)
    with col1:
        age_group = st.selectbox(
            "Age Group",
            age_options,
            index=age_idx,
            format_func=lambda x: {
                "toddler": "Toddler (1-3 yrs)",
                "preschool": "Preschool (3-5 yrs)",
                "school_age": "School Age (5-8 yrs)",
                "preteen": "Preteen (8-12 yrs)",
                "all_ages": "All Ages (universal)",
            }[x],
            key="age_group",
        )
    with col2:
        duration = st.slider("Duration (min)", 3, 15, queue_dur, key="duration")
    with col3:
        c3a, c3b = st.columns(2)
        with c3a:
            create_shorts = st.checkbox("Create Shorts", value=True, key="create_shorts")
        with c3b:
            upload_yt = st.checkbox("Auto Upload to YouTube", value=False, key="auto_upload_yt")

    mode = st.radio(
        "Mode",
        ["Auto", "Manual"],
        horizontal=True,
        help="Auto: one-click pipeline. Manual: edit each step.",
        key="mode_select",
    )
    st.session_state["mode"] = mode

    if not topic:
        st.info("Enter a topic to begin")
        return

    st.session_state.pop("queue_duration", None)
    st.session_state.pop("queue_age_group", None)

    if st.button("Start", type="primary", key="start_btn"):
        st.session_state["running"] = True
        st.session_state["topic_from_queue"] = None
        st.rerun()

    # Show final video preview after pipeline completes
    video_path = st.session_state.get("video_path")
    if video_path and os.path.exists(video_path) and st.session_state.get("current_step", 0) >= 4:
        st.divider()
        st.subheader("Video Preview")
        st.video(video_path)


def render_step_script():
    script = st.session_state.get("script")
    if not script:
        st.info("No script yet. Go back to Configure.")
        return

    st.subheader("Script")
    st.text_input("Title", value=script.get("title", ""), key="edit_title", disabled=(st.session_state["mode"] == "Auto"))
    st.text_area("Description", value=script.get("description", ""), key="edit_desc", disabled=(st.session_state["mode"] == "Auto"))

    for seg in script.get("segments", []):
        num = seg.get("segment_number", 0)
        with st.expander(f"Segment {num} ({seg.get('duration_seconds', 0)}s)", expanded=False):
            st.text_area("Narration", value=seg.get("narration", ""), height=100, key="narr_%d" % num,
                         disabled=(st.session_state["mode"] == "Auto"))
            st.text_area("Image Prompt", value=seg.get("image_prompt", ""), height=60, key="img_prompt_%d" % num,
                         disabled=(st.session_state["mode"] == "Auto"))

    if st.session_state["mode"] == "Manual":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Regenerate Script", key="regen_script"):
                st.session_state["script"] = None
                st.session_state["completed_steps"] = [s for s in st.session_state["completed_steps"] if s != 1]
                st.rerun()
        with c2:
            if st.button("Save Edits", key="save_edits"):
                st.success("Saved!")

    if st.button("Next →", key="next_script"):
        st.session_state["current_step"] = 2
        st.rerun()


def render_step_images():
    image_paths = st.session_state.get("image_paths", [])
    script = st.session_state.get("script")

    if not image_paths:
        if st.session_state["mode"] == "Manual":
            st.subheader("Generate Images")
            if script:
                for seg in script.get("segments", []):
                    num = seg.get("segment_number", 0)
                    prompt = seg.get("image_prompt", "")
                    edited = st.text_input(f"Prompt #{num}", value=prompt, key="manual_prompt_%d" % num)
                    seg["image_prompt"] = edited

            if st.button("Generate Images", type="primary", key="gen_images_manual"):
                with st.spinner("Generating images..."):
                    ig = ImageGenerator()
                    prefix = "story_%d" % int(time.time())
                    paths = ig.generate_images(script["segments"], output_prefix=prefix)
                    st.session_state["image_paths"] = paths
                    st.session_state["completed_steps"].append(2)
                    st.success(f"Generated {len(paths)} images!")
                    st.rerun()
        else:
            st.info("Images not generated yet")
        return

    st.subheader("Images")
    cols = st.columns(min(4, len(image_paths)))
    for idx, p in enumerate(image_paths):
        with cols[idx % len(cols)]:
            if os.path.exists(p):
                st.image(p, caption=f"Scene {idx + 1}", use_container_width=True)

    if st.session_state["mode"] == "Manual":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Regenerate Images", key="regen_imgs"):
                st.session_state["image_paths"] = []
                st.session_state["completed_steps"] = [s for s in st.session_state["completed_steps"] if s != 2]
                st.rerun()
        with c2:
            uploaded = st.file_uploader(
                "Upload custom images",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="upload_imgs",
            )
            if uploaded and st.button("Use Uploaded", key="use_uploaded"):
                img_dir = Path("./output/images")
                paths = []
                for idx, f in enumerate(uploaded):
                    out = img_dir / ("upload_%03d.png" % (idx + 1))
                    with open(out, "wb") as fp:
                        fp.write(f.read())
                    paths.append(str(out))
                st.session_state["image_paths"] = paths
                st.success(f"Loaded {len(paths)} images!")
                st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", key="back_img"):
            st.session_state["current_step"] = 1
            st.rerun()
    with c2:
        if st.button("Next →", key="next_img"):
            st.session_state["current_step"] = 3
            st.rerun()


def render_step_audio():
    audio_paths = st.session_state.get("audio_paths", [])

    if not audio_paths:
        if st.session_state["mode"] == "Manual":
            st.subheader("Generate Voiceover")
            if st.button("Generate Voiceover", type="primary", key="gen_audio_manual"):
                with st.spinner("Generating voiceover with Edge TTS..."):
                    script = st.session_state["script"]
                    vg = VoiceoverGenerator()
                    prefix = "story_%d" % int(time.time())
                    paths = vg.generate_voiceover(script["segments"], output_prefix=prefix)
                    st.session_state["audio_paths"] = paths
                    st.session_state["completed_steps"].append(3)
                    st.success(f"Generated {len(paths)} audio segments!")
                    st.rerun()
        else:
            st.info("Voiceover not generated yet")
        return

    st.subheader("Voiceover")
    for idx, p in enumerate(audio_paths):
        if os.path.exists(p):
            st.audio(p, format="audio/wav")

    if st.session_state["mode"] == "Manual":
        if st.button("Regenerate Voiceover", key="regen_audio"):
            st.session_state["audio_paths"] = []
            st.session_state["completed_steps"] = [s for s in st.session_state["completed_steps"] if s != 3]
            st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", key="back_audio"):
            st.session_state["current_step"] = 2
            st.rerun()
    with c2:
        if st.button("Next →", key="next_audio"):
            st.session_state["current_step"] = 4
            st.rerun()


def render_step_video():
    script = st.session_state.get("script")
    image_paths = st.session_state.get("image_paths", [])
    audio_paths = st.session_state.get("audio_paths", [])

    if not script or not image_paths or not audio_paths:
        st.info("Complete previous steps first")
        return

    st.subheader("Assemble Video")

    if st.button("Assemble Video", type="primary", key="assemble_btn"):
        with st.spinner("Assembling video..."):
            va = VideoAssembler()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c if c.isalnum() else "_" for c in script.get("title", "video")[:30])
            output_file = "%s_%s.mp4" % (safe_title, timestamp)

            video_path = va.assemble_video(
                image_paths=image_paths,
                audio_paths=audio_paths,
                output_filename=output_file,
            )

            short_paths = []
            create_shorts = st.session_state.get("create_shorts", True)
            if create_shorts and video_path:
                sc = ShortsCreator()
                short_paths = sc.create_shorts(video_path, script, output_prefix="short_%s" % timestamp)

            if video_path:
                st.session_state["video_path"] = video_path
                st.session_state["short_paths"] = short_paths
                usage = UsageTracker()
                usage.record_video_created(len(short_paths))
                st.session_state["completed_steps"].append(4)
                st.success("Video assembled!")
                st.rerun()
            else:
                st.error("Video assembly failed")

    if st.button("← Back", key="back_video"):
        st.session_state["current_step"] = 3
        st.rerun()

    video_path = st.session_state.get("video_path")
    if video_path and st.button("Next → Upload to YouTube", key="next_video"):
        st.session_state["current_step"] = 5
        st.rerun()


def render_step_youtube():
    video_path = st.session_state.get("video_path")
    script = st.session_state.get("script")
    youtube_result = st.session_state.get("youtube_result")

    if not video_path:
        st.info("Complete video assembly first")
        return

    st.subheader("Upload to YouTube")
    st.caption("Channel: Dreamland Narrations (@DreamlandNarrations)")

    if youtube_result:
        st.success("Already uploaded!")
        st.markdown(f"**[{youtube_result['title']}]({youtube_result['url']})**")
        st.caption(f"Video ID: {youtube_result['video_id']}")
        if youtube_result.get("thumbnail_set"):
            st.info("Thumbnail set")
    else:
        if script:
            uploader = YouTubeUploader()
            metadata = uploader.build_metadata_from_script(script, privacy="private")

            with st.expander("Preview Metadata", expanded=True):
                st.text_input("Title", value=metadata["title"], key="yt_title", disabled=True)
                st.text_area("Description", value=metadata["description"], height=150, key="yt_desc", disabled=True)
                st.text_area("Tags", value=", ".join(metadata["tags"]), key="yt_tags", disabled=True)

            privacy = st.selectbox("Privacy", ["private", "unlisted", "public"], key="yt_privacy")
            st.session_state["upload_privacy"] = privacy

            if st.button("Upload to YouTube", type="primary", key="yt_upload_btn"):
                with st.spinner("Authenticating with YouTube..."):
                    uploader = YouTubeUploader()
                    metadata = uploader.build_metadata_from_script(script, privacy=privacy)

                    with st.spinner("Uploading video..."):
                        result = uploader.upload_video(
                            video_path=video_path,
                            title=metadata["title"],
                            description=metadata["description"],
                            tags=metadata["tags"],
                            privacy_status=privacy,
                            made_for_kids=True,
                        )

                        if result:
                            st.session_state["youtube_result"] = result
                            st.success("Uploaded!")
                            st.rerun()
                        else:
                            st.error("Upload failed. Check logs.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", key="back_yt"):
            st.session_state["current_step"] = 4
            st.rerun()
    with c2:
        if st.button("Done", key="done_yt"):
            st.session_state["current_step"] = 6
            st.rerun()


def render_step_done():
    video_path = st.session_state.get("video_path")
    short_paths = st.session_state.get("short_paths", [])
    youtube_result = st.session_state.get("youtube_result")

    st.subheader("All Done!")

    if youtube_result:
        st.success(f"Uploaded to YouTube: [{youtube_result['title']}]({youtube_result['url']})")
        st.caption(f"Video ID: {youtube_result['video_id']} | Privacy: {youtube_result.get('privacy', 'private')}")

    if video_path and os.path.exists(video_path):
        info = VideoAssembler().get_video_info(video_path)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.video(video_path)
        with col2:
            st.metric("Duration", "%ds" % info.get("duration", 0))
            st.metric("Size", "%.1f MB" % info.get("size_mb", 0))
            st.caption(Path(video_path).name)

    if short_paths:
        st.subheader("YouTube Shorts")
        cols = st.columns(min(3, len(short_paths)))
        for idx, sp in enumerate(short_paths[:3]):
            with cols[idx]:
                if os.path.exists(sp):
                    st.video(sp)
                st.caption("Short %d" % (idx + 1))

    if st.button("Create Another", key="new_video"):
        reset_all()
        st.rerun()


def render_topics_tab():
    st.header("Story Topics Queue")
    topics_path = Path("./config/topics.json")
    topics = []
    if topics_path.exists():
        with open(topics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            topics = data.get("topics", [])

    if not topics:
        st.info("No topics yet.")
        return

    for t in topics:
        with st.container():
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1:
                st.write(f"**{t['title']}**")
                st.caption(f"{t.get('category', 'general')} | {', '.join(t.get('age_groups', []))} | {t.get('duration_minutes', 5)}min")
            with c2:
                status = t.get("status", "pending")
                color = "green" if status == "done" else "orange" if status == "in_progress" else "gray"
                st.markdown(f":{color}[{status}]")
            with c3:
                if st.button("Generate", key="gen_%d" % t["id"], disabled=(status == "done")):
                    st.session_state["topic_from_queue"] = t["title"]
                    st.session_state["queue_duration"] = t.get("duration_minutes", 5)
                    st.session_state["queue_age_group"] = (t.get("age_groups") or ["all_ages"])[0]
                    st.session_state["mode"] = "Auto"
                    st.session_state["current_step"] = 0
                    st.session_state["running"] = True
                    st.rerun()

    st.divider()
    st.subheader("Add Topic")
    with st.form("add_topic"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Title")
            cat = st.selectbox("Category", [
                "islamic_history", "western_history", "motivational",
                "moral_stories", "animal_fables", "fairy_tales",
                "prophets_stories", "companion_stories",
            ])
        with c2:
            ages = st.multiselect("Age Groups", ["toddler", "preschool", "school_age", "preteen"], default=["preschool"])
            dur = st.slider("Duration (min)", 3, 15, 5)

        if st.form_submit_button("Add Topic"):
            if title:
                topics.append({
                    "id": len(topics) + 1, "title": title, "category": cat,
                    "age_groups": ages, "duration_minutes": dur, "status": "pending",
                    "priority": len(topics) + 1,
                })
                out = {"metadata": {"version": "1.0", "last_updated": datetime.now().isoformat()}, "topics": topics}
                with open(topics_path, "w", encoding="utf-8") as f:
                    json.dump(out, f, indent=2, ensure_ascii=False)
                st.success("Added!")
                st.rerun()


def render_api_tab():
    st.header("API Status")
    usage = UsageTracker()
    status = usage.get_status()

    col1, col2, col3 = st.columns(3)
    col1.metric("Videos", status.get("videos_created", 0))
    col2.metric("Shorts", status.get("shorts_created", 0))
    col3.metric("Date", status.get("date", "N/A"))

    st.divider()
    for service, info in status.get("services", {}).items():
        with st.expander(service.upper()):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Used", info.get("used", 0))
            c2.metric("Limit", info.get("limit", "N/A"))
            c3.metric("Remaining", info.get("remaining", "N/A"))
            c4.metric("Usage %%", "%s%%" % info.get("percent", 0))
            if info.get("limit") != "unlimited":
                st.progress(info.get("percent", 0) / 100)

    if st.button("Refresh"):
        st.rerun()


def render_youtube_test_tab():
    st.header("YouTube Upload Test")
    st.caption("Test upload any video file to Dreamland Narrations")

    # Check auth status
    from src.youtube_uploader import YouTubeUploader, TOKEN_PATH

    if not TOKEN_PATH.exists():
        st.warning("Not authenticated yet. Run `python auth_youtube.py` from terminal first, or click below.")
        if st.button("Authenticate with YouTube", type="primary", key="yt_auth_btn"):
            u = YouTubeUploader()
            if u.authenticate():
                st.success("Authenticated!")
                st.rerun()
            else:
                st.error("Auth failed")
        return

    st.success("YouTube authenticated")

    # Show channel info
    u = YouTubeUploader()
    if u.authenticate():
        try:
            resp = u.youtube.channels().list(part="snippet,statistics", mine=True).execute()
            if resp["items"]:
                ch = resp["items"][0]
                st.info(f"Channel: **{ch['snippet']['title']}** | Subscribers: {ch['statistics'].get('subscriberCount', '0')} | Videos: {ch['statistics'].get('videoCount', '0')}")
        except Exception:
            st.info("Channel: Dreamland Narrations (@DreamlandNarrations)")

    st.divider()

    # Video file selector
    video_dir = Path("./output/full_videos")
    video_files = list(video_dir.glob("*.mp4")) if video_dir.exists() else []

    # Also check output root for any mp4
    root_videos = list(Path("./output").glob("*.mp4"))
    all_videos = video_files + root_videos

    col1, col2 = st.columns([2, 1])

    with col1:
        if all_videos:
            selected = st.selectbox(
                "Select video to upload",
                all_videos,
                format_func=lambda x: f"{x.name} ({x.stat().st_size // 1024 // 1024}MB)",
                key="test_vid_select",
            )
        else:
            st.info("No videos found in output/")
            uploaded = st.file_uploader("Or upload a video file", type=["mp4", "mkv", "avi", "webm"], key="test_vid_upload")
            if uploaded:
                save_path = video_dir / uploaded.name
                with open(save_path, "wb") as f:
                    f.write(uploaded.read())
                st.success(f"Saved: {save_path}")
                st.rerun()
            selected = None

    with col2:
        privacy = st.selectbox("Privacy", ["private", "unlisted", "public"], key="test_privacy")

    if selected or (not all_videos and 'test_vid_upload' not in st.session_state):
        pass

    # Metadata
    st.subheader("Metadata")
    title = st.text_input("Title", value="Bedtime Story for Kids - Dreamland Narrations", key="test_title")
    description = st.text_area("Description", value="A magical bedtime story for kids. Subscribe to Dreamland Narrations for more!\n\n#bedtimestory #kidsstory #dreamlandnarrations", height=120, key="test_desc")
    tags = st.text_input("Tags (comma separated)", value="bedtime story, kids story, children story, dreamland narrations, fairy tale, sleep story", key="test_tags")

    st.divider()

    if st.button("Upload to YouTube", type="primary", key="test_upload_btn"):
        video_path = str(selected) if selected else None
        if not video_path:
            st.error("Select or upload a video first")
            return

        with st.spinner("Uploading..."):
            u = YouTubeUploader()
            result = u.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=[t.strip() for t in tags.split(",") if t.strip()],
                privacy_status=privacy,
                made_for_kids=True,
            )

            if result:
                st.success("Uploaded!")
                st.markdown(f"**[{result['title']}]({result['url']})**")
                st.caption(f"Video ID: {result['video_id']}")
            else:
                st.error("Upload failed. Check logs.")


def main():
    st.title("Bedtime Stories Automator")
    sidebar()

    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "Create Video"

    tab_names = ["Create Video", "YouTube Test", "API Status", "Topics Queue"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_names)

    with tab1:
        render_stepper()

        mode = st.session_state.get("mode", "Auto")
        step = st.session_state["current_step"]

        if mode == "Auto" and st.session_state.get("running"):
            topic = st.session_state.get("topic_from_queue") or st.session_state.get("topic_input", "")
            age_group = st.session_state.get("queue_age_group") or st.session_state.get("age_group", "all_ages")
            duration = st.session_state.get("queue_duration") or st.session_state.get("duration", 5)
            create_shorts = st.session_state.get("create_shorts", True)
            run_auto_pipeline(topic, age_group, duration, create_shorts)
            return

        if step == 0:
            render_step_configure()
        elif step == 1:
            render_step_script()
        elif step == 2:
            render_step_images()
        elif step == 3:
            render_step_audio()
        elif step == 4:
            render_step_video()
        elif step == 5:
            render_step_youtube()
        elif step == 6:
            render_step_done()

    with tab2:
        render_youtube_test_tab()
    with tab3:
        render_api_tab()
    with tab4:
        render_topics_tab()


if __name__ == "__main__":
    main()
