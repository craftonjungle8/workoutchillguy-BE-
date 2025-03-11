from flask import Flask
app = Flask(__name__)

@app.route('/')
def main():
   return 'This is Home!'

@app.route('/login')
def login():
   return 'This is Login'

@app.route('/signup')
def signUp():
   return 'This is Signup'

@app.route('/mate')
def findMate():
   return 'This is Findmate'

@app.route('/diary')
def diary():
   return 'This is Diary'

@app.route('/board')
def board():
   return 'This is borad'
if __name__ == '__main__':  
   app.run('0.0.0.0', port=5000, debug=True)
