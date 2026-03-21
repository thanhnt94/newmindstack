from database import engine, Base
from models import WTChatMessage, WTVideoHistory

def patch():
    print("Creating layout for WTChatMessage and WTVideoHistory...")
    Base.metadata.create_all(bind=engine, tables=[WTChatMessage.__table__, WTVideoHistory.__table__])
    print("wt5 DB patched!")

if __name__ == '__main__':
    patch()
