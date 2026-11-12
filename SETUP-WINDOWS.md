# Setup guide for Windows

This guide takes you from a Windows PC with nothing installed to Skills-First Hiring running in your browser. Follow the steps in order. Allow about an hour the first time, mostly waiting for downloads.

Everything runs on your own computer. CVs, team ratings and client details never leave it. The only things downloaded from the internet are the software in steps 1–3 and the AI model on first start.

---

## What you need

| | Minimum | Your workstation |
| --- | --- | --- |
| Windows | Windows 10 (version 22H2) or Windows 11, 64-bit | |
| Graphics card | NVIDIA with 8 GB of video memory (for the fast setup) | NVIDIA, 8 GB+ ✓ |
| Memory (RAM) | 16 GB recommended | |
| Free disk space | 20 GB | |
| Rights | An administrator account on the PC | |

No NVIDIA card? It still works on the processor alone, just slower. Skip step 4 and use `start-cpu.bat` instead of `start.bat` in step 6.

---

## Step 1. Update your NVIDIA graphics driver

The AI model uses your graphics card, so the driver must be recent.

1. Open the **NVIDIA app** (or **GeForce Experience** on older PCs) from the Start menu.
2. Go to **Drivers** and install any update it offers. If you don't have the app, download the latest driver for your card from [nvidia.com/drivers](https://www.nvidia.com/drivers).
3. Restart your PC if asked.
4. Check it worked: press **Start**, type **PowerShell**, open it, and run:

   ```
   nvidia-smi
   ```

   You should see a table with your graphics card's name. If you get "not recognized", reinstall the driver.

---

## Step 2. Turn on WSL 2 (Windows Subsystem for Linux)

Docker uses WSL 2 to run containers on Windows.

1. Press **Start**, type **PowerShell**, right-click **Windows PowerShell** and choose **Run as administrator**. Click **Yes**.
2. Run:

   ```
   wsl --install
   ```

3. When it finishes, **restart your PC**.
4. After the restart, a window may open asking you to create a Linux username and password. Choose anything simple and remember it. (Skills-First Hiring doesn't use it.)
5. Open PowerShell again (normal, not administrator) and run:

   ```
   wsl --update
   wsl --status
   ```

   Look for **Default Version: 2**.

---

## Step 3. Install Docker Desktop

1. Go to [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) and download **Docker Desktop for Windows**.
2. Run the installer. When asked, keep **Use WSL 2 instead of Hyper-V** ticked.
3. When it finishes, click **Close and log out** (or restart), then sign back in.
4. Open **Docker Desktop** from the Start menu. Accept the terms. You can skip signing in to a Docker account.
5. Wait until the bottom-left corner shows **Engine running** (green).
6. Recommended: open **Settings** (the gear icon) → **General**, and tick **Start Docker Desktop when you sign in to your computer**. Click **Apply & restart**.

Check it worked: in PowerShell, run:

```
docker --version
docker compose version
```

Both should print a version number.

---

## Step 4. Check Docker can use your graphics card

In PowerShell, run:

```
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

The first time, this downloads a small test image. You should then see the same graphics-card table as in step 1. That means Docker can use your GPU.

If you see an error such as **could not select device driver "nvidia"**, see section 9.

---

## Step 5. Put the app in a folder

1. Unzip **skills-first-hiring.zip** to a simple folder, for example `C:\skills-first-hiring`.
   - Avoid OneDrive, Dropbox or network folders. Syncing can interfere with Docker.
2. Open the folder. You should see `start.bat`, `stop.bat`, `docker-compose.yml`, a `sample-cvs` folder and others.

---

## Step 6. Start it

1. Make sure Docker Desktop shows **Engine running**.
2. Double-click **`start.bat`** (or `start-cpu.bat` without an NVIDIA card).
   - If Windows shows "Windows protected your PC", click **More info → Run anyway**. The file only runs the Docker commands you can read inside it (right-click → Edit).
3. A black window shows progress. The first time it builds the app, which takes 2–5 minutes.
4. Your browser opens **http://localhost:8080**.
5. **First start only:** the AI model (Qwen 2.5 7B, about 4.7 GB) downloads in the background. The top-right corner of the page shows **Downloading AI model 37%** and so on. Depending on your internet, this takes 10–30 minutes. You can explore the app with the sample data while you wait.
6. When it shows **AI ready · qwen2.5:7b**, everything is working.

---

## Step 7. Try it with the sample CVs

1. Go to tab **2 Candidates** and click **Add CVs** (top right).
2. Click **Choose CV files** and pick `sample-cvs\noura-al-hashimi.docx` from the app folder.
3. Wait about a minute while the local AI reads it. Noura appears in the grid with her scores.
4. Click her name. The **Evidence from the CV** section shows the exact line behind each score. **View CV** opens the original file.
5. On a candidate's page, click **Not progressing**. Then go to **5 Rejection review** and click **Draft with AI**. The checks under the message must all be green before you can approve it.
6. Go to **6 Onboarding** and click **Draft with AI** to get a 30-60-90 day plan, then pair a mentor.

The sample people, clients and CVs are fictional. Click **Reset sample data** (top right) to start again from scratch. This also deletes uploaded CVs.

---

## Step 8. Set it up for a real role

Work through the tabs in order:

1. **Role.** Enter the role title, 2–3 other titles the industry uses, the team name, your 3–5 top clients (with logos) and the core and complementary skills. For each skill, the "what good looks like" text is used by the AI when it writes rejection messages.
2. **Team.** Set the team rule (how many people need each skill). Enter each team member's self-rating, adjust where needed, add context, and tick possible mentors.
3. **Customer insights.** For each client, fill in needs, a recent win and challenge, and the skills that matter most.
4. **Candidates.** Add CVs. Scores are suggestions: check the evidence and confirm in interview.
5. **Rejection review** and **Onboarding** as above.

### Changing the AI model or the port (optional)

1. In the app folder, copy `.env.example` and rename the copy to `.env`.
2. Open `.env` in Notepad. Change `OLLAMA_MODEL` (for example to `llama3.1:8b`) or `APP_PORT` (for example to `8090`).
3. Run `stop.bat`, then `start.bat`. A new model downloads on first use.

---

## Everyday use

| To | Do this |
| --- | --- |
| Start | Open Docker Desktop, then double-click `start.bat`. Open http://localhost:8080 |
| Stop | Double-click `stop.bat`. Your data is kept. |
| See what's happening | Double-click `logs.bat` (press Ctrl+C to close) |
| Work offline | After the first start, no internet is needed. |

### Back up your data

Your data lives in a Docker volume called `skills-first-hiring_app_data`. To copy it to a file, open PowerShell in the app folder and run:

```
docker run --rm -v skills-first-hiring_app_data:/data -v ${PWD}:/backup alpine tar czf /backup/backup.tgz -C /data .
```

This creates `backup.tgz` in the app folder. Keep it somewhere safe: it contains CVs and team ratings.

---

## 9. If something goes wrong

| What you see | What to do |
| --- | --- |
| "Docker Desktop is not running" | Open Docker Desktop and wait for **Engine running**, then run `start.bat` again. |
| **could not select device driver "nvidia"** or a GPU error | Update the NVIDIA driver (step 1), run `wsl --update` in PowerShell, restart the PC and try again. If it still fails, use `start-cpu.bat`. |
| The page says **App server not reachable** | Wait a minute and refresh. If it stays, run `logs.bat` and look for red errors. |
| The status is stuck on **Waiting for the AI model** | Check your internet connection, then run `logs.bat`. A download that was interrupted restarts on its own. |
| **port is already allocated** | Another program uses port 8080. Set `APP_PORT=8090` in `.env` (see step 8) and open http://localhost:8090. |
| Reading a CV takes several minutes | The graphics card may not be in use. Run `docker compose logs ollama` in the app folder and look for a line mentioning **CUDA**. If it isn't there, repeat step 4. |
| "Hardly any text could be read" | The CV is a scanned image. Ask for a text-based PDF or Word file. |
| Scores look wrong | Small local models make mistakes. Check the evidence lines, click **Re-read CV with AI**, and always confirm in interview. |

### Remove everything

To remove the app and **delete all its data**, open PowerShell in the app folder and run `docker compose down -v`. Then delete the folder.

---

## How your data is protected

- The app only listens on your own computer (`127.0.0.1`). Other computers on your network cannot open it.
- The AI model runs inside Docker on your machine. CV text is never sent to an online AI service.
- Nothing is emailed: mentor emails and rejection messages are drafts you copy and send yourself.
- Uploaded CVs are deleted when you click **Reset sample data** or remove the app.
