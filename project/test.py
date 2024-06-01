import logging
import asyncio
import aiohttp
from aiohttp import web
from models import db, Person
from sqlalchemy import select, func
from datetime import datetime

async def create_person(request):
    try:
        data = await request.json()
        # Validations
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
            return web.json_response({'error': 'Bad request', 'details': errors}, status=400)

        person = Person(
            nome=data['nome'], 
            apelido=data['apelido'], 
            nascimento=nascimento, 
            stack=data.get('stack', [])
        )
        async with request.app['db'].acquire() as conn:
            await conn.execute(Person.__table__.insert().values(
                nome=person.nome,
                apelido=person.apelido,
                nascimento=person.nascimento,
                stack=person.stack
            ))
            return web.json_response({'id': str(person.id)}, status=201, headers={'Location': f'/pessoas/{person.id}'})
    except IntegrityError:
        return web.json_response({'error': 'Apelido must be unique'}, status=422)
    except Exception as e:
        return web.json_response({'message': f'An error occurred: {e}'}, status=500)

async def get_person(request):
    try:
        person_id = request.match_info['id']
        async with request.app['db'].acquire() as conn:
            query = select([Person]).where(Person.id == person_id)
            result = await conn.execute(query)
            person = await result.fetchone()
            if person:
                return web.json_response({
                    'id': str(person.id),
                    'nome': person.nome,
                    'apelido': person.apelido,
                    'nascimento': person.nascimento.isoformat(), 
                    'stack': person.stack
                }, status=200)
            else:
                return web.json_response({'error': 'Person not found'}, status=404)
    except Exception as e:
        return web.json_response({'message': f'An error occurred: {e}'}, status=500)

async def search_person(request):
    try:
        term = request.query.get('t')
        if not term:
            return web.json_response({'error': 'Search term is required'}, status=400)

        async with request.app['db'].acquire() as conn:
            query = select([Person]).where(
                (Person.nome.ilike(f'%{term}%')) |
                (Person.apelido.ilike(f'%{term}%')) |
                (func.array_to_string(Person.stack, '||').ilike(f'%{term}%'))
            ).limit(50)
            result = await conn.execute(query)
            persons = await result.fetchall()

        response = [{
            'id': str(person.id),
            'nome': person.nome,
            'apelido': person.apelido,
            'nascimento': person.nascimento.isoformat(), 
            'stack': person.stack
        } for person in persons]
        return web.json_response(response, status=200)
    except Exception as e:
        return web.json_response({'message': f'An error occurred: {e}'}, status=500)

async def count_person(request):
    try:
        async with request.app['db'].acquire() as conn:
            query = select([func.count()]).select_from(Person)
            result = await conn.execute(query)
            count = await result.scalar()
        return web.json_response({'count': count}, status=200)
    except Exception as e:
        return web.json_response({'message': f'An error occurred: {e}'}, status=500)

async def create_app():
    app = web.Application()
    app.add_routes([
        web.post('/pessoas', create_person),
        web.get('/pessoas/{id}', get_person),
        web.get('/pessoas', search_person),
        web.get('/contagem-pessoas', count_person),
        web.get('/', hello),
    ])
    app['db'] = await db.init_db()
    return app

async def hello(request):
    return web.Response(text='Hello, fidalgo docker is working!')

if __name__ == '__main__':
    web.run_app(create_app(), port=5000)
