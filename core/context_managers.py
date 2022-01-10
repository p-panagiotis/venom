from contextlib import contextmanager

from core import venom


@contextmanager
def session_scope():
    """ Creates a new database session scope """
    session = venom.database.Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
        venom.database.Session.remove()
