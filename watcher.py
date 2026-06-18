import logging
import time
from datetime import datetime

from googleapiclient.errors import HttpError

from audio_helpers import record_audio, speak, transcribe
from config import (
    DEFAULT_USER_NAME,
    MAX_DRAFT_EMAILS,
    MAX_EMAIL_PREVIEW,
    RECORD_SAMPLERATE,
    RECORD_SECONDS,
    WATCH_SENDERS,
)
from gmail_client import (
    create_gmail_draft,
    get_unread_emails,
    is_watched_sender,
    send_gmail_message,
)
from llm_helpers import (
    build_draft_chain,
    build_refine_chain,
    build_summary_chain,
    generate_draft_reply,
    refine_message,
    summarize_email,
)

log = logging.getLogger(__name__)


def run_watcher_mode(service, llm, tts, whisper_model, interval: int, fast_mode: bool = False):
    print("\n" + "=" * 60)
    print("  MODE: Watch + TTS + Draft Choices")
    print("=" * 60)
    print(f"  Watching: {WATCH_SENDERS}")
    print(f"  Interval: {interval}s | Fast: {fast_mode} | Press Ctrl+C to stop\n")

    summary_chain = None if fast_mode else build_summary_chain(llm)
    draft_chain = build_draft_chain(llm)
    refine_chain = build_refine_chain(llm)

    seen_ids = set()

    speak(tts, f"Hi, {DEFAULT_USER_NAME}. I'm your Gmail assistant.")
    speak(tts, "Gmail watcher is active. I will notify you when a watched email arrives.")

    while True:
        try:
            log.info(f"[{datetime.now().strftime('%H:%M:%S')}] Polling Gmail...")
            emails = get_unread_emails(service, max_results=MAX_DRAFT_EMAILS)

            for email in emails:
                if email["id"] in seen_ids:
                    continue
                seen_ids.add(email["id"])

                if not is_watched_sender(email, WATCH_SENDERS):
                    continue

                log.info(f"MATCH: {email['sender']} — {email['subject']}")

                if fast_mode:
                    summary = f"{email['sender_name']} sent an email about {email['subject']}."
                else:
                    summary = summarize_email(summary_chain, email)

                print(f"\n  From:    {email['sender']}")
                print(f"  Subject: {email['subject']}")
                print(f"  Preview: {email['body'][:MAX_EMAIL_PREVIEW]}...")

                spoken = f"{DEFAULT_USER_NAME}, you have a message from {email['sender_name']}. {summary}"
                speak(tts, spoken)

                while True:
                    print("\n  Choose an option:")
                    print("    [1] Use my draft")
                    print("    [2] Use LLM response")
                    print("    [3] Skip")
                    choice = input("  Choice (1/2/3): ").strip().lower()

                    if choice in ("1", "use my draft", "use my message"):
                        speak(tts, "Please speak your message now.")
                        audio = record_audio(seconds=RECORD_SECONDS)
                        if audio is None or len(audio) < RECORD_SAMPLERATE * 0.5:
                            speak(tts, "No audio captured. Please try again.")
                            continue

                        raw_text = transcribe(whisper_model, audio)
                        if not raw_text:
                            speak(tts, "I could not understand your message. Please try again.")
                            continue

                        print(f"\n  Your message: {raw_text}")
                        refined = refine_message(refine_chain, raw_text)
                        if not refined:
                            speak(tts, "I could not refine your message.")
                            break

                        print(f"  Final message:\n{refined}")
                        speak(tts, f"Here is your final message: {refined}")

                        send_now = input("\n  Send this reply now? (y/n): ").strip().lower()
                        if send_now == "y":
                            sent_id = send_gmail_message(
                                service,
                                email["sender"],
                                f"Re: {email['subject']}",
                                refined,
                                thread_id=email["thread_id"],
                            )
                            if sent_id:
                                print(f"\n  Email sent. ID: {sent_id}")
                                speak(tts, "Your reply has been sent.")
                            else:
                                speak(tts, "I could not send the email.")
                        else:
                            save_now = input(
                                "\n  Save this reply as a draft instead? (y/n): "
                            ).strip().lower()
                            if save_now == "y":
                                draft_id = create_gmail_draft(service, email, refined)
                                if draft_id:
                                    print(f"\n  Draft saved. ID: {draft_id}")
                                    speak(tts, "Your reply has been saved to Gmail drafts.")
                                else:
                                    speak(tts, "I could not save the draft.")
                            else:
                                speak(tts, "Reply cancelled.")
                        break

                    elif choice in ("2", "llm response", "use llm"):
                        reply = generate_draft_reply(draft_chain, email)
                        if not reply:
                            speak(tts, "The AI response could not be generated.")
                            break

                        send_now = input("\n  Send this AI reply now? (y/n): ").strip().lower()
                        if send_now == "y":
                            sent_id = send_gmail_message(
                                service,
                                email["sender"],
                                f"Re: {email['subject']}",
                                reply,
                                thread_id=email["thread_id"],
                            )
                            if sent_id:
                                print(f"\n  Email sent. ID: {sent_id}")
                                speak(tts, "The AI reply has been sent.")
                            else:
                                speak(tts, "I could not send the email.")
                        else:
                            save_now = input(
                                "\n  Save this AI reply as a draft instead? (y/n): "
                            ).strip().lower()
                            if save_now == "y":
                                draft_id = create_gmail_draft(service, email, reply)
                                if draft_id:
                                    print(f"\n  Draft saved. ID: {draft_id}")
                                    speak(tts, "The AI reply has been saved to Gmail drafts.")
                                else:
                                    speak(tts, "I could not save the draft.")
                            else:
                                speak(tts, "Reply cancelled.")
                        break

                    elif choice in ("3", "skip", "s"):
                        speak(tts, "Skipping this email for now.")
                        break

                    else:
                        print("  Please choose 1, 2, or 3.")

        except HttpError as e:
            log.error(f"Gmail error: {e}")
        except KeyboardInterrupt:
            speak(tts, "Watcher stopped. Goodbye.")
            break
        except Exception as e:
            log.error(f"Error: {e}")

        time.sleep(interval)
