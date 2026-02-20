from .__init__ import db

# Define Python classes that map to your existing MySQL tables.
# Use __tablename__ to specify the exact table name in MySQL.

class User(db.Model):
    __tablename__ = 'tbl_user' # Matches your existing table name
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(45))
    user_username = db.Column(db.String(45), unique=True)
    user_password = db.Column(db.String(45))

    def __repr__(self):
        return f'<User {self.user_username}>'

# Define other models for your other tables...
