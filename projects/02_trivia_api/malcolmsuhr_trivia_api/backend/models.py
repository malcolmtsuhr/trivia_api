import os
from sqlalchemy import (
    Table, Column, String, Integer, create_engine, ForeignKey)
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import json

database_name = "trivia"
user_name = "malcolmsuhr"
database_path = "postgres://{}:{}@{}/{}".format(
    user_name, 'postgres', 'localhost:5432', database_name)

db = SQLAlchemy()
migrate = Migrate()

'''
setup_db(app)
    binds a flask application and a SQLAlchemy service
'''


def setup_db(app, database_path=database_path):
    app.config["SQLALCHEMY_DATABASE_URI"] = database_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.app = app
    db.init_app(app)
    migrate.init_app(app, db)
    db.create_all()


'''
Question

'''


class Question(db.Model):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    question = Column(String)
    answer = Column(String)
    difficulty = Column(Integer)
    category = Column(Integer, ForeignKey('categories.id'))

    def __init__(self, question, answer, category, difficulty):
        self.question = question
        self.answer = answer
        self.category = category
        self.difficulty = difficulty

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
          'id': self.id,
          'question': self.question,
          'answer': self.answer,
          'category': self.category,
          'difficulty': self.difficulty
        }


'''
Category

'''


class Category(db.Model):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    type = Column(String)
    questions = relationship('Question', backref='categories',
                             cascade='all, delete-orphan', lazy='joined')

    def __init__(self, type):
        self.type = type

    def format(self):
        return {
          'id': self.id,
          'type': self.type
        }
