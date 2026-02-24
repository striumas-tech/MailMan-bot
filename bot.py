import discord
from discord.ext import tasks
import os
import imaplib
import email
import re
from email.header import decode_header
from datetime import datetime, timezone

# ================= ENV VARIABLES =================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# ================= DISCORD SETUP =================

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Keep track of processed email IDs (in-memory)
processed_uids = set()

# ================= READY EVENT =================

@client.event
async def on_ready():
    print(f"Bot ready: {client.user}")
    if not check_mail.is_running():
        check_mail.start()

# ================= MAIL CHECK LOOP =================

@tasks.loop(seconds=30)
async def check_mail():
    print("Checking mail...")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Search for unseen emails
        status, messages = mail.search(None, '(UNSEEN)')
        if status != "OK":
            mail.logout()
            return

        for uid in messages[0].split():

            if uid in processed_uids:
                continue

            status, msg_data = mail.fetch(uid, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            sender = msg.get("From", "")
            subject_raw = msg.get("Subject", "")

            subject, encoding = decode_header(subject_raw)[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")

            # 🔎 Adjust this filter if needed after testing
            if "reborn" not in sender.lower():
                continue

            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/html":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
                    elif content_type == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            # Extract first HTTPS link
            link_match = re.search(r'https://[^\s"]+', body)

            if not link_match:
                continue

            confirmation_link = link_match.group(0)

            channel = client.get_channel(CHANNEL_ID)

            if channel:
                embed = discord.Embed(
                    title="VIP Login Confirmation Required",
                    description="A VIP login attempt requires confirmation.",
                    color=0xFFD700,
                    timestamp=datetime.now(timezone.utc)
                )

                embed.add_field(
                    name="Email Subject",
                    value=subject,
                    inline=False
                )

                embed.add_field(
                    name="Confirmation Link",
                    value=confirmation_link,
                    inline=False
                )

                await channel.send(embed=embed)

            processed_uids.add(uid)

        mail.logout()

    except Exception as e:
        print("Mail check error:", e)

# ================= START BOT =================

client.run(DISCORD_TOKEN)
