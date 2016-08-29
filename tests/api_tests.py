import unittest
import os
import shutil
import json
try: from urllib.parse import urlparse
except ImportError: from urlparse import urlparse # Py2 compatibility
from io import StringIO, BytesIO

import sys; print(list(sys.modules.keys()))
# Configure our app to use the testing databse
os.environ["CONFIG_PATH"] = "tuneful.config.TestingConfig"

from tuneful import app
from tuneful import models
from tuneful.utils import upload_path
from tuneful.database import Base, engine, session

class TestAPI(unittest.TestCase):
    """ Tests for the tuneful API """

    def setUp(self):
        """ Test setup """
        self.client = app.test_client()

        # Set up the tables in the database
        Base.metadata.create_all(engine)

        # Create folder for test uploads
        os.mkdir(upload_path())

    def tearDown(self):
        """ Test teardown """
        session.close()
        # Remove the tables and their data from the database
        Base.metadata.drop_all(engine)

        # Delete test upload folder
        shutil.rmtree(upload_path())

    def test_get_empty_songs(self):
        """ Getting songs from an empty database """
        response = self.client.get("/api/songs", headers=[("Accept", "application/json")])
    
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
    
        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data, [])

    def test_get_songs(self):
        """ Getting songs from a populated database """
        fileA = models.File(filename="Abbey_Road.mp3")
        fileB = models.File(filename="Yellow_Submarine.mp3")

        session.add_all([fileA, fileB])
        session.commit()
        
        songA = models.Song(song_file_id=fileA.id)
        songB = models.Song(song_file_id=fileB.id)

        session.add_all([songA, songB])
        session.commit()       
        
        response = self.client.get("/api/songs", headers=[("Accept", "application/json")])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(len(data), 2)

        songA = data[0]
        self.assertEqual(songA["id"], 1)
        self.assertEqual(songA["file"]["id"], 1)
        self.assertEqual(songA["file"]["name"], "Abbey_Road.mp3")
        
        songB = data[1]
        self.assertEqual(songB["id"], 2)
        self.assertEqual(songB["file"]["id"], 2)
        self.assertEqual(songB["file"]["name"], "Yellow_Submarine.mp3")

    def test_post_post(self):
        """ Posting a new post """
        
        fileA = models.File(filename='FileA')

        session.add(fileA)
        session.commit()

        data = {
                    "file": {
                        "id": fileA.id
                        }
                    }

        response = self.client.post("/api/songs",
            data=json.dumps(data),
            content_type="application/json",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(urlparse(response.headers.get("Location")).path,
                         "/api/songs")
       
        data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(data["id"], fileA.id)

        songs = session.query(models.Song).all()
        self.assertEqual(len(songs), 1)

        song = songs[0]
        self.assertEqual(song.id, fileA.id)

    def test_delete_song(self):
        """ Deleting a single song from a populated database """
        
        fileA = models.File(filename='FileA')
        
        session.add(fileA)
        session.commit()
        
        songA = models.Song(song_file_id=fileA.id)
        
        session.add(songA)
        session.commit()

        response = self.client.delete("/api/songs/{}".format(songA.id), headers=[("Accept", "application/json")])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        songs = session.query(models.Song).all()
        self.assertEqual(len(songs), 0)

    def test_delete_non_existent_song(self):
        """ Deleting a single song which doesn't exist """
        response = self.client.delete("/api/songs/1", headers=[("Accept", "application/json")])

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data["message"], "Could not find song with id 1")
        
    def test_get_uploaded_file(self):
        """Add file to an upload folder and access it through an HTTP request"""
        path = upload_path("test.txt")
        with open(path, "wb") as f:
            f.write(b"File contents")

        response = self.client.get("/uploads/test.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(response.data, b"File contents")
        
    def test_file_upload(self):
        """ Upload a simple text file to the server"""
        data = {
            "file": (BytesIO(b"File contents"), "test.txt")
        }

        response = self.client.post("/api/files",
            data=data,
            content_type="multipart/form-data",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(urlparse(data["path"]).path, "/uploads/test.txt")

        path = upload_path("test.txt")
        self.assertTrue(os.path.isfile(path))
        with open(path, "rb") as f:
            contents = f.read()
        self.assertEqual(contents, b"File contents")