import os.path

from flask import url_for
from sqlalchemy import Column, Integer, String, Sequence, ForeignKey
from sqlalchemy.orm import relationship

from tuneful import app
from .database import Base, engine, session

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True)
    song_file_id = Column(Integer, ForeignKey("files.id"), nullable=False)

    def as_dictionary(self):
        song_info = session.query(File).filter_by(id=self.song_file_id).first()
        return {
            "id": self.id,
            "file": {
                "id": song_info.id,
                "name": song_info.filename
            }
        }

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    filename = Column(String(1024))
    song = relationship("Song", backref="song", uselist=False)

    def as_dictionary(self):
        return {
            "id": self.id,
            "name": self.filename,
            "path": url_for("uploaded_file", filename=self.filename)
        }
        

# song = Song()
# file = File()
# file.filename = "song1.mp3"
# file.song = "song1"