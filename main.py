from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Resource, Api
import datetime

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
ma = Marshmallow(app)

association_table = db.Table('association_table', db.Model.metadata,
                             db.Column(
                                 'room_id',
                                 db.Integer,
                                 db.ForeignKey('room.id')
                             ),
                             db.Column(
                                 'booking_id',
                                 db.Integer,
                                 db.ForeignKey('booking.id')
                             ))


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), unique=True)
    rating = db.Column(db.String(32))
    bookings = db.relationship("Booking", secondary=association_table, back_populates="rooms", lazy="subquery")

    def __init__(self, number, rating):
        self.number = number
        self.rating = rating


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    rooms = db.relationship("Room", secondary=association_table, back_populates="bookings", lazy="subquery")

    def __init__(self, name, start, end):
        self.name = name
        self.start = start
        self.end = end


class RoomSchema(ma.Schema):
    class Meta:
        fields = ('id', 'number', 'rating')


class BookingSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'start', 'end', 'duration')


room_schema = RoomSchema()
rooms_schema = RoomSchema(many=True)
booking_schema = BookingSchema()
bookings_schema = BookingSchema(many=True)


class RoomManager(Resource):
    @staticmethod
    def get():
        try:
            id = request.args['id']
        except Exception as _:
            id = None

        if not id:
            rooms = Room.query.all()
            return jsonify(rooms_schema.dump(rooms))

        room = Room.query.get(id)
        return jsonify(room_schema.dump(room))

    @staticmethod
    def post():
        number = request.json['number']
        rating = request.json['rating']

        room = Room(number, rating)
        db.session.add(room)
        db.session.commit()
        return jsonify({
            'Message': f'Room {number} inserted.'
        })

    @staticmethod
    def put():
        try:
            id = request.args['id']
        except Exception as _:
            id = None

        if not id:
            return jsonify({'Message': 'Must provide the room ID'})

        room = Room.query.get(id)
        number = request.json['number']
        rating = request.json['rating']

        room.number = number
        room.rating = rating

        db.session.commit()
        return jsonify({'Message': f'Room {number} updated.'})

    @staticmethod
    def delete():
        try:
            id = request.args['id']
        except Exception as _:
            id = None

        if not id:
            return jsonify({'Message': "Must provide room id"})

        room = Room.query.get(id)
        db.session.delete(room)
        db.session.commit()

        return jsonify({'Message': f'Room {str(id)} deleted'})


def add_data(booking):
    data = booking_schema.dump(booking)
    data['duration'] = (booking.end - booking.start).days
    prices = {"A": 200, "B": 150, "C": 100, "D": 50}
    if booking.rooms:
        data["rooms"] = [room.number for room in booking.rooms]
        cost = [prices[room.rating] * data["duration"] for room in booking.rooms]
        data['total cost'] = cost

    return data


def render_all():
    bookings = Booking.query.all()
    all = []
    for booking in bookings:
        d = add_data(booking)
        all.append(d)
    return all


class BookingManager(Resource):
    @staticmethod
    def get():
        try:
            id = request.args['id']
        except Exception as _:
            id = None

        try:
            name = request.args['name']
        except Exception as _:
            name = None

        if not (name or id):
            return jsonify(render_all())

        if id:
            booking = Booking.query.get(id)
        elif name:
            booking = Booking.query.filter_by(name=name).first()
        data = add_data(booking)
        return jsonify(data)

    @staticmethod
    def post():
        for key in ['name', 'start', 'end', 'rooms']:
            if key not  in request.json.keys():
                return jsonify({"Message": "Input data incomplete"})

        name = request.json['name']
        start = datetime.datetime(request.json['start'][0], request.json['start'][1], request.json['start'][2])
        end = datetime.datetime(request.json['end'][0], request.json['end'][1], request.json['end'][2])
        rooms = request.json["rooms"]

        if start < end:
            booking = Booking(name, start, end)
        else:
            return jsonify({"Message": "Start date must not be prior to end date."})

        if not request.json['rooms'] is None:
            for room in rooms:
                r = Room.query.get(room)
                booking.rooms.append(r)

        db.session.add(booking)
        db.session.commit()
        return jsonify({
            'Message': f'Booking:  {name} from {start.strftime("%Y-%m-%d")} to {end.strftime("%Y-%m-%d")} inserted.'
        })

    @staticmethod
    def put():
        try:
            id = request.args['id']
        except Exception as _:
            id = None

        if not id:
            return jsonify({'Message': 'You must provide booking id'})

        booking = Booking.query.get(id)
        name = request.json['name']
        start = datetime.datetime(request.json['start'][0], request.json['start'][1], request.json['start'][2])
        end = datetime.datetime(request.json['end'][0], request.json['end'][1], request.json['end'][2])

        booking.name = name
        booking.start = start
        booking.end = end
        if request.json['rooms']:
            for room in request.json['rooms']:
                r = Room.query.get(room)
                booking.rooms.append(r)

        db.session.commit()
        return jsonify({'Message': f'Booking: {name} from {start} to {end} updated.'})

    @staticmethod
    def delete():
        try:
            id = request.args['id']
        except Exception as _:
            id = None

        if not id:
            return jsonify({'Message': "You must provide booking id"})

        booking = Booking.query.get(id)
        db.session.delete(booking)
        db.session.commit()

        return jsonify({'Message': f'Booking {str(id)} deleted'})


api.add_resource(RoomManager, '/api/rooms')
api.add_resource(BookingManager, '/api/bookings')

if __name__ == '__main__':
    app.run(debug=True)
