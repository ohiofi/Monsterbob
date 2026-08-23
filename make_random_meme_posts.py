import os, sys
import random
from mastodon import Mastodon
from dotenv import load_dotenv
from pathlib import Path
import logging

PROJECT_DIR = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOGS_DIR / "monsterbob.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

load_dotenv()

devilgirl_path = os.getenv("DEVILGIRL_PATH")
if devilgirl_path and devilgirl_path not in sys.path:
    sys.path.insert(0, devilgirl_path)



from shared_utils import (
    load_sentences, 
    save_sentences, 
    update_history, 
    select_random_image,
    make_image, 
    build_alt_text
)

mastodon = Mastodon(
    client_id=os.getenv("MONSTERBOB_CLIENT_KEY"),
    client_secret=os.getenv("MONSTERBOB_CLIENT_SECRET"),
    access_token=os.getenv("MONSTERBOB_ACCESS_TOKEN"),
    api_base_url=os.getenv("MONSTERBOB_BASE_URL", "https://mastodon.social"),
    request_timeout=40
)

MONSTERBOB_WIDTH = 640
MONSTERBOB_HEIGHT = 480
MONSTERBOB_IMAGES_DIR = os.path.join(os.getcwd(), "images")

def run_random_meme_post():
    """
    Selects a sentence from the local pool, creates a meme, 
    posts it, and logs the source/result to history.
    """
    
    # This reads the possible_sentences.json populated by your scraper
    pool = load_sentences()
    
    if not pool:
        print("DEBUG: The sentence pool is empty. Please run the scraper script.")
        return False

    # SELECT AND REMOVE A SENTENCE
    # We pick one at random to use for the post
    selection = random.choice(pool)
    sentence = selection['sentence']
    source_url = selection['url']
    
    # Remove it immediately so it isn't picked again by another process
    pool.remove(selection)
    save_sentences(pool)

    print(f"DEBUG: Selected sentence: {sentence[:50]}...")

    try:
        # 1. Select the base image
        image_path = select_random_image(MONSTERBOB_IMAGES_DIR)
        print(f"DEBUG: Selected image: {os.path.basename(image_path)}")

        # 2. Render meme with specific dimensions
        png_path = make_image(
            image_path=image_path,
            user_text=sentence, 
            target_size=(640, 480)
        )
        
        alt_text = build_alt_text(
            sentence, 
            subject="A SpongeBob SquarePants meme"
        )

        # 5. UPLOAD MEDIA & POST TO MASTODON
        print("DEBUG: Uploading media...")
        with open(png_path, "rb") as f:
            media = mastodon.media_post(
                f, 
                mime_type='image/png', 
                description=alt_text
            )
            media_id = media["id"]

        print("DEBUG: Sending status post...")
        response = mastodon.status_post(
            status=sentence,
            media_ids=[media_id],
            visibility="public"
        )
        
        meme_url = response.get("url") or response.get("uri")
        print(f"SUCCESS: Post live at {meme_url}")

        # 6. LOG TO SHARED HISTORY
        # Stores the sentence, original toot URL, and your new meme URL
        update_history(
            text=sentence,
            source_url=source_url,
            meme_url=meme_url
        )
        return True

    except Exception as e:
        print(f"CRITICAL ERROR: Failed to create or post random meme: {e}")
        # If the post failed, we don't put the sentence back in the pool 
        # to prevent broken sentences from looping, but you could 
        # choose to append it back if the error was just a network timeout.
        return False

if __name__ == "__main__":
    run_random_meme_post()