<p align="center">
  <img src="data/icons/hicolor/scalable/apps/io.github.stepan.WayVoice.svg" width="112" alt="WayVoice — offline voice typing for Linux">
</p>

<h1 align="center">WayVoice</h1>

<p align="center">
  <strong>Offline voice typing and speech-to-text for Linux, GNOME and Wayland.</strong><br>
  Press to start, press again to stop. Get local transcription with clipboard fallback.
</p>

<p align="center">
  <a href="https://github.com/pavlenkosa/wayvoice/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/pavlenkosa/wayvoice/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/pavlenkosa/wayvoice/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/pavlenkosa/wayvoice?display_name=tag&sort=semver"></a>
  <img alt="Linux" src="https://img.shields.io/badge/Linux-Wayland-ffbc00?logo=linux&logoColor=black">
  <img alt="GTK 4" src="https://img.shields.io/badge/GTK-4-4a86cf?logo=gtk&logoColor=white">
  <img alt="License" src="https://img.shields.io/github/license/pavlenkosa/wayvoice">
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#recognition-engines">Recognition engines</a> ·
  <a href="#command-line">CLI</a> ·
  <a href="#privacy">Privacy</a>
</p>

## Voice typing for Linux that stays out of the way

WayVoice is an open-source Linux dictation app built with GTK4/libadwaita. Record through PipeWire, recognize speech locally, then paste the result automatically where supported or use the clipboard.

Speech recognition can run locally with **Faster-Whisper** or **whisper.cpp**, so your recordings do not need to leave your computer. WayVoice is designed around **GNOME, GTK4/libadwaita and Wayland**, while keeping a simple clipboard fallback when automatic paste is not available.

WayVoice is currently alpha software. GNOME Wayland is the primary tested environment; KDE, wlroots and installed Flatpak scenarios still need desktop acceptance. A successful build does not establish compatibility with every compositor.

## Why WayVoice?

- **Voice typing across applications** — browsers, editors, chats, IDEs and other places where you can paste text.
- **Local speech-to-text** — use Faster-Whisper or whisper.cpp without sending recordings to a transcription API.
- **Built for Wayland** — records through PipeWire tools, writes to the Wayland clipboard and can paste automatically with `ydotool`.
- **100 Whisper languages** — use automatic language detection or pin a language manually.
- **Spoken punctuation** — commands such as “comma”, “question mark”, “точка” and “запятая”.
- **Fast repeat dictation** — Faster-Whisper can keep the selected model warm in memory between recordings.
- **Model management in the UI** — download models, see disk usage and free space, cancel downloads and remove models you no longer need.
- **Preparation guidance** — check runtime, model, recording, clipboard and shortcut readiness from Home.
- **Recognition presets** — Fast / Balanced / More accurate edit the settings draft without silently saving or downloading.
- **Settings protection** — Save applies changes; leaving with unsaved edits prompts you. Downloading a model does not select it for saved dictation settings.
- **Compact status indicator** — optional ordinary window; no transcript display or automatic raising.
- **Diagnostics preview** — inspect a report before copying or saving it.
- **GNOME-style interface** — GTK4 + libadwaita, with Russian and English UI.
- **No forced downloads from the hotkey** — if a model is missing, WayVoice tells you instead of silently downloading gigabytes.
- **Useful without automatic paste** — recognized text stays in the clipboard if simulated `Ctrl+V` is unavailable.

## Install

### Fedora 44

Download the `.rpm` from [GitHub Releases](https://github.com/pavlenkosa/wayvoice/releases). Version 0.6.8 includes DEB, RPM, source archives and SHA-256 checksums. Install with:

```bash
sudo dnf install ./wayvoice-0.6.8-1.fc44.x86_64.rpm
```

RPM builds target Fedora 44; other RPM-based
distributions are not yet validated. User services follow the distribution's
preset policy; launch WayVoice from the application menu after installation.

Installation, upgrade, removal and reinstallation were checked in a disposable Fedora 44 container, including GTK/Adwaita imports. That does not verify a live Fedora desktop, microphone, udev permissions or automatic paste.

### Debian / Ubuntu

Download the latest `.deb` package from [GitHub Releases](https://github.com/pavlenkosa/wayvoice/releases), then install it with APT:

```bash
sudo apt install ./wayvoice_*_amd64.deb
```

Launch **WayVoice** from the application grid, or run:

```bash
wayvoice-settings
```

On a fresh configuration, the first-run wizard lets you choose Russian, English or the system interface language, then a Fast / Balanced / More accurate model. **Download and prepare** explicitly starts component and model downloads with progress, cancellation and retry. **Set up later** saves the choice without starting preparation. Existing configurations open normally.

The recognition runtime and model weights are downloaded only when they are needed and you choose to download them.

### Flatpak / Flathub status

The [Flatpak manifest](io.github.stepan.WayVoice.json) is experimental local-build packaging, not a Flathub-ready submission. There is no supported Flathub install command yet.

The sandbox runs without a systemd user manager. Automatic host shortcut registration and the bundled native `ydotool` helper are unavailable there: use a desktop-configured shortcut and manual clipboard paste. Models are downloaded only by an explicit action; the Flatpak runtime includes the recognition dependencies.

Before submission, the maintainer needs to:

- Prepare an offline-buildable manifest with declared dependency sources instead of networked `pip install`, and pin the application to published source rather than a local directory.
- Resolve the App ID: `io.github.stepan.WayVoice` does not match the current `pavlenkosa/wayvoice` repository namespace. Check ownership or an exception before choosing an ID; renaming affects sandbox data paths and desktop integration.
- Complete screenshots, license installation for bundled components and Flathub lint checks.
- Verify installed microphone capture, model download/cancellation, clipboard and manual shortcuts on target desktops. Automatic paste must not require an undocumented privileged host setup.

See the official [requirements](https://docs.flathub.org/docs/for-app-authors/requirements), [maintenance guidance](https://docs.flathub.org/docs/for-app-authors/maintenance) and [submission process](https://docs.flathub.org/docs/for-app-authors/submission). Current policy prohibits AI-generated or AI-assisted submission manifests and AI-automated submission interactions; known AI contributions elsewhere must be disclosed by the human submitter. Acceptance is decided by Flathub reviewers.

## Compact status indicator

Choose **Open indicator** in the WayVoice menu, or run `wayvoice-settings --indicator`.
It shows recording, recognition, preparation and attention states without showing your
transcript. You can close Settings and keep this window open; closing the indicator
stops its monitoring, not the background daemon. Status updates never raise the window
or request activation. It is a normal window: placement, focus on explicit opening,
occlusion and any always-on-top option are controlled by your desktop.

## KDE Plasma

On Plasma, assign the command shown beside the shortcut in WayVoice Settings in
**System Settings → Keyboard → Shortcuts → Add New → Command or Script**.
The saved key in WayVoice is the desired binding; Plasma owns the active shortcut.
Manual registration is expected and does not make saving other settings fail.

Use **Ctrl+V** for ordinary editors and **Ctrl+Shift+V** for Konsole. If automatic
paste is unavailable, the recognized text remains in the clipboard for manual paste.
The helper needs access to `/dev/uinput`; diagnostics distinguish clipboard delivery
from automatic paste. GlobalShortcuts portal registration is not implemented yet.
Plasma 6.3.6 Wayland service/environment checks have passed; this is not a completed
installed dictation and paste acceptance test.

## How it works

1. Open WayVoice and use Home preparation guidance to prepare the recognition runtime and explicitly download a model.
2. Choose the engine/model or a preset, then **Save**. Set the dictation hotkey; on KDE/wlroots or Flatpak, bind the command shown by Settings in your desktop.
3. Put the cursor into any text field.
4. Press the hotkey and speak.
5. Press it again to stop recording.

WayVoice transcribes the recording and places the result into the active workflow. When automatic paste is available, the text is inserted for you. Otherwise, it remains in the Wayland clipboard so you can paste it normally.

A model that is not yet installed is never downloaded just because you pressed the hotkey. Download it from Settings or from the command line:

```bash
wayvoice model --download
```

## Features at a glance

| Area | What WayVoice provides |
| --- | --- |
| Dictation | Toggle recording, CLI start/stop/cancel and recognition timeout; shortcut setup depends on desktop |
| Speech recognition | Faster-Whisper, whisper.cpp or any external command |
| Languages | All 100 languages supported by Whisper, with automatic detection |
| Punctuation | Automatic punctuation plus spoken punctuation commands |
| Wayland | PipeWire recording, Wayland clipboard and optional automatic paste |
| Models | Download progress, cancellation, disk usage, free space and deletion |
| Performance | Optional warm Faster-Whisper worker between dictations |
| Desktop | GTK4, libadwaita, GNOME-style UI, RU/EN localization |
| Privacy | Local engines keep recognition and recordings on your machine |

## Recognition engines

### Faster-Whisper

The recommended default. It supports multilingual Whisper models, English-only models and compatible CTranslate2 models.

For faster repeated dictation, WayVoice can keep the model loaded between recordings. This uses more memory but avoids reloading the model every time. You can disable the warm worker in Settings if you prefer lower idle memory usage.

On one test machine, the resident worker used roughly **0.6 GB** with the `small` model and **1.6 GB** with `medium`. Larger models require more memory.

### whisper.cpp

Use a local `whisper-cli` binary with a compatible GGML/GGUF model. This is useful if you already have a whisper.cpp setup or prefer its runtime.

### External command

WayVoice can hand the recorded audio to another program and use whatever that command prints to stdout as the recognized text.

Example:

```text
vosk-transcriber -i {audio}
```

The command template runs through `/bin/sh`, and `{audio}` is replaced with the path to the recorded audio file.

## Languages and spoken punctuation

Automatic language detection is the default. You can also pin one of the languages supported by Whisper when you know exactly what you will be speaking.

Spoken punctuation is applied in the active recognition language, including English and Russian commands such as:

- “comma”, “period”, “question mark”
- “запятая”, “точка”, “вопросительный знак”

This makes WayVoice useful for longer Linux voice dictation, not only short search queries or commands.

## Models and storage

Faster-Whisper model files live in the Hugging Face cache, which may be shared with other applications.

WayVoice shows:

- whether the selected model is available locally;
- the model's size on disk;
- total space used by WayVoice models;
- total shared cache size;
- free disk space;
- download progress and cancellation.

Deleting a model from WayVoice does not blindly erase shared files that another cached model still uses.

You can select a model from the built-in catalogue, enter a full Hugging Face repository id such as `Systran/faster-whisper-large-v3`, or point WayVoice at a local model directory.

## Wayland clipboard and automatic paste

Wayland intentionally prevents normal applications from pretending to be your keyboard. Because of that, WayVoice separates **recognition** from **automatic paste**.

Core runtime tools include:

- `pw-record` for microphone recording;
- `wl-copy` for the Wayland clipboard;
- `notify-send` for desktop notifications;
- `ydotool` for optional automatic `Ctrl+V`.

If `ydotool` is unavailable, dictation still works — the recognized text is copied to the clipboard.

Native Debian and Fedora packages also include a bundled `ydotool` fallback for systems that do not provide a suitable package. A system-installed copy is preferred when available.

## Privacy

With a local recognition engine selected, WayVoice does **not** send your recordings to a cloud transcription service.

Network access is used to download the speech-recognition runtime and model files when you explicitly request them. Recognition itself runs locally. External commands are user-supplied programs and may have their own network behavior.

Temporary recordings are cleaned up after processing/cancellation. Dictation text is hidden in notifications by default; showing it is opt-in. Clipboard content remains available to other applications and clipboard managers according to desktop behavior.

That makes WayVoice suitable for people who want **private offline speech-to-text on Linux** without routing everyday dictation through a third-party API.

## Command line

The GUI covers normal daily use, but WayVoice also provides a small CLI.

### Dictation and status

```bash
wayvoice toggle
wayvoice cancel
wayvoice status
wayvoice engine-status
wayvoice settings
```

### Model management

```bash
wayvoice model
wayvoice model --download
wayvoice model --cancel
```

### Service log

```bash
journalctl --user -u wayvoice -f
```

## Troubleshooting

**The hotkey works, but text is not pasted automatically**

Check the clipboard first. If the recognized text is there, speech recognition succeeded and only automatic paste is unavailable. Check whether `ydotool` is installed and usable on your system.

**WayVoice says the model is missing**

Open Settings and download the selected model, or run:

```bash
wayvoice model --download
```

**Recognition takes a long time on the first use**

First verify that runtime and model preparation have completed. Dictation never downloads missing weights automatically. Loading a ready model into memory can still take time; the warm worker makes repeated dictation faster.

**Need more detail?**

See the [changelog](CHANGELOG.md), open an [issue](https://github.com/pavlenkosa/wayvoice/issues), or inspect the service log shown above.

## Planned capabilities

These are directions, not currently implemented features or release promises:

1. Reliable hold-to-talk and shortcut cancellation, with truthful desktop capability reporting.
2. Microphone selection and clear active-device feedback.
3. Vocabulary corrections for names and technical terms.
4. Additional engines such as Parakeet, after language/latency/quality measurements.
5. Opt-in local text history, followed by application-specific formatting and profiles.

Streaming and optional LLM cleanup come later. No general plugin framework or extension store is implemented. Current work prioritizes acceptance of the existing input loop over adding more settings.

## Development and contributing

Contributions, bug reports and testing on different Linux/Wayland setups are welcome. Include version, package type, desktop/session, recognition engine and whether text reached the clipboard; redact dictated text from reports.

```bash
make lint
make test
make deb
```

For RPM builds on Fedora, install `rpm-build`, `gcc`, `python3`, `systemd-rpm-macros`, `tar` and `gzip`, then run `make rpm`. With Docker, `./scripts/build-rpm-container.sh` builds in Fedora's official image. Packages and checksums go into `dist/`; the build scripts do not install packages on the host or start its services.

Tests requiring GTK bindings are skipped when those bindings are absent. Unit tests do not replace installed desktop, microphone or insertion checks.

Faster-Whisper selects its compute type automatically: `int8` on CPU and `float16`
on CUDA, in both worker and one-shot modes. Legacy `compute_type_cpu` and
`compute_type_cuda` configuration keys never controlled recognition; they are now
ignored when reading old files and omitted on the next explicit settings save.
Reading a configuration does not rewrite it.


Native engine preparation and Flatpak builds use the same exact dependency versions
in `app/src/wayvoice/runtime-requirements.txt`. Updating the runtime means updating
and checking that set, including Python 3.11 compatibility.

Debian builds honor `SOURCE_DATE_EPOCH`; otherwise they use the Git commit timestamp
or, for a source archive, the timestamp of `app/src/wayvoice/__init__.py`. Use the same
source, compiler/toolchain and epoch when comparing artifacts from repeated builds.

- [Contributing guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Security policy](SECURITY.md)
- [Releases](https://github.com/pavlenkosa/wayvoice/releases)

## License

WayVoice is licensed under the **GNU Affero General Public License v3.0 or later** (`AGPL-3.0-or-later`).

See [LICENSE](LICENSE) and [third_party/ydotool](third_party/ydotool/README.wayvoice.md) for details.
