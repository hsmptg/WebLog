from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap
from flask import Flask, render_template
import sys
import os
import signal #signal
import boards
import time
import datetime
from idlelib.IOBinding import filesystemencoding

def getFilename():
    numFilename = "/home/pi/logger/static/data/num.dat" 
    if os.path.isfile(numFilename):
        f = open(numFilename, "r")
        s = f.readline()
        f.close()
        n = int(s)+1
        f = open(numFilename, "w")
        f.write(str(n) + "\n")
        f.close()       
    else:
        n = 1
    filename = "log{:04d}.txt".format(n)
    f = open(numFilename, "w")
    f.write(str(n) + "\n")
    f.close()
    return filename       
                
class WebLog():
    def __init__(self):
        print("Started Logger WebGUI")
        signal.signal(signal.SIGINT, self.signal_handler)
        
        app = Flask(__name__)
        Bootstrap(app)        
        app.config['DEBUG'] = False
        self.socketio = SocketIO(app)
        self.counter = -1
        self.nSamples = 0
        self.bLogging = False

        self.filename = ""
        self.board = boards.Duino()
        self.board.connect('/dev/ttyS0')
                
        #=======================================================================
        # @app.before_first_request
        # def initialize():
        #     print('Called only once, when the first request comes in')
        #=======================================================================
            
        @app.route('/')
        def index():
            print("render index.html")
            return render_template("index.html")

        @self.socketio.on('connect', namespace='/test')
        def test_connect():
            print('Client connected')
            self.socketio.emit('msg', {'filename': self.filename, 'samples': self.nSamples}, namespace='/test')

        @app.route('/', defaults={'req_path': ''})
        @app.route('/<path:req_path>')
        def dir_listing(req_path):
            BASE_DIR = '/home/pi/logger/static'
        
            # Joining the base and the requested path
            abs_path = os.path.join(BASE_DIR, req_path)
        
            # Return 404 if path doesn't exist
            if not os.path.exists(abs_path):
                return abort(404)
        
            # Check if path is a file and serve
            if os.path.isfile(abs_path):
                return send_file(abs_path)
        
            # Show directory contents
            files = os.listdir(abs_path)
            files.sort()
            filex = []
            for file in files:
                (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(abs_path + "/" + file)
                dat = datetime.datetime.fromtimestamp(ctime)
                if file <> "num.dat":
                    filex.append([file, "{}".format(dat)])
            return render_template('files.html', files=filex)
        
        @self.socketio.on('Shutdown', namespace='/test')
        def shutdown(message):
            print("Shutting down...")
            os.system("sudo shutdown -h now")
            self.exit()   
                                        
        @self.socketio.on('Logging', namespace='/test')
        def logging(message):
            if message['state']:
                self.startLog()
            else:
                self.stopLog()
                                        
        @self.socketio.on('Time', namespace='/test')
        def setTime(message):
            ms = message['millis']
            dat = datetime.datetime.fromtimestamp(ms/1000.0)
            os.system("sudo date --set '{}'".format(dat))

        self.socketio.run(app, host = '0.0.0.0', port = 5001)

    def signal_handler(self, signal, frame):
        print("\rYou pressed Ctrl+C!")
        self.exit()

    def exit(self):
        sys.exit(0)

    def onMsg(self, msg):
        if self.bLogging:
            try:
                self.file.write(msg + '\r')
                self.nSamples = self.nSamples + 1
                if self.nSamples % 1000 == 0:
                    print(self.nSamples)
                    self.file.flush()
                    self.socketio.emit('msg', {'samples': self.nSamples}, namespace='/test')
            except Exception, e:
                print("Error: {}".format(e))                    

    def startLog(self):
        print("Start logging")
        self.filename = getFilename()
        self.file = open("/home/pi/logger/static/data/" + self.filename, "w")
        self.nSamples = 0
        self.socketio.emit('msg', {'filename': self.filename, 'samples': self.nSamples}, namespace='/test')
        self.bLogging = True
        self.board.onMsg = self.onMsg
            
    def stopLog(self):
        print("Stop logging")
        self.board.onMsg = None
        self.bLogging = False
        self.filename = ""
        self.socketio.emit('msg', {'filename': self.filename}, namespace='/test')
        self.file.close()

if __name__ == '__main__':
    gui = WebLog()