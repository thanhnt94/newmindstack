import json
import os
from hanzipy.decomposer import HanziDecomposer
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_kanji_db_with_hanzipy(kanji_db_path: str, overwrite_components: bool = False):
    """
    Updates kanji_db.json with decomposition data from hanzipy.

    :param kanji_db_path: Path to the kanji_db.json file.
    :param overwrite_components: If True, hanzipy level 2 radicals will overwrite
                                 existing 'components' if 'components' is empty.
    """
    if not os.path.exists(kanji_db_path):
        logger.error(f"Kanji DB file not found: {kanji_db_path}")
        return

    try:
        with open(kanji_db_path, 'r', encoding='utf-8') as f:
            kanji_db = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {kanji_db_path}: {e}")
        return

    logger.info("Initializing HanziDecomposer...")
    try:
        decomposer = HanziDecomposer()
    except Exception as e:
        logger.error(f"Failed to initialize HanziDecomposer: {e}. Aborting update.", exc_info=True)
        return

    updated_count = 0
    total_kanji = len(kanji_db)
    logger.info(f"Processing {total_kanji} Kanji characters...")

    for i, (kanji, data) in enumerate(kanji_db.items()):
        if i % 100 == 0:
            logger.info(f"Processed {i}/{total_kanji} Kanji.")

        try:
            # Get decomposition from hanzipy
            level1_immediate = decomposer.decompose(kanji, 1)
            level2_radicals = decomposer.decompose(kanji, 2)
            level3_strokes = decomposer.decompose(kanji, 3)

            # Store in new dedicated fields
            kanji_db[kanji]['hanzipy_level1_immediate'] = {
                "character": kanji,
                "components": level1_immediate
            }
            kanji_db[kanji]['hanzipy_level2_radicals'] = {
                "character": kanji,
                "components": level2_radicals
            }
            kanji_db[kanji]['hanzipy_level3_strokes'] = {
                "character": kanji,
                "components": level3_strokes
            }

            # Optionally overwrite existing 'components' if empty
            if overwrite_components and not data.get('components'):
                kanji_db[kanji]['components'] = level2_radicals # Using level2 as a sensible default for 'components'

            updated_count += 1

        except Exception as e:
            logger.warning(f"Could not process kanji '{kanji}': {e}")
            # Ensure decomposition fields are at least empty lists if an error occurs
            kanji_db[kanji]['hanzipy_level1_immediate'] = {"character": kanji, "components": []}
            kanji_db[kanji]['hanzipy_level2_radicals'] = {"character": kanji, "components": []}
            kanji_db[kanji]['hanzipy_level3_strokes'] = {"character": kanji, "components": []}

    logger.info(f"Finished processing. Updated {updated_count} Kanji characters.")

    try:
        with open(kanji_db_path, 'w', encoding='utf-8') as f:
            json.dump(kanji_db, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully wrote updated Kanji DB to {kanji_db_path}")
    except Exception as e:
        logger.error(f"Error writing updated Kanji DB to {kanji_db_path}: {e}")

if __name__ == '__main__':
    # Adjust this path if your script is run from a different directory
    current_dir = os.path.dirname(__file__)
    kanji_data_dir = os.path.join(current_dir, '..', 'mindstack_app', 'modules', 'kanji', 'logics')
    kanji_db_file = os.path.join(kanji_data_dir, 'kanji_db.json')

    # Example usage:
    # Set overwrite_components to True if you want hanzipy's level 2 radicals
    # to fill in empty 'components' fields.
    update_kanji_db_with_hanzipy(kanji_db_file, overwrite_components=False)
    # If you want to overwrite components:
    # update_kanji_db_with_hanzipy(kanji_db_file, overwrite_components=True)
