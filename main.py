from flask import Flask, render_template, request, redirect, url_for, session, send_file
import json
import os
from datetime import datetime, timezone,timedelta
import csv
from io import StringIO
import time


app = Flask(__name__)
app.secret_key = 'supersecretkey'  # 可換成環境變數

# 啟動時間 = 現在時間，結束時間 = 啟動後 9 分鐘
start_time = datetime.now(timezone.utc)
END_TIME = start_time + timedelta(minutes=6)

# 載入題目資料
with open('questions.json', 'r', encoding='utf-8') as f:
    QUESTIONS = json.load(f)

# 分數板（記憶體暫存）
scoreboard = {}
# 題目答對者紀錄
solvers = {q['id']: [] for q in QUESTIONS}


@app.route('/')
def index():
    now = datetime.now(timezone.utc)
    ended = now > END_TIME
    name = session.get('name')  # 從 session 取得使用者名字
    return render_template('index.html', questions=QUESTIONS, ended=ended, name=name)


@app.route('/question/<qid>', methods=['GET', 'POST'])
def question(qid):
    now = datetime.now(timezone.utc)
    ended = now > END_TIME

    if 'name' not in session:
        return redirect(url_for('login'))

    question = next((q for q in QUESTIONS if q['id'] == qid), None)
    if not question:
        return "找不到這一題"

    if request.method == 'POST' and not ended:
        name = session['name']
        answer = request.form.get('flag', '').strip()
        correct = (answer == question['flag'])

        # 答對且之前沒答對過才加分
        if correct:
            scoreboard.setdefault(name, {'score': 0, 'correct': []})
            if qid not in scoreboard[name]['correct']:
                # 動態計分：先答的人分數高
                current_solver_count = len(solvers[qid])
                dynamic_points = max(10 - current_solver_count, 3)

                scoreboard[name]['score'] += dynamic_points
                scoreboard[name]['correct'].append(qid)
                solvers[qid].append(name)
        else:
            time.sleep(3)  # 錯誤延遲三秒
        
        # 顯示答題結果頁（不跳轉記分板）
        return render_template('result.html', correct=correct, question=question)

    return render_template('question.html', question=question, ended=ended)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            session['name'] = name
            return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/scoreboard')
def scoreboard_page():
    sorted_scores = sorted(scoreboard.items(), key=lambda x: x[1]['score'], reverse=True)
    return render_template('scoreboard.html', scores=sorted_scores, solvers=solvers, questions=QUESTIONS)


@app.route('/export')
def export_csv():
    now = datetime.now(timezone.utc)
    if now <= END_TIME:
        return "活動尚未結束，無法匯出紀錄。"

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['姓名', '分數', '答對題號'])
    for name, data in scoreboard.items():
        writer.writerow([name, data['score'], ', '.join(data['correct'])])

    si.seek(0)
    return send_file(
        StringIO(si.read()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='scoreboard.csv'
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
