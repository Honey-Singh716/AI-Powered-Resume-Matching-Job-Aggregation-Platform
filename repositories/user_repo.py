from models.user import User

def create_user(email,password,role,db):

    user = User(email=email,password=password,role=role)

    db.add(user)
    db.commit()

    db.refresh(user)


    return user


def get_user_by_email(email,db):
    return db.query(User).filter(User.email == email).first()