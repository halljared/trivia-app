from flask import Blueprint, request, jsonify
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from ...models import Round, Event
from ...database import db
from ...utils.auth import require_auth
from ... import app

round_bp = Blueprint('round', __name__)

@round_bp.route('/rounds/<int:round_id>', methods=['GET'])
@require_auth
def get_round(round_id):
    """Fetch a specific round and all its questions."""
    # Check if the round exists
    round_exists = db.session.get(Round, round_id)
    if not round_exists:
        return jsonify({'error': f'Round with id {round_id} not found'}), 404

    # Verify user has access to the event
    event_owner_id = db.session.scalar(select(Event.user_id).join(Round).filter(Round.id == round_id))
    if event_owner_id is None:
        return jsonify({'error': 'Round data inconsistent'}), 500
    if event_owner_id != request.user.id:
        return jsonify({'error': 'Permission denied to access this round'}), 403

    try:
        # Select the Round and eager load the normalized questions
        stmt = (
            select(Round)
            .where(Round.id == round_id)
            .options(
                selectinload(Round.normalized_questions)
            )
        )
        round_obj = db.session.scalars(stmt).first()

        if not round_obj:
            return jsonify({'error': f'Round with id {round_id} not found'}), 404

        # Construct questions list
        questions_list = [{
            'roundQuestionId': q.round_question_id,
            'roundId': q.round_id,
            'questionNumber': q.question_number,
            'questionId': q.question_id,
            'questionType': q.question_type,
            'question': q.question,
            'answer': q.answer,
            'difficulty': q.difficulty,
            'categoryId': q.category_id,
            'categoryName': q.category_name
        } for q in round_obj.normalized_questions]

        # Construct round response
        round_response = {
            'id': round_obj.id,
            'name': round_obj.name,
            'roundNumber': round_obj.round_number,
            'eventId': round_obj.event_id,
            'categoryId': round_obj.category_id,
            'createdAt': round_obj.created_at.isoformat() if round_obj.created_at else None,
            'questions': questions_list
        }

        return jsonify(round_response)
    except Exception as e:
        app.logger.error(f"Error fetching round {round_id}: {e}")
        return jsonify({'error': 'Failed to retrieve round data'}), 500

@round_bp.route('/rounds/<int:round_id>/questions', methods=['GET'])
@require_auth
def get_round_questions(round_id):
    """Fetch all questions for a specific round using the normalized view."""

    # Optional but recommended: Check if the round itself exists first
    round_exists = db.session.get(Round, round_id)
    if not round_exists:
         return jsonify({'error': f'Round with id {round_id} not found'}), 404

    # Verify the user has access to the event this round belongs to
    event_owner_id = db.session.scalar(select(Event.user_id).join(Round).filter(Round.id == round_id))
    if event_owner_id is None: # Should not happen if round exists, but safety check
        return jsonify({'error': 'Round data inconsistent'}), 500
    if event_owner_id != request.user.id:
        return jsonify({'error': 'Permission denied to access this round\'s questions'}), 403

    try:
        # Select the Round and eager load the normalized questions from the view
        stmt = (
            select(Round)
            .where(Round.id == round_id)
            .options(
                selectinload(Round.normalized_questions) # Eager load the view relationship
            )
        )
        round_obj = db.session.scalars(stmt).first()

        # Double check if round_obj was actually found
        if not round_obj:
            # This case should ideally be caught by the initial get, but good safety check
            return jsonify({'error': f'Round with id {round_id} not found after loading relationships'}), 404

        # Construct response with camelCase keys from the normalized view data
        questions_list = [{
            'roundQuestionId': q.round_question_id, 
            'roundId': q.round_id,                
            'questionNumber': q.question_number,  
            'questionId': q.question_id,           
            'questionType': q.question_type,       
            'question': q.question,
            'answer': q.answer,
            'difficulty': q.difficulty,
            'categoryId': q.category_id,           
            'categoryName': q.category_name        
        } for q in round_obj.normalized_questions] 

        return jsonify(questions_list)
    except Exception as e:
        # Log the error for debugging
        app.logger.error(f"Database error fetching questions for round {round_id}: {e}")
        return jsonify({'error': 'Failed to retrieve questions due to a database error'}), 500

@round_bp.route('/rounds', methods=['POST'])
@require_auth
def create_round():
    """Create a new round for a specific event."""
    data = request.get_json()
    if not data or 'event_id' not in data:
        return jsonify({'error': 'Missing event_id'}), 400

    event_id = data['event_id']

    # Verify the event exists and belongs to the current user
    event = db.session.scalar(
        select(Event).filter_by(id=event_id, user_id=request.user.id)
    )
    if not event:
        # Check if the event exists at all to give a more specific error
        event_exists = db.session.get(Event, event_id)
        if not event_exists:
             return jsonify({'error': f'Event with id {event_id} not found'}), 404
        else:
             return jsonify({'error': 'Permission denied to add rounds to this event'}), 403

    try:
        # Find the highest current round number for this event
        max_round_number = db.session.scalar(
            select(func.max(Round.round_number))
            .filter_by(event_id=event_id)
        )
        new_round_number = (max_round_number or 0) + 1

        # Create the new round
        new_round = Round(
            event_id=event_id,
            round_number=new_round_number,
            name=f"Round {new_round_number}" # Default name
            # category_id will be null by default
        )

        db.session.add(new_round)
        db.session.commit()

        # Construct response with camelCase keys
        return jsonify({
            'id': new_round.id,
            'name': new_round.name,
            'roundNumber': new_round.round_number,
            'eventId': new_round.event_id,
            'categoryId': new_round.category_id,
            'questions': [], # makes UI code cleaner
            'createdAt': new_round.created_at.isoformat() if new_round.created_at else None # Add createdAt
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating round for event {event_id}: {e}")
        return jsonify({'error': 'Could not create round'}), 500

@round_bp.route('/rounds/<int:round_id>', methods=['DELETE'])
@require_auth
def delete_round(round_id):
    """Soft delete a round by setting is_deleted to true."""
    try:
        # Get the round and verify it exists
        round_obj = db.session.get(Round, round_id)
        
        if not round_obj:
            return jsonify({'error': 'Round not found'}), 404
            
        # Verify the user has permission (owns the event)
        if round_obj.event.user_id != request.user.id:
            return jsonify({'error': 'Permission denied'}), 403
            
        # Soft delete the round
        round_obj.is_deleted = True
        db.session.commit()
        
        return jsonify({'message': 'Round deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting round {round_id}: {e}")
        return jsonify({'error': 'Failed to delete round'}), 500