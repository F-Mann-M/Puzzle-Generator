from uuid import uuid4, UUID

from app.llm import get_llm
from app import models



class SessionService:

    def __init__(self, db):
       self.db = db

    async def create_topic_name(self, message: str, model: str) -> str:
        """ Takes in first message of a session and creates a new topic name"""
        llm = get_llm(model)
        system_prompt = "Summarize this user query in 3 to 5 words. Do not use punctuation. Describe user as nobel man"
        prompt = {"system_prompt": system_prompt, "user_prompt": message}
        llm_response = await llm.chat(prompt)
        print("New topic name:", llm_response)
        return llm_response


    async def get_or_create_session(self, session_id: UUID, user_message: str, model: str):
        """ Gets a session by id or creates a new one if it doesn't exist """
        print("takes in session id: ", session_id)

        if session_id:
            existing = self.db.query(models.Session).filter(models.Session.id == session_id).first()
            print("Continue session with id:", existing.id)
            return existing.id
        else:
            print("No session found")

        topic_name = await self.create_topic_name(message=user_message, model=model)

        new_session = models.Session(
           id=uuid4(),
           topic_name=topic_name,
        )
        self.db.add(new_session)
        self.db.commit()

        print(f"New session was created. \nSession id: ", new_session.id)

        return new_session.id


    async def add_message(self, session_id: UUID, role: str, content: str):
        """ Takes in message of a session and adds it to the database"""
        new_message = models.Message(
            session_id=session_id,
            role=role,
            content=content,
        )
        self.db.add(new_message)
        self.db.commit()
        print(f"Added message from {role} to database")


    def get_session_messages(self, session_id: UUID):
        """ Gets session by id"""
        print(f"Query for session messages with session id: {session_id}")
        try:
            session = (self.db.query(models.Message)).filter(models.Message.session_id == session_id).all()
            print("Fetch session messages successfully")
            if not session:
                raise Exception("No session found")
        except Exception as e:
            print(f"Error: {e}")
            return []

        return session


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
            print(f"Error getting latest session: {e}")
            return [], None


    def get_all_sessions(self):
        """ Gets a list of all sessions """
        sessions = (self.db.query(models.Session).order_by(models.Session.created_at.desc()).all())
        return sessions


    def delete_session(self, session_id):
        """ Deletes a session by id """
        print("services delete session: ", session_id)
        session = self.db.query(models.Session).filter(models.Session.id == session_id).one()
        if session:
            print("session found")
            self.db.delete(session)
            self.db.commit()
        else:
            print("session not found")
        print(f"session successfully deleted: {session_id}")


    def get_chat_history(self, session_id):
        """
        Gets a chat history by session id. It is limited to the last 3500 characters (around 1000 token)
        It's like a dummy memory.
        Nice to have: would be to use an operation to extract important information,
        puzzles, feedback and results from the chat history, categorise it and use RAG to store information
        ...or somthing like that :D
        """
        #  get messages
        chat_messages = self.get_session_messages(session_id)
        chat_history = ""
        for message in chat_messages:
            chat_history += f"{message.role}: {message.content} \n"
        if chat_history:
            print("Chat history loaded")
        else:
            print("Chat history not found")

        # limit characters to 3500 characters
        if len(chat_history) > 3500:  # around 1000 token
            chat_history = chat_history[-3500:]

        print(f"Chat history length: {len(chat_history)}")

        return chat_history


    def update_topic_name(self, session_id, model):
        chat_history = self.get_chat_history(session_id)
        topic_name = self.create_topic_name(chat_history, model)
        session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        session.topic_name = topic_name
        self.db.commit()
        print(f"updated topic name: {topic_name}")


    def add_puzzle_id(self, puzzle_id: UUID, session_id: UUID):
        query = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        query.puzzle_id = puzzle_id
        self.db.commit()


    async def get_puzzle_id(self, session_id: UUID):
        """Get puzzle id by session id"""
        if not session_id:
            return None

        session = self.db.query(models.Session).filter(models.Session.id == session_id).first()
        if session:
            puzzle_id = session.puzzle_id
            return puzzle_id
        return None
