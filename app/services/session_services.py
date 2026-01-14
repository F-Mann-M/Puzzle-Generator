from concurrent.futures import thread
from uuid import uuid4, UUID
import logging
from app.llm import get_llm
from app import models
from app.core.config import settings
import aiosqlite

logger = logging.getLogger(__name__)

class SessionService:

    def __init__(self, db):
       self.db = db

    async def create_topic_name(self, message: str, model: str) -> str:
        """ Takes in first message of a session and creates a new topic name"""
        llm = get_llm(model)
        system_prompt = "Summarize this user query in 3 to 5 words. Do not use punctuation. Describe user as nobel man"
        prompt = {"system_prompt": system_prompt, "user_prompt": message}
        llm_response = await llm.chat(prompt)
        logger.debug("New topic name:", llm_response)
        return llm_response


    async def get_or_create_session(self, session_id: UUID, user_message: str, model: str):
        """ Gets a session by id or creates a new one if it doesn't exist """
        logger.debug("takes in session id: ", session_id)

        if session_id:
            existing = self.db.query(models.Session).filter(models.Session.id == session_id).first()
            if existing.puzzle_id:
                await self.update_session_title(existing.puzzle_id, session_id)
            logger.debug("Continue session with id:", existing.id)
            return existing.id
        else:
            logger.debug("No session found")

        topic_name = await self.create_topic_name(message=user_message, model=model)

        new_session = models.Session(
           id=uuid4(),
           topic_name=topic_name,
        )
        self.db.add(new_session)
        self.db.commit()

        logger.debug(f"New session was created. \nSession id: ", new_session.id)

        return new_session.id


    def get_latest_session(self):
        """ Gets latest session """
        try:
            latest_session = (self.db.query(models.Session).order_by(models.Session.created_at.desc()).first())

            if latest_session is None:
                return [], None

            latest_chat = (self.db.query(models.Message)
                           .filter(models.Message.session_id == latest_session.id)
                           .all())

            return latest_chat, latest_session.id
            
        except Exception as e:
            logger.error(f"Error getting latest session: {e}", exc_info=True)
            return [], None


    def get_all_sessions(self):
        """ Gets a list of all sessions """
        sessions = (self.db.query(models.Session).order_by(models.Session.created_at.desc()).all())
        return sessions


    async def delete_session(self, session_id):
        """ Deletes a session by id """
        logger.debug("services delete session: ", session_id)

        try:
            session = self.db.query(models.Session).filter(models.Session.id == session_id).one()
            if session:
                logger.debug("session found")

                if session.puzzle_id:
                    puzzle = self.db.query(models.Puzzle).filter(models.Puzzle.id == session.puzzle_id).first()
                    if puzzle:
                        self.db.delete(puzzle)
                    else:
                        logger.debug("Could not delete puzzle", exc_info=True)

                self.db.delete(session)
                self.db.commit()
                logger.info(f"session successfully deleted: {session_id}")
            else:
                logger.warning("session not found", exc_info=True)
        except Exception as e:
            logger.error(f"Error deleting session: {e}", exc_info=True)

        try:
            # since langgraph has no build-in delete for (tread, checkpoints) memory
            # each thread related to current session_id has deleted by SQL DELETE
            db_path = settings.CHECKPOINTS_URL

            logger.debug(f"Cleaning checkpoints for thread_id {session_id} in {db_path}")

            async with aiosqlite.connect(db_path) as conn: # open a session
                # Delete form 'checkpoints' tables
                await conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (str(session_id),))
                # Commit the changes
                await conn.commit()

            logger.info(f"LangGraph checkpoints deleted for thread {session_id}")

        except Exception as e:
            logger.error(f"Error deleting LangGraph checkpoints: {e}", exc_info=True)


    def add_puzzle_id(self, puzzle_id: UUID, session_id: UUID):
        query = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        query.puzzle_id = puzzle_id
        self.db.commit()


    def get_puzzle_id(self, session_id: UUID):
        """Get puzzle id by session id"""
        if not session_id:
            return None

        session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        if session:
            puzzle_id = session.puzzle_id
            return puzzle_id
        return None


    async def update_session_title(self, puzzle_id: UUID, session_id: UUID) -> bool:
        """Change session title to puzzle name, if there is a puzzle id"""
        TOOL = "update_session_title: "
        logger.debug(f"{TOOL} updating session title to puzzle name...")
        try:
            puzzle = self.db.query(models.Puzzle).filter(models.Puzzle.id == puzzle_id).first()
            logger.debug(f"{TOOL} New puzzle title: {puzzle.name}")
            session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
            logger.debug(f"{TOOL} Current session title: {session.topic_name}")

            if puzzle and session:
                if session.topic_name != puzzle.name:
                    session.topic_name = puzzle.name
                    self.db.commit()
                    logger.debug(f"{TOOL} Changed session title to new puzzle name: {puzzle.name}")
                    return True  # Trigger sidebar update in chat router
        except Exception as e:
            logger.error(f"{TOOL} could not update session topic: {e}", exc_info=True)

        return False


    async def ensure_puzzles_have_sessions(self):
        """
        Startup Check: Iterates through all puzzles.
        If a puzzle has no linked session, creates one automatically.
        """

        logger.info(f"Checking for orphaned puzzles...")

        # Get all puzzles
        puzzles = self.db.query(models.Puzzle).all()
        created_count = 0

        for puzzle in puzzles:
            # Check if a session already exists for this puzzle
            existing_session = self.db.query(models.Session).filter(
                models.Session.puzzle_id == puzzle.id
            ).first()

            if not existing_session:
                logger.info(f"Creating missing session for puzzle '{puzzle.name}'")

                # 3. Create new session linked to the puzzle
                new_session = models.Session(
                    id=uuid4(),
                    topic_name=puzzle.name,  # Use puzzle name as default topic
                    puzzle_id=puzzle.id
                )
                self.db.add(new_session)
                created_count += 1

        # Commit only if changes were made
        if created_count > 0:
            self.db.commit()
            logger.info(f"Successfully created {created_count} missing sessions.")
        else:
            logger.info(f"All puzzles are correctly linked to sessions.")


    async def ensure_checkpointer_have_sessions(self):
        logger.info("Checking for orphaned checkpointers...")

        # get all sessions
        try:
            valid_session_ids = [str(session.id) for session in self.db.query(models.Session).all()]
            logger.info(f"Current session ids: {valid_session_ids}")
        except Exception as e:
            logger.error(f"Error checking for orphaned checkpointers: {e}", exc_info=True)

        # get thread_ids
        try:
            async with aiosqlite.connect(settings.CHECKPOINTS_URL) as conn:
                # Get existing threads
                async with conn.execute("SELECT DISTINCT thread_id FROM checkpoints") as cursor:
                    existing_threads = await cursor.fetchall()

                # Identify orphans
                orphan_threads = [thread[0] for thread in existing_threads if thread[0] not in valid_session_ids]

                if not orphan_threads:
                    logger.info("No orphan threads found.")
                    return

                logger.debug(f"{len(orphan_threads)} orphan threads found. Deleting...")

                # delete orphan threads
                for thread_id in orphan_threads:
                    await conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (str(thread_id),))

                await conn.commit()
                logger.info(f"Orphan threads successfully deleted: {orphan_threads}")

        except Exception as e:
            logger.error(f"Error cleaning orphaned checkpointers: {e}", exc_info=True)
