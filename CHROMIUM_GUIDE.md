### `CHROMIUM_GUIDE.md`

# 🌐 Chromium in Codespaces Guide

This project uses a Docker-based Chromium instance to allow web browsing directly from the Codespace's network. This is useful for coding in restricted environments with firewall limitations.

## 🚀 Quick Start

Run this command in your terminal to start the browser:

```bash
docker run -d \
  --name chromium_gui \
  -p 4000:3000 \
  --shm-size="2gb" \
  lscr.io/linuxserver/chromium:latest

```

## 🛠 How to Access

1. **Wait 15–30 seconds** for the container to fully boot.
2. Open the **Ports** tab in the bottom panel of VS Code.
3. Look for **Port 4000**.
4. Click the **Open in Browser** (globe) icon.
5. A new tab will open showing the Chromium desktop.

---

## 🧭 Troubleshooting (The "502 Bad Gateway" Fix)

If you see a **502 error** when opening the link:

1. **Give it a moment:** The container needs time to start the internal VNC server. Refresh after 10 seconds.
2. **Restart the Port:** In the **Ports** tab, right-click Port 4000 -> **Unforward Port**, then manually **Forward Port** 4000 again.
3. **Check Logs:** Run `docker logs -f chromium_gui`. If you see "swirl starting," the web UI is ready.

---

## 🧠 Key Concepts

### Why Port 4000?

We map **4000 (Codespace)** to **3000 (Container)** because:

* **Port 3000** is the default for our frontend app. We can't have two things using the same "apartment number" in the Codespace.
* The Chromium image is hardcoded to live in **Internal Apartment 3000**.
* **The Command:** `-p 4000:3000` creates a tunnel from the outside (4000) to the inside (3000).

### Memory Management

The `--shm-size="2gb"` flag is **mandatory**. Chromium is memory-hungry; without this, tabs will crash immediately (the "Aw, Snap!" error) because Docker containers default to a very tiny amount of shared memory.

### Cleanup

If you need to reset the browser or it hangs:

```bash
docker rm -f chromium_gui

```

---

## 💡 Pro-Tip: Auto-Start a URL

If you want the browser to open your app automatically on launch, add this flag to the `docker run` command:
`-e CHROME_CLI="https://google.com"` (Replace with your URL).

---
