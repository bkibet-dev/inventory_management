"""Application factory for the inventory management API."""
from flask import Flask, jsonify


def create_app():
    app = Flask(__name__)

    from .routes import bp
    app.register_blueprint(bp)

    # Return JSON (not HTML) for common errors so the CLI/Postman get clean messages.
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"error": "Method not allowed"}), 405

    return app
