import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# repo_root is c:\Code\MindStack (3 levels up from this file)
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(repo_root, 'Storage', 'database', 'watchtogether.sqlite')
os.makedirs(os.path.dirname(db_path), exist_ok=True)

engine = create_engine(f'sqlite:///{db_path}', connect_args={'check_same_thread': False})
TargetSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(TargetSession)

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    import watchtogether.models
    Base.metadata.create_all(bind=engine)
