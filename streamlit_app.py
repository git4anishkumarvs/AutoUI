import streamlit as st
import os
import sys
import subprocess
import io

# Setup global debug logs interceptor
if 'debug_logs' not in st.session_state:
    st.session_state.debug_logs = []

class UIInterceptor:
    def __init__(self, orig):
        self.orig = orig
    def write(self, text):
        self.orig.write(text)
        # Avoid overwhelming the UI with empty newlines or generic tasklist errors
        if text.strip() and not text.strip().startswith("Tasklist Scan Error"):
            try:
                st.session_state.debug_logs.append(text.strip())
                if len(st.session_state.debug_logs) > 30:
                    st.session_state.debug_logs.pop(0)
            except Exception:
                pass
    def flush(self):
        self.orig.flush()

if not hasattr(sys.stdout, 'is_ui_interceptor'):
    new_out = UIInterceptor(sys.stdout)
    new_out.is_ui_interceptor = True
    sys.stdout = new_out

# Append root to path so core imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from core.common.config_parser import load_config
from core.app_manager import AppManager
from core.common.vlm_config import build_vlm_url, get_local_service_binding, get_vlm_service_url

st.set_page_config(page_title="AutoUI Dashboard", page_icon="🤖", layout="wide")
st.title("🤖 AutoUI Control Center")

# Initialize AppManager globally in Streamlit session state
if 'app_manager' not in st.session_state:
    try:
        config = load_config("config.ini")
    except Exception:
        # Fallback to empty if config.ini doesn't exist
        import configparser
        config = configparser.ConfigParser()
        config.add_section("Automation")
        config.set("Automation", "tool", "PyGUITest")
        
    st.session_state.app_manager = AppManager(config)

app_manager = st.session_state.app_manager

# Helper to dynamically parse feature files for app executables
def get_apps_from_features():
    import glob, re
    apps = set()
    features_dir = os.path.join(os.path.dirname(__file__), "bdd_tests", "features")
    if os.path.exists(features_dir):
        for f in glob.glob(os.path.join(features_dir, "*.feature")):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    content = file.read()
                    matches = re.findall(r'launch "([^"]+)"', content)
                    for match in matches:
                        apps.add(os.path.basename(match))
            except Exception:
                pass
    return apps

# Sidebar for Launching new apps dynamically
st.sidebar.header("Launch New Application")
st.sidebar.markdown("Use this panel to launch applications dynamically without strictly defining them in `config.ini`.")

new_app_alias = st.sidebar.text_input("Application Alias (e.g. NoteApp)")
new_app_path = st.sidebar.text_input("Executable Path (e.g. notepad.exe or C:\\Windows\\calc.exe)")

if st.sidebar.button("Launch Application"):
    if new_app_alias and new_app_path:
        try:
            app_manager.launch_app(new_app_alias, app_path=new_app_path)
            st.sidebar.success(f"Launched {new_app_alias} successfully!")
        except Exception as e:
            st.sidebar.error(str(e))
    else:
        st.sidebar.warning("Please provide both an alias and executable path.")

# ===========================
# VLM Subprocess Management
# ===========================
st.sidebar.markdown("---")
st.sidebar.header("🧠 Vision-Language Engine")
st.sidebar.markdown("Toggle the background FastAPI AI Server isolated deep learning pipeline.")

if 'vlm_process' not in st.session_state:
    st.session_state.vlm_process = None

vlm_service_url = get_vlm_service_url()
vlm_status_url = build_vlm_url("/status")
vlm_warmup_url = build_vlm_url("/warmup")

# Poll the server safely
api_status = None
vlm_active = False
try:
    import requests
    response = requests.get(vlm_status_url, timeout=0.2)
    if response.status_code == 200:
        vlm_active = True
        api_status = response.json()
except:
    pass

st.sidebar.write(f"**API Pipeline:** {'🟢 Online' if vlm_active else '🔴 Offline'}")

if vlm_active and api_status:
    is_loaded = api_status.get("loaded", False)
    hardware_status = api_status.get("status", "Unknown")
    backend_type = api_status.get("backend", "unknown")
    display_name = api_status.get("display_name", "Vision Model")
    
    if is_loaded:
        st.sidebar.success(f"🧠 **{display_name}**\n\n`{hardware_status}`")
    else:
        st.sidebar.warning(f"**{display_name}**\n\n`{hardware_status}`")
        
        button_text = "⚡ Load Model into Memory"
        loading_text = f"Loading {display_name}..."
        
        if backend_type == "openai_compatible":
            button_text = "⚡ Verify API Connection"
            loading_text = f"Pinging {display_name}..."
            
        if st.sidebar.button(button_text, use_container_width=True):
            with st.spinner(loading_text):
                try:
                    res = requests.get(vlm_warmup_url, timeout=600)
                    if res.status_code == 200:
                        st.sidebar.success("✅ Ready!")
                        st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Failed: {e}")


    if st.sidebar.button("🛑 Terminate AI Engine", use_container_width=True):
        if st.session_state.vlm_process:
            st.session_state.vlm_process.kill()
            st.session_state.vlm_process = None
            st.rerun()
        else:
            st.sidebar.warning("VLM is online but wasn't launched by this specific UI cycle. Close the background terminal window manually.")
else:
    if st.sidebar.button("🚀 Load Vision Model Server in Background", type="primary", use_container_width=True):
        import subprocess, os, time
        # Hard-link to venv python to avoid global Python313 bleed-over
        venv_python = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
        vlm_dir = os.path.join(os.path.dirname(__file__), "vlm_service")
        host, port = get_local_service_binding()
        cmd = [venv_python, "-m", "uvicorn", "vision_service:app", "--host", host, "--port", str(port)]
        st.session_state.vlm_process = subprocess.Popen(cmd, cwd=vlm_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait up to 8 seconds for the server to be reachable before rerunning
        with st.spinner("Starting Vision Model Server..."):
            for _ in range(16):
                time.sleep(0.5)
                try:
                    r = requests.get(vlm_status_url, timeout=0.3)
                    if r.status_code == 200:
                        break
                except:
                    pass
        st.rerun()

# ===========================
# Global Cleanup Tools
# ===========================
st.sidebar.markdown("---")
if st.sidebar.button("🛑 Terminate All Active Apps", type="primary", use_container_width=True):
    app_manager.terminate_all()
    
    # Cleanup ghost instances dynamically parsed from .feature files
    try:
        import subprocess
        apps_to_kill = get_apps_from_features()
        for app in apps_to_kill:
            # Ensure we don't accidentally kill safe system files unless actively defined in features
            subprocess.call(['taskkill', '/F', '/IM', app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.lower() == "calc.exe":
                subprocess.call(['taskkill', '/F', '/IM', 'CalculatorApp.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
        
    st.sidebar.success("All managed applications and feature ghosts terminated securely.")
    st.rerun()

# Create tabs for the UI
tab1, tab2 = st.tabs(["🚀 Application Manager", "🧪 Automated Behave Tests"])

with tab1:
    st.subheader("Foreground Managed Applications")

    active_apps = app_manager.active_apps

    if not active_apps:
        st.info("No interactive UI applications are currently tracking. Start one from the sidebar.")
    else:
        for alias, wrapper in list(active_apps.items()):
            proc = wrapper.process
            pid = proc.pid if proc else "N/A"
            with st.expander(f"📦 {alias} (PID: {pid})", expanded=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                is_running = proc is not None and proc.poll() is None
                
                with col1:
                    st.write(f"**Status:** {'🟢 Running' if is_running else '🔴 Terminated'}")
                    
                with col2:
                    if st.button("🔄 Switch Focus", key=f"focus_{alias}"):
                        if is_running:
                            try:
                                app_manager.switch_to_app(alias)
                                st.success(f"Focused {alias}")
                            except Exception as e:
                                st.error(f"Failed to focus: {e}")
                        else:
                            st.warning("App is not running natively.")
                            
                with col3:
                    if st.button("❌ Terminate", key=f"term_{alias}"):
                        try:
                            wrapper.terminate()
                            del app_manager.active_apps[alias]
                            st.success(f"{alias} cleanly terminated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to terminate: {e}")

    st.subheader("Background BDD Test Applications")
    st.markdown("These stray processes match the test executables defined in your `.feature` scenarios.")

    try:
        import subprocess, csv, io
        apps_from_features = get_apps_from_features()
        if apps_from_features:
            output = subprocess.check_output('tasklist /FO CSV /NH', shell=True, text=True)
            reader = csv.reader(io.StringIO(output))
            ghosts = []
            
            target_names = set(a.lower() for a in apps_from_features)
            if "calc.exe" in target_names:
                target_names.add("calculatorapp.exe")
                
            for row in reader:
                if not row: continue
                exe_name = row[0]
                pid = row[1]
                if exe_name.lower() in target_names:
                    ghosts.append((exe_name, pid))
            
            if not ghosts:
                st.info("✅ System Clean: No stray background test apps running.")
            else:
                for exe, pid in ghosts:
                    with st.expander(f"👻 Background: {exe} (PID: {pid})", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Status:** 🟠 Running (Orphaned Subprocess)")
                        with col2:
                            if st.button("❌ Terminate", key=f"kill_ghost_{pid}"):
                                subprocess.call(['taskkill', '/F', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                st.rerun()
        else:
            st.info("No `.feature` scenarios are tracking executables currently.")
    except Exception as e:
        st.error(f"Tasklist Scan Error: {e}")

with tab2:
    st.subheader("Automated BDD Framework Runner")
    st.markdown("Execute UI test scenarios directly from this dashboard.")

    features_dir = os.path.join(os.path.dirname(__file__), "bdd_tests", "features")
    feature_files = [f for f in os.listdir(features_dir) if f.endswith('.feature')] if os.path.exists(features_dir) else []

    col_select, col_debug = st.columns([3, 1])
    with col_select:
        selected_feature = st.selectbox("Select Feature file to run", ["All Features"] + feature_files)
    with col_debug:
        st.markdown("<br>", unsafe_allow_html=True)
        debug_mode = st.toggle("Debug Mode", value=False, help=(
            "When ON: each BDD step is shown in its own expandable panel "
            "with full VLM pipeline details (Step 1-8 screenshot/coordinate logs)."
        ))

    if debug_mode:
        st.info(
            "**Debug Mode ON** -- After running, each BDD step will be shown in a "
            "separate expandable panel with the full VLM pipeline trace (Step 1 capture, "
            "Step 2 resize, Step 3 API query, Step 4 coordinates, Step 5-6 scaling, "
            "Step 7 focus, Step 8 action).",
        )

    if st.button("Run Automated Tests", type="primary", use_container_width=True):
        with st.spinner("Executing BDD Scenarios... Please wait."):
            venv_python = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
            cmd = [venv_python, "-m", "behave", "--no-capture", "--format", "pretty"]
            if selected_feature != "All Features":
                cmd.append(os.path.join("bdd_tests", "features", selected_feature))
            else:
                cmd.append("bdd_tests")

            try:
                import copy
                env = copy.copy(os.environ)
                env["PYTHONIOENCODING"] = "utf-8"   # Force UTF-8 output on Windows cp1252 terminals
                
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    cwd=os.path.dirname(__file__),
                    encoding="utf-8", errors="replace",
                    env=env
                )

                passed = result.returncode == 0
                combined = result.stdout + ("\n" + result.stderr if result.stderr else "")

                if passed:
                    st.success("All tests PASSED")
                else:
                    st.error("One or more tests FAILED")

                if debug_mode:
                    # ── Parse output into per-step blocks ────────────────────
                    st.markdown("---")
                    st.markdown("### Step-by-Step Debug Trace")

                    # Split on lines that start with BDD step keywords
                    import re
                    lines = combined.splitlines()
                    
                    # Collect step blocks: each step starts with Given/When/And/Then/But
                    step_pattern = re.compile(
                        r"^\s*(Given|When|And|Then|But)\s+(.+?)(\s+#\s*.+)?$", re.IGNORECASE
                    )
                    # VLM pipeline step pattern
                    vlm_step_pattern = re.compile(r"^\[Step \d+\]")

                    current_step_label = None
                    current_step_lines = []
                    step_blocks = []   # list of (label, lines, passed)

                    for line in lines:
                        m = step_pattern.match(line)
                        if m:
                            # Save previous block
                            if current_step_label is not None:
                                step_blocks.append((current_step_label, current_step_lines))
                            keyword = m.group(1).strip()
                            desc = m.group(2).strip()
                            current_step_label = f"{keyword} {desc}"
                            current_step_lines = [line]
                        elif current_step_label is not None:
                            current_step_lines.append(line)

                    if current_step_label is not None:
                        step_blocks.append((current_step_label, current_step_lines))

                    if not step_blocks:
                        # Fallback: show raw output if parse failed
                        st.code(combined, language="bash")
                    else:
                        for i, (label, block_lines) in enumerate(step_blocks, start=1):
                            raw_block = "\n".join(block_lines)

                            if "failed" in raw_block.lower() or "Error" in raw_block:
                                icon = "X"
                                colour = "red"
                            else:
                                icon = "OK"
                                colour = "green"

                            header = f"[{icon}] Step {i}: {label}"
                            with st.expander(header, expanded=(colour == "red")):
                                # ── Categorise lines from the block ──────────────
                                vlm_pipeline  = [l for l in block_lines if re.match(r"\[Step \d+\]", l.strip())]
                                appmgr_lines  = [l for l in block_lines if "[AppManager]" in l]
                                pygui_lines   = [l for l in block_lines if "[PyGUIWrapper]" in l]
                                raw_rest      = [l for l in block_lines
                                                 if not re.match(r"\[Step \d+\]", l.strip())
                                                 and "[AppManager]" not in l
                                                 and "[PyGUIWrapper]" not in l]

                                if appmgr_lines:
                                    st.markdown("**App / Window Focus:**")
                                    st.code("\n".join(l.strip() for l in appmgr_lines), language="text")

                                if vlm_pipeline:
                                    st.markdown("**VLM Pipeline (Steps 1-8):**")
                                    step_labels = {
                                        "1": "Screenshot captured",
                                        "2": "Image resized for model",
                                        "3": "API call sent",
                                        "4": "Coordinates received from VLM",
                                        "5": "Scaled to window-relative pixels",
                                        "6": "Absolute screen position resolved",
                                        "7": "Window re-focused",
                                        "8": "Click / Type action executed",
                                    }
                                    for vl in vlm_pipeline:
                                        m2 = re.match(r"\[Step (\d+)\]\s*(.+)", vl.strip())
                                        if m2:
                                            snum  = m2.group(1)
                                            stext = m2.group(2).strip()
                                            slabel = step_labels.get(snum, f"Step {snum}")
                                            if snum == "3":
                                                st.info(f"**[Step {snum}] {slabel}**\n\n`{stext}`")
                                            elif snum == "4":
                                                st.success(f"**[Step {snum}] {slabel}**\n\n`{stext}`")
                                            elif snum == "8":
                                                st.success(f"**[Step {snum}] {slabel}**\n\n`{stext}`")
                                            elif snum in ("5", "6"):
                                                st.warning(f"**[Step {snum}] {slabel}**\n\n`{stext}`")
                                            else:
                                                st.markdown(f"`Step {snum}` **{slabel}** — {stext}")

                                if pygui_lines and not vlm_pipeline:
                                    st.markdown("**Wrapper Activity:**")
                                    st.code("\n".join(l.strip() for l in pygui_lines), language="text")

                                if raw_rest:
                                    with st.expander("Raw Behave output", expanded=False):
                                        st.code("\n".join(raw_rest), language="bash")

                else:
                    # Normal mode: single collapsible log
                    with st.expander("Execution Logs", expanded=True):
                        st.code(combined, language="bash")

            except Exception as e:
                st.error(f"Error executing tests: {e}")



# ===========================
# Live UI Debug Log Block
# ===========================
st.markdown("---")
st.subheader("📺 System Output Logs")
st.markdown("Provides live diagnostic tracing from internal terminal processes (App UI launches, clicks).")
if st.session_state.debug_logs:
    st.code("\n".join(st.session_state.debug_logs), language="bash")
else:
    st.info("System outputs will gradually populate as you issue actions.")
