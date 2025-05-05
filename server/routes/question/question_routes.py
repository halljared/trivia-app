from flask import Blueprint, request, jsonify
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from ...utils.auth import require_auth
from ...models import TriviaQuestion, Category, User, UserGeneratedQuestion
from ...database import db  
from ... import app

question_bp = Blueprint('question', __name__)

@question_bp.route('/question', methods=['GET'])
def get_question():
    """Get a random trivia question, optionally filtered."""
    difficulty = request.args.get('difficulty')
    category_id = request.args.get('category_id', type=int)

    # Base query
    stmt = select(TriviaQuestion).options(joinedload(TriviaQuestion.category)) # Eager load category

    # Apply filters
    if difficulty:
        stmt = stmt.filter(TriviaQuestion.difficulty == difficulty)
    if category_id:
        stmt = stmt.filter(TriviaQuestion.category_id == category_id)

    # Order randomly and fetch one
    stmt = stmt.order_by(func.random()).limit(1)
    q = db.session.scalar(stmt)

    if not q:
        return jsonify({"error": "No questions found with these criteria"}), 404

    # Construct response with camelCase keys
    return jsonify({
        'id': q.id,
        'question': q.question,
        'answer': q.answer,
        'category': q.category.name if q.category else None,
        'difficulty': q.difficulty
        # No snake_case keys here, so no change needed from previous state, but good practice to verify.
    })


@question_bp.route('/questions/user-generated', methods=['POST'])
@require_auth
def add_user_generated_question():
    """Add a new user-generated question."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    question = data.get('question')
    answer = data.get('answer')
    category_id = data.get('category_id') # Optional category
    difficulty = data.get('difficulty')
    created_by = data.get('created_by') # Assuming you pass the user ID
    notes = data.get('notes')

    # Basic Validation
    if not all([question, answer, difficulty]):
        return jsonify({'error': 'Missing required fields: question, answer, difficulty'}), 400
    if difficulty not in ['easy', 'medium', 'hard']:
        return jsonify({'error': 'Invalid difficulty. Must be one of: easy, medium, hard'}), 400

    # Optional: Validate category_id exists if provided
    if category_id and not db.session.get(Category, category_id):
         return jsonify({'error': f'Category with id {category_id} not found'}), 400

    # Optional: Validate created_by exists if provided (or get from session)
    # If using auth, you'd likely get this from the token instead of the payload
    if created_by and not db.session.get(User, created_by):
         return jsonify({'error': f'User with id {created_by} not found'}), 400

    new_q = UserGeneratedQuestion(
        question=question,
        answer=answer,
        category_id=category_id,
        difficulty=difficulty,
        created_by=created_by,
        notes=notes
        # status defaults to 'active'
    )

    try:
        db.session.add(new_q)
        db.session.commit()
        return jsonify({'id': new_q.id, 'message': 'Question added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding user question: {e}")
        # Provide a more specific error if possible (e.g., FK violation)
        return jsonify({'error': f'Could not add question: {e}'}), 500