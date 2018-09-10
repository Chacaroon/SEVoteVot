from pymodm.connection import connect

connect("mongodb://localhost:27017/votes_db", alias='votes')