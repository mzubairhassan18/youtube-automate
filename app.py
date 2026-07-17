"""
YouTube Automate - Streamlit Web GUI
Full-featured interface for bedtime stories automation.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import streamlit as st
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))

from src.usage_tracker import UsageTracker
from src.script_generator import ScriptGenerator
from src.image_generator import ImageGenerator
from src.voiceover_generator import VoiceoverGenerator
from src.video_assembler import VideoAssembler
from src.shorts_creator import ShortsCreator
from src.script_generator import SYSTEM_PROMPT

for d in ["output/images", "output/audio", "output/full_videos", "output/shorts", "output/scripts"]:
    Path(d).mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Bedtime Stories Automator", page_icon=":crescent_moon:", layout="wide")


def init_session():
    defaults = {
        "mode": "Auto",
        "script": None,
        "image_paths": [],
        "audio_paths": [],
        "video_path": None,
        "short_paths": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


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
        st.caption("Groq + Edge TTS + FFmpeg")


def render_create_tab():
    st.header("Create New Video")

    mode = st.radio(
        "Mode",
        ["Auto", "Manual"],
        horizontal=True,
        help="Auto: fully automatic. Manual: review and edit each step.",
    )
    st.session_state["mode"] = mode

    st.subheader("Configuration")
    col1, col2, col3 = st.columns(3)
    with col1:
        topic = st.text_input("Story Topic", placeholder="e.g., The Story of Prophet Yusuf")
    with col2:
        age_group = st.selectbox(
            "Age Group",
            ["toddler", "preschool", "school_age", "preteen", "all_ages"],
            index=1,
            format_func=lambda x: {
                "toddler": "Toddler (1-3 yrs)",
                "preschool": "Preschool (3-5 yrs)",
                "school_age": "School Age (5-8 yrs)",
                "preteen": "Preteen (8-12 yrs)",
                "all_ages": "All Ages (universal)",
            }[x],
        )
    with col3:
        duration = st.slider("Duration (min)", 3, 15, 8)
        create_shorts = st.checkbox("Create Shorts", value=True)

    st.divider()
    render_script_section(topic, age_group, duration)

    if st.session_state.get("script"):
        st.divider()
        render_image_section()
    if st.session_state.get("image_paths"):
        st.divider()
        render_audio_section()
    if st.session_state.get("audio_paths") and st.session_state.get("image_paths"):
        st.divider()
        render_video_section(create_shorts)
    if st.session_state.get("video_path"):
        st.divider()
        render_results_section()


def render_script_section(topic, age_group, duration):
    st.subheader("Step 1: Script")

    source = st.radio(
        "Script Source",
        ["AI Generate (Groq)", "Paste Your Own"],
        horizontal=True,
        key="script_source",
    )

    if source == "AI Generate (Groq)":
        st.caption("Editable prompt sent to AI. Modify then click Generate.")
        groq_system = SYSTEM_PROMPT.format(
            topic=topic or "general bedtime story",
            age_group=age_group,
            duration=duration,
            style="calm",
        )
        st.text_area(
            "Groq Prompt (editable)",
            value=groq_system,
            height=200,
            key="groq_prompt_area",
        )

        if st.button("Generate Script", type="primary", key="gen_script"):
            if not topic:
                st.error("Enter a topic first")
                return
            with st.spinner("Generating script with Groq..."):
                sg = ScriptGenerator()
                script = sg.generate_script(topic, age_group, duration)
                if script:
                    st.session_state["script"] = script
                    st.success("Script generated!")
                    st.rerun()
                else:
                    st.error("Script generation failed. Check Groq quota.")
    else:
        paste_json = st.text_area(
            "Paste script JSON here",
            height=300,
            placeholder='{"title": "...", "segments": [{"segment_number": 1, "narration": "...", "image_prompt": "...", "duration_seconds": 45}]}',
            key="paste_script",
        )
        if st.button("Load Script", type="primary", key="load_script"):
            try:
                script = json.loads(paste_json)
                if "segments" not in script:
                    st.error("JSON must have a 'segments' array")
                    return
                st.session_state["script"] = script
                st.success("Script loaded!")
                st.rerun()
            except json.JSONDecodeError as e:
                st.error("Invalid JSON: %s" % e)

    script = st.session_state.get("script")
    if script:
        with st.expander("View / Edit Script", expanded=True):
            st.text_input("Title", value=script.get("title", ""), key="edit_title")
            st.text_area("Description", value=script.get("description", ""), key="edit_desc")

            for seg in script.get("segments", []):
                num = seg.get("segment_number", 0)
                st.markdown("**Segment %d** (%ds)" % (num, seg.get("duration_seconds", 0)))
                seg["narration"] = st.text_area(
                    "Narration %d" % num,
                    value=seg.get("narration", ""),
                    height=100,
                    key="narr_%d" % num,
                )
                seg["image_prompt"] = st.text_area(
                    "Image Prompt %d" % num,
                    value=seg.get("image_prompt", ""),
                    height=60,
                    key="img_prompt_%d" % num,
                )

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Save Edits", key="save_script_edits"):
                    st.session_state["script"] = script
                    st.success("Edits saved!")
                    st.rerun()
            with c2:
                if st.button("Regenerate Script", key="regen_script"):
                    st.session_state["script"] = None
                    st.rerun()


def render_image_section():
    st.subheader("Step 2: Images")

    img_source = st.radio(
        "Image Source",
        ["AI Generate (Pollinations)", "Upload Your Own Images"],
        horizontal=True,
        key="img_source",
    )

    if img_source == "AI Generate (Pollinations)":
        script = st.session_state["script"]
        st.caption("Edit prompts before generating.")

        for seg in script.get("segments", []):
            num = seg.get("segment_number", 0)
            prompt = seg.get("image_prompt", "")
            edited = st.text_input("Prompt Segment %d" % num, value=prompt, key="poll_prompt_%d" % num)
            seg["image_prompt"] = edited

        if st.button("Generate Images", type="primary", key="gen_images"):
            with st.spinner("Generating images..."):
                ig = ImageGenerator()
                paths = ig.generate_images(script["segments"], output_prefix="story_%d" % int(time.time()))
                st.session_state["image_paths"] = paths
                st.success("Generated %d images!" % len(paths))
                st.rerun()
    else:
        uploaded = st.file_uploader(
            "Upload images (one per segment, in order)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="upload_imgs",
        )
        if uploaded and st.button("Load Uploaded Images", type="primary", key="load_imgs"):
            img_dir = Path("./output/images")
            paths = []
            for idx, f in enumerate(uploaded):
                out = img_dir / ("upload_%03d.png" % (idx + 1))
                with open(out, "wb") as fp:
                    fp.write(f.read())
                paths.append(str(out))
            st.session_state["image_paths"] = paths
            st.success("Loaded %d images!" % len(paths))
            st.rerun()

    image_paths = st.session_state.get("image_paths", [])
    if image_paths:
        st.caption("%d images ready" % len(image_paths))
        cols = st.columns(min(4, len(image_paths)))
        for idx, p in enumerate(image_paths):
            with cols[idx % len(cols)]:
                if os.path.exists(p):
                    st.image(p, caption="Image %d" % (idx + 1), use_container_width=True)
        if st.button("Regenerate Images", key="regen_imgs"):
            st.session_state["image_paths"] = []
            st.rerun()


def render_audio_section():
    st.subheader("Step 3: Voiceover")

    script = st.session_state["script"]

    if st.button("Generate Voiceover", type="primary", key="gen_audio"):
        with st.spinner("Generating voiceover with Edge TTS..."):
            vg = VoiceoverGenerator()
            paths = vg.generate_voiceover(script["segments"], output_prefix="story_%d" % int(time.time()))
            st.session_state["audio_paths"] = paths
            st.success("Generated %d audio segments!" % len(paths))
            st.rerun()

    audio_paths = st.session_state.get("audio_paths", [])
    if audio_paths:
        for idx, p in enumerate(audio_paths):
            if os.path.exists(p):
                st.audio(p, format="audio/wav")
        if st.button("Regenerate Voiceover", key="regen_audio"):
            st.session_state["audio_paths"] = []
            st.rerun()


def render_video_section(create_shorts):
    st.subheader("Step 4: Assemble Video")

    if st.button("Assemble Video", type="primary", key="assemble"):
        script = st.session_state["script"]
        image_paths = st.session_state["image_paths"]
        audio_paths = st.session_state["audio_paths"]

        progress = st.progress(0, text="Creating segments...")
        va = VideoAssembler()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in script.get("title", "video")[:30])
        output_file = "%s_%s.mp4" % (safe_title, timestamp)

        video_path = va.assemble_video(
            image_paths=image_paths,
            audio_paths=audio_paths,
            output_filename=output_file,
        )

        progress.progress(90, text="Creating shorts...")

        short_paths = []
        if create_shorts and video_path:
            sc = ShortsCreator()
            short_paths = sc.create_shorts(video_path, script, output_prefix="short_%s" % timestamp)

        progress.progress(100, text="Done!")

        if video_path:
            st.session_state["video_path"] = video_path
            st.session_state["short_paths"] = short_paths
            usage = UsageTracker()
            usage.record_video_created(len(short_paths))
            st.success("Video assembled!")
            st.rerun()
        else:
            st.error("Video assembly failed")


def render_results_section():
    st.subheader("Results")

    video_path = st.session_state.get("video_path")
    short_paths = st.session_state.get("short_paths", [])

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

    if st.button("New Video", key="new_video"):
        for k in ["script", "image_paths", "audio_paths", "video_path", "short_paths"]:
            st.session_state[k] = [] if isinstance(st.session_state.get(k), list) else None
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

    st.dataframe(topics, use_container_width=True)

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
            dur = st.slider("Duration (min)", 3, 15, 8)

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


def main():
    st.title("Bedtime Stories Automator")
    sidebar()

    tab1, tab2, tab3 = st.tabs(["Create Video", "API Status", "Topics Queue"])

    with tab1:
        render_create_tab()
    with tab2:
        render_api_tab()
    with tab3:
        render_topics_tab()


if __name__ == "__main__":
    main()
