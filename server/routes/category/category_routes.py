from ...database import db
from ...models import Category, TriviaQuestion
from sqlalchemy import select, func
from flask import jsonify, request, Blueprint

category_bp = Blueprint('category', __name__)

@category_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all available trivia categories."""
    categories = db.session.scalars(
        select(Category).order_by(Category.name)
    ).all()

    # Construct response with camelCase keys (no change needed as keys were simple)
    return jsonify([{"id": c.id, "name": c.name} for c in categories])

@category_bp.route('/categories/active', methods=['GET'])
def get_active_categories():
    """Get categories that have a minimum number of questions."""
    min_questions = request.args.get('min_questions', default=80, type=int)

    stmt = (
        select(Category.id, Category.name, func.count(TriviaQuestion.id).label('question_count'))
        .outerjoin(TriviaQuestion, Category.id == TriviaQuestion.category_id) # Use outerjoin
        .group_by(Category.id, Category.name)
        .having(func.count(TriviaQuestion.id) >= min_questions)
        .order_by(Category.name)
    )
    results = db.session.execute(stmt).all() # Returns Row objects

    # Manually create dicts with camelCase keys
    categories_data = [
        {"id": row.id, "name": row.name, "questionCount": row.question_count} # Renamed question_count
        for row in results
    ]
    return jsonify(categories_data) # Return the transformed data

@category_bp.route('/category/<int:category_id>/questions', methods=['GET'])
def get_category_questions(category_id):
    """Get multiple random questions from a specific category."""
    count = min(request.args.get('count', default=10, type=int), 50) # Cap at 50

    # Verify category exists first
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    # Fetch random questions
    stmt = (
        select(TriviaQuestion)
        .filter_by(category_id=category_id)
        .order_by(func.random())
        .limit(count)
    )
    questions = db.session.scalars(stmt).all()

    if not questions:
        return jsonify({"error": "No questions found in this category"}), 404

    # Construct response with camelCase keys (no change needed as keys were simple)
    questions_data = [
        {
            'id': q.id,
            'question': q.question,
            'answer': q.answer,
            'category': category.name, # Use the fetched category name
            'difficulty': q.difficulty
        } for q in questions
    ]
    return jsonify(questions_data)
