from flask import Flask, jsonify, request
import psycopg2
from con import set_connection
from loggerinstance import logger
import json

app = Flask(__name__)


def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except psycopg2.Error as e:
            conn = kwargs.get('conn')
            if conn:
                conn.rollback()
            logger.error(str(e))
            return jsonify({"error": "Database error"})
        except Exception as e:
            logger.error(str(e))
            return jsonify({"error": "Internal server error"})
        finally:
            conn = kwargs.get('conn')
            cur = kwargs.get('cur')
            if cur:
                cur.close()
            if conn:
                conn.close()
    return wrapper


# CREATE TABLE characters (
#     name VARCHAR(50) PRIMARY KEY,
#     strength INTEGER NOT NULL,
#     agility INTEGER NOT NULL,
#     intelligence INTEGER NOT NULL
# );


@app.route('/v1/create_character', methods=['POST'])
@handle_exceptions
def create_character():
    """
    {
        "name": "Akshith",
        "strength": 10,
        "agility": 8,
        "intelligence": 6
    }
    """
    # Extract data from request
    data = request.get_json()
    name = data.get('name')
    strength = data.get('strength')
    agility = data.get('agility')
    intelligence = data.get('intelligence')

    # Validate input data
    if not name or not strength or not agility or not intelligence:
        logger.error('Invalid input data')
        return jsonify({'message': 'Invalid input data'}), 400

    # Create new character
    cur, conn = set_connection()

    cur.execute(
        f"INSERT INTO characters (name, strength, agility, intelligence) VALUES ('{name}', {strength}, {agility}, {intelligence})")
    conn.commit()
    cur.close()

    logger.info(f'Character {name} created successfully')
    return jsonify({'message': 'Character created successfully'}), 201


@app.route('/v1/get_character/<string:name>', methods=['GET'], endpoint='get_character')
@handle_exceptions
def get_character(name):
    """
    Returns the character with the given name.
    """
    # Retrieve character data from database
    cur, conn = set_connection()

    cur.execute(f"SELECT * FROM characters WHERE name = '{name}'")
    character = cur.fetchone()
    cur.close()

    if not character:
        logger.error(f'Character {name} not found')
        return jsonify({'message': 'Character not found'}), 404

    logger.info(f'Returned data for character {name}')
    return jsonify({
        'name': character[0],
        'strength': character[1],
        'agility': character[2],
        'intelligence': character[3]
    }), 200


@app.route('/v1/update_character/<string:name>', methods=['PUT'], endpoint='update_character')
@handle_exceptions
def update_character(name):
    """
    Updates the stats of the character with the given name.
    {
        "attribute": "strength",
        "value": 20
    }
    """
    # Extract data from request
    data = request.get_json()
    attribute = data.get('attribute')
    value = data.get('value')

    # Validate input data
    if not attribute or not value:
        logger.error(f"Invalid input data for character {name}")
        return jsonify({'message': 'Invalid input data'}), 400

    # Update character stats in the database
    cur, conn = set_connection()
    cur.execute(f"UPDATE characters SET {attribute} = {value} WHERE name = '{name}'")
    conn.commit()
    cur.close()

    logger.info(f"Stats updated for character {name}")
    return jsonify({'message': 'Character stats updated successfully'}), 200


@app.route('/v1/delete_character/<string:name>', methods=['DELETE'], endpoint='delete_character')
@handle_exceptions
def delete_character(name):
    """
    Deletes the character with the given name.
    """
    # Delete character from the database
    cur, conn = set_connection()
    cur.execute(f"DELETE FROM characters WHERE name = '{name}'")
    conn.commit()
    cur.close()

    logger.info(f"Character {name} deleted successfully")
    return jsonify({'message': 'Character deleted successfully'}), 200


@app.route('/v1/attack', methods=['POST'], endpoint='attack')
@handle_exceptions
def attack():
    """
    Simulates an attack between two characters.
    Example request body:
    {
        "attacker": "Ragnar",
        "defender": "Lagertha"
    }
    """

    # Extract data from request
    data = request.get_json()
    attacker = data.get('attacker')
    defender = data.get('defender')

    # Validate input data
    if not attacker or not defender:
        return jsonify({'message': 'Invalid input data'}), 400

    cur, conn = set_connection()

    # Retrieve character information from the database
    cur.execute("SELECT * FROM characters WHERE name=%s;", (attacker,))
    attacker_data = cur.fetchone()
    cur.execute("SELECT * FROM characters WHERE name=%s;", (defender,))
    defender_data = cur.fetchone()

    # Check if characters exist in the database
    if not attacker_data:
        logger.debug(f'Attacker not found in the database: {attacker}')
        return jsonify({'message': 'Attacker not found in the database'}), 404
    if not defender_data:
        logger.debug(f'Defender not found in the database: {defender}')
        return jsonify({'message': 'Defender not found in the database'}), 404

    # Calculate damage
    damage = attacker_data[2] - defender_data[3]
    if damage < 0:
        damage = 0

    # Apply damage to defender in the database
    new_intelligence = defender_data[4] - damage
    if new_intelligence <= 0:
        cur.execute("DELETE FROM characters WHERE name=%s;", (defender,))
        conn.commit()
        logger.debug(f'Attack successful, damage: {damage}, defender: {defender}, status: dead')
        return jsonify(
            {'message': 'Attack successful', 'damage': damage, 'defender': defender, 'status': 'dead'}), 200
    else:
        cur.execute("UPDATE characters SET intelligence=%s WHERE name=%s;", (new_intelligence, defender,))
        conn.commit()
        logger.debug(f'Attack successful, damage: {damage}, defender: {defender}, status: alive')
        return jsonify(
            {'message': 'Attack successful', 'damage': damage, 'defender': defender, 'status': 'alive'}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
