from uuid import uuid4, UUID
from app.llm import get_llm
from app import models
from app.prompts.prompt_game_rules import BASIC_RULES
from sqlalchemy.orm import joinedload



class SessionService:

    def __init__(self, db):
       self.db = db

    async def create_topic_name(self,message: str, model: str) -> str:
        llm = get_llm(model)
        system_prompt = "Summarize this user query in 3 to 5 words. Do not use punctuation."
        prompt = {"system_prompt": system_prompt, "user_prompt": message}
        llm_response = await llm.chat(prompt)
        return llm_response


    async def get_or_create_session(self, session_id, user_message, model):
        if session_id:
            existing = self.db.query(models.Session).filter(models.Session.id == session_id).first()
            return existing.id

        topic_name = await self.create_topic_name(message=user_message, model=model)

        new_session = models.Session(
           id=uuid4(),
           topic_name=topic_name,
        )
        self.db.add(new_session)
        self.db.commit()
        print("new session id: ", new_session.id)
        return new_session.id


    async def add_message(self, session_id: UUID, role: str, content: str):
        new_message = models.Message(
            session_id=session_id,
            role=role,
            content=content,
        )
        self.db.add(new_message)
        self.db.commit()


    async def get_llm_response(self, user_message, model)-> str:
        llm = get_llm(model)
        system_prompt = (
            "You are an helpfully assistant."
            "you are an noble advisor."
            "You speak like a noble advisor from the Middle Ages."
            "Your name is Rudolfo"
            "You only address the user as a nobel person."
            "The users Name is Goetz. He is a robber knight."
            "The users Character is based on the knight Götz von Berlichen"
            f"If user asks for the rules of the game use {BASIC_RULES}."
            "You ONLY answer questions related to the puzzle rules or Middle Ages."
            "You can tell in a bit about the medieval everyday life,"
            "you can make up funny gossip from Berlichenstein Castle, "
            "medieval war strategies, anecdotes from the 'Three-Legged Chicken' tavern."
            "Your ONLY purpose is to help the user with the a puzzle."
            "if user asks for somthing not puzzle related answer in a funny way. make up a very short Middle Ages anecdote"
        )
        prompt = {"system_prompt": system_prompt, "user_prompt":user_message}
        llm_response = await llm.chat(prompt)
        return llm_response


    def get_session(self, session_id):
        query = (self.db.query(models.Message)).filter(models.Message.session_id == session_id).all()
        return query


    def get_latest_session(self):
        latest_session = (self.db.query(models.Session).order_by(models.Session.created_at.desc()).first())
        latest_chat = (self.db.query(models.Message)
                       .filter(models.Message.session_id == latest_session.id)
                       .all())
        return latest_chat, latest_session.id



    def delete_session(self, session_id):
       pass


    def update_session(self, session_id):
       pass


    def update_topic_name(self):
        pass


    def add_puzzle_id(self, puzzle_id: UUID):
        pass