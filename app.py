import os, sqlite3, secrets
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get('DATABASE_PATH', 'cbt.db')
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
SCHOOL = 'NEW DAWN CITY COLLEGE'
LOCATION = 'GUSAU, ZAMFARA STATE'

CSS = '''<style>
*{box-sizing:border-box}body{margin:0;background:#f2f5f9;color:#202938;font-family:Arial,sans-serif}header{background:#12345a;color:white;text-align:center;padding:24px 12px}header h1{margin:0 0 6px;font-size:23px}nav{background:white;padding:12px 4%;display:flex;gap:18px;flex-wrap:wrap;border-bottom:1px solid #ddd}a{color:#1769aa;text-decoration:none;font-weight:bold}.wrap{max-width:1000px;margin:24px auto;padding:0 14px}.card{background:white;border-radius:12px;padding:22px;margin-bottom:18px;box-shadow:0 2px 10px #122b440b}h2{color:#12345a;margin-top:0}label{display:block;font-weight:bold;margin:12px 0 6px}input,select,textarea{width:100%;padding:11px;border:1px solid #c4ceda;border-radius:7px;font:inherit}button,.btn{display:inline-block;background:#1769aa;color:white;border:0;border-radius:7px;padding:11px 15px;margin-top:12px;cursor:pointer;font-weight:bold}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e5e9ef}th{background:#edf3f9}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.notice{padding:11px;background:#fff1c7;border-radius:7px;margin-bottom:12px}.muted{color:#667085;font-size:13px}.q{padding:14px;border:1px solid #e2e7ee;border-radius:8px;margin:14px 0}.opt{display:flex;gap:8px;align-items:flex-start;font-weight:normal}.opt input{width:auto;margin-top:3px}footer{text-align:center;padding:25px;color:#667085;font-size:12px}
</style>'''

def connect():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def init_db():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,name TEXT NOT NULL,class_name TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'student');
        CREATE TABLE IF NOT EXISTS exams(id INTEGER PRIMARY KEY,title TEXT NOT NULL,subject TEXT NOT NULL,class_name TEXT NOT NULL,duration INTEGER NOT NULL,is_published INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY,exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,question TEXT NOT NULL,a TEXT NOT NULL,b TEXT NOT NULL,c TEXT NOT NULL,d TEXT NOT NULL,correct TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'mcq');
        CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),exam_id INTEGER NOT NULL REFERENCES exams(id),score INTEGER NOT NULL,total INTEGER NOT NULL,submitted TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,exam_id));
        ''')
        if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            c.execute('INSERT INTO users(username,name,class_name,password_hash,role) VALUES(?,?,?,?,?)',('admin','School Administrator','ALL',generate_password_hash('ChangeMe123!'),'admin'))
        if not c.execute("SELECT 1 FROM users WHERE username='NDCC001'").fetchone():
            c.execute('INSERT INTO users(username,name,class_name,password_hash,role) VALUES(?,?,?,?,?)',('NDCC001','Sample Student','JSS 1',generate_password_hash('482915'),'student'))

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def inner(*a,**kw):
            if not session.get('uid'): return redirect(url_for('login'))
            if role and session.get('role') != role: flash('You do not have permission to access that page.'); return redirect(url_for('home'))
            return fn(*a,**kw)
        return inner
    return deco

def page(title, body, **kwargs):
    shell='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ title }} - {{ school }}</title>'''+CSS+'''</head><body><header><h1>{{ school }}</h1><div>{{ location }} · ONLINE CBT EXAMINATION PORTAL</div></header>{% if session.get('uid') %}<nav><a href="{{ url_for('home') }}">Dashboard</a>{% if session.get('role')=='admin' %}<a href="{{ url_for('students') }}">Students</a><a href="{{ url_for('exams') }}">Examinations</a><a href="{{ url_for('results') }}">Results</a>{% endif %}<a href="{{ url_for('logout') }}">Log out</a></nav>{% endif %}<main class="wrap">{% for m in get_flashed_messages() %}<div class="notice">{{ m }}</div>{% endfor %}{{ body|safe }}</main><footer>New Dawn City College CBT · Protect student information and back up results.</footer></body></html>'''
    return render_template_string(shell,title=title,school=SCHOOL,location=LOCATION,body=render_template_string(body,**kwargs))

@app.route('/')
def home():
    if not session.get('uid'): return redirect(url_for('login'))
    with connect() as c:
        if session['role']=='admin':
            nstudents=c.execute("SELECT COUNT(*) n FROM users WHERE role='student'").fetchone()['n']; nexams=c.execute('SELECT COUNT(*) n FROM exams').fetchone()['n']
            nresults=c.execute('SELECT COUNT(*) n FROM results').fetchone()['n']
            return page('Dashboard','''<div class="card"><h2>Administrator dashboard</h2><div class="grid"><div class="card"><h2>{{ ns }}</h2>Students</div><div class="card"><h2>{{ ne }}</h2>Examinations</div><div class="card"><h2>{{ nr }}</h2>Submissions</div></div><a class="btn" href="{{ url_for('students') }}">Manage students</a> <a class="btn" href="{{ url_for('exams') }}">Manage examinations</a> <a class="btn" href="{{ url_for('results') }}">View results</a></div>''',ns=nstudents,ne=nexams,nr=nresults)
        student=c.execute('SELECT class_name FROM users WHERE id=?',(session['uid'],)).fetchone()
        exams=c.execute('''SELECT e.* FROM exams e WHERE e.is_published=1 AND e.class_name=? AND NOT EXISTS(SELECT 1 FROM results r WHERE r.exam_id=e.id AND r.user_id=?)''',(student['class_name'],session['uid'])).fetchall()
        results=c.execute('SELECT e.title,e.subject,r.score,r.total,r.submitted FROM results r JOIN exams e ON e.id=r.exam_id WHERE r.user_id=? ORDER BY r.id DESC',(session['uid'],)).fetchall()
    return page('Student dashboard','''<div class="card"><h2>Welcome, {{ name }}</h2><p>Class: {{ cls }}</p><h3>Available examinations</h3>{% if exams %}<table><tr><th>Exam</th><th>Subject</th><th>Duration</th><th></th></tr>{% for e in exams %}<tr><td>{{ e.title }}</td><td>{{ e.subject }}</td><td>{{ e.duration }} min</td><td><a class="btn" href="{{ url_for('take_exam',eid=e.id) }}">Start exam</a></td></tr>{% endfor %}</table>{% else %}<p>No examinations available right now.</p>{% endif %}<h3>My results</h3>{% if results %}<table><tr><th>Exam</th><th>Subject</th><th>Score</th></tr>{% for r in results %}<tr><td>{{ r.title }}</td><td>{{ r.subject }}</td><td>{{ r.score }}/{{ r.total }} ({{ (100*r.score/r.total)|round|int if r.total else 0 }}%)</td></tr>{% endfor %}</table>{% else %}<p>No results yet.</p>{% endif %}</div>''',name=session.get('name'),cls=student['class_name'],exams=exams,results=results)

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        with connect() as c: u=c.execute('SELECT * FROM users WHERE username=?',(request.form.get('username','').strip(),)).fetchone()
        if u and check_password_hash(u['password_hash'],request.form.get('password','')):
            session.clear(); session.update(uid=u['id'],username=u['username'],name=u['name'],role=u['role']); return redirect(url_for('home'))
        flash('Invalid username or password.')
    return page('Login','''<div class="card" style="max-width:480px;margin:auto"><h2>Login to CBT Portal</h2><form method="post"><label>Username / Admission number</label><input name="username" required autocomplete="username"><label>Password</label><input type="password" name="password" required autocomplete="current-password"><button>Log in</button></form><p class="muted">Initial admin login: admin / ChangeMe123! · Sample student: NDCC001 / 482915. Change the demo credentials before public use.</p></div>''')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/students',methods=['GET','POST'])
@login_required('admin')
def students():
    classes=['JSS 1','JSS 2','JSS 3','SS 1','SS 2','SS 3']
    if request.method=='POST':
        try:
            with connect() as c: c.execute("INSERT INTO users(username,name,class_name,password_hash,role) VALUES(?,?,?,?, 'student')",(request.form['username'].strip(),request.form['name'].strip(),request.form['class_name'],generate_password_hash(request.form['password'])))
            flash('Student account created.')
        except sqlite3.IntegrityError: flash('That username already exists.')
        return redirect(url_for('students'))
    with connect() as c: rows=c.execute("SELECT username,name,class_name FROM users WHERE role='student' ORDER BY class_name,name").fetchall()
    return page('Students','''<div class="card"><h2>Create student account</h2><form method="post" class="grid"><div><label>Username / admission number</label><input name="username" required></div><div><label>Full name</label><input name="name" required></div><div><label>Class</label><select name="class_name">{% for x in classes %}<option>{{ x }}</option>{% endfor %}</select></div><div><label>Temporary password (6+ characters)</label><input name="password" minlength="6" required></div><div><button>Create student</button></div></form></div><div class="card"><h2>Student accounts</h2><table><tr><th>Username</th><th>Name</th><th>Class</th></tr>{% for r in rows %}<tr><td>{{ r.username }}</td><td>{{ r.name }}</td><td>{{ r.class_name }}</td></tr>{% endfor %}</table></div>''',classes=classes,rows=rows)

@app.route('/exams',methods=['GET','POST'])
@login_required('admin')
def exams():
    classes=['JSS 1','JSS 2','JSS 3','SS 1','SS 2','SS 3']
    if request.method=='POST':
        with connect() as c: c.execute('INSERT INTO exams(title,subject,class_name,duration) VALUES(?,?,?,?)',(request.form['title'].strip(),request.form['subject'].strip(),request.form['class_name'],max(1,min(240,int(request.form['duration']))))) ; eid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        return redirect(url_for('edit_exam',eid=eid))
    with connect() as c: rows=c.execute('SELECT e.*,(SELECT COUNT(*) FROM questions q WHERE q.exam_id=e.id) n FROM exams e ORDER BY e.id DESC').fetchall()
    return page('Examinations','''<div class="card"><h2>Create examination</h2><form method="post" class="grid"><div><label>Exam title</label><input name="title" required></div><div><label>Subject</label><input name="subject" required></div><div><label>Class</label><select name="class_name">{% for x in classes %}<option>{{ x }}</option>{% endfor %}</select></div><div><label>Duration (minutes)</label><input type="number" name="duration" min="1" max="240" value="30" required></div><div><button>Create exam and add questions</button></div></form></div><div class="card"><h2>Examinations</h2><table><tr><th>Title</th><th>Subject / class</th><th>Questions</th><th>Status</th><th>Actions</th></tr>{% for e in rows %}<tr><td>{{ e.title }}</td><td>{{ e.subject }} / {{ e.class_name }}</td><td>{{ e.n }}</td><td>{{ 'Published' if e.is_published else 'Draft' }}</td><td><a href="{{ url_for('edit_exam',eid=e.id) }}">Edit</a> · <a href="{{ url_for('publish',eid=e.id) }}">{{ 'Unpublish' if e.is_published else 'Publish' }}</a></td></tr>{% endfor %}</table></div>''',classes=classes,rows=rows)

@app.route('/exams/<int:eid>/edit',methods=['GET','POST'])
@login_required('admin')
def edit_exam(eid):
    with connect() as c: exam=c.execute('SELECT * FROM exams WHERE id=?',(eid,)).fetchone()
    if not exam: return 'Exam not found',404
    if request.method=='POST':
        kind=request.form['kind']; q=request.form['question'].strip()
        if kind=='tf': a,b,cc,d='True','False','—','—'; correct=request.form['correct']
        else: a,b,cc,d=[request.form.get('o'+x,'').strip() for x in 'abcd']; correct=request.form['correct']
        if not q or (kind=='mcq' and not all([a,b,cc,d])): flash('Enter the question and all four options.')
        else:
            with connect() as c: c.execute('INSERT INTO questions(exam_id,question,a,b,c,d,correct,kind) VALUES(?,?,?,?,?,?,?,?)',(eid,q,a,b,cc,d,correct,kind))
            flash('Question added.')
        return redirect(url_for('edit_exam',eid=eid))
    with connect() as c: qs=c.execute('SELECT * FROM questions WHERE exam_id=? ORDER BY id',(eid,)).fetchall()
    return page('Edit exam','''<div class="card"><h2>{{ exam.title }} — {{ exam.subject }}</h2><p>{{ exam.class_name }} · {{ exam.duration }} minutes</p><form method="post"><label>Question type</label><select name="kind" id="kind" onchange="switchKind()"><option value="mcq">Multiple choice A–D</option><option value="tf">True / False</option></select><label>Question</label><textarea name="question" required rows="3"></textarea><div id="options" class="grid">{% for x in 'abcd' %}<div><label>Option {{ x|upper }}</label><input name="o{{ x }}" required></div>{% endfor %}</div><label>Correct answer</label><select name="correct" id="correct"><option>A</option><option>B</option><option>C</option><option>D</option></select><button>Add question</button></form><p class="muted">Only objective questions are automatically marked. Theory questions need a separate manual-marking feature.</p></div><div class="card"><h2>Questions ({{ qs|length }})</h2><ol>{% for q in qs %}<li style="margin:12px 0">{{ q.question }} <span class="muted">({{ q.kind }})</span></li>{% endfor %}</ol><a class="btn" href="{{ url_for('exams') }}">Back to exams</a></div><script>function switchKind(){let tf=document.getElementById('kind').value==='tf';document.getElementById('options').style.display=tf?'none':'grid';document.querySelectorAll('#options input').forEach(x=>x.required=!tf);document.getElementById('correct').innerHTML=tf?'<option value="T">True</option><option value="F">False</option>':'<option>A</option><option>B</option><option>C</option><option>D</option>'}</script>''',exam=exam,qs=qs)

@app.route('/exams/<int:eid>/publish')
@login_required('admin')
def publish(eid):
    with connect() as c:
        e=c.execute('SELECT * FROM exams WHERE id=?',(eid,)).fetchone(); n=c.execute('SELECT COUNT(*) n FROM questions WHERE exam_id=?',(eid,)).fetchone()['n']
        if not e: return 'Exam not found',404
        if not e['is_published'] and n==0: flash('Add at least one question before publishing.')
        else: c.execute('UPDATE exams SET is_published=? WHERE id=?',(0 if e['is_published'] else 1,eid)); flash('Exam status updated.')
    return redirect(url_for('exams'))

@app.route('/exam/<int:eid>',methods=['GET','POST'])
@login_required('student')
def take_exam(eid):
    with connect() as c:
        e=c.execute('SELECT * FROM exams WHERE id=? AND is_published=1',(eid,)).fetchone(); u=c.execute('SELECT class_name FROM users WHERE id=?',(session['uid'],)).fetchone()
        if not e or e['class_name']!=u['class_name']: return 'This exam is not available to your account.',403
        if c.execute('SELECT 1 FROM results WHERE user_id=? AND exam_id=?',(session['uid'],eid)).fetchone(): flash('You already submitted this exam.'); return redirect(url_for('home'))
        qs=c.execute('SELECT * FROM questions WHERE exam_id=? ORDER BY id',(eid,)).fetchall()
    if request.method=='POST':
        score=sum(1 for q in qs if request.form.get('q'+str(q['id']))==q['correct']); total=len(qs)
        try:
            with connect() as c: c.execute('INSERT INTO results(user_id,exam_id,score,total) VALUES(?,?,?,?)',(session['uid'],eid,score,total)); rid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        except sqlite3.IntegrityError: flash('Your submission was already recorded.'); return redirect(url_for('home'))
        return redirect(url_for('result',rid=rid))
    return page('Take exam','''<div class="card"><h2>{{ e.title }}</h2><p>{{ e.subject }} · {{ e.class_name }} · {{ e.duration }} minutes</p><div class="notice">Choose one answer for each question, then submit. The displayed timer is advisory in this starter version and does not force-submit automatically.</div><b>Time remaining: <span id="timer">{{ e.duration }}:00</span></b><form method="post" id="examform">{% for q in qs %}<div class="q"><b>{{ loop.index }}. {{ q.question }}</b>{% if q.kind=='tf' %}{% for v,l in [('T','True'),('F','False')] %}<label class="opt"><input type="radio" name="q{{ q.id }}" value="{{ v }}">{{ l }}</label>{% endfor %}{% else %}{% for v,l in [('A',q.a),('B',q.b),('C',q.c),('D',q.d)] %}<label class="opt"><input type="radio" name="q{{ q.id }}" value="{{ v }}"><b>{{ v }}.</b> {{ l }}</label>{% endfor %}{% endif %}</div>{% endfor %}<button onclick="return confirm('Submit now? You cannot attempt this exam again.')">Submit examination</button></form></div><script>let s={{ e.duration }}*60;setInterval(()=>{if(s>0)s--;document.getElementById('timer').textContent=Math.floor(s/60)+':'+String(s%60).padStart(2,'0')},1000)</script>''',e=e,qs=qs)

@app.route('/result/<int:rid>')
@login_required()
def result(rid):
    with connect() as c: r=c.execute('SELECT r.*,e.title,e.subject,u.name FROM results r JOIN exams e ON e.id=r.exam_id JOIN users u ON u.id=r.user_id WHERE r.id=?',(rid,)).fetchone()
    if not r or (session['role']!='admin' and r['user_id']!=session['uid']): return 'Result not found',404
    return page('Result','''<div class="card"><h2>Examination result</h2><p>{{ r.name }} · {{ r.title }} — {{ r.subject }}</p><h1>{{ r.score }} / {{ r.total }}</h1><h2>{{ (100*r.score/r.total)|round|int if r.total else 0 }}%</h2><p>Submitted: {{ r.submitted }}</p><a class="btn" href="{{ url_for('home') }}">Dashboard</a></div>''',r=r)

@app.route('/results')
@login_required('admin')
def results():
    with connect() as c: rows=c.execute('SELECT u.name,u.username,u.class_name,e.title,e.subject,r.score,r.total,r.submitted FROM results r JOIN users u ON u.id=r.user_id JOIN exams e ON e.id=r.exam_id ORDER BY r.id DESC').fetchall()
    return page('Results','''<div class="card"><h2>Examination results</h2>{% if rows %}<table><tr><th>Student</th><th>Username</th><th>Class</th><th>Exam / subject</th><th>Score</th><th>Percentage</th><th>Submitted</th></tr>{% for r in rows %}<tr><td>{{ r.name }}</td><td>{{ r.username }}</td><td>{{ r.class_name }}</td><td>{{ r.title }} / {{ r.subject }}</td><td>{{ r.score }}/{{ r.total }}</td><td>{{ (100*r.score/r.total)|round|int if r.total else 0 }}%</td><td>{{ r.submitted }}</td></tr>{% endfor %}</table>{% else %}<p>No submissions yet.</p>{% endif %}</div>''',rows=rows)

@app.route('/health')
def health(): return {'status':'ok','school':SCHOOL}

init_db()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
