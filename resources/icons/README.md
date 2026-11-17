# CP2K Studio application icons

`cp2k_studio.png` is the user-supplied application artwork, copied byte for byte.
It is a 1024 × 1024 RGBA PNG with transparency. It has not been resized, cropped,
recoloured, or re-encoded.

SHA-256: `abf05e661c75f382f998ea5dab3567a4481570f4224ece695dcd00fe33472cc0`

The shared loader is `ui/app_icon.py`. It uses core/resources.py to resolve source and frozen bundle resources,
not the process working directory. `main.py` loads the image after
creating QApplication, applies it to the application, and assigns the same QIcon
to the main window. Applicable child windows inherit the application/parent
icon; native file panels remain system-managed. Missing or unreadable artwork
produces a logging warning without preventing application startup.

Platform resources:

- `cp2k_studio.icns` — macOS bundle icon, with appropriate bundle metadata.
- `cp2k_studio.ico` — Windows executable icon.
- `cp2k_studio.png` — shared Qt/Linux icon.

The v1.0.0 macOS build includes cp2k_studio.icns, derived with macOS sips and
iconutil, plus the unchanged PNG for Qt. build_macos.sh and CP2K_Studio.spec
retain the resources/icons layout inside the standalone ARM64 application.
The Windows ICO remains reserved; no Windows package is built here.

A nonempty QApplication.windowIcon() confirms the Qt icon loaded; it does not
prove the macOS Dock is displaying it. A process launched through Python may
retain the interpreter's Dock identity. The macOS app now supplies the ICNS resource and bundle metadata for its own
application identity. See docs/macos-test-report.md for the actual verification
scope; Qt icon loading alone is not claimed as a Dock screenshot test.
