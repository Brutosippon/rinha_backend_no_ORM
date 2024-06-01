import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from datetime import datetime

app = Flask(__name__)
app.config['DATABASE_URI'] = 'postgresql://user:password@db:5432/mydatabase'

logging.basicConfig(filename='app.log', level=logging.INFO)

def get_db_connection():
    conn = psycopg2.connect(app.config['DATABASE_URI'])
    return conn

@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    return jsonify(error=str(e)), code

@app.route('/')
def hello():
    return 'Hello, fidalgo docker is working (Part2)!'

@app.route('/pessoas', methods=['POST'])
def create_person():
    data = request.get_json()

    errors = []
    if not isinstance(data.get('apelido'), str) or len(data['apelido']) > 32:
        errors.append("apelido deve ser uma string de até 32 caracteres")
    if not isinstance(data.get('nome'), str) or len(data['nome']) > 100:
        errors.append("nome deve ser uma string de até 100 caracteres")
    if not isinstance(data.get('nascimento'), str):
        errors.append("nascimento deve ser uma string no formato AAAA-MM-DD")
    else:
        try:
            nascimento = datetime.strptime(data['nascimento'], "%Y-%m-%d").date()
        except ValueError:
            errors.append("nascimento deve ser uma data válida no formato AAAA-MM-DD")
    if 'stack' in data and not (isinstance(data['stack'], list) and all(isinstance(item, str) and len(item) <= 32 for item in data['stack'])):
        errors.append("stack deve ser um vetor de strings de até 32 caracteres cada")

    if errors:
        return jsonify({'error': 'Bad request', 'details': errors}), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur: #gen_random_uuid() = uuid_generate_v4()
                cur.execute(
                    '''
                    INSERT INTO persons (nome, apelido, nascimento, stack) 
                    VALUES (%s, %s, %s, %s) RETURNING id
                    ''',
                    (data['nome'], data['apelido'], nascimento, data.get('stack', []))
                )
                new_id = cur.fetchone()['id']
                conn.commit()
        return jsonify({'id': str(new_id)}), 201, {'Location': f'/pessoas/{new_id}'}
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Apelido must be unique'}), 422
    except Exception as e:
        return jsonify({'message': f'An error occurred: {e}'}), 500

@app.route('/pessoas/<uuid:id>', methods=['GET'])
def get_person(id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    '''
                    SELECT id, nome, apelido, nascimento, stack
                    FROM persons
                    WHERE id = %s
                    ''',
                    (str(id),)
                )
                person = cur.fetchone()
        if person:
            return jsonify(person), 200
        else:
            return jsonify({'error': 'Person not found'}), 404    
    except Exception as e:
        return jsonify({'message': f'An error occurred: {e}'}), 500

@app.route('/pessoas', methods=['GET'])
def search_person():
    term = request.args.get('t')
    if not term:
        return jsonify({'error': 'Search term is required'}), 400
    
    term = f'%{term}%'
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    '''
                    SELECT id, nome, apelido, nascimento, stack
                    FROM persons
                    WHERE nome ILIKE %s OR apelido ILIKE %s OR %s = ANY(stack)
                    ''',
                    (term, term, term)
                )
                persons = cur.fetchall()
        return jsonify(persons), 200
    except Exception as e:
        return jsonify({'message': f'An error occurred: {e}'}), 500
    

@app.route('/contagem-pessoas', methods=['GET'])
def count_person():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT COUNT(*) FROM persons')
                count = cur.fetchone()['count']
        return jsonify({'count': count}), 200
    except Exception as e:
        return jsonify({'message': f'An error occurred: {e}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    