"""Publication via Upload-Post (https://docs.upload-post.com/api/upload-video).

Une seule requête multipart publie la vidéo sur Instagram (Reels), YouTube
(Shorts) et LinkedIn, avec un texte adapté à chaque plateforme. La réponse est
gardée dans `publish.json` pour ne jamais publier deux fois la même vidéo.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

API = "https://api.upload-post.com/api"


def build_fields(story: dict, platforms: list[str], user: str, schedule: str | None = None,
                 timezone: str | None = None, queue: bool = False) -> list[tuple[str, str]]:
    post = story.get("post", {})
    tags = post.get("hashtags", [])
    caption = (post.get("caption", "") + "\n\n" + " ".join(tags)).strip()
    yt_title = (post.get("youtube_title") or story.get("title", ""))[:90].strip()
    if "#shorts" not in yt_title.lower() and len(yt_title) <= 90 - 8:
        yt_title += " #Shorts"
    yt_desc = (post.get("caption", "") + "\n\n" + "\n".join(f"• {s}" for s in story.get("sources", [])[:3])
               + "\n\n" + " ".join(tags + ["#Shorts"])).strip()
    li_text = (post.get("linkedin_text") or post.get("caption", "")).strip()
    li_text = (li_text + "\n\n" + " ".join(tags[:5])).strip()

    fields = [("user", user), ("title", yt_title)]
    fields += [("platform[]", p) for p in platforms]
    if "instagram" in platforms:
        fields += [("instagram_title", caption[:2200]), ("media_type", "REELS"), ("share_to_feed", "true")]
    if "youtube" in platforms:
        fields += [("youtube_title", yt_title), ("youtube_description", yt_desc[:5000]),
                   ("privacyStatus", "public"), ("categoryId", "27"),  # Éducation
                   ("defaultLanguage", "fr"), ("defaultAudioLanguage", "fr-FR")]
        fields += [("tags[]", t.lstrip("#")) for t in tags[:15]]
    if "tiktok" in platforms:
        fields += [("tiktok_title", caption[:2200])]
    if "facebook" in platforms:
        fields += [("facebook_title", caption[:2000]), ("facebook_description", caption[:5000])]
    if "linkedin" in platforms:
        fields += [("linkedin_title", li_text[:200]), ("linkedin_description", li_text[:3000]),
                   ("visibility", "PUBLIC")]
    if queue and not schedule:
        # prochain créneau libre du calendrier de publication du profil Upload-Post
        fields.append(("add_to_queue", "true"))
    if schedule:
        if len(schedule) == 16:  # 2026-10-20T18:00 → 2026-10-20T18:00:00
            schedule += ":00"
        fields.append(("scheduled_date", schedule))
        if timezone:
            fields.append(("timezone", timezone))
    return fields


def publish(video: Path, story: dict, api_key: str, user: str, platforms: list[str],
            schedule: str | None = None, timezone: str | None = None, force: bool = False,
            queue: bool = False) -> dict:
    record = video.parent / "publish.json"
    if record.exists() and not force:
        prev = json.loads(record.read_text())
        raise SystemExit(f"Déjà publié ({prev.get('at')}). Utilise --force pour republier.")
    if not api_key:
        raise SystemExit("UPLOAD_POST_API_KEY manquante dans .env")
    fields = build_fields(story, platforms, user, schedule, timezone, queue)
    rid = f"{story.get('brand', 'x')}-{story.get('domain', 'x')}-{story.get('id', video.parent.name)}-{int(time.time())}"
    headers = {"Authorization": f"Apikey {api_key}", "Idempotency-Key": rid}
    fields += [("request_id", rid), ("external_id", story.get("id", video.parent.name))]
    print(f"📤 Upload-Post → {', '.join(platforms)} (profil « {user} »)" + (f", programmé {schedule}" if schedule else ""))
    files = [("video", (video.name, open(video, "rb"), "video/mp4"))]
    cover = video.parent / "cover.jpg"
    if cover.exists():
        # couverture du Reel + vignette YouTube / LinkedIn (≤ 2 Mo)
        if "instagram" in platforms:
            files.append(("cover_image", ("cover.jpg", open(cover, "rb"), "image/jpeg")))
        if "youtube" in platforms or "linkedin" in platforms:
            files.append(("thumbnail", ("cover.jpg", open(cover, "rb"), "image/jpeg")))
    try:
        r = requests.post(f"{API}/upload", headers=headers, data=fields, files=files, timeout=600)
    finally:
        for _, (_, fh, _) in files:
            fh.close()
    try:
        data = r.json()
    except ValueError:
        data = {"success": False, "message": r.text[:500]}
    if r.status_code >= 400 or not data.get("success"):
        raise SystemExit(f"Upload-Post {r.status_code} : {data.get('message') or data.get('error') or data}")
    # envoi long → traitement en arrière-plan : on suit le statut
    if data.get("request_id") and not data.get("results") and not data.get("job_id"):
        data = wait_status(api_key, data["request_id"]) or data
    record.write_text(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "request_id": rid,
                                  "platforms": platforms, "response": data}, ensure_ascii=False, indent=2))
    report(data)
    return data


def wait_status(api_key: str, request_id: str, timeout: int = 900) -> dict | None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(10)
        r = requests.get(f"{API}/uploadposts/status", params={"request_id": request_id},
                         headers={"Authorization": f"Apikey {api_key}"}, timeout=60)
        if r.status_code != 200:
            continue
        data = r.json()
        status = str(data.get("status", "")).lower()
        print(f"   … statut : {status or 'en cours'}")
        if status in ("completed", "finished", "done", "success", "failed", "error") or data.get("results"):
            return data
    return None


def report(data: dict):
    if data.get("job_id"):
        print(f"   ✅ programmé (job {data['job_id']}) pour {data.get('scheduled_date')}")
        return
    for plat, res in (data.get("results") or {}).items():
        if res.get("success"):
            print(f"   ✅ {plat}: {res.get('url') or res.get('post_id') or 'publié'}")
        elif res.get("skipped"):
            print(f"   ⏭️  {plat}: aucun compte connecté sur ce profil Upload-Post")
        else:
            print(f"   ❌ {plat}: {res.get('error')}")
