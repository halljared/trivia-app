from flask import Blueprint, request, jsonify
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from ...models import Event, Round
from ...database import db
from ...utils.auth import require_auth
from ... import app
from datetime import datetime, timezone

event_bp = Blueprint('event', __name__)

@event_bp.route('/api/events/my', methods=['GET'])
@require_auth
def get_my_events():
    """Fetch all non-deleted events created by the authenticated user."""
    try:
        # Build the query with optional filters
        stmt = (
            select(Event)
            .filter_by(user_id=request.user.id)
            .filter_by(is_deleted=False)  # Only return non-deleted events
            .order_by(Event.created_at.desc())  # Most recent first
        )
        
        # Add status filter if provided
        status = request.args.get('status')
        if status:
            stmt = stmt.filter_by(status=status)
            
        events = db.session.scalars(stmt).all()
        
        # Manually create dicts with camelCase keys
        events_data = [{
            'id': event.id,
            'name': event.name,
            'eventDate': event.event_date.isoformat() if event.event_date else None, # Renamed event_date
            'createdAt': event.created_at.isoformat(), # Renamed created_at
            'status': event.status,
            # We might need roundsCount here if ListEvent expects it based on the TS type
            # 'roundsCount': len(event.rounds) # Example if needed - requires loading rounds
        } for event in events]
        return jsonify(events_data) # Return the transformed data
        
    except Exception as e:
        app.logger.error(f"Error fetching user events: {e}")
        return jsonify({'error': 'Failed to retrieve events'}), 500

@event_bp.route('/api/events', methods=['POST'])
@require_auth
def create_or_update_event():
    """Create a new event or update an existing one for the authenticated user."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    event_id = data.get('id')
    name = data.get('name')

    # Name is always required for creation, and usually present for updates
    if not event_id and not name:
         return jsonify({'error': 'Event name is required for creation'}), 400
    # If updating, name is optional, but if provided, it must be non-empty
    if event_id and 'name' in data and not name:
         return jsonify({'error': 'Event name cannot be empty if provided'}), 400


    try:
        # Prepare dictionary ONLY with fields present in the request
        event_data = {}
        if 'name' in data:
             event_data['name'] = name
        if 'description' in data:
            event_data['description'] = data.get('description')
        if 'status' in data:
            event_data['status'] = data.get('status')

        # Handle event_date separately due to conversion
        if 'event_date' in data:
            event_date_str = data.get('event_date')
            if event_date_str is None:
                 # Explicitly setting date to null
                 event_data['event_date'] = None
            else:
                try:
                    parsed_date = datetime.fromisoformat(event_date_str)
                    if parsed_date.tzinfo is None:
                        # Assume UTC if no timezone is provided
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    event_data['event_date'] = parsed_date
                except (ValueError, TypeError): # Catch TypeError for None
                    return jsonify({'error': 'Invalid event_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS[+-]HH:MM) or null'}), 400

        # Get or create pattern
        if event_id:
            event = db.session.get(Event, event_id)
            if not event:
                 return jsonify({'error': 'Event not found'}), 404
            # Check permissions only when updating an existing event
            if event.user_id != request.user.id:
                return jsonify({'error': 'Permission denied'}), 403
            # Apply updates from the filtered dictionary
            for key, value in event_data.items():
                setattr(event, key, value)
        else:
            # Create new event
            # Ensure required fields are present
            if 'name' not in event_data:
                 return jsonify({'error': 'Event name is required for creation'}), 400

            # Set creation defaults if not provided
            if 'status' not in event_data:
                 event_data['status'] = 'draft'
            
            # Add user_id explicitly for creation
            event_data['user_id'] = request.user.id

            event = Event(**event_data) # Create using the prepared dict
            db.session.add(event)


        db.session.commit()
        db.session.refresh(event) # Ensure computed fields like created_at are loaded

        # Construct response with camelCase keys
        return jsonify({
            'id': event.id,
            'name': event.name,
            'eventDate': event.event_date.isoformat() if event.event_date else None, # Renamed event_date
            'createdAt': event.created_at.isoformat(), # Renamed created_at
            'status': event.status,
            'description': event.description,
            'userId': event.user_id # Add userId
             # 'updatedAt': event.updated_at.isoformat() if event.updated_at else None # If you add an updated_at field later
        }), 200 if event_id else 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error {'updating' if event_id else 'creating'} event (ID: {event_id}): {e}")
        return jsonify({'error': f'Could not {"update" if event_id else "create"} event'}), 500

@event_bp.route('/api/events/<int:event_id>', methods=['GET'])
@require_auth
def get_event(event_id):
    """Fetch an event and its associated rounds by event ID."""
    stmt = (
        select(Event)
        .options(
            selectinload(Event.rounds.and_(Round.is_deleted == False))  # Only load non-deleted rounds
            .selectinload(Round.normalized_questions)
        )
        .filter_by(id=event_id)
    )
    event = db.session.scalar(stmt)


    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    # Check permission AFTER fetching, to give correct 404 vs 403
    if event.user_id != request.user.id:
        return jsonify({'error': 'Permission denied'}), 403


    # Structure the response with camelCase keys
    rounds_data = [
        {
            'id': r.id,
            'roundNumber': r.round_number,
            'name': r.name,
            'createdAt': r.created_at.isoformat() if r.created_at else None,
            'categoryId': r.category_id,
            'questions': [
                {
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
                } for q in r.normalized_questions
            ]
        } for r in event.rounds
    ]
    
    event_data = {
        'id': event.id,
        'name': event.name,
        'eventDate': event.event_date.isoformat() if event.event_date else None, # Renamed event_date
        'status': event.status,
        'description': event.description,
        'rounds': rounds_data,
        'createdAt': event.created_at.isoformat() if event.created_at else None, # Renamed created_at
        'userId': event.user_id, # Added userId
        # 'updatedAt': event.updated_at.isoformat() if event.updated_at else None # Assuming you add an updated_at field later
    }
    return jsonify(event_data)


@event_bp.route('/api/events/<int:event_id>', methods=['DELETE'])
@require_auth
def delete_event(event_id):
    """Soft delete an event by setting is_deleted to true."""
    try:
        event = db.session.get(Event, event_id)
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
            
        if event.user_id != request.user.id:
            return jsonify({'error': 'Permission denied'}), 403
            
        event.is_deleted = True
        db.session.commit()
        
        return jsonify({'message': 'Event deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting event {event_id}: {e}")
        return jsonify({'error': 'Failed to delete event'}), 500