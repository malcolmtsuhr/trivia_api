import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
import random

from models import *

QUESTIONS_PER_PAGE = 10


def paginate_questions(request, selection):
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    questions = [question.format() for question in selection]
    current_questions = questions[start:end]

    return current_questions


'''
Configure & set up app with CORS. Allow '*' for origins.
'''


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    '''
    Use the after_request decorator to set Access-Control-Allow.
    '''
    # CORS Headers
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type,Authorization,true')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET,PUT,POST,PATCH,DELETE,OPTIONS')
        return response

    '''
    Endpoint to handle GET requests
    for all available categories.
    '''
    @app.route('/categories', methods=['GET', 'POST'])
    def getCategories():
        categories = Category.query.order_by(Category.id).all()
        format_categories = {category.id: category.type
                             for category in categories}

        if len(format_categories) == 0:
            abort(404)

        return jsonify({
            'success': True,
            'categories': format_categories
        })

    '''
    Endpoint to handle GET requests for questions,
    including pagination (every 10 questions).
    This endpoint returns a list of questions,
    number of total questions, current category, & all categories.
    '''
    @app.route('/questions', methods=['GET'])
    def getQuestions():
        selection = Question.query.order_by(Question.id).all()
        current_questions = paginate_questions(request, selection)

        categories = Category.query.order_by(Category.id).all()
        format_categories = {category.id: category.type
                             for category in categories}
        current_category = request.args.get('currentCategory', None)

        if len(current_questions) == 0:
            abort(404)

        return jsonify({
            'success': True,
            'questions': current_questions,
            'total_questions': len(selection),
            'categories': format_categories,
            'current_category': current_category
        })

    '''
    Endpoint to DELETE question using a question ID.
    '''
    @app.route('/questions/<int:question_id>', methods=['DELETE'])
    def deleteQuestion(question_id):
        try:
            question = Question.query.filter(
                Question.id == question_id).one_or_none()

            if question is None:
                abort(404)

            question.delete()
            selection = Question.query.order_by(Question.id).all()
            current_questions = paginate_questions(request, selection)

            return jsonify({
                'success': True,
                'deleted': question_id,
                'questions': current_questions,
                'total_questions': len(selection)
            })

        except Exception:
            abort(422)

    '''
    Endpoint to POST a new question or SEARCH questions based on a search term.

    Search returns any questions for which the search term is a substring
    of the question.

    Post new question takes required data for the question and answer text,
    category, and difficulty score.
    '''
    @app.route('/questions', methods=['POST'])
    def submitQuestion():
        body = request.get_json()

        new_question = body.get('question', None)
        new_answer = body.get('answer', None)
        new_category = body.get('category', None)
        new_difficulty = body.get('difficulty', None)

        search = body.get('searchTerm', None)

        try:
            if search:
                current_category = request.args.get('currentCategory', None)
                selection = Question.query.order_by(Question.id).filter(
                    Question.question.ilike('%{}%'.format(search)))
                current_questions = paginate_questions(request, selection)

                return jsonify({
                  'success': True,
                  'questions': current_questions,
                  'total_questions': len(selection.all()),
                  'current_category': current_category
                })

            else:
                newQuestion = Question(
                    question=new_question,
                    answer=new_answer,
                    category=new_category,
                    difficulty=new_difficulty)
                newQuestion.insert()

                selection = Question.query.order_by(Question.id).all()
                current_questions = paginate_questions(request, selection)

                return jsonify({
                    'success': True,
                    'created': newQuestion.id,
                    'questions': current_questions,
                    'total_questions': len(selection)
                })

        except Exception:
            abort(422)

    '''
    Endpoint to GET questions based on category.
    '''
    @app.route('/categories/<int:category_id>/questions', methods=['GET'])
    def getQuestionsByCategory(category_id):
        selection = Question.query.filter(
            Question.category == category_id).order_by(Question.id).all()
        current_questions = paginate_questions(request, selection)

        categories = Category.query.order_by(Category.id).all()
        format_categories = [category.format() for category in categories]
        current_category = request.args.get('currentCategory', None)

        if len(current_questions) == 0:
            abort(404)

        return jsonify({
            'success': True,
            'questions': current_questions,
            'total_questions': len(selection),
            'categories': format_categories,
            'current_category': current_category
        })

    '''
    POST endpoint to get questions to play the quiz.
    This endpoint takes category and previous question parameters
    and returns a random question within the given category,
    if provided, that is not one of the previous questions.
    '''
    @app.route('/quizzes', methods=['POST'])
    def playQuiz():
        body = request.get_json()
        quiz_category = body.get('quiz_category', None).get('id')
        previous_questions = body.get('previous_questions', None)

        if quiz_category == 0:
            quiz_questions = Question.query.all()

        else:
            quiz_questions = Question.query.filter(
                Question.category == quiz_category).all()

        question_pool = []

        try:
            for question in quiz_questions:
                if question.id not in previous_questions:
                    question_pool.append(question.format())
                else:
                    pass

            if len(question_pool) != 0:
                current_question = random.choice(question_pool)
                return jsonify({
                    'success': True,
                    'question': current_question
                })
            else:
                return jsonify({
                    'success': True,
                    'question': False
                })

        except Exception:
            abort(404)

    '''
    Error handlers for
    400, 404, 405, 422, and 500.
    '''

    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            'success': False,
            'error': 400,
            "message": "Bad Request"
        }), 400

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'success': False,
            'error': 404,
            "message": "resource not found"
        }), 404

    @app.errorhandler(405)
    def not_found_error(error):
        return jsonify({
            'success': False,
            'error': 405,
            "message": "Method Not Allowed"
        }), 405

    @app.errorhandler(422)
    def not_processable_error(error):
        return jsonify({
            'success': False,
            'error': 422,
            "message": "Not Processable"
        }), 422

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({
            'success': False,
            'error': 500,
            "message": "Server Error"
        }), 500

    return app
