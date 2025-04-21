from .question.question_routes import question_bp
from .event.event_routes import event_bp
from .round.round_routes import round_bp
from .user.user_routes import user_bp
from .category.category_routes import category_bp

def init_routes(app):
    """Initialize all route blueprints"""
    app.register_blueprint(question_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(round_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(category_bp)